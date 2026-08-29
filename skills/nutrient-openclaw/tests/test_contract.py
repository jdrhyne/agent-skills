import json
import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"
REFERENCE = ROOT / "references" / "plugin-contract.md"
FIXTURE = ROOT / "tests" / "routing-and-safety.json"

TOOLS = {
    "nutrient_convert_to_pdf",
    "nutrient_convert_to_image",
    "nutrient_convert_to_office",
    "nutrient_extract_text",
    "nutrient_ocr",
    "nutrient_redact",
    "nutrient_ai_redact",
    "nutrient_watermark",
    "nutrient_sign",
    "nutrient_check_credits",
}


def load_frontmatter(text: str) -> dict:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    return yaml.safe_load(match.group(1))


class NutrientOpenClawContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.reference = REFERENCE.read_text(encoding="utf-8")
        cls.published_text = cls.skill + "\n" + cls.reference
        cls.frontmatter = load_frontmatter(cls.skill)
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]

    def test_canonical_frontmatter_and_pin(self) -> None:
        self.assertEqual(self.frontmatter["name"], "nutrient-openclaw")
        metadata = self.frontmatter["metadata"]
        self.assertEqual(metadata["version"], "1.3.0")
        self.assertIn("openclaw", metadata)
        self.assertNotIn("clawdis", self.frontmatter)
        install = metadata["openclaw"]["install"]
        self.assertEqual(len(install), 1)
        self.assertEqual(
            install[0]["package"], "@nutrient-sdk/nutrient-openclaw@0.1.1"
        )
        self.assertIn("{baseDir}/references/plugin-contract.md", self.skill)

    def test_exact_tool_inventory(self) -> None:
        documented = set(re.findall(r"`(nutrient_[a-z_]+)`", self.published_text))
        self.assertEqual(documented, TOOLS)

    def test_reviewed_runtime_contract_is_explicit(self) -> None:
        for value in (
            "@nutrient-sdk/nutrient-openclaw",
            "0.1.1",
            "Node.js 18",
            "64077d47c648c5a3219131de2dbddc22836cbf09",
            "optional `openclaw`",
        ):
            self.assertIn(value, self.reference)

    def test_secret_boundary(self) -> None:
        forbidden = (
            r"Authorization\s*:\s*Bearer",
            r"\bcurl\b",
            r"export\s+NUTRIENT_API_KEY",
            r"\$NUTRIENT_API_KEY",
            r"apiKey\s*:\s*[\"']",
            r"\becho\s+.*(?:API_KEY|apiKey)",
            r"\bprint(?:ln)?\s*\(.*(?:API_KEY|apiKey)",
        )
        for pattern in forbidden:
            self.assertIsNone(
                re.search(pattern, self.published_text, re.IGNORECASE),
                msg=f"published package violates secret boundary: {pattern}",
            )
        self.assertIn("does not declare `secretInputs`", self.published_text)
        self.assertIn("plugins.entries.nutrient-openclaw.config.apiKey", self.published_text)
        self.assertIn("Never ask for, display, copy, log, or summarize", self.skill)

    def test_metered_gate_is_action_time_and_per_invocation(self) -> None:
        for phrase in (
            "For **every** credit-consuming invocation",
            "numeric estimate or bounded range",
            "Immediately before the tool call",
            "One approval authorizes one unchanged invocation",
            "retry",
            "chained stage",
            "verification render",
        ):
            self.assertIn(phrase, self.skill)

    def test_credit_check_is_not_preflight_or_authorization(self) -> None:
        self.assertIn("last-known local usage ledger", self.skill)
        self.assertIn("not a live account query, exact preflight quote", self.skill)
        self.assertIn("cannot replace an estimate or authorize processing", self.skill)

    def test_high_risk_boundaries(self) -> None:
        for phrase in (
            "has no AI-redaction dry-run",
            "human must inspect every affected page",
            "no user-controlled certificate or private-key input",
            "not, by itself, proof of signer identity",
            "human/legal approval",
        ):
            self.assertIn(phrase, self.skill)

    def test_routing_fixture_has_unique_valid_cases(self) -> None:
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))
        for case in self.cases:
            self.assertTrue(set(case["tools"]).issubset(TOOLS), case["id"])
            self.assertEqual(
                case["metered_calls"], case["action_confirmations"], case["id"]
            )

    def test_chains_and_retries_have_separate_approval(self) -> None:
        chained = [case for case in self.cases if case["metered_calls"] > 1]
        self.assertTrue(chained)
        for case in chained:
            self.assertEqual(
                case["metered_calls"], case["action_confirmations"], case["id"]
            )
        retry = next(case for case in self.cases if case["id"] == "retry-after-failure")
        self.assertTrue(retry["retry_requires_fresh_estimate"])

    def test_sensitive_workflow_fixture_boundaries(self) -> None:
        ai = next(case for case in self.cases if case["id"] == "semantic-redaction")
        self.assertTrue(ai["preserve_source"])
        self.assertTrue(ai["candidate_output"])
        self.assertTrue(ai["human_output_review"])
        self.assertTrue(ai["no_dry_run_disclosed"])
        sign = next(case for case in self.cases if case["id"] == "signing-boundary")
        self.assertTrue(sign["legal_authority_gate"])
        self.assertTrue(sign["not_identity_proof"])

    def test_package_is_portable_and_tests_are_excluded(self) -> None:
        self.assertNotRegex(self.published_text, r"/Users/|(?<!\w)~/")
        ignore = (ROOT / ".clawhubignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("tests/", ignore)
        self.assertTrue(REFERENCE.is_file())


if __name__ == "__main__":
    unittest.main()
