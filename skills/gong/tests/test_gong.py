#!/usr/bin/env python3
"""Offline behavioral tests for the Gong helper."""

from __future__ import annotations

import json
import os
import signal
import stat
import subprocess
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gong.sh"
COMPANY_TIMEZONE = "Pacific/Kiritimati"


class GongHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.capture = self.root / "capture"
        self.capture.mkdir()
        self.tmp = self.root / "tmp"
        self.tmp.mkdir()
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.creds = self.root / "credentials.json"
        self.creds.write_text(
            json.dumps(
                {
                    "base_url": "https://us-example.api.gong.io",
                    "access_key": "access-secret-marker",
                    "secret_key": "secret-secret-marker",
                    "company_timezone": COMPANY_TIMEZONE,
                }
            ),
            encoding="utf-8",
        )
        self.creds.chmod(stat.S_IRUSR | stat.S_IWUSR)
        fake_curl = self.bin / "curl"
        fake_curl.write_text(
            textwrap.dedent(
                """\
                #!/usr/bin/env python3
                import json, os, pathlib, sys, time
                root = pathlib.Path(os.environ["MOCK_CAPTURE"])
                counter = root / "counter"
                index = int(counter.read_text() or "0") if counter.exists() else 0
                counter.write_text(str(index + 1))
                (root / f"args-{index}.json").write_text(json.dumps(sys.argv[1:]))
                (root / f"config-{index}.txt").write_text(sys.stdin.read())
                responses = json.loads(os.environ.get("MOCK_RESPONSES", "[]"))
                response = responses[index] if index < len(responses) else {}
                if index == int(os.environ.get("MOCK_BLOCK_AT", "-1")):
                    (root / "block-ready").write_text("ready")
                    time.sleep(60)
                if index == int(os.environ.get("MOCK_FAIL_AT", "-1")):
                    print(json.dumps(response))
                    raise SystemExit(22)
                print(json.dumps(response))
                """
            ),
            encoding="utf-8",
        )
        fake_curl.chmod(0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    @staticmethod
    def call_record(call_id: str, title: str = "Call") -> dict[str, object]:
        return {
            "metaData": {
                "id": call_id,
                "title": title,
                "started": "2026-08-28T15:00:00Z",
                "duration": 60,
                "url": f"https://app.gong.io/call?id={call_id}",
            }
        }

    @staticmethod
    def basic_call(call_id: str, title: str = "Call") -> dict[str, object]:
        return {
            "id": call_id,
            "title": title,
            "started": "2026-08-28T15:00:00Z",
            "duration": 60,
            "url": f"https://app.gong.io/call?id={call_id}",
        }

    @staticmethod
    def stat_record(user_id: str, count: int) -> dict[str, object]:
        return {
            "userId": user_id,
            "userEmailAddress": f"user-{user_id}@example.com",
            "userAggregateActivityStats": {"callsAsHost": count},
        }

    @staticmethod
    def stats_records(
        days: int = 30,
        cursor: object = None,
        timezone_name: str = COMPANY_TIMEZONE,
    ) -> dict[str, object]:
        zone = ZoneInfo(timezone_name)
        to_date = datetime.now(zone).date()
        from_date = to_date - timedelta(days=days)
        from_datetime = datetime(
            from_date.year,
            from_date.month,
            from_date.day,
            tzinfo=zone,
        ).isoformat()
        to_datetime = datetime(
            to_date.year,
            to_date.month,
            to_date.day,
            tzinfo=zone,
        ).isoformat()
        return {
            "cursor": cursor,
            "timeZone": timezone_name,
            "fromDateTime": from_datetime,
            "toDateTime": to_datetime,
        }

    @staticmethod
    def records_as_utc(records: dict[str, object]) -> dict[str, object]:
        converted = dict(records)
        for field in ("fromDateTime", "toDateTime"):
            value = converted[field]
            assert isinstance(value, str)
            converted[field] = (
                datetime.fromisoformat(value)
                .astimezone(ZoneInfo("UTC"))
                .isoformat()
                .replace("+00:00", "Z")
            )
        return converted

    def helper_env(
        self,
        responses: list[object] | None = None,
        fail_at: int | None = None,
        block_at: int | None = None,
    ) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                "GONG_CREDS": str(self.creds),
                "MOCK_CAPTURE": str(self.capture),
                "MOCK_RESPONSES": json.dumps(responses or []),
                "PATH": f"{self.bin}:{env['PATH']}",
                "TMPDIR": str(self.tmp),
            }
        )
        if fail_at is not None:
            env["MOCK_FAIL_AT"] = str(fail_at)
        if block_at is not None:
            env["MOCK_BLOCK_AT"] = str(block_at)
        return env

    def run_helper(
        self,
        *args: str,
        responses: list[object] | None = None,
        fail_at: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = self.helper_env(responses=responses, fail_at=fail_at)
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_credentials_stay_out_of_argv_and_output(self) -> None:
        result = self.run_helper("test", responses=[{"records": {}, "users": []}])
        self.assertEqual(result.returncode, 0, result.stderr)
        args = (self.capture / "args-0.json").read_text(encoding="utf-8")
        config = (self.capture / "config-0.txt").read_text(encoding="utf-8")
        self.assertNotIn("access-secret-marker", args + result.stdout + result.stderr)
        self.assertNotIn("secret-secret-marker", args + result.stdout + result.stderr)
        self.assertIn("access-secret-marker", config)
        self.assertIn("secret-secret-marker", config)
        self.assertIn("--fail-with-body", args)
        self.assertIn("--retry", args)
        self.assertIn('"3"', args)
        self.assertIn("--retry-max-time", args)
        output = json.loads(result.stdout)
        self.assertIn("first_page_user_count", output)
        self.assertNotIn("user_count", output)

    def test_rejects_broad_credential_permissions(self) -> None:
        self.creds.chmod(0o644)
        result = self.run_helper("test")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mode 0600", result.stderr)
        self.assertFalse((self.capture / "counter").exists())

    def test_rejects_wrong_owner_and_broad_parent_permissions(self) -> None:
        fake_id = self.bin / "id"
        fake_id.write_text("#!/usr/bin/env sh\nprintf '%s\\n' 999999\n", encoding="utf-8")
        fake_id.chmod(0o755)
        wrong_owner = self.run_helper("test")
        self.assertNotEqual(wrong_owner.returncode, 0)
        self.assertIn("owned by the current user", wrong_owner.stderr)
        self.assertFalse((self.capture / "counter").exists())
        fake_id.unlink()

        self.root.chmod(0o755)
        broad_parent = self.run_helper("test")
        self.assertNotEqual(broad_parent.returncode, 0)
        self.assertIn("reject group and other access", broad_parent.stderr)
        self.assertFalse((self.capture / "counter").exists())
        self.root.chmod(0o700)

    def test_help_does_not_require_credentials(self) -> None:
        self.creds.unlink()
        result = self.run_helper("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Gong read-only helper", result.stdout)
        self.assertFalse((self.capture / "counter").exists())

    def test_rejects_invalid_tenant_days_and_call_id(self) -> None:
        data = json.loads(self.creds.read_text(encoding="utf-8"))
        data["base_url"] = "https://example.com"
        self.creds.write_text(json.dumps(data), encoding="utf-8")
        self.creds.chmod(0o600)
        self.assertNotEqual(self.run_helper("test").returncode, 0)

        data["base_url"] = "https://us-example.api.gong.io"
        self.creds.write_text(json.dumps(data), encoding="utf-8")
        self.creds.chmod(0o600)
        self.assertNotEqual(self.run_helper("calls", "0").returncode, 0)
        self.assertNotEqual(self.run_helper("call", "1;whoami").returncode, 0)
        self.assertNotEqual(self.run_helper("call", "123456789012345678901").returncode, 0)

    def test_calls_rejects_extra_arguments_before_api_access(self) -> None:
        result = self.run_helper("calls", "7", "5", "unexpected")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage: gong.sh calls [days] [max_pages]", result.stderr)
        self.assertFalse((self.capture / "counter").exists())

    def test_users_follow_cursor_and_report_page_bound(self) -> None:
        responses = [
            {
                "records": {"cursor": "next-user-page"},
                "users": [{"id": "1", "firstName": "One", "lastName": "User", "active": True}],
            },
            {
                "records": {"cursor": None},
                "users": [{"id": "2", "firstName": "Two", "lastName": "User", "active": False}],
            },
        ]
        result = self.run_helper("users", "5", responses=responses)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 2)
        self.assertEqual(output["returned"], 2)
        self.assertFalse(output["has_more"])
        second_args = json.loads((self.capture / "args-1.json").read_text(encoding="utf-8"))
        self.assertIn("--data-urlencode", second_args)
        self.assertIn("cursor=next-user-page", second_args)

    def test_users_report_when_page_bound_leaves_more_data(self) -> None:
        response = {
            "records": {"cursor": "next-user-page"},
            "users": [{"id": "1", "firstName": "One", "lastName": "User", "active": True}],
        }
        result = self.run_helper("users", "1", responses=[response])
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 1)
        self.assertEqual(output["returned"], 1)
        self.assertTrue(output["has_more"])

    def test_api_and_jq_failures_remove_temporary_results(self) -> None:
        first_page = {
            "records": {"cursor": "next-page"},
            "calls": [self.call_record("1", "One")],
        }
        api_failure = self.run_helper("calls", "7", "5", responses=[first_page, {}], fail_at=1)
        self.assertNotEqual(api_failure.returncode, 0)
        self.assertEqual(list(self.tmp.iterdir()), [])

        self.capture.joinpath("counter").unlink()
        malformed = self.run_helper("users", responses=[{"users": "not-an-array"}])
        self.assertNotEqual(malformed.returncode, 0)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_all_user_call_and_probe_cursors_reject_non_strings(self) -> None:
        cases = [
            (
                ("users",),
                {"records": {"cursor": 123}, "users": []},
                "malformed users cursor",
            ),
            (
                ("calls",),
                {"records": {"cursor": 123}, "calls": []},
                "malformed calls cursor",
            ),
            (
                ("test",),
                {"records": {"cursor": 123}, "users": []},
                "malformed users cursor",
            ),
        ]
        for index, (args, response, error) in enumerate(cases):
            with self.subTest(command=args[0]):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper(*args, responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)
                self.assertEqual(list(self.tmp.iterdir()), [])

    def test_cursor_rejects_empty_oversized_and_line_break_values(self) -> None:
        cases = [
            (("users",), {"records": {"cursor": ""}, "users": []}, "malformed users cursor"),
            (
                ("calls",),
                {"records": {"cursor": "x" * 4097}, "calls": []},
                "malformed calls cursor",
            ),
            (
                ("test",),
                {"records": {"cursor": "bad\ncursor"}, "users": []},
                "malformed users cursor",
            ),
        ]
        for index, (args, response, error) in enumerate(cases):
            with self.subTest(command=args[0]):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper(*args, responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)
                self.assertEqual(list(self.tmp.iterdir()), [])

    def test_all_user_call_and_probe_paths_reject_missing_records(self) -> None:
        cases = [
            (("users",), {"users": []}, "malformed users cursor"),
            (("calls",), {"calls": []}, "malformed calls cursor"),
            (("test",), {"users": []}, "malformed users cursor"),
        ]
        for index, (args, response, error) in enumerate(cases):
            with self.subTest(command=args[0]):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper(*args, responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)
                self.assertEqual(list(self.tmp.iterdir()), [])

    def test_sigterm_during_api_call_removes_registered_temp(self) -> None:
        env = self.helper_env(
            responses=[{"records": {}, "users": []}],
            block_at=0,
        )
        process = subprocess.Popen(
            ["bash", str(SCRIPT), "users"],
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            deadline = time.monotonic() + 5
            while not self.capture.joinpath("block-ready").exists():
                if process.poll() is not None:
                    self.fail("Gong helper exited before the fake API call blocked")
                if time.monotonic() >= deadline:
                    self.fail("Timed out waiting for the fake API call to block")
                time.sleep(0.02)

            files_during_call = list(self.tmp.iterdir())
            self.assertEqual(len(files_during_call), 1)
            self.assertEqual(stat.S_IMODE(files_during_call[0].stat().st_mode), 0o600)
            os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(list(self.tmp.iterdir()), [])
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate(timeout=5)

    def test_calls_follow_cursor_and_report_page_bound(self) -> None:
        responses = [
            {
                "records": {"cursor": "next-page"},
                "calls": [self.call_record("1", "One")],
            },
            {
                "records": {},
                "calls": [self.call_record("2", "Two")],
            },
        ]
        result = self.run_helper("calls", "7", "5", responses=responses)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 2)
        self.assertEqual(output["returned"], 2)
        self.assertFalse(output["has_more"])
        self.assertEqual((self.capture / "counter").read_text(), "2")
        second_args = (self.capture / "args-1.json").read_text(encoding="utf-8")
        self.assertIn("next-page", second_args)

    def test_calls_report_when_page_bound_leaves_more_data(self) -> None:
        response = {
            "records": {"cursor": "next-page"},
            "calls": [self.call_record("1", "One")],
        }
        result = self.run_helper("calls", "7", "1", responses=[response])
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 1)
        self.assertTrue(output["has_more"])

    def test_stats_follow_top_level_cursor_and_report_results(self) -> None:
        responses = [
            {
                "records": self.stats_records(cursor="next-stats-page"),
                "usersAggregateActivityStats": [self.stat_record("1", 3)],
            },
            {
                "records": self.stats_records(),
                "usersAggregateActivityStats": [self.stat_record("2", 4)],
            },
        ]
        result = self.run_helper("stats", "30", "5", responses=responses)
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 2)
        self.assertEqual(output["returned"], 2)
        self.assertFalse(output["has_more"])
        self.assertEqual(
            output["usersAggregateActivityStats"],
            [self.stat_record("1", 3), self.stat_record("2", 4)],
        )
        first_args = json.loads((self.capture / "args-0.json").read_text(encoding="utf-8"))
        first_body = json.loads(first_args[first_args.index("--data-binary") + 1])
        today = datetime.now(ZoneInfo(COMPANY_TIMEZONE)).date()
        from_date = (today - timedelta(days=30)).isoformat()
        to_date = today.isoformat()
        self.assertEqual(
            first_body,
            {
                "filter": {
                    "fromDate": from_date,
                    "toDate": to_date,
                }
            },
        )
        self.assertEqual(
            output["range"],
            {
                "fromDate": from_date,
                "toDate": to_date,
                "toDateExclusive": True,
                "timeZone": COMPANY_TIMEZONE,
                "fromDateTime": responses[0]["records"]["fromDateTime"],
                "toDateTime": responses[0]["records"]["toDateTime"],
            },
        )
        second_args = json.loads((self.capture / "args-1.json").read_text(encoding="utf-8"))
        body = second_args[second_args.index("--data-binary") + 1]
        self.assertEqual(json.loads(body)["cursor"], "next-stats-page")

    def test_stats_report_when_page_bound_leaves_more_data(self) -> None:
        response = {
            "records": self.stats_records(cursor="next-stats-page"),
            "usersAggregateActivityStats": [self.stat_record("1", 3)],
        }
        result = self.run_helper("stats", "30", "1", responses=[response])
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 1)
        self.assertEqual(output["returned"], 1)
        self.assertTrue(output["has_more"])

    def test_stats_accepts_equivalent_offset_and_utc_midnight_provenance(self) -> None:
        offset_records = self.stats_records(cursor="next-stats-page")
        utc_records = self.records_as_utc(self.stats_records())
        result = self.run_helper(
            "stats",
            responses=[
                {
                    "records": offset_records,
                    "usersAggregateActivityStats": [self.stat_record("1", 3)],
                },
                {
                    "records": utc_records,
                    "usersAggregateActivityStats": [self.stat_record("2", 4)],
                },
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["pages"], 2)
        self.assertEqual(output["returned"], 2)
        self.assertEqual(output["range"]["fromDateTime"], offset_records["fromDateTime"])
        self.assertEqual(output["range"]["toDateTime"], offset_records["toDateTime"])

    def test_stats_reject_malformed_array_and_cursor_with_cleanup(self) -> None:
        malformed_array = self.run_helper(
            "stats",
            responses=[
                {
                    "records": self.stats_records(),
                    "usersAggregateActivityStats": "not-an-array",
                }
            ],
        )
        self.assertNotEqual(malformed_array.returncode, 0)
        self.assertIn("malformed activity statistics response", malformed_array.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

        self.capture.joinpath("counter").unlink()
        malformed_cursor = self.run_helper(
            "stats",
            responses=[
                {
                    "records": self.stats_records(cursor=123),
                    "usersAggregateActivityStats": [],
                }
            ],
        )
        self.assertNotEqual(malformed_cursor.returncode, 0)
        self.assertIn("malformed activity statistics cursor", malformed_cursor.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

        self.capture.joinpath("counter").unlink()
        missing_records = self.run_helper(
            "stats",
            responses=[{"usersAggregateActivityStats": []}],
        )
        self.assertNotEqual(missing_records.returncode, 0)
        self.assertIn("malformed or mismatched activity statistics provenance", missing_records.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_stats_api_failure_removes_temporary_results(self) -> None:
        first_page = {
            "records": self.stats_records(cursor="next-stats-page"),
            "usersAggregateActivityStats": [self.stat_record("1", 3)],
        }
        result = self.run_helper("stats", "30", "5", responses=[first_page, {}], fail_at=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("activity statistics API request failed", result.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_company_timezone_is_optional_except_for_stats_and_validated_before_api(self) -> None:
        data = json.loads(self.creds.read_text(encoding="utf-8"))
        del data["company_timezone"]
        self.creds.write_text(json.dumps(data), encoding="utf-8")
        self.creds.chmod(0o600)

        probe = self.run_helper("test", responses=[{"records": {}, "users": []}])
        self.assertEqual(probe.returncode, 0, probe.stderr)
        self.capture.joinpath("counter").unlink()

        missing = self.run_helper("stats")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("company_timezone is required for stats", missing.stderr)
        self.assertFalse((self.capture / "counter").exists())
        self.assertEqual(list(self.tmp.iterdir()), [])

        data["company_timezone"] = "Mars/Olympus_Mons"
        self.creds.write_text(json.dumps(data), encoding="utf-8")
        self.creds.chmod(0o600)
        invalid = self.run_helper("stats")
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("not available through Python zoneinfo", invalid.stderr)
        self.assertFalse((self.capture / "counter").exists())
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_stats_rejects_mismatched_or_malformed_range_provenance(self) -> None:
        base_records = self.stats_records()
        noon_start = str(base_records["fromDateTime"]).replace("T00:00:00", "T12:00:00")
        shifted_end = (
            datetime.fromisoformat(str(base_records["toDateTime"]))
            + timedelta(minutes=1)
        ).isoformat()
        cases = [
            {**base_records, "timeZone": "America/Los_Angeles"},
            {**base_records, "timeZone": ""},
            {**base_records, "fromDateTime": None},
            {**base_records, "toDateTime": "not-a-date-time"},
            {**base_records, "fromDateTime": noon_start},
            {**base_records, "toDateTime": shifted_end},
            {
                **base_records,
                "fromDateTime": base_records["toDateTime"],
            },
        ]
        for index, records in enumerate(cases):
            with self.subTest(records=records):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper(
                    "stats",
                    responses=[
                        {
                            "records": records,
                            "usersAggregateActivityStats": [self.stat_record("1", 3)],
                        }
                    ],
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "malformed or mismatched activity statistics provenance",
                    result.stderr,
                )
                self.assertEqual(result.stdout, "")
                self.assertEqual(list(self.tmp.iterdir()), [])

    def test_stats_rejects_range_provenance_changes_between_pages(self) -> None:
        first_records = self.stats_records(cursor="next-stats-page")
        second_records = self.stats_records()
        second_records["fromDateTime"] = second_records["toDateTime"]
        result = self.run_helper(
            "stats",
            responses=[
                {
                    "records": first_records,
                    "usersAggregateActivityStats": [self.stat_record("1", 3)],
                },
                {
                    "records": second_records,
                    "usersAggregateActivityStats": [self.stat_record("2", 4)],
                },
            ],
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("malformed or mismatched activity statistics provenance", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_collection_records_and_emitted_fields_fail_closed(self) -> None:
        valid_user = {"id": "1", "firstName": "One", "lastName": "User", "active": True}
        malformed_cases: list[tuple[tuple[str, ...], dict[str, object], str]] = [
            (("users",), {"records": {}, "users": [None]}, "malformed users response"),
            (
                ("users",),
                {"records": {}, "users": [{**valid_user, "id": None}]},
                "malformed users response",
            ),
            (
                ("users",),
                {"records": {}, "users": [{key: value for key, value in valid_user.items() if key != "lastName"}]},
                "malformed users response",
            ),
            (
                ("users",),
                {"records": {}, "users": [{**valid_user, "active": "true"}]},
                "malformed users response",
            ),
            (("calls",), {"records": {}, "calls": [None]}, "malformed calls response"),
            (("calls",), {"records": {}, "calls": [{"metaData": {}}]}, "malformed calls response"),
            (
                ("calls",),
                {"records": {}, "calls": [{"metaData": {**self.call_record("1")["metaData"], "title": None}}]},
                "malformed calls response",
            ),
            (
                ("calls",),
                {"records": {}, "calls": [{"metaData": {**self.call_record("1")["metaData"], "duration": "60"}}]},
                "malformed calls response",
            ),
            (
                ("stats",),
                {
                    "records": self.stats_records(),
                    "usersAggregateActivityStats": [None],
                },
                "malformed activity statistics response",
            ),
            (
                ("stats",),
                {
                    "records": self.stats_records(),
                    "usersAggregateActivityStats": [
                        {
                            **self.stat_record("1", 3),
                            "userAggregateActivityStats": {"callsAsHost": None},
                        }
                    ],
                },
                "malformed activity statistics response",
            ),
            (
                ("stats",),
                {
                    "records": self.stats_records(),
                    "usersAggregateActivityStats": [
                        {"userId": "1", "userEmailAddress": "u@example.com", "callsAsHost": 3}
                    ],
                },
                "malformed activity statistics response",
            ),
            (
                ("stats",),
                {
                    "records": self.stats_records(),
                    "usersAggregateActivityStats": [
                        {
                            "userId": "1",
                            "userEmailAddress": "u@example.com",
                            "userAggregateActivityStats": {"callsAsHost": -1},
                        }
                    ],
                },
                "malformed activity statistics response",
            ),
            (
                ("stats",),
                {
                    "records": self.stats_records(),
                    "usersAggregateActivityStats": [
                        {
                            "userId": "1",
                            "userEmailAddress": "u@example.com",
                            "userAggregateActivityStats": {"callsAsHost": 1.5},
                        }
                    ],
                },
                "malformed activity statistics response",
            ),
        ]
        for index, (args, response, error) in enumerate(malformed_cases):
            with self.subTest(command=args[0], response=response):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper(*args, responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(error, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertEqual(list(self.tmp.iterdir()), [])

    def test_exact_call_and_transcript_nested_fields_fail_closed(self) -> None:
        malformed_calls = []
        for field, value in (
            ("title", None),
            ("started", None),
            ("duration", "60"),
            ("url", None),
        ):
            malformed_calls.append({"call": {**self.basic_call("123"), field: value}})

        for index, response in enumerate(malformed_calls):
            with self.subTest(call=response):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper("call", "123", responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no single exact call object", result.stderr)
                self.assertEqual(result.stdout, "")

        malformed_transcripts = [
            {"callId": "123", "transcript": [None]},
            {"callId": "123", "transcript": [{"speakerId": None, "sentences": []}]},
            {"callId": "123", "transcript": [{"speakerId": "s1", "sentences": None}]},
            {"callId": "123", "transcript": [{"speakerId": "s1", "sentences": [None]}]},
            {
                "callId": "123",
                "transcript": [{"speakerId": "s1", "sentences": [{"text": 123}]}],
            },
        ]
        for response in malformed_transcripts:
            with self.subTest(transcript=response):
                self.capture.joinpath("counter").unlink()
                result = self.run_helper(
                    "transcript",
                    "123",
                    responses=[{"callTranscripts": [response]}],
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no single exact transcript object", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_transcript_is_bounded_without_raw_fallback(self) -> None:
        response = {
            "callTranscripts": [
                {
                    "callId": "123",
                    "transcript": [
                        {
                            "speakerId": "speaker-1",
                            "sentences": [{"text": "one"}, {"text": "two"}, {"text": "three"}],
                        }
                    ]
                }
            ]
        }
        result = self.run_helper("transcript", "123", "2", responses=[response])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip().splitlines(), ["speaker-1: one", "speaker-1: two"])

    def test_call_requires_exact_provider_resource_identity(self) -> None:
        valid = self.run_helper(
            "call",
            "123",
            responses=[{"call": self.basic_call("123", "Exact")}],
        )
        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertEqual(json.loads(valid.stdout)["id"], "123")
        valid_args = json.loads((self.capture / "args-0.json").read_text(encoding="utf-8"))
        self.assertIn("https://us-example.api.gong.io/v2/calls/123", valid_args)
        self.assertNotIn("https://us-example.api.gong.io/v2/calls/extensive", valid_args)

        invalid_responses = [
            {"call": self.basic_call("456", "Mismatch")},
            {"call": {}},
            {"call": [{"id": "123"}, {"id": "123"}]},
            {"call": None},
            {"calls": [{}]},
            {"calls": [{"metaData": {"id": "123"}}, {"metaData": {"id": "123"}}]},
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                self.capture.joinpath("counter").unlink()
                result = self.run_helper("call", "123", responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no single exact call object", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_transcript_requires_one_exact_well_formed_resource(self) -> None:
        invalid_responses = [
            {"callTranscripts": [{"callId": "456", "transcript": []}]},
            {
                "callTranscripts": [
                    {"callId": "123", "transcript": []},
                    {"callId": "123", "transcript": []},
                ]
            },
            {"callTranscripts": [{"callId": "123", "transcript": None}]},
            {"callTranscripts": [{}]},
        ]
        for index, response in enumerate(invalid_responses):
            with self.subTest(response=response):
                if index:
                    self.capture.joinpath("counter").unlink()
                result = self.run_helper("transcript", "123", responses=[response])
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("no single exact transcript object", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_missing_call_and_unavailable_transcript_fail_explicitly(self) -> None:
        missing_call = self.run_helper("call", "123", responses=[{"calls": []}])
        self.assertNotEqual(missing_call.returncode, 0)
        self.assertIn("no single exact call object", missing_call.stderr)
        self.assertNotIn("null", missing_call.stdout)

        self.capture.joinpath("counter").unlink()
        unavailable = self.run_helper(
            "transcript",
            "123",
            responses=[{"callTranscripts": [{"callId": "123", "transcript": []}]}],
        )
        self.assertNotEqual(unavailable.returncode, 0)
        self.assertIn("no available segments", unavailable.stderr)
        self.assertEqual(unavailable.stdout, "")


if __name__ == "__main__":
    unittest.main()
