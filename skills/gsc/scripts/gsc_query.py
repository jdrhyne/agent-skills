#!/usr/bin/env python3
"""Bounded, read-only Google Search Console queries."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import json
import math
import re
import sys
import time
from typing import Any, Callable, Iterable
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

from gsc_auth import AuthError, DEFAULT_TOKEN_FILE, load_stored_credentials


PT = ZoneInfo("America/Los_Angeles")
DIMENSIONS = {"country", "date", "device", "hour", "page", "query", "searchAppearance"}
FILTER_DIMENSIONS = {"country", "device", "page", "query", "searchAppearance"}
FILTER_OPERATORS = {"contains", "equals", "notContains", "notEquals", "includingRegex", "excludingRegex"}
SEARCH_TYPES = {"discover", "googleNews", "news", "image", "video", "web"}
DATA_STATES = {"final", "all", "hourly_all"}
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
DOMAIN_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\Z"
)


class QueryError(RuntimeError):
    """Safe validation or provider-contract error."""


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


def validate_site(site: str) -> str:
    if not site or len(site) > 2048 or any(ord(char) < 32 for char in site):
        raise QueryError("site must be a nonempty Search Console property identifier")
    if site.startswith("sc-domain:"):
        domain = site.removeprefix("sc-domain:")
        if not DOMAIN_RE.fullmatch(domain):
            raise QueryError("domain properties must use sc-domain: followed by a valid ASCII domain")
        return site
    parsed = urlsplit(site)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise QueryError("site must be an http(s) URL-prefix property or sc-domain: property")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise QueryError("site URL must not contain credentials, a query, or a fragment")
    return site


def validate_inspection_url(site: str, value: str) -> str:
    if not value or len(value) > 2048 or any(ord(char) < 32 for char in value):
        raise QueryError("inspection URL must be nonempty and at most 2048 characters")
    if not urlsplit(value).scheme:
        if site.startswith("sc-domain:"):
            raise QueryError("relative inspection URLs cannot be used with a domain property")
        value = urljoin(site.rstrip("/") + "/", value.lstrip("/"))
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise QueryError("inspection URL must be an absolute http(s) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise QueryError("inspection URL must not contain credentials or a fragment")
    return value


def parse_iso_date(value: str, label: str) -> date:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise QueryError(f"{label} must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise QueryError(f"{label} is not a valid calendar date") from exc


def resolve_date_range(
    *, days: int | None, start_date: str | None, end_date: str | None, data_state: str, today: date | None = None
) -> tuple[str, str, int]:
    if data_state not in DATA_STATES:
        raise QueryError("data_state must be final, all, or hourly_all")
    if (start_date is None) != (end_date is None):
        raise QueryError("start_date and end_date must be supplied together")
    if start_date is not None:
        if days is not None:
            raise QueryError("days cannot be combined with explicit start_date/end_date")
        start = parse_iso_date(start_date, "start_date")
        end = parse_iso_date(end_date or "", "end_date")
        window_days = (end - start).days + 1
    else:
        window_days = 28 if days is None else days
        if not 1 <= window_days <= 480:
            raise QueryError("days must be from 1 to 480")
        current = today or datetime.now(PT).date()
        end = current - timedelta(days=3 if data_state == "final" else 0)
        start = end - timedelta(days=window_days - 1)
    if start > end:
        raise QueryError("start_date must be on or before end_date")
    current = today or datetime.now(PT).date()
    if end > current:
        raise QueryError("end_date must not be later than the current America/Los_Angeles date")
    if not 1 <= window_days <= 480:
        raise QueryError("date range must contain from 1 to 480 inclusive days")
    return start.isoformat(), end.isoformat(), window_days


def validate_dimensions(values: Iterable[str], data_state: str) -> list[str]:
    dimensions = list(values)
    if not dimensions or any(value not in DIMENSIONS for value in dimensions):
        raise QueryError(f"dimensions must be selected from: {', '.join(sorted(DIMENSIONS))}")
    if len(set(dimensions)) != len(dimensions):
        raise QueryError("dimensions must not contain duplicates")
    if data_state == "hourly_all" and "hour" not in dimensions:
        raise QueryError("hourly_all requires the hour dimension")
    return dimensions


def parse_filters(values: Iterable[str]) -> list[dict[str, str]]:
    filters: list[dict[str, str]] = []
    for value in values:
        parts = value.split(":", 2)
        if len(parts) != 3:
            raise QueryError("filters must use dimension:operator:expression")
        dimension, operator, expression = parts
        if dimension not in FILTER_DIMENSIONS:
            raise QueryError(f"filter dimension must be selected from: {', '.join(sorted(FILTER_DIMENSIONS))}")
        if operator not in FILTER_OPERATORS:
            raise QueryError(f"filter operator must be selected from: {', '.join(sorted(FILTER_OPERATORS))}")
        if not expression or len(expression) > 4096 or any(ord(char) < 32 for char in expression):
            raise QueryError("filter expression must be nonempty, control-free, and at most 4096 characters")
        if dimension == "device" and operator in {"equals", "notEquals"} and expression not in {"DESKTOP", "MOBILE", "TABLET"}:
            raise QueryError("exact device filters must use DESKTOP, MOBILE, or TABLET")
        if dimension == "country" and operator in {"equals", "notEquals"} and not re.fullmatch(r"[A-Z]{3}", expression):
            raise QueryError("exact country filters must use an uppercase ISO 3166-1 alpha-3 code")
        filters.append({"dimension": dimension, "operator": operator, "expression": expression})
    return filters


def transient_status(exc: Exception) -> int | None:
    response = getattr(exc, "resp", None)
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    code = getattr(exc, "status_code", None)
    return code if isinstance(code, int) else None


def execute_with_retries(
    request_factory: Callable[[], Any], retries: int, sleep: Callable[[float], None] = time.sleep
) -> dict[str, Any]:
    for attempt in range(retries + 1):
        try:
            result = request_factory().execute(num_retries=0)
            if not isinstance(result, dict):
                raise QueryError("Google API returned a non-object response")
            return result
        except QueryError:
            raise
        except Exception as exc:
            if attempt < retries and (transient_status(exc) in TRANSIENT_STATUS or isinstance(exc, (TimeoutError, ConnectionError))):
                sleep(min(2**attempt, 8))
                continue
            raise QueryError("Google API request failed") from None
    raise QueryError("Google API request failed")


def build_service(token_file: str):
    credentials = load_stored_credentials(token_file)
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise QueryError("Search Console dependencies are not installed; use requirements.txt") from exc
    return build("searchconsole", "v1", credentials=credentials, cache_discovery=False)


def validate_freshness_metadata(
    metadata: Any,
    dimensions: list[str],
    data_state: str,
) -> dict[str, str]:
    if not isinstance(metadata, dict):
        raise QueryError("Search Analytics metadata must be an object")
    if data_state not in DATA_STATES:
        raise QueryError("Search Analytics data_state is invalid")

    allowed_fields: set[str]
    if data_state == "final":
        allowed_fields = set()
    elif data_state == "all":
        allowed_fields = {"first_incomplete_date"} if "date" in dimensions else set()
    else:
        allowed_fields = {"first_incomplete_hour"}

    unexpected = set(metadata) - allowed_fields
    if unexpected:
        raise QueryError(
            f"Search Analytics metadata contradicts data_state {data_state} or requested dimensions"
        )

    incomplete_date = metadata.get("first_incomplete_date")
    if "first_incomplete_date" in metadata:
        if not isinstance(incomplete_date, str) or not incomplete_date:
            raise QueryError("first_incomplete_date must be a nonempty string")
        parse_iso_date(incomplete_date, "first_incomplete_date")

    incomplete_hour = metadata.get("first_incomplete_hour")
    if "first_incomplete_hour" in metadata:
        if not isinstance(incomplete_hour, str) or not incomplete_hour:
            raise QueryError("first_incomplete_hour must be a nonempty string")
        try:
            parsed_hour = datetime.fromisoformat(incomplete_hour.replace("Z", "+00:00"))
        except ValueError as exc:
            raise QueryError("first_incomplete_hour must be an ISO 8601 offset date-time") from exc
        if parsed_hour.tzinfo is None:
            raise QueryError("first_incomplete_hour must include an offset")
    return metadata


def validate_search_page(
    response: dict[str, Any],
    dimensions: list[str],
    data_state: str,
) -> list[dict[str, Any]]:
    rows = response.get("rows", [])
    if not isinstance(rows, list):
        raise QueryError("Search Analytics rows must be an array")
    for row in rows:
        if not isinstance(row, dict):
            raise QueryError("Search Analytics row must be an object")
        keys = row.get("keys")
        if not isinstance(keys, list) or len(keys) != len(dimensions) or any(not isinstance(key, str) for key in keys):
            raise QueryError("Search Analytics row keys do not match requested dimensions")
        for metric in ("clicks", "impressions", "ctr", "position"):
            value = row.get(metric)
            try:
                is_finite = math.isfinite(value) if isinstance(value, (int, float)) else False
            except OverflowError:
                is_finite = False
            if isinstance(value, bool) or not is_finite or value < 0:
                raise QueryError(f"Search Analytics row has invalid {metric}")
        if row["ctr"] > 1:
            raise QueryError("Search Analytics ctr must be from 0 through 1")
    validate_freshness_metadata(response.get("metadata", {}), dimensions, data_state)
    return rows


def query_search_analytics(
    service: Any,
    *,
    site: str,
    start_date: str,
    end_date: str,
    dimensions: list[str],
    search_type: str,
    data_state: str,
    filters: list[dict[str, str]],
    limit: int,
    page_size: int,
    max_pages: int,
    retries: int,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    site = validate_site(site)
    parse_iso_date(start_date, "start_date")
    parse_iso_date(end_date, "end_date")
    if start_date > end_date:
        raise QueryError("start_date must be on or before end_date")
    dimensions = validate_dimensions(dimensions, data_state)
    if search_type not in SEARCH_TYPES:
        raise QueryError(f"search_type must be selected from: {', '.join(sorted(SEARCH_TYPES))}")
    if not 1 <= limit <= 500_000:
        raise QueryError("limit must be from 1 to 500000")
    if not 1 <= page_size <= 25_000:
        raise QueryError("page_size must be from 1 to 25000")
    if not 1 <= max_pages <= 20:
        raise QueryError("max_pages must be from 1 to 20")

    base_body: dict[str, Any] = {
        "startDate": start_date,
        "endDate": end_date,
        "dimensions": dimensions,
        "type": search_type,
        "dataState": data_state,
    }
    if filters:
        base_body["dimensionFilterGroups"] = [{"groupType": "and", "filters": filters}]

    all_rows: list[dict[str, Any]] = []
    pages = 0
    start_row = 0
    has_more = False
    response_aggregation_type: str | None = None
    freshness: dict[str, str] = {"data_state": data_state, "time_zone": "America/Los_Angeles"}
    while pages < max_pages and len(all_rows) < limit:
        requested = min(page_size, limit - len(all_rows))
        body = {**base_body, "startRow": start_row, "rowLimit": requested}
        response = execute_with_retries(
            lambda body=body: service.searchanalytics().query(siteUrl=site, body=body), retries, sleep
        )
        page_rows = validate_search_page(response, dimensions, data_state)
        if len(page_rows) > requested:
            raise QueryError("Search Analytics returned more rows than requested")
        metadata = response.get("metadata", {})
        page_aggregation_type = response.get("responseAggregationType")
        if page_aggregation_type is not None:
            if page_aggregation_type not in {"auto", "byPage", "byProperty"}:
                raise QueryError("Search Analytics responseAggregationType is malformed")
            if response_aggregation_type is not None and response_aggregation_type != page_aggregation_type:
                raise QueryError("Search Analytics responseAggregationType changed between pages")
            response_aggregation_type = page_aggregation_type
        for name, value in metadata.items():
            if name in freshness and freshness[name] != value:
                raise QueryError("Search Analytics freshness metadata changed between pages")
            freshness[name] = value
        all_rows.extend(page_rows)
        pages += 1
        start_row += len(page_rows)
        if len(page_rows) < requested:
            has_more = False
            break
        has_more = True

    partial = has_more and (pages >= max_pages or len(all_rows) >= limit)
    return {
        "query": base_body,
        "freshness": freshness,
        "response_aggregation_type": response_aggregation_type,
        "pagination": {
            "pages": pages,
            "returned": len(all_rows),
            "limit": limit,
            "page_size": page_size,
            "max_pages": max_pages,
            "next_start_row": start_row if has_more else None,
            "has_more": has_more,
            "partial": partial,
            "provider_top_rows_only": True,
        },
        "rows": all_rows,
    }


def list_sites(service: Any, retries: int, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    response = execute_with_retries(lambda: service.sites().list(), retries, sleep)
    entries = response.get("siteEntry", [])
    if not isinstance(entries, list):
        raise QueryError("sites response must contain a siteEntry array")
    sites: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("siteUrl"), str) or not isinstance(entry.get("permissionLevel"), str):
            raise QueryError("sites response contains a malformed entry")
        sites.append({"siteUrl": validate_site(entry["siteUrl"]), "permissionLevel": entry["permissionLevel"]})
    return {"returned": len(sites), "sites": sites}


def list_sitemaps(service: Any, site: str, retries: int, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    site = validate_site(site)
    response = execute_with_retries(lambda: service.sitemaps().list(siteUrl=site), retries, sleep)
    entries = response.get("sitemap", [])
    if not isinstance(entries, list):
        raise QueryError("sitemaps response must contain a sitemap array")
    fields = ("path", "type", "lastSubmitted", "lastDownloaded", "isPending", "isSitemapsIndex", "warnings", "errors")
    sitemaps: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) or not entry["path"]:
            raise QueryError("sitemaps response contains a malformed entry")
        sitemaps.append({name: entry[name] for name in fields if name in entry})
    return {"site": site, "returned": len(sitemaps), "sitemaps": sitemaps}


def inspect_url(service: Any, site: str, url: str, retries: int, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    site = validate_site(site)
    inspection_url = validate_inspection_url(site, url)
    response = execute_with_retries(
        lambda: service.urlInspection().index().inspect(body={"inspectionUrl": inspection_url, "siteUrl": site}),
        retries,
        sleep,
    )
    result = response.get("inspectionResult")
    if not isinstance(result, dict):
        raise QueryError("URL Inspection response is missing inspectionResult")
    return {"site": site, "inspectionUrl": inspection_url, "inspectionResult": result}


def add_search_args(parser: argparse.ArgumentParser, dimensions: list[str] | None = None, default_limit: int = 1000) -> None:
    parser.add_argument("--site", required=True)
    parser.add_argument("--days", type=bounded_int(1, 480))
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--data-state", choices=sorted(DATA_STATES), default="final")
    if dimensions is None:
        parser.add_argument("--dimensions", nargs="+", default=["query", "page"])
    parser.set_defaults(fixed_dimensions=dimensions)
    parser.add_argument("--search-type", choices=sorted(SEARCH_TYPES), default="web")
    parser.add_argument("--filter", action="append", default=[], metavar="DIMENSION:OPERATOR:EXPRESSION")
    parser.add_argument("--limit", type=bounded_int(1, 500_000), default=default_limit)
    parser.add_argument("--page-size", type=bounded_int(1, 25_000), default=25_000)
    parser.add_argument("--max-pages", type=bounded_int(1, 20), default=5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only Google Search Console helper", allow_abbrev=False)
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_FILE), help="protected OAuth token JSON path")
    parser.add_argument("--retries", type=bounded_int(0, 5), default=3)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("sites", help="list accessible properties", allow_abbrev=False)
    add_search_args(subparsers.add_parser("search-analytics", allow_abbrev=False))
    add_search_args(subparsers.add_parser("top-queries", allow_abbrev=False), ["query"], 20)
    add_search_args(subparsers.add_parser("top-pages", allow_abbrev=False), ["page"], 20)
    add_search_args(subparsers.add_parser("query-page", allow_abbrev=False), ["query", "page"], 50)
    opportunities = subparsers.add_parser("opportunities", allow_abbrev=False)
    add_search_args(opportunities, ["query", "page"], 500)
    opportunities.add_argument("--min-impressions", type=bounded_int(1, 1_000_000_000), default=100)
    inspection = subparsers.add_parser("inspect-url", allow_abbrev=False)
    inspection.add_argument("--site", required=True)
    inspection.add_argument("--url", required=True)
    sitemap_parser = subparsers.add_parser("sitemaps", allow_abbrev=False)
    sitemap_parser.add_argument("--site", required=True)
    args = parser.parse_args(argv)

    try:
        if args.command in {"search-analytics", "top-queries", "top-pages", "query-page", "opportunities"}:
            validate_site(args.site)
            dimensions = args.fixed_dimensions or args.dimensions
            dimensions = validate_dimensions(dimensions, args.data_state)
            filters = parse_filters(args.filter)
            start_date, end_date, _ = resolve_date_range(
                days=args.days,
                start_date=args.start_date,
                end_date=args.end_date,
                data_state=args.data_state,
            )
        elif args.command == "sitemaps":
            validate_site(args.site)
        elif args.command == "inspect-url":
            validated_site = validate_site(args.site)
            validate_inspection_url(validated_site, args.url)
        service = build_service(args.token_file)
        if args.command == "sites":
            output = list_sites(service, args.retries)
        elif args.command == "sitemaps":
            output = list_sitemaps(service, args.site, args.retries)
        elif args.command == "inspect-url":
            output = inspect_url(service, args.site, args.url, args.retries)
        else:
            output = query_search_analytics(
                service,
                site=args.site,
                start_date=start_date,
                end_date=end_date,
                dimensions=dimensions,
                search_type=args.search_type,
                data_state=args.data_state,
                filters=filters,
                limit=args.limit,
                page_size=args.page_size,
                max_pages=args.max_pages,
                retries=args.retries,
            )
            if args.command == "opportunities":
                source_rows = output["rows"]
                output["rows"] = [
                    row for row in source_rows if row["impressions"] >= args.min_impressions and row["ctr"] < 0.03
                ]
                output["opportunity_filter"] = {"min_impressions": args.min_impressions, "max_ctr_exclusive": 0.03}
                output["opportunities_returned"] = len(output["rows"])
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except (AuthError, QueryError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
