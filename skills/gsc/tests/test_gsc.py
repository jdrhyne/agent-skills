#!/usr/bin/env python3
"""Deterministic offline tests for the Search Console skill."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import io
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import gsc_auth  # noqa: E402
import gsc_query  # noqa: E402


class FakeRequest:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.num_retries = None

    def execute(self, *, num_retries):
        self.num_retries = num_retries
        if self.error:
            raise self.error
        return self.result


class FakeSearchAnalytics:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def query(self, *, siteUrl, body):
        self.calls.append((siteUrl, body))
        return FakeRequest(self.responses.pop(0))


class FakeService:
    def __init__(self, responses):
        self.analytics = FakeSearchAnalytics(responses)

    def searchanalytics(self):
        return self.analytics


def row(key: str) -> dict[str, object]:
    return {"keys": [key], "clicks": 1, "impressions": 2, "ctr": 0.5, "position": 3.0}


class SearchConsoleTests(unittest.TestCase):
    def test_site_date_dimension_and_filter_validation(self) -> None:
        self.assertEqual(gsc_query.validate_site("sc-domain:example.com"), "sc-domain:example.com")
        self.assertEqual(gsc_query.validate_site("https://example.com/blog/"), "https://example.com/blog/")
        for invalid in ("example.com", "sc-domain:bad/path", "https://user:pass@example.com/"):
            with self.subTest(site=invalid), self.assertRaises(gsc_query.QueryError):
                gsc_query.validate_site(invalid)

        self.assertEqual(
            gsc_query.resolve_date_range(
                days=3,
                start_date=None,
                end_date=None,
                data_state="all",
                today=date(2026, 8, 29),
            ),
            ("2026-08-27", "2026-08-29", 3),
        )
        self.assertEqual(
            gsc_query.resolve_date_range(
                days=3,
                start_date=None,
                end_date=None,
                data_state="final",
                today=date(2026, 8, 29),
            ),
            ("2026-08-24", "2026-08-26", 3),
        )
        with self.assertRaises(gsc_query.QueryError):
            gsc_query.resolve_date_range(
                days=7,
                start_date="2026-08-01",
                end_date="2026-08-02",
                data_state="final",
            )
        with self.assertRaises(gsc_query.QueryError):
            gsc_query.validate_dimensions(["query"], "hourly_all")
        self.assertEqual(gsc_query.validate_dimensions(["hour", "query"], "hourly_all"), ["hour", "query"])

        filters = gsc_query.parse_filters(
            ["device:equals:MOBILE", "page:includingRegex:^https://example\\.com/"]
        )
        self.assertEqual(filters[0], {"dimension": "device", "operator": "equals", "expression": "MOBILE"})
        self.assertEqual(filters[1]["expression"], "^https://example\\.com/")
        for invalid_filter in ("page=bad", "device:equals:mobile", "date:equals:2026-01-01", "query:bad:value"):
            with self.subTest(filter=invalid_filter), self.assertRaises(gsc_query.QueryError):
                gsc_query.parse_filters([invalid_filter])

    def test_search_analytics_paginates_with_start_row_and_partial_metadata(self) -> None:
        metadata = {"first_incomplete_date": "2026-08-28"}
        service = FakeService(
            [
                {"rows": [row("2026-08-27"), row("2026-08-28")], "metadata": metadata},
                {"rows": [row("2026-08-29"), row("2026-08-30")], "metadata": metadata},
            ]
        )
        output = gsc_query.query_search_analytics(
            service,
            site="https://example.com/",
            start_date="2026-08-27",
            end_date="2026-08-29",
            dimensions=["date"],
            search_type="web",
            data_state="all",
            filters=[],
            limit=5,
            page_size=2,
            max_pages=2,
            retries=0,
        )
        self.assertEqual([call[1]["startRow"] for call in service.analytics.calls], [0, 2])
        self.assertEqual([call[1]["rowLimit"] for call in service.analytics.calls], [2, 2])
        self.assertTrue(output["pagination"]["partial"])
        self.assertTrue(output["pagination"]["has_more"])
        self.assertEqual(output["pagination"]["next_start_row"], 4)
        self.assertEqual(output["freshness"]["first_incomplete_date"], "2026-08-28")
        self.assertEqual(output["query"]["type"], "web")
        self.assertNotIn("searchType", output["query"])

    def test_search_analytics_terminal_page_and_hourly_freshness(self) -> None:
        service = FakeService(
            [
                {
                    "rows": [row("2026-08-29T08:00:00-07:00")],
                    "metadata": {"first_incomplete_hour": "2026-08-29T08:00:00-07:00"},
                }
            ]
        )
        output = gsc_query.query_search_analytics(
            service,
            site="sc-domain:example.com",
            start_date="2026-08-29",
            end_date="2026-08-29",
            dimensions=["hour"],
            search_type="googleNews",
            data_state="hourly_all",
            filters=gsc_query.parse_filters(["country:equals:USA"]),
            limit=100,
            page_size=25_000,
            max_pages=5,
            retries=0,
        )
        self.assertFalse(output["pagination"]["partial"])
        self.assertFalse(output["pagination"]["has_more"])
        self.assertEqual(service.analytics.calls[0][1]["rowLimit"], 100)
        self.assertEqual(output["freshness"]["first_incomplete_hour"], "2026-08-29T08:00:00-07:00")

    def test_limits_rows_and_freshness_fail_closed(self) -> None:
        service = FakeService([{"rows": [row("a")], "metadata": {"first_incomplete_date": None}}])
        with self.assertRaises(gsc_query.QueryError):
            gsc_query.query_search_analytics(
                service,
                site="https://example.com/",
                start_date="2026-08-01",
                end_date="2026-08-02",
                dimensions=["query"],
                search_type="web",
                data_state="all",
                filters=[],
                limit=1,
                page_size=25_001,
                max_pages=1,
                retries=0,
            )
        with self.assertRaises(gsc_query.QueryError):
            gsc_query.validate_search_page(
                {"rows": [{"keys": ["q"], "clicks": 1, "impressions": 2, "ctr": 2, "position": 1}]},
                ["query"],
                "final",
            )
        with self.assertRaises(gsc_query.QueryError):
            gsc_query.validate_search_page(
                {"rows": [row("q")], "metadata": {"first_incomplete_hour": "2026-08-29T12:00:00"}},
                ["hour"],
                "hourly_all",
            )

    def test_freshness_metadata_is_state_specific(self) -> None:
        self.assertEqual(gsc_query.validate_freshness_metadata({}, ["query"], "final"), {})
        self.assertEqual(
            gsc_query.validate_freshness_metadata(
                {"first_incomplete_date": "2026-08-28"}, ["date"], "all"
            ),
            {"first_incomplete_date": "2026-08-28"},
        )
        self.assertEqual(
            gsc_query.validate_freshness_metadata(
                {"first_incomplete_hour": "2026-08-29T08:00:00-07:00"}, ["hour"], "hourly_all"
            ),
            {"first_incomplete_hour": "2026-08-29T08:00:00-07:00"},
        )

        invalid_cases = (
            ("final date metadata", {"first_incomplete_date": "2026-08-28"}, ["date"], "final"),
            ("final hour metadata", {"first_incomplete_hour": "2026-08-29T08:00:00-07:00"}, ["hour"], "final"),
            ("all hour metadata", {"first_incomplete_hour": "2026-08-29T08:00:00-07:00"}, ["date"], "all"),
            ("all without date grouping", {"first_incomplete_date": "2026-08-28"}, ["query"], "all"),
            ("hourly date metadata", {"first_incomplete_date": "2026-08-28"}, ["hour"], "hourly_all"),
            (
                "both incomplete fields",
                {
                    "first_incomplete_date": "2026-08-28",
                    "first_incomplete_hour": "2026-08-29T08:00:00-07:00",
                },
                ["date"],
                "all",
            ),
            ("unknown metadata", {"unknown": "value"}, ["date"], "all"),
            ("null allowed field", {"first_incomplete_date": None}, ["date"], "all"),
        )
        for label, metadata, dimensions, data_state in invalid_cases:
            with self.subTest(label=label), self.assertRaises(gsc_query.QueryError):
                gsc_query.validate_freshness_metadata(metadata, dimensions, data_state)

    def test_search_analytics_metrics_must_be_finite(self) -> None:
        for metric in ("clicks", "impressions", "ctr", "position"):
            for invalid in (math.nan, math.inf, -math.inf):
                malformed = row("q")
                malformed[metric] = invalid
                with self.subTest(metric=metric, invalid=invalid), self.assertRaises(gsc_query.QueryError):
                    gsc_query.validate_search_page(
                        {"rows": [malformed]},
                        ["query"],
                        "final",
                    )

    def test_transient_retries_are_bounded_and_hide_provider_details(self) -> None:
        class Retryable(Exception):
            def __init__(self):
                self.resp = types.SimpleNamespace(status=429)

        attempts = [FakeRequest(error=Retryable()), FakeRequest(result={"ok": True})]
        sleeps = []
        result = gsc_query.execute_with_retries(lambda: attempts.pop(0), 1, sleeps.append)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(sleeps, [1])

        with self.assertRaisesRegex(gsc_query.QueryError, "Google API request failed") as raised:
            gsc_query.execute_with_retries(lambda: FakeRequest(error=ValueError("secret-provider-body")), 5, sleeps.append)
        self.assertNotIn("secret-provider-body", str(raised.exception))

    def test_auth_files_are_private_and_tokens_are_not_printed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            client = root / "client_secret.json"
            client.write_text(
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
            client.chmod(0o600)
            self.assertEqual(gsc_auth.validate_installed_client_file(client), client)
            token = root / "token.json"
            marker = '{"refresh_token":"refresh-secret-marker"}'
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                gsc_auth.write_private_token(token, marker)
            self.assertEqual(stat.S_IMODE(token.stat().st_mode), 0o600)
            self.assertEqual(token.read_text(encoding="utf-8"), marker)
            self.assertNotIn("refresh-secret-marker", stdout.getvalue())

            client.chmod(0o644)
            with self.assertRaises(gsc_auth.AuthError):
                gsc_auth.validate_installed_client_file(client)
            client.chmod(0o600)
            root.chmod(0o755)
            with self.assertRaises(gsc_auth.AuthError):
                gsc_auth.validate_installed_client_file(client)

    def test_auth_cli_has_no_secret_or_code_arguments_and_no_console_fallback(self) -> None:
        source = Path(gsc_auth.__file__).read_text(encoding="utf-8")
        self.assertNotIn("run_console", source)
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = gsc_auth.main(["--client-secret", "secret-value-marker"])
        self.assertEqual(result, 1)
        self.assertNotIn("secret-value-marker", stderr.getvalue())
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            result = gsc_auth.main(["--code", "authorization-code-marker"])
        self.assertEqual(result, 1)
        self.assertNotIn("authorization-code-marker", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
