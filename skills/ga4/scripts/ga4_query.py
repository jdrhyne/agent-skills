#!/usr/bin/env python3
"""Bounded, read-only GA4 Data API reports with compatibility preflight."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import os
import re
import sys
import time
from typing import Any, Callable, Iterable, TextIO

from ga4_auth import AuthError, DEFAULT_TOKEN_FILE, load_stored_credentials


TRANSIENT_STATUS = {429, 500, 502, 503, 504}
TRANSIENT_CODES = {"DEADLINE_EXCEEDED", "INTERNAL", "RESOURCE_EXHAUSTED", "UNAVAILABLE"}
NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}\Z")
FILTER_RE = re.compile(r"([A-Za-z][A-Za-z0-9_.:-]{0,127})(!\*=|!=|!~|=~|\*=|=)(.+)\Z", re.DOTALL)
QUOTA_FIELDS = (
    "tokens_per_day",
    "tokens_per_hour",
    "concurrent_requests",
    "server_errors_per_project_per_hour",
    "potentially_thresholded_requests_per_hour",
    "tokens_per_project_per_hour",
)


class QueryError(RuntimeError):
    """Safe validation or provider-contract error."""


@dataclass(frozen=True)
class FilterSpec:
    field: str
    match_type: str
    value: str
    negate: bool


def bounded_int(minimum: int, maximum: int) -> Callable[[str], int]:
    def parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"must be an integer from {minimum} to {maximum}") from exc
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be from {minimum} to {maximum}")
        return parsed

    return parse


def validate_property_id(value: str | None) -> str:
    if not value or not re.fullmatch(r"[0-9]{1,20}", value):
        raise QueryError("GA4 property ID must contain 1 to 20 decimal digits")
    return value


def parse_names(value: str, label: str, maximum: int) -> list[str]:
    names = value.split(",")
    if not names or len(names) > maximum or any(not NAME_RE.fullmatch(name) for name in names):
        raise QueryError(f"{label} must contain 1 to {maximum} comma-separated API names")
    if len(set(names)) != len(names):
        raise QueryError(f"{label} must not contain duplicates")
    if label == "metrics" and "conversions" in names:
        raise QueryError("metric 'conversions' is obsolete terminology; use current keyEvents metrics")
    return names


def parse_iso_date(value: str, label: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise QueryError(f"{label} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise QueryError(f"{label} is not a valid calendar date") from exc


def resolve_dates(start: str | None, end: str | None, today: date | None = None) -> tuple[str, str]:
    current = today or datetime.now().date()
    start_date = parse_iso_date(start, "start") if start else current - timedelta(days=29)
    end_date = parse_iso_date(end, "end") if end else current
    if start_date > end_date:
        raise QueryError("start must be on or before end")
    if end_date > current:
        raise QueryError("end must not be in the future")
    return start_date.isoformat(), end_date.isoformat()


def parse_filter(value: str, selected_dimensions: Iterable[str]) -> FilterSpec:
    if len(value) > 4352 or any(ord(char) < 32 for char in value):
        raise QueryError("filter must be control-free and at most 4352 characters")
    match = FILTER_RE.fullmatch(value)
    if not match:
        raise QueryError("filter must use FIELD=VALUE, FIELD!=VALUE, FIELD*=VALUE, FIELD!*=VALUE, FIELD=~REGEX, or FIELD!~REGEX")
    field, operator, expression = match.groups()
    if operator == "=" and expression.startswith("="):
        raise QueryError("filter equality uses one '=' character")
    if field not in set(selected_dimensions):
        raise QueryError("filter field must be one of the requested dimensions")
    if not expression or len(expression) > 4096:
        raise QueryError("filter value must be from 1 to 4096 characters")
    match_type = {"=": "EXACT", "!=": "EXACT", "*=": "CONTAINS", "!*=": "CONTAINS", "=~": "PARTIAL_REGEXP", "!~": "PARTIAL_REGEXP"}[operator]
    return FilterSpec(field=field, match_type=match_type, value=expression, negate=operator.startswith("!"))


def import_api():
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta import types
    except ImportError as exc:
        raise QueryError("GA4 dependencies are not installed; use requirements.txt") from exc
    return BetaAnalyticsDataClient, types


def build_filter_expression(specs: list[FilterSpec], types: Any):
    expressions = []
    for spec in specs:
        match_type = getattr(types.Filter.StringFilter.MatchType, spec.match_type)
        leaf = types.FilterExpression(
            filter=types.Filter(
                field_name=spec.field,
                string_filter=types.Filter.StringFilter(
                    match_type=match_type,
                    value=spec.value,
                    case_sensitive=False,
                ),
            )
        )
        expressions.append(types.FilterExpression(not_expression=leaf) if spec.negate else leaf)
    if not expressions:
        return None
    if len(expressions) == 1:
        return expressions[0]
    return types.FilterExpression(and_group=types.FilterExpressionList(expressions=expressions))


def transient_status(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


def transient_code(exc: Exception) -> str | None:
    method = getattr(exc, "code", None)
    if not callable(method):
        return None
    try:
        code = method()
    except Exception:
        return None
    name = getattr(code, "name", None)
    return name if isinstance(name, str) else None


def call_with_retries(call: Callable[[], Any], retries: int, sleep: Callable[[float], None] = time.sleep) -> Any:
    for attempt in range(retries + 1):
        try:
            return call()
        except Exception as exc:
            retryable = (
                transient_status(exc) in TRANSIENT_STATUS
                or transient_code(exc) in TRANSIENT_CODES
                or isinstance(exc, (TimeoutError, ConnectionError))
            )
            if attempt < retries and retryable:
                sleep(min(2**attempt, 8))
                continue
            raise QueryError("Google Analytics Data API request failed") from None
    raise QueryError("Google Analytics Data API request failed")


def metadata_names(response: Any) -> tuple[set[str], set[str]]:
    dimensions = getattr(response, "dimensions", None)
    metrics = getattr(response, "metrics", None)
    if dimensions is None or metrics is None:
        raise QueryError("metadata response is malformed")

    def collect(entries: Any, label: str) -> set[str]:
        names: set[str] = set()
        try:
            iterator = iter(entries)
        except TypeError as exc:
            raise QueryError(f"metadata response {label} must be an array") from exc
        for item in iterator:
            name = getattr(item, "api_name", None)
            if not isinstance(name, str) or not NAME_RE.fullmatch(name):
                raise QueryError(f"metadata response contains a malformed {label} api_name")
            if name in names:
                raise QueryError(f"metadata response contains a duplicate {label} api_name")
            names.add(name)
        return names

    dimension_names = collect(dimensions, "dimension")
    metric_names = collect(metrics, "metric")
    return dimension_names, metric_names


def get_and_validate_metadata(client: Any, types: Any, property_id: str, dimensions: list[str], metrics: list[str], retries: int, sleep: Callable[[float], None] = time.sleep) -> Any:
    request = types.GetMetadataRequest(name=f"properties/{property_id}/metadata")
    response = call_with_retries(lambda: client.get_metadata(request=request), retries, sleep)
    available_dimensions, available_metrics = metadata_names(response)
    missing_dimensions = sorted(set(dimensions) - available_dimensions)
    missing_metrics = sorted(set(metrics) - available_metrics)
    if missing_dimensions or missing_metrics:
        raise QueryError(
            "metadata preflight rejected unavailable names: "
            + json.dumps({"dimensions": missing_dimensions, "metrics": missing_metrics}, separators=(",", ":"))
        )
    return response


def enum_name(value: Any) -> str:
    name = getattr(value, "name", None)
    return name if isinstance(name, str) else str(value).split(".")[-1]


def check_compatibility(client: Any, types: Any, property_id: str, dimensions: list[str], metrics: list[str], filter_expression: Any, retries: int, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    request = types.CheckCompatibilityRequest(
        property=f"properties/{property_id}",
        dimensions=[types.Dimension(name=name) for name in dimensions],
        metrics=[types.Metric(name=name) for name in metrics],
        dimension_filter=filter_expression,
    )
    response = call_with_retries(lambda: client.check_compatibility(request=request), retries, sleep)
    dimension_results = getattr(response, "dimension_compatibilities", None)
    metric_results = getattr(response, "metric_compatibilities", None)
    if dimension_results is None or metric_results is None:
        raise QueryError("compatibility response is malformed")

    def collect_statuses(entries: Any, metadata_field: str, label: str) -> dict[str, str]:
        statuses: dict[str, str] = {}
        try:
            iterator = iter(entries)
        except TypeError as exc:
            raise QueryError(f"compatibility response {label}s must be an array") from exc
        for item in iterator:
            metadata = getattr(item, metadata_field, None)
            name = getattr(metadata, "api_name", None)
            if not isinstance(name, str) or not name:
                raise QueryError(f"compatibility response contains a malformed {label}")
            if name in statuses:
                raise QueryError(f"compatibility response contains a duplicate {label}")
            status = enum_name(getattr(item, "compatibility", ""))
            if status not in {"COMPATIBILITY_UNSPECIFIED", "COMPATIBLE", "INCOMPATIBLE"}:
                raise QueryError(f"compatibility response contains a malformed {label} status")
            statuses[name] = status
        return statuses

    statuses = {
        "dimensions": collect_statuses(dimension_results, "dimension_metadata", "dimension"),
        "metrics": collect_statuses(metric_results, "metric_metadata", "metric"),
    }
    if set(statuses["dimensions"]) != set(dimensions) or set(statuses["metrics"]) != set(metrics):
        raise QueryError("compatibility response contains missing or unexpected names")
    incompatible = {
        category: sorted(name for name, status in values.items() if status != "COMPATIBLE")
        for category, values in statuses.items()
    }
    if incompatible["dimensions"] or incompatible["metrics"]:
        raise QueryError("compatibility preflight rejected the report: " + json.dumps(incompatible, separators=(",", ":")))
    return statuses


def quota_to_dict(quota: Any) -> dict[str, dict[str, int]]:
    if quota is None:
        raise QueryError("runReport omitted property quota despite returnPropertyQuota")
    result: dict[str, dict[str, int]] = {}
    for name in QUOTA_FIELDS:
        status = getattr(quota, name, None)
        consumed = getattr(status, "consumed", None)
        remaining = getattr(status, "remaining", None)
        if isinstance(consumed, bool) or isinstance(remaining, bool) or not isinstance(consumed, int) or not isinstance(remaining, int):
            raise QueryError(f"property quota field {name} is malformed")
        if consumed < 0 or remaining < 0:
            raise QueryError(f"property quota field {name} must be nonnegative")
        result[name] = {"consumed": consumed, "remaining": remaining}
    return result


def response_rows(response: Any, dimensions: list[str], metrics: list[str]) -> tuple[list[dict[str, dict[str, str]]], int]:
    dimension_headers = [getattr(item, "name", None) for item in getattr(response, "dimension_headers", [])]
    metric_headers = [getattr(item, "name", None) for item in getattr(response, "metric_headers", [])]
    if dimension_headers != dimensions or metric_headers != metrics:
        raise QueryError("runReport headers do not match the requested columns")
    row_count = getattr(response, "row_count", None)
    rows = getattr(response, "rows", None)
    if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0 or rows is None:
        raise QueryError("runReport response has invalid row_count or rows")
    result: list[dict[str, dict[str, str]]] = []
    for row in rows:
        dimension_values = getattr(row, "dimension_values", None)
        metric_values = getattr(row, "metric_values", None)
        if dimension_values is None or metric_values is None or len(dimension_values) != len(dimensions) or len(metric_values) != len(metrics):
            raise QueryError("runReport row does not match requested columns")
        dimension_data = [getattr(item, "value", None) for item in dimension_values]
        metric_data = [getattr(item, "value", None) for item in metric_values]
        if any(not isinstance(value, str) for value in dimension_data + metric_data):
            raise QueryError("runReport row contains a non-string value")
        result.append(
            {
                "dimensions": dict(zip(dimensions, dimension_data, strict=True)),
                "metrics": dict(zip(metrics, metric_data, strict=True)),
            }
        )
    return result, row_count


def run_paginated_report(
    client: Any,
    types: Any,
    *,
    property_id: str,
    dimensions: list[str],
    metrics: list[str],
    start_date: str,
    end_date: str,
    filter_expression: Any,
    page_size: int,
    max_pages: int,
    retries: int,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    if not 1 <= page_size <= 250_000:
        raise QueryError("page_size must be from 1 to 250000")
    if not 1 <= max_pages <= 20:
        raise QueryError("max_pages must be from 1 to 20")
    if not 0 <= retries <= 5:
        raise QueryError("retries must be from 0 to 5")
    rows: list[dict[str, dict[str, str]]] = []
    quotas: list[dict[str, Any]] = []
    pages = 0
    total_rows: int | None = None
    while pages < max_pages:
        offset = len(rows)
        request = types.RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[types.Dimension(name=name) for name in dimensions],
            metrics=[types.Metric(name=name) for name in metrics],
            date_ranges=[types.DateRange(start_date=start_date, end_date=end_date)],
            dimension_filter=filter_expression,
            offset=offset,
            limit=page_size,
            return_property_quota=True,
        )
        response = call_with_retries(lambda request=request: client.run_report(request=request), retries, sleep)
        page_rows, row_count = response_rows(response, dimensions, metrics)
        if len(page_rows) > page_size:
            raise QueryError("runReport returned more rows than requested")
        if total_rows is None:
            total_rows = row_count
        elif total_rows != row_count:
            raise QueryError("runReport row_count changed between pages")
        if offset + len(page_rows) > row_count:
            raise QueryError("runReport returned rows beyond row_count")
        quotas.append({"page": pages + 1, "property_quota": quota_to_dict(getattr(response, "property_quota", None))})
        rows.extend(page_rows)
        pages += 1
        if len(rows) >= row_count:
            break
        if not page_rows:
            raise QueryError("runReport returned an empty page before row_count was reached")
    total = 0 if total_rows is None else total_rows
    partial = len(rows) < total
    return {
        "pagination": {
            "pages": pages,
            "returned": len(rows),
            "row_count": total,
            "page_size": page_size,
            "max_pages": max_pages,
            "next_offset": len(rows) if partial else None,
            "has_more": partial,
            "partial": partial,
        },
        "quota_by_page": quotas,
        "rows": rows,
    }


def metadata_entry(item: Any) -> dict[str, Any]:
    api_name = getattr(item, "api_name", None)
    ui_name = getattr(item, "ui_name", None)
    description = getattr(item, "description", None)
    if not isinstance(api_name, str) or not NAME_RE.fullmatch(api_name) or not all(
        isinstance(value, str) for value in (ui_name, description)
    ):
        raise QueryError("metadata response contains a malformed entry")
    return {"api_name": api_name, "ui_name": ui_name, "description": description}


def format_metadata(response: Any, limit: int) -> dict[str, Any]:
    metadata_names(response)
    dimensions = [metadata_entry(item) for item in getattr(response, "dimensions", [])]
    metrics = [metadata_entry(item) for item in getattr(response, "metrics", [])]
    return {
        "name": getattr(response, "name", ""),
        "dimensions": dimensions[:limit],
        "metrics": metrics[:limit],
        "pagination": {
            "limit_per_kind": limit,
            "dimensions_returned": min(len(dimensions), limit),
            "dimensions_total": len(dimensions),
            "metrics_returned": min(len(metrics), limit),
            "metrics_total": len(metrics),
            "partial": len(dimensions) > limit or len(metrics) > limit,
        },
    }


def write_csv(rows: list[dict[str, dict[str, str]]], dimensions: list[str], metrics: list[str], stream: TextIO) -> None:
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(dimensions + metrics)
    for row in rows:
        writer.writerow([row["dimensions"][name] for name in dimensions] + [row["metrics"][name] for name in metrics])


def add_report_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--metrics", default="screenPageViews")
    parser.add_argument("--dimensions", default="pagePath")
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--filter", action="append", default=[])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only GA4 Data API helper", allow_abbrev=False)
    parser.add_argument("--property", default=os.environ.get("GA4_PROPERTY_ID"))
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_FILE), help="protected OAuth token JSON path")
    parser.add_argument("--retries", type=bounded_int(0, 5), default=3)
    subparsers = parser.add_subparsers(dest="command", required=True)
    metadata_parser = subparsers.add_parser("metadata", allow_abbrev=False)
    metadata_parser.add_argument("--limit", type=bounded_int(1, 1000), default=100)
    compatibility_parser = subparsers.add_parser("check-compatibility", allow_abbrev=False)
    add_report_args(compatibility_parser)
    report_parser = subparsers.add_parser("report", allow_abbrev=False)
    add_report_args(report_parser)
    report_parser.add_argument("--page-size", type=bounded_int(1, 250_000), default=10_000)
    report_parser.add_argument("--max-pages", type=bounded_int(1, 20), default=5)
    report_parser.add_argument("--format", choices=("json", "csv"), default="json")
    args = parser.parse_args(argv)

    try:
        property_id = validate_property_id(args.property)
        if args.command != "metadata":
            dimensions = parse_names(args.dimensions, "dimensions", 9)
            metrics = parse_names(args.metrics, "metrics", 10)
            start_date, end_date = resolve_dates(args.start, args.end)
            filter_specs = [parse_filter(value, dimensions) for value in args.filter]
        credentials = load_stored_credentials(args.token_file)
        client_class, types = import_api()
        client = client_class(credentials=credentials)
        if args.command == "metadata":
            response = call_with_retries(
                lambda: client.get_metadata(request=types.GetMetadataRequest(name=f"properties/{property_id}/metadata")),
                args.retries,
            )
            output = format_metadata(response, args.limit)
            print(json.dumps(output, indent=2, sort_keys=True))
            return 0

        filter_expression = build_filter_expression(filter_specs, types)
        get_and_validate_metadata(client, types, property_id, dimensions, metrics, args.retries)
        compatibility = check_compatibility(
            client, types, property_id, dimensions, metrics, filter_expression, args.retries
        )
        if args.command == "check-compatibility":
            print(json.dumps({"compatible": True, "compatibility": compatibility}, indent=2, sort_keys=True))
            return 0

        output = run_paginated_report(
            client,
            types,
            property_id=property_id,
            dimensions=dimensions,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date,
            filter_expression=filter_expression,
            page_size=args.page_size,
            max_pages=args.max_pages,
            retries=args.retries,
        )
        output["query"] = {
            "property": property_id,
            "dimensions": dimensions,
            "metrics": metrics,
            "start": start_date,
            "end": end_date,
            "filters": [spec.__dict__ for spec in filter_specs],
        }
        output["preflight"] = {"metadata": "validated", "compatibility": compatibility}
        if args.format == "csv":
            write_csv(output["rows"], dimensions, metrics, sys.stdout)
            csv_metadata = {key: output[key] for key in ("query", "preflight", "pagination", "quota_by_page")}
            print(json.dumps(csv_metadata, sort_keys=True), file=sys.stderr)
        else:
            print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (AuthError, QueryError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
