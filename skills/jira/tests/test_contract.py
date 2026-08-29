#!/usr/bin/env python3
"""Deterministic offline checks for Jira routing and mutation boundaries."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
SKILL = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
COMMANDS = (SKILL_DIR / "references" / "commands.md").read_text(encoding="utf-8")
CONNECTOR = (SKILL_DIR / "references" / "mcp.md").read_text(encoding="utf-8")
CASES = json.loads(
    (SKILL_DIR / "tests" / "routing-and-safety.json").read_text(encoding="utf-8")
)

MUTATIONS = {"create", "edit", "assign", "transition", "link", "comment", "sprint"}


class JiraContractTests(unittest.TestCase):
    def test_description_requires_explicit_jira_context(self) -> None:
        frontmatter = SKILL.split("---", 2)[1]
        description = next(
            line.removeprefix("description:").strip()
            for line in frontmatter.splitlines()
            if line.startswith("description:")
        )
        self.assertIn("explicit Jira or Atlassian context", description)
        self.assertIn("generic mentions", description)

    def test_frontmatter_has_no_runtime_backend_gate(self) -> None:
        frontmatter = SKILL.split("---", 2)[1]
        self.assertNotIn("requires", frontmatter)
        self.assertNotIn("JIRA_API_TOKEN", frontmatter)

    def test_backend_names_are_discovered_not_hard_coded(self) -> None:
        package_text = "\n".join((SKILL, COMMANDS, CONNECTOR))
        self.assertNotRegex(package_text, r"mcp__[A-Za-z0-9_-]+__")
        self.assertNotIn("JIRA_API_TOKEN", package_text)
        self.assertNotRegex(package_text, r"curl\s+[^\n]*-[uH]\s")

    def test_executing_agent_has_only_needed_package_docs(self) -> None:
        self.assertFalse((SKILL_DIR / "README.md").exists())
        self.assertIn("references/commands.md", SKILL)
        self.assertIn("references/mcp.md", SKILL)

    def test_mutations_require_state_diff_approval_and_verification(self) -> None:
        for case in CASES:
            if case["operation"] not in MUTATIONS:
                continue
            with self.subTest(case=case["id"]):
                self.assertTrue(case["requires_current_state"])
                self.assertTrue(case["requires_diff"])
                self.assertTrue(case["requires_approval"])
                self.assertTrue(case["verify_after"])
                self.assertFalse(case["auto_comment"])

    def test_reads_and_drafts_do_not_inherit_write_approval(self) -> None:
        for case in CASES:
            if case["operation"] not in {"read", "draft"}:
                continue
            with self.subTest(case=case["id"]):
                self.assertFalse(case["requires_approval"])
                self.assertFalse(case["auto_comment"])

    def test_bulk_review_is_bounded(self) -> None:
        for case in CASES:
            target_count = len(case["targets"])
            with self.subTest(case=case["id"]):
                if target_count > 10:
                    self.assertEqual(case["expected"], "split-before-review")
                elif target_count > 1 and case["operation"] in MUTATIONS:
                    self.assertEqual(case["expected"], "approved-batch")
                    self.assertEqual(case["approval_scope"], "displayed-batch")

    def test_issue_keys_are_complete_and_fixture_ids_are_unique(self) -> None:
        seen_ids: set[str] = set()
        issue_key = re.compile(r"^[A-Z][A-Z0-9]+-[0-9]+$")
        for case in CASES:
            self.assertNotIn(case["id"], seen_ids)
            seen_ids.add(case["id"])
            for target in case["targets"]:
                if "-" in target:
                    self.assertRegex(target, issue_key)

    def test_untrusted_ticket_instruction_is_not_executed(self) -> None:
        case = next(item for item in CASES if item["id"] == "instruction-in-ticket-body")
        self.assertEqual(case["expected"], "treat-as-data")
        self.assertFalse(case["requires_approval"])


if __name__ == "__main__":
    unittest.main()
