#!/usr/bin/env python3
"""Offline contract checks for Nudocs routing and external actions."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
FORMATS = (SKILL_DIR / "references" / "formats.md").read_text(encoding="utf-8")
CASES = json.loads(
    (SKILL_DIR / "tests" / "routing-and-safety.json").read_text(encoding="utf-8")
)


class NudocsContractTests(unittest.TestCase):
    def test_auth_methods_are_not_simultaneous_runtime_gates(self) -> None:
        frontmatter = SKILL.split("---", 2)[1]
        self.assertIn('"bins": ["nudocs"]', frontmatter)
        self.assertNotIn('"env"', frontmatter)
        self.assertNotIn('"config"', frontmatter)

    def test_secret_and_obsolete_command_patterns_are_absent(self) -> None:
        package_text = SKILL + "\n" + FORMATS
        self.assertNotRegex(package_text, r"(?im)^\s*echo\s+.*NUDOCS")
        self.assertNotRegex(package_text, r"(?im)^\s*gimme\b")
        self.assertNotIn("DOCUMENT_LIMIT_REACHED", package_text)
        self.assertNotIn("10 docs", package_text)

    def test_generic_document_tutorial_was_removed(self) -> None:
        self.assertFalse((SKILL_DIR / "references" / "document-design.md").exists())
        self.assertIn("read [references/formats.md]", SKILL)

    def test_sensitive_upload_public_share_and_delete_are_gated(self) -> None:
        gated = {"sensitive-upload", "publish-edit-link", "delete-document"}
        for case in CASES:
            with self.subTest(case=case["id"]):
                self.assertEqual(case["requires_action_approval"], case["id"] in gated)

    def test_link_pull_and_delete_commands_pass_exact_document_ids(self) -> None:
        actionable = {
            case["operation"]: case
            for case in CASES
            if case.get("command") and case["operation"] in {"link", "pull", "delete"}
        }
        self.assertEqual(set(actionable), {"link", "pull", "delete"})
        for operation, case in actionable.items():
            with self.subTest(operation=operation):
                document_id = case["document_id"]
                self.assertTrue(document_id)
                self.assertRegex(
                    case["command"],
                    rf"^nudocs {operation} {re.escape(document_id)}(?:\s|$)",
                )

        for command in (
            "nudocs link <document-id>",
            "nudocs pull <document-id> --format <format> --output <exact-output-path>",
            "nudocs delete <document-id>",
        ):
            self.assertIn(command, SKILL)

    def test_non_id_targets_are_refused_not_sent_to_cli_defaults(self) -> None:
        refusals = [case for case in CASES if case.get("input_kind")]
        self.assertEqual(
            {case["operation"] for case in refusals},
            {"link", "pull", "delete"},
        )
        for case in refusals:
            with self.subTest(case=case["id"]):
                self.assertNotIn("document_id", case)
                self.assertEqual(case["expected"], "refuse-and-resolve-exact-id")

        self.assertIn(
            "Never run bare `nudocs link`, `nudocs pull`, or `nudocs delete`",
            SKILL,
        )
        self.assertIn("never rely on a CLI default such as the last uploaded document", SKILL)
        self.assertIn("non-ID reference is not an action target", SKILL)
        self.assertIn("refuse the action and ask the user to choose an exact ID", SKILL)

    def test_current_documented_export_formats_are_present(self) -> None:
        for value in ("docx", "md", "pdf", "html", "txt"):
            self.assertRegex(FORMATS, rf"`{re.escape(value)}`")

    def test_fixture_ids_are_unique(self) -> None:
        ids = [case["id"] for case in CASES]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
