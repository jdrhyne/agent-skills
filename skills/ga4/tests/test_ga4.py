#!/usr/bin/env python3
"""Deterministic offline tests for the GA4 skill."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import csv
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ga4_auth  # noqa: E402
import ga4_query  # noqa: E402


class Message:
    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)


class FakeFilter(Message):
    class StringFilter(Message):
        class MatchType:
            EXACT = "EXACT"
            CONTAINS = "CONTAINS"
            PARTIAL_REGEXP = "PARTIAL_REGEXP"


class FakeTypes:
    Filter = FakeFilter
    FilterExpression = Message
    FilterExpressionList = Message
    Dimension = Message
    Metric = Message
    DateRange = Message
    GetMetadataRequest = Message
    CheckCompatibilityRequest = Message
    RunReportRequest = Message


def quota(consumed: int = 1, remaining: int = 99):
    status = lambda: types.SimpleNamespace(consumed=consumed, remaining=remaining)
    return types.SimpleNamespace(**{name: status() for name in ga4_query.QUOTA_FIELDS})


def report_response(offset: int, count: int, total: int):
    rows = []
    for index in range(offset, offset + count):
        rows.append(
            types.SimpleNamespace(
                dimension_values=[types.SimpleNamespace(value=f"/page,{index}")],
                metric_values=[types.SimpleNamespace(value=str(index))],
            )
        )
    return types.SimpleNamespace(
        dimension_headers=[types.SimpleNamespace(name="pagePath")],
        metric_headers=[types.SimpleNamespace(name="keyEvents")],
        rows=rows,
        row_count=total,
        property_quota=quota(),
    )


def metadata_response():
    return types.SimpleNamespace(
        name="properties/123/metadata",
        dimensions=[types.SimpleNamespace(api_name="pagePath", ui_name="Page path", description="Path")],
        metrics=[types.SimpleNamespace(api_name="keyEvents", ui_name="Key events", description="Key event count")],
    )


def compatibility_response(dimension_status="COMPATIBLE", metric_status="COMPATIBLE"):
    return types.SimpleNamespace(
        dimension_compatibilities=[
            types.SimpleNamespace(
                dimension_metadata=types.SimpleNamespace(api_name="pagePath"),
                compatibility=types.SimpleNamespace(name=dimension_status),
            )
        ],
        metric_compatibilities=[
            types.SimpleNamespace(
                metric_metadata=types.SimpleNamespace(api_name="keyEvents"),
                compatibility=types.SimpleNamespace(name=metric_status),
            )
        ],
    )


def dimension_compatibility(name="pagePath", status="COMPATIBLE"):
    return types.SimpleNamespace(
        dimension_metadata=types.SimpleNamespace(api_name=name),
        compatibility=types.SimpleNamespace(name=status),
    )


def metric_compatibility(name="keyEvents", status="COMPATIBLE"):
    return types.SimpleNamespace(
        metric_metadata=types.SimpleNamespace(api_name=name),
        compatibility=types.SimpleNamespace(name=status),
    )


class FakeClient:
    def __init__(self, reports=None, compatibility=None, metadata=None):
        self.reports = list(reports or [])
        self.compatibility = compatibility or compatibility_response()
        self.metadata = metadata or metadata_response()
        self.report_requests = []
        self.compatibility_requests = []
        self.metadata_requests = []

    def run_report(self, *, request):
        self.report_requests.append(request)
        return self.reports.pop(0)

    def check_compatibility(self, *, request):
        self.compatibility_requests.append(request)
        return self.compatibility

    def get_metadata(self, *, request):
        self.metadata_requests.append(request)
        return self.metadata


class GA4Tests(unittest.TestCase):
    def test_property_names_dates_and_key_event_terminology(self) -> None:
        self.assertEqual(ga4_query.validate_property_id("123456"), "123456")
        for value in (None, "properties/123", "1;rm", "1" * 21):
            with self.subTest(value=value), self.assertRaises(ga4_query.QueryError):
                ga4_query.validate_property_id(value)
        self.assertEqual(ga4_query.parse_names("pagePath,country", "dimensions", 9), ["pagePath", "country"])
        self.assertEqual(ga4_query.parse_names("keyEvents", "metrics", 10), ["keyEvents"])
        with self.assertRaisesRegex(ga4_query.QueryError, "keyEvents"):
            ga4_query.parse_names("conversions", "metrics", 10)
        self.assertEqual(
            ga4_query.resolve_dates(None, None, today=date(2026, 8, 29)),
            ("2026-07-31", "2026-08-29"),
        )
        with self.assertRaises(ga4_query.QueryError):
            ga4_query.resolve_dates("2026-08-30", "2026-08-29", today=date(2026, 8, 29))

    def test_filter_grammar_and_not_expression_shape(self) -> None:
        specs = [
            ga4_query.parse_filter("pagePath!=/private", ["pagePath"]),
            ga4_query.parse_filter("pagePath=~^/blog/", ["pagePath"]),
        ]
        expression = ga4_query.build_filter_expression(specs, FakeTypes)
        self.assertTrue(hasattr(expression, "and_group"))
        negated = expression.and_group.expressions[0]
        self.assertTrue(hasattr(negated, "not_expression"))
        self.assertFalse(isinstance(negated.not_expression, bool))
        self.assertEqual(negated.not_expression.filter.field_name, "pagePath")
        self.assertEqual(negated.not_expression.filter.string_filter.match_type, "EXACT")
        self.assertEqual(expression.and_group.expressions[1].filter.string_filter.match_type, "PARTIAL_REGEXP")

        for invalid in ("pagePath==/x", "unknown=/x", " pagePath=/x", "pagePath", "pagePath=bad\nvalue"):
            with self.subTest(filter=invalid), self.assertRaises(ga4_query.QueryError):
                ga4_query.parse_filter(invalid, ["pagePath"])

    def test_metadata_and_compatibility_preflight(self) -> None:
        client = FakeClient()
        response = ga4_query.get_and_validate_metadata(
            client,
            FakeTypes,
            "123",
            ["pagePath"],
            ["keyEvents"],
            retries=0,
        )
        self.assertEqual(response.name, "properties/123/metadata")
        self.assertEqual(client.metadata_requests[0].name, "properties/123/metadata")
        result = ga4_query.check_compatibility(
            client,
            FakeTypes,
            "123",
            ["pagePath"],
            ["keyEvents"],
            None,
            retries=0,
        )
        self.assertEqual(result["metrics"]["keyEvents"], "COMPATIBLE")

        missing = FakeClient(
            metadata=types.SimpleNamespace(name="properties/123/metadata", dimensions=[], metrics=[])
        )
        with self.assertRaisesRegex(ga4_query.QueryError, "metadata preflight rejected"):
            ga4_query.get_and_validate_metadata(
                missing, FakeTypes, "123", ["pagePath"], ["keyEvents"], retries=0
            )
        incompatible = FakeClient(compatibility=compatibility_response(metric_status="INCOMPATIBLE"))
        with self.assertRaisesRegex(ga4_query.QueryError, "compatibility preflight rejected"):
            ga4_query.check_compatibility(
                incompatible,
                FakeTypes,
                "123",
                ["pagePath"],
                ["keyEvents"],
                None,
                retries=0,
            )

    def test_compatibility_response_requires_exact_unique_entries(self) -> None:
        valid_dimension = dimension_compatibility()
        valid_metric = metric_compatibility()
        cases = {
            "duplicate dimension same status": types.SimpleNamespace(
                dimension_compatibilities=[valid_dimension, dimension_compatibility()],
                metric_compatibilities=[valid_metric],
            ),
            "duplicate dimension conflicting status": types.SimpleNamespace(
                dimension_compatibilities=[valid_dimension, dimension_compatibility(status="INCOMPATIBLE")],
                metric_compatibilities=[valid_metric],
            ),
            "duplicate metric same status": types.SimpleNamespace(
                dimension_compatibilities=[valid_dimension],
                metric_compatibilities=[valid_metric, metric_compatibility()],
            ),
            "missing requested dimension": types.SimpleNamespace(
                dimension_compatibilities=[],
                metric_compatibilities=[valid_metric],
            ),
            "unexpected extra dimension": types.SimpleNamespace(
                dimension_compatibilities=[valid_dimension, dimension_compatibility(name="country")],
                metric_compatibilities=[valid_metric],
            ),
            "unexpected extra metric": types.SimpleNamespace(
                dimension_compatibilities=[valid_dimension],
                metric_compatibilities=[valid_metric, metric_compatibility(name="sessions")],
            ),
            "malformed dimension": types.SimpleNamespace(
                dimension_compatibilities=[types.SimpleNamespace()],
                metric_compatibilities=[valid_metric],
            ),
            "malformed metric status": types.SimpleNamespace(
                dimension_compatibilities=[valid_dimension],
                metric_compatibilities=[metric_compatibility(status="UNKNOWN")],
            ),
        }
        for label, response in cases.items():
            with self.subTest(label=label), self.assertRaises(ga4_query.QueryError):
                ga4_query.check_compatibility(
                    FakeClient(compatibility=response),
                    FakeTypes,
                    "123",
                    ["pagePath"],
                    ["keyEvents"],
                    None,
                    retries=0,
                )

    def test_metadata_api_names_are_nonempty_unique_and_all_entries_valid(self) -> None:
        valid_dimension = types.SimpleNamespace(api_name="pagePath", ui_name="Path", description="Path")
        valid_metric = types.SimpleNamespace(api_name="keyEvents", ui_name="Events", description="Events")
        cases = {
            "empty requested dimension": ([types.SimpleNamespace(api_name="")], [valid_metric]),
            "duplicate dimension": ([valid_dimension, valid_dimension], [valid_metric]),
            "malformed extra dimension": ([valid_dimension, types.SimpleNamespace(api_name=None)], [valid_metric]),
            "whitespace extra dimension": ([valid_dimension, types.SimpleNamespace(api_name=" ")], [valid_metric]),
            "empty requested metric": ([valid_dimension], [types.SimpleNamespace(api_name="")]),
            "duplicate metric": ([valid_dimension], [valid_metric, valid_metric]),
            "malformed extra metric": ([valid_dimension], [valid_metric, types.SimpleNamespace(api_name=42)]),
        }
        for label, (dimensions, metrics) in cases.items():
            response = types.SimpleNamespace(
                name="properties/123/metadata",
                dimensions=dimensions,
                metrics=metrics,
            )
            with self.subTest(label=label), self.assertRaises(ga4_query.QueryError):
                ga4_query.get_and_validate_metadata(
                    FakeClient(metadata=response),
                    FakeTypes,
                    "123",
                    ["pagePath"],
                    ["keyEvents"],
                    retries=0,
                )
            with self.subTest(label=f"format {label}"), self.assertRaises(ga4_query.QueryError):
                ga4_query.format_metadata(response, 100)

    def test_offset_pagination_is_bounded_and_reports_quota(self) -> None:
        client = FakeClient(reports=[report_response(0, 2, 5), report_response(2, 2, 5)])
        output = ga4_query.run_paginated_report(
            client,
            FakeTypes,
            property_id="123",
            dimensions=["pagePath"],
            metrics=["keyEvents"],
            start_date="2026-08-01",
            end_date="2026-08-29",
            filter_expression=None,
            page_size=2,
            max_pages=2,
            retries=0,
        )
        self.assertEqual([request.offset for request in client.report_requests], [0, 2])
        self.assertEqual([request.limit for request in client.report_requests], [2, 2])
        self.assertTrue(all(request.return_property_quota for request in client.report_requests))
        self.assertEqual(output["pagination"]["returned"], 4)
        self.assertEqual(output["pagination"]["row_count"], 5)
        self.assertTrue(output["pagination"]["partial"])
        self.assertEqual(output["pagination"]["next_offset"], 4)
        self.assertEqual(len(output["quota_by_page"]), 2)
        self.assertEqual(output["quota_by_page"][0]["property_quota"]["tokens_per_day"], {"consumed": 1, "remaining": 99})

        with self.assertRaises(ga4_query.QueryError):
            ga4_query.run_paginated_report(
                FakeClient(),
                FakeTypes,
                property_id="123",
                dimensions=["pagePath"],
                metrics=["keyEvents"],
                start_date="2026-08-01",
                end_date="2026-08-29",
                filter_expression=None,
                page_size=250_001,
                max_pages=1,
                retries=0,
            )

    def test_complete_pagination_and_malformed_quota_fail_closed(self) -> None:
        client = FakeClient(reports=[report_response(0, 1, 1)])
        output = ga4_query.run_paginated_report(
            client,
            FakeTypes,
            property_id="123",
            dimensions=["pagePath"],
            metrics=["keyEvents"],
            start_date="2026-08-01",
            end_date="2026-08-29",
            filter_expression=None,
            page_size=250_000,
            max_pages=5,
            retries=0,
        )
        self.assertFalse(output["pagination"]["partial"])
        malformed = report_response(0, 1, 1)
        malformed.property_quota.tokens_per_day.remaining = None
        with self.assertRaisesRegex(ga4_query.QueryError, "quota"):
            ga4_query.run_paginated_report(
                FakeClient(reports=[malformed]),
                FakeTypes,
                property_id="123",
                dimensions=["pagePath"],
                metrics=["keyEvents"],
                start_date="2026-08-01",
                end_date="2026-08-29",
                filter_expression=None,
                page_size=1,
                max_pages=1,
                retries=0,
            )

    def test_csv_writer_quotes_commas_quotes_and_newlines(self) -> None:
        rows = [
            {
                "dimensions": {"pagePath": '/path,"quoted"\nnext'},
                "metrics": {"keyEvents": "3"},
            }
        ]
        stream = io.StringIO()
        ga4_query.write_csv(rows, ["pagePath"], ["keyEvents"], stream)
        parsed = list(csv.reader(io.StringIO(stream.getvalue())))
        self.assertEqual(parsed, [["pagePath", "keyEvents"], ['/path,"quoted"\nnext', "3"]])
        self.assertIn('"/path,""quoted""', stream.getvalue())

    def test_transient_retries_are_bounded(self) -> None:
        class Retryable(Exception):
            status_code = 503

        attempts = [Retryable("provider secret"), "ok"]
        sleeps = []

        def call():
            value = attempts.pop(0)
            if isinstance(value, Exception):
                raise value
            return value

        self.assertEqual(ga4_query.call_with_retries(call, 1, sleeps.append), "ok")
        self.assertEqual(sleeps, [1])
        with self.assertRaisesRegex(ga4_query.QueryError, "request failed") as raised:
            ga4_query.call_with_retries(lambda: (_ for _ in ()).throw(ValueError("secret body")), 5)
        self.assertNotIn("secret body", str(raised.exception))

    def test_installed_app_flow_writes_private_token_without_secret_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            client_file = root / "client_secret.json"
            client_file.write_text(
                json.dumps(
                    {
                        "installed": {
                            "client_id": "client-id-marker",
                            "client_secret": "client-secret-marker",
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                        }
                    }
                ),
                encoding="utf-8",
            )
            client_file.chmod(0o600)
            token_file = root / "token.json"
            calls = {}

            class Credentials:
                def to_json(self):
                    return '{"refresh_token":"refresh-secret-marker"}'

            class Flow:
                @classmethod
                def from_client_secrets_file(cls, path, scopes):
                    calls["client_file"] = path
                    calls["scopes"] = scopes
                    return cls()

                def run_local_server(self, **kwargs):
                    calls["local_server"] = kwargs
                    return Credentials()

            package = types.ModuleType("google_auth_oauthlib")
            flow_module = types.ModuleType("google_auth_oauthlib.flow")
            flow_module.InstalledAppFlow = Flow
            stdout = io.StringIO()
            with mock.patch.dict(
                sys.modules,
                {"google_auth_oauthlib": package, "google_auth_oauthlib.flow": flow_module},
            ), redirect_stdout(stdout):
                result = ga4_auth.authorize(client_file, token_file, 0)
            self.assertEqual(result, token_file)
            self.assertEqual(calls["local_server"]["host"], "127.0.0.1")
            self.assertEqual(calls["local_server"]["port"], 0)
            self.assertTrue(calls["local_server"]["open_browser"])
            self.assertEqual(stat.S_IMODE(token_file.stat().st_mode), 0o600)
            self.assertNotIn("refresh-secret-marker", stdout.getvalue())

            source = Path(ga4_auth.__file__).read_text(encoding="utf-8")
            self.assertNotIn("run_console", source)
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = ga4_auth.main(["--client-secret", "secret-value-marker"])
            self.assertEqual(result, 1)
            self.assertNotIn("secret-value-marker", stderr.getvalue())
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = ga4_auth.main(["--code", "authorization-code-marker"])
            self.assertEqual(result, 1)
            self.assertNotIn("authorization-code-marker", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
