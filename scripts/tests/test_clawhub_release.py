from __future__ import annotations

import copy
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
import clawhub_release  # noqa: E402


EXACT_SHA = "a" * 40
EXACT_REF = "refs/heads/main"
WORKFLOW = clawhub_release.DEFAULT_WORKFLOW.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise AssertionError(f"expected exactly one occurrence of {old!r}")
    return text.replace(old, new, 1)


def mutate_publish(old: str, new: str) -> str:
    marker = "      - name: Publish exact ten-skill batch"
    prefix, block = WORKFLOW.split(marker, maxsplit=1)
    if old not in block:
        raise AssertionError(f"publish block does not contain {old!r}")
    return prefix + marker + block.replace(old, new, 1)


def mutate_preview(old: str, new: str) -> str:
    marker = "      - name: Preview exact ten-skill batch"
    prefix, block = WORKFLOW.split(marker, maxsplit=1)
    preview, suffix = block.split("\n  publish:\n", maxsplit=1)
    if old not in preview:
        raise AssertionError(f"preview block does not contain {old!r}")
    return prefix + marker + preview.replace(old, new, 1) + "\n  publish:\n" + suffix


class ReleaseManifestTests(unittest.TestCase):
    def test_manifest_has_exact_ten_release_identities(self) -> None:
        template = clawhub_release.load_template()
        self.assertEqual(
            template["releases"], list(clawhub_release.EXPECTED_RELEASE_SPECS)
        )
        self.assertEqual(template["release_batch"]["default_mode"], "validate")
        self.assertEqual(
            template["prohibited_without_separate_approval"],
            [
                "ClawHub migration",
                "ClawHub rename",
                "ClawHub merge",
                "ClawHub hide",
                "ClawHub delete",
                "ClawHub transfer",
            ],
        )

    def test_manifest_catalog_metadata_is_bounded_and_allowed(self) -> None:
        template = clawhub_release.load_template()
        for release in template["releases"]:
            self.assertGreaterEqual(len(release["categories"]), 1)
            self.assertLessEqual(len(release["categories"]), 3)
            self.assertFalse(set(release["categories"]) - clawhub_release.ALLOWED_CATEGORIES)
            self.assertGreaterEqual(len(release["topics"]), 1)
            self.assertLessEqual(len(release["topics"]), 5)
            self.assertFalse(set(release["topics"]) & clawhub_release.RESERVED_TOPICS)

    def test_duplicate_manifest_or_baseline_json_key_is_rejected(self) -> None:
        attacks = (
            clawhub_release.DEFAULT_TEMPLATE.read_text(encoding="utf-8").replace(
                '  "schema_version": 1,',
                '  "schema_version": 1,\n  "schema_version": 1,',
                1,
            ),
            clawhub_release.DEFAULT_BASELINE.read_text(encoding="utf-8").replace(
                '  "publisher": "jdrhyne",',
                '  "publisher": "jdrhyne",\n  "publisher": "jdrhyne",',
                1,
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, payload in enumerate(attacks):
                with self.subTest(index=index):
                    path = Path(directory) / f"attack-{index}.json"
                    path.write_text(payload, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "duplicate key"):
                        if index == 0:
                            clawhub_release.load_template(path)
                        else:
                            clawhub_release.load_public_baseline(path)

    def test_reserved_topic_is_rejected(self) -> None:
        template = copy.deepcopy(clawhub_release.load_template())
        template["releases"][0]["topics"] = ["official"]
        with self.assertRaisesRegex(ValueError, "reserved"):
            clawhub_release.validate_template(template)

    def test_unofficial_category_is_rejected(self) -> None:
        template = copy.deepcopy(clawhub_release.load_template())
        template["releases"][0]["categories"] = ["marketing"]
        with self.assertRaisesRegex(ValueError, "categories invalid"):
            clawhub_release.validate_template(template)

    def test_release_path_drift_is_rejected(self) -> None:
        template = copy.deepcopy(clawhub_release.load_template())
        template["releases"][0]["source_path"] = "skills/other"
        with self.assertRaisesRegex(ValueError, "source path drifted"):
            clawhub_release.validate_template(template)

    def test_coordinated_valid_catalog_drift_is_rejected(self) -> None:
        template = copy.deepcopy(clawhub_release.load_template())
        template["releases"][0]["name"] = "Google Advertising"
        template["releases"][0]["changelog"] = "A coordinated but unreviewed change."
        template["releases"][0]["categories"] = ["productivity"]
        template["releases"][0]["topics"] = ["advertising"]
        with self.assertRaisesRegex(ValueError, "immutable ten-entry"):
            clawhub_release.validate_template(template)

    def test_prohibited_action_value_order_and_completeness_are_immutable(self) -> None:
        for values in (
            ["ClawHub migration", "ClawHub rename"],
            [
                "ClawHub rename",
                "ClawHub migration",
                "ClawHub merge",
                "ClawHub hide",
                "ClawHub delete",
                "ClawHub transfer",
            ],
            [
                "ClawHub migration",
                "ClawHub rename",
                "ClawHub merge",
                "ClawHub hide",
                "ClawHub delete",
                "ClawHub transfer",
                "ClawHub publish",
            ],
        ):
            with self.subTest(values=values):
                template = copy.deepcopy(clawhub_release.load_template())
                template["prohibited_without_separate_approval"] = values
                with self.assertRaisesRegex(ValueError, "action list or order drifted"):
                    clawhub_release.validate_template(template)

    def test_sysadmin_deprecation_cannot_become_executable(self) -> None:
        template = copy.deepcopy(clawhub_release.load_template())
        template["deprecations"][0]["executable_registry_action"] = True
        with self.assertRaisesRegex(ValueError, "approval-only"):
            clawhub_release.validate_template(template)

    def test_public_baseline_matches_publisher_source_versions_and_paths(self) -> None:
        template = clawhub_release.load_template()
        baseline = clawhub_release.load_public_baseline()
        clawhub_release.validate_public_baseline(baseline, template)
        self.assertEqual(baseline["publisher"], "jdrhyne")
        self.assertEqual(baseline["source_repository"], "jdrhyne/agent-skills")

    def test_public_baseline_publisher_drift_is_rejected(self) -> None:
        baseline = copy.deepcopy(clawhub_release.load_public_baseline())
        baseline["publisher"] = "other"
        with self.assertRaisesRegex(ValueError, "immutable snapshot drifted"):
            clawhub_release.validate_public_baseline(baseline, clawhub_release.load_template())

    def test_public_baseline_version_drift_is_rejected(self) -> None:
        baseline = copy.deepcopy(clawhub_release.load_public_baseline())
        baseline["skills"][0]["version"] = "9.9.9"
        with self.assertRaisesRegex(ValueError, "immutable snapshot drifted"):
            clawhub_release.validate_public_baseline(baseline, clawhub_release.load_template())

    def test_public_baseline_date_commit_notes_and_extra_fields_are_immutable(self) -> None:
        attacks = []
        for key, value in (
            ("captured_at", "2026-08-30"),
            ("source_commit", "b" * 40),
            ("notes", ["rewritten"]),
        ):
            baseline = copy.deepcopy(clawhub_release.load_public_baseline())
            baseline[key] = value
            attacks.append(baseline)
        baseline = copy.deepcopy(clawhub_release.load_public_baseline())
        baseline["extra"] = True
        attacks.append(baseline)
        for baseline in attacks:
            with self.subTest(baseline=baseline):
                with self.assertRaisesRegex(ValueError, "immutable snapshot drifted"):
                    clawhub_release.validate_public_baseline(
                        baseline, clawhub_release.load_template()
                    )

    def test_public_baseline_entry_evidence_and_external_replacement_are_immutable(self) -> None:
        attacks = []
        for field, value in (
            ("verification", "pass"),
            ("security", "clean"),
            ("source_tree", "b" * 40),
            ("release_action", "publish-hardened-version"),
        ):
            baseline = copy.deepcopy(clawhub_release.load_public_baseline())
            baseline["skills"][0][field] = value
            attacks.append(baseline)
        baseline = copy.deepcopy(clawhub_release.load_public_baseline())
        baseline["skills"][0]["extra"] = "drift"
        attacks.append(baseline)
        baseline = copy.deepcopy(clawhub_release.load_public_baseline())
        baseline["external_replacement"]["source_commit"] = "b" * 40
        attacks.append(baseline)
        for baseline in attacks:
            with self.subTest(baseline=baseline):
                with self.assertRaisesRegex(ValueError, "immutable snapshot drifted"):
                    clawhub_release.validate_public_baseline(
                        baseline, clawhub_release.load_template()
                    )

    def test_package_layout_and_ignore_contract(self) -> None:
        template = clawhub_release.load_template()
        clawhub_release.validate_package_layout(template)
        for release in template["releases"]:
            package = clawhub_release.REPO_ROOT / release["source_path"]
            rules = (package / ".clawhubignore").read_text(encoding="utf-8").splitlines()
            self.assertEqual(
                rules,
                list(clawhub_release.EXPECTED_IGNORE_RULES[release["source_path"]]),
            )

    def test_ignore_negation_reordering_duplicates_and_extras_are_rejected(self) -> None:
        source_path = "skills/google-ads"
        canonical = list(clawhub_release.EXPECTED_IGNORE_RULES[source_path])
        attacks = [
            canonical + ["!_meta.json"],
            canonical + ["!tests/"],
            list(reversed(canonical)),
            canonical + [canonical[-1]],
            canonical + ["*.tmp"],
        ]
        for rules in attacks:
            with self.subTest(rules=rules):
                with self.assertRaisesRegex(ValueError, "ignore rules or order drifted"):
                    clawhub_release.validate_ignore_rules(source_path, rules)

    def test_render_binds_exact_commit_ref_and_all_paths(self) -> None:
        rendered = clawhub_release.render_manifest(
            clawhub_release.load_template(), EXACT_SHA, EXACT_REF
        )
        self.assertEqual(rendered["source"]["commit"], EXACT_SHA)
        self.assertEqual(rendered["source"]["ref"], EXACT_REF)
        self.assertEqual(rendered["source"]["repository"], "jdrhyne/agent-skills")
        self.assertEqual(
            [release["source_path"] for release in rendered["releases"]],
            [path for _, path in clawhub_release.EXPECTED_RELEASES.values()],
        )

    def test_short_or_uppercase_commit_is_rejected(self) -> None:
        for commit in ("abc123", "A" * 40):
            with self.subTest(commit=commit):
                with self.assertRaisesRegex(ValueError, "full lowercase"):
                    clawhub_release.render_manifest(
                        clawhub_release.load_template(), commit, EXACT_REF
                    )

    def test_invalid_ref_is_rejected(self) -> None:
        for ref in ("main", "refs/heads/main injected"):
            with self.subTest(ref=ref):
                with self.assertRaisesRegex(ValueError, "exact refs"):
                    clawhub_release.render_manifest(
                        clawhub_release.load_template(), EXACT_SHA, ref
                    )

    def test_rendered_manifest_contains_no_credential_material(self) -> None:
        rendered = clawhub_release.render_manifest(
            clawhub_release.load_template(), EXACT_SHA, EXACT_REF
        )
        serialized = json.dumps(rendered).lower()
        self.assertNotIn("authorization", serialized)
        self.assertNotIn("publish_token", serialized)

    def test_workflow_is_the_exact_structural_contract(self) -> None:
        clawhub_release.validate_workflow_publish_contract(
            WORKFLOW, clawhub_release.load_template()
        )

    def test_workflow_has_exact_twenty_canonical_commands(self) -> None:
        commands = clawhub_release.extract_publish_commands(WORKFLOW)
        self.assertEqual(len(commands), 20)
        self.assertEqual(["--dry-run" in command for command in commands], [True] * 10 + [False] * 10)

    def test_publish_must_depend_on_preview(self) -> None:
        mutated = replace_once(WORKFLOW, "    needs: preview\n", "")
        with self.assertRaisesRegex(ValueError, "job controls drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_preview_must_depend_on_validation(self) -> None:
        mutated = replace_once(WORKFLOW, "    needs: validate\n", "")
        with self.assertRaisesRegex(ValueError, "job controls drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_publish_checkout_cannot_switch_to_main_tip(self) -> None:
        prefix, publish = WORKFLOW.split("\n  publish:\n", maxsplit=1)
        publish = publish.replace("          ref: ${{ github.sha }}", "          ref: refs/heads/main", 1)
        with self.assertRaisesRegex(ValueError, "metadata drifted"):
            clawhub_release.validate_workflow_publish_contract(
                prefix + "\n  publish:\n" + publish,
                clawhub_release.load_template(),
            )

    def test_publish_condition_cannot_be_relaxed(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "  publish:\n    if: inputs.mode == 'publish'",
            "  publish:\n    if: always()",
        )
        with self.assertRaisesRegex(ValueError, "job controls drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_duplicate_yaml_key_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "    needs: preview\n",
            "    needs: preview\n    needs: preview\n",
        )
        with self.assertRaisesRegex(ValueError, "duplicate YAML key"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_extra_job_is_rejected(self) -> None:
        mutated = WORKFLOW + "\n  bypass:\n    runs-on: ubuntu-latest\n    steps: []\n"
        with self.assertRaisesRegex(ValueError, "job surface drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_extra_step_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "      - name: Remove temporary ClawHub auth config",
            "      - name: Unexpected step\n        run: \"true\"\n\n"
            "      - name: Remove temporary ClawHub auth config",
        )
        with self.assertRaisesRegex(ValueError, "step surface drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_legacy_publish_alias_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "      - name: Remove temporary ClawHub auth config",
            "      - name: Legacy alias\n        run: clawhub --no-input publish skills/gong --version 1.2.0\n\n"
            "      - name: Remove temporary ClawHub auth config",
        )
        with self.assertRaisesRegex(ValueError, "legacy publish alias"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_sync_invocation_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "      - name: Remove temporary ClawHub auth config",
            "      - name: Sync bypass\n        run: clawhub --no-input sync\n\n"
            "      - name: Remove temporary ClawHub auth config",
        )
        with self.assertRaisesRegex(ValueError, "registry mutation"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_computed_executable_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "      - name: Remove temporary ClawHub auth config",
            "      - name: Computed executable\n        run: $(npm prefix -g)/bin/clawhub --no-input sync\n\n"
            "      - name: Remove temporary ClawHub auth config",
        )
        with self.assertRaisesRegex(ValueError, "registry mutation|step surface drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_split_executable_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "      - name: Remove temporary ClawHub auth config",
            "      - name: Split executable\n        run: |\n"
            "          CLI_NAME=claw\n          ${CLI_NAME}hub --no-input sync\n\n"
            "      - name: Remove temporary ClawHub auth config",
        )
        with self.assertRaisesRegex(ValueError, "step surface drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_stale_universal_slug_is_rejected(self) -> None:
        mutated = mutate_publish("--slug gong", "--slug nutrient-document-processing-universal")
        with self.assertRaisesRegex(ValueError, "stale or deprecated slug"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_sysadmin_slug_is_rejected(self) -> None:
        mutated = mutate_publish("--slug gong", "--slug sysadmin-toolbox")
        with self.assertRaisesRegex(ValueError, "stale or deprecated slug"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_owner_migration_is_rejected(self) -> None:
        mutated = mutate_publish("--json", "--migrate-owner --json")
        with self.assertRaisesRegex(ValueError, "owner migration"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_preview_token_drift_is_rejected(self) -> None:
        mutated = mutate_preview("--version 1.2.0", "--version 9.9.9")
        with self.assertRaisesRegex(ValueError, "run body drifted|command tokens"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_publish_token_drift_is_rejected(self) -> None:
        mutated = mutate_publish("--version 1.2.0", "--version 9.9.9")
        with self.assertRaisesRegex(ValueError, "run body drifted|command tokens"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_non_publish_run_body_drift_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            '          test "$GITHUB_REPOSITORY" = "$EXPECTED_REPOSITORY"',
            "          true",
        )
        with self.assertRaisesRegex(ValueError, "run body drifted"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_secret_printing_is_rejected(self) -> None:
        mutated = replace_once(
            WORKFLOW,
            "          test -n \"$CLAWHUB_PUBLISH_TOKEN\"",
            "          echo \"$CLAWHUB_PUBLISH_TOKEN\"",
        )
        with self.assertRaisesRegex(ValueError, "secret value printing"):
            clawhub_release.validate_workflow_publish_contract(
                mutated, clawhub_release.load_template()
            )

    def test_whoami_occurs_only_in_gated_publish_job(self) -> None:
        document = clawhub_release._load_unique_workflow(WORKFLOW)
        occurrences = []
        for job_name, job in document["jobs"].items():
            for step in job["steps"]:
                if "whoami" in str(step.get("run", "")):
                    occurrences.append((job_name, step["name"], step["run"]))
        self.assertEqual(
            occurrences,
            [("publish", "Verify ClawHub authentication", "clawhub --no-input whoami")],
        )

    def test_auth_config_writer_is_read_by_actual_pinned_cli(self) -> None:
        script_match = re.search(r"(?ms)^\s*node -e '\n(?P<script>.*?)^\s*'\s*$", WORKFLOW)
        self.assertIsNotNone(script_match)
        version = subprocess.run(
            ["clawhub", "--cli-version"], check=True, capture_output=True, text=True
        ).stdout.strip()
        self.assertEqual(version, "0.23.3")

        candidates: list[Path] = []
        if shutil.which("asdf"):
            resolved = subprocess.run(
                ["asdf", "which", "clawhub"], capture_output=True, text=True, check=False
            )
            if resolved.returncode == 0:
                executable = Path(resolved.stdout.strip())
                candidates.extend(
                    [
                        executable.parents[1] / "lib" / "node_modules" / "clawhub" / "dist" / "cli" / "authToken.js",
                        executable.resolve().parents[1] / "dist" / "cli" / "authToken.js",
                    ]
                )
        npm_root = Path(
            subprocess.run(
                ["npm", "root", "-g"], check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        candidates.append(npm_root / "clawhub" / "dist" / "cli" / "authToken.js")
        auth_reader = next((candidate for candidate in candidates if candidate.is_file()), None)
        self.assertIsNotNone(auth_reader)

        sentinel = "test-only-clawhub-token"
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "clawhub" / "config.json"
            config_path.parent.mkdir(mode=0o700)
            env = os.environ.copy()
            env.update(
                {
                    "CLAWHUB_PUBLISH_TOKEN": sentinel,
                    "CLAWHUB_CONFIG_PATH": str(config_path),
                }
            )
            subprocess.run(
                ["node", "-e", script_match.group("script")],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                json.loads(config_path.read_text(encoding="utf-8")),
                {"registry": "https://clawhub.ai", "token": sentinel},
            )
            self.assertEqual(config_path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(config_path.parent.stat().st_mode & 0o777, 0o700)
            reader_script = (
                "const { getOptionalAuthToken } = await import(process.argv[1]);"
                "if (await getOptionalAuthToken() !== process.argv[2]) process.exit(3);"
            )
            subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    reader_script,
                    auth_reader.as_uri(),
                    sentinel,
                ],
                check=True,
                env=env,
                capture_output=True,
                text=True,
            )

    def test_actual_pinned_packager_excludes_release_only_files(self) -> None:
        version = subprocess.run(
            ["clawhub", "--cli-version"], check=True, capture_output=True, text=True
        ).stdout.strip()
        self.assertEqual(version, "0.23.3")
        candidates: list[Path] = []
        if shutil.which("asdf"):
            resolved = subprocess.run(
                ["asdf", "which", "clawhub"], capture_output=True, text=True, check=False
            )
            if resolved.returncode == 0:
                executable = Path(resolved.stdout.strip())
                candidates.extend(
                    [
                        executable.parents[1] / "lib" / "node_modules" / "clawhub" / "dist" / "skills.js",
                        executable.resolve().parents[1] / "dist" / "skills.js",
                    ]
                )
        npm_root = Path(
            subprocess.run(
                ["npm", "root", "-g"], check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        candidates.append(npm_root / "clawhub" / "dist" / "skills.js")
        skills_reader = next((candidate for candidate in candidates if candidate.is_file()), None)
        self.assertIsNotNone(skills_reader)

        packages = [
            str(clawhub_release.REPO_ROOT / release["source_path"])
            for release in clawhub_release.load_template()["releases"]
        ]
        reader_script = """
            const { listSkillFiles } = await import(process.argv[1]);
            for (const root of process.argv.slice(2)) {
              const paths = (await listSkillFiles(root)).map((entry) => entry.relPath);
              if (!paths.includes("SKILL.md")) process.exit(3);
              const bad = paths.filter((path) =>
                path === "_meta.json" ||
                path === "tests" || path.startsWith("tests/") ||
                path === "__pycache__" || path.includes("/__pycache__/") ||
                path.endsWith(".pyc")
              );
              if (bad.length) process.exit(4);
            }
        """
        subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                reader_script,
                skills_reader.as_uri(),
                *packages,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def test_actual_pinned_packager_negation_reincludes_and_validator_rejects(self) -> None:
        version = subprocess.run(
            ["clawhub", "--cli-version"], check=True, capture_output=True, text=True
        ).stdout.strip()
        self.assertEqual(version, "0.23.3")
        candidates: list[Path] = []
        if shutil.which("asdf"):
            resolved = subprocess.run(
                ["asdf", "which", "clawhub"], capture_output=True, text=True, check=False
            )
            if resolved.returncode == 0:
                executable = Path(resolved.stdout.strip())
                candidates.extend(
                    [
                        executable.parents[1] / "lib" / "node_modules" / "clawhub" / "dist" / "skills.js",
                        executable.resolve().parents[1] / "dist" / "skills.js",
                    ]
                )
        npm_root = Path(
            subprocess.run(
                ["npm", "root", "-g"], check=True, capture_output=True, text=True
            ).stdout.strip()
        )
        candidates.append(npm_root / "clawhub" / "dist" / "skills.js")
        skills_reader = next((candidate for candidate in candidates if candidate.is_file()), None)
        self.assertIsNotNone(skills_reader)

        bad_rules = list(clawhub_release.COMMON_IGNORE_RULES) + ["!_meta.json"]
        with self.assertRaisesRegex(ValueError, "ignore rules or order drifted"):
            clawhub_release.validate_ignore_rules("skills/google-ads", bad_rules)

        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "skill"
            package.mkdir()
            (package / "SKILL.md").write_text(
                "---\nname: test\ndescription: test\n---\n", encoding="utf-8"
            )
            (package / "_meta.json").write_text("{}\n", encoding="utf-8")
            (package / ".clawhubignore").write_text(
                "_meta.json\n!_meta.json\n", encoding="utf-8"
            )
            reader_script = """
                const { listSkillFiles } = await import(process.argv[1]);
                const paths = (await listSkillFiles(process.argv[2]))
                  .map((entry) => entry.relPath)
                  .sort();
                process.stdout.write(JSON.stringify(paths));
            """
            result = subprocess.run(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    reader_script,
                    skills_reader.as_uri(),
                    str(package),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("_meta.json", json.loads(result.stdout))

    def test_sysadmin_document_contains_no_executable_mutation(self) -> None:
        clawhub_release.validate_deprecation_document()

    def test_external_reviewer_caveat_is_documented(self) -> None:
        documentation = (
            clawhub_release.REPO_ROOT / "docs" / "clawhub-release" / "README.md"
        ).read_text(encoding="utf-8")
        self.assertIn("required reviewers", documentation)
        self.assertIn(
            "Merely naming the environment in workflow YAML does not add reviewer protection",
            documentation,
        )
        self.assertIn("CLAWHUB_RELEASE_ENABLED", documentation)


if __name__ == "__main__":
    unittest.main()
