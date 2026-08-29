import json
import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"
API_REFERENCE = SKILL_ROOT / "references" / "api-setup.md"
BROWSER_REFERENCE = SKILL_ROOT / "references" / "browser-workflows.md"
MUTATION_REFERENCE = SKILL_ROOT / "references" / "mutation-workflow.md"
ROUTING_FIXTURES = Path(__file__).parent / "fixtures" / "routing-cases.json"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class GoogleAdsSkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = read(SKILL_MD)
        cls.api = read(API_REFERENCE)
        cls.browser = read(BROWSER_REFERENCE)
        cls.mutation = read(MUTATION_REFERENCE)
        cls.runtime_text = "\n".join((cls.skill, cls.api, cls.browser, cls.mutation))

    def test_browser_mode_has_no_hard_python_or_credential_gate(self):
        frontmatter = self.skill.split("---", 2)[1]
        self.assertNotIn("requires:", frontmatter)
        self.assertNotIn("permissions:", frontmatter)
        self.assertNotIn("compatibility:", frontmatter)
        for block in re.findall(r"- name: GOOGLE_ADS_[A-Z_]+\n(?: {8}.*\n?)+", frontmatter):
            self.assertIn("required: false", block)
        self.assertIn("A browser-only workflow does not require Python", self.skill)

    def test_runtime_instructions_never_disclose_credentials(self):
        forbidden = (
            r"cat\s+[^\n]*google-ads\.yaml",
            r"print\s*\([^\n]*refresh[_ ]?token",
            r"echo\s+[\"']?\$GOOGLE_ADS_",
            r"env\s*\|\s*grep\s+GOOGLE_ADS",
        )
        for pattern in forbidden:
            self.assertNotRegex(self.runtime_text, re.compile(pattern, re.IGNORECASE))

    def test_mutation_guidance_is_progressively_gated(self):
        self.assertIn("Explicit account-changing request only", self.skill)
        self.assertIn("Do not load mutation guidance", self.skill)
        self.assertIn("Read this file only after", self.mutation)
        self.assertIn("recommendations", self.mutation)

    def test_mutation_contract_contains_every_safety_gate(self):
        required_terms = (
            "Account identity",
            "Customer ID",
            "exact resource IDs",
            "Before → after",
            "validate_only=True",
            "action-time approval",
            "partial-failure",
            "read every changed value back",
            "at most 25 exact entities",
            "stop all remaining batches",
        )
        for term in required_terms:
            self.assertIn(term, self.mutation)

    def test_browser_writes_are_attended_and_capability_based(self):
        self.assertIn("user-attached", self.browser)
        self.assertIn("current accessibility tree", self.browser)
        self.assertIn("Keep the session user-attended", self.browser)
        self.assertIn("accessible name", self.browser)
        self.assertNotRegex(self.browser, re.compile(r"table\.[a-z]|\[role=", re.IGNORECASE))

    def test_recommendations_are_goal_aware(self):
        for term in (
            "business objective",
            "conversion lag",
            "attribution model",
            "seasonality",
            "not an automatic action threshold",
        ):
            self.assertIn(term, self.skill)

    def test_compatibility_baseline_and_primary_sources_are_present(self):
        self.assertIn("reviewed on 2026-08-29", self.skill)
        self.assertIn("v25.1", self.skill)
        self.assertIn("developers.google.com/google-ads/api/docs/release-notes", self.skill)
        self.assertIn("developers.google.com/google-ads/api/docs/upgrade", self.skill)
        self.assertIn("Do not force an API version", self.skill)

    def test_referenced_runtime_files_exist(self):
        referenced = set(re.findall(r"\((references/[^)]+\.md)\)", self.skill))
        self.assertEqual(
            referenced,
            {
                "references/api-setup.md",
                "references/browser-workflows.md",
                "references/mutation-workflow.md",
            },
        )
        for relative_path in referenced:
            self.assertTrue((SKILL_ROOT / relative_path).is_file(), relative_path)

    def test_routing_fixtures_cover_read_and_write_boundaries(self):
        cases = json.loads(read(ROUTING_FIXTURES))
        self.assertEqual(len(cases), 5)
        by_name = {case["name"]: case for case in cases}
        self.assertEqual(
            by_name["browser read without api dependencies"]["expected_write_state"],
            "read-only",
        )
        self.assertFalse(
            by_name["recommendation is not mutation approval"]["load_mutation_reference"]
        )
        self.assertTrue(
            by_name["explicit mutation still needs exact preview approval"][
                "load_mutation_reference"
            ]
        )
        bounded = by_name["large mutation is independently bounded"]
        self.assertEqual(bounded["maximum_batch_size"], 25)
        self.assertEqual(bounded["expected_batch_sizes"], [25, 25, 13])
        self.assertTrue(bounded["verify_after_each_batch"])
        self.assertTrue(bounded["stop_on_failure_or_drift"])


if __name__ == "__main__":
    unittest.main()
