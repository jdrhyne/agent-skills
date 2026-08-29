#!/usr/bin/env python3
"""Validate and render the exact ten-skill ClawHub release contract."""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = REPO_ROOT / "docs" / "clawhub-release" / "release-manifest.template.json"
DEFAULT_BASELINE = REPO_ROOT / "docs" / "clawhub-release" / "public-baseline.json"
DEFAULT_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "clawhub-release.yml"
DEFAULT_DEPRECATION = REPO_ROOT / "docs" / "clawhub-release" / "sysadmin-toolbox.md"
COMMIT_SENTINEL = "__EXACT_GITHUB_SHA__"
REF_SENTINEL = "__EXACT_GITHUB_REF__"

EXPECTED_RELEASE_SPECS = (
    {
        "slug": "google-ads",
        "name": "Google Ads",
        "version": "1.2.0",
        "source_path": "skills/google-ads",
        "changelog": "Harden read-only analysis, browser and API routing, goal-aware recommendations, credential handling, and bounded approval-gated mutations.",
        "tags": ["latest"],
        "categories": ["integrations", "automation", "productivity"],
        "topics": ["google-ads", "advertising", "campaign-analysis", "paid-search"],
    },
    {
        "slug": "jira",
        "name": "Jira",
        "version": "1.4.0",
        "source_path": "skills/jira",
        "changelog": "Harden capability discovery, issue identity and scope, credential handling, and bounded approval-gated writes.",
        "tags": ["latest"],
        "categories": ["integrations", "productivity", "operations"],
        "topics": ["jira", "issue-tracking", "project-management", "agile"],
    },
    {
        "slug": "context-recovery",
        "name": "Context Recovery",
        "version": "1.3.0",
        "source_path": "skills/context-recovery",
        "changelog": "Constrain activation and recovery scope, treat recovered material as untrusted, surface provenance and conflicts, and gate cross-source actions and persistence.",
        "tags": ["latest"],
        "categories": ["productivity", "knowledge", "agents"],
        "topics": ["context-recovery", "conversation-history", "provenance", "continuity"],
    },
    {
        "slug": "nudocs",
        "name": "Nudocs",
        "version": "1.3.0",
        "source_path": "skills/nudocs",
        "changelog": "Harden credential setup, exact document identity, and explicit upload, sharing, export, and deletion authority boundaries.",
        "tags": ["latest"],
        "categories": ["integrations", "productivity", "communication"],
        "topics": ["nudocs", "documents", "collaboration", "document-editing"],
    },
    {
        "slug": "nutrient-openclaw",
        "name": "Nutrient OpenClaw",
        "version": "1.3.0",
        "source_path": "skills/nutrient-openclaw",
        "changelog": "Pin the plugin contract, use canonical metadata and portable paths, and require bounded estimates and confirmation for every credit-consuming DWS run.",
        "tags": ["latest"],
        "categories": ["integrations", "automation", "productivity"],
        "topics": ["nutrient", "document-processing", "pdf", "ocr", "redaction"],
    },
    {
        "slug": "todo-tracker",
        "name": "Todo Tracker",
        "version": "1.1.0",
        "source_path": "clawdbot/todo-tracker",
        "changelog": "Make task storage portable with monotonic stable IDs, literal matching, locked atomic writes, recoverable backups, and opt-in count-only heartbeats.",
        "tags": ["latest"],
        "categories": ["productivity", "automation"],
        "topics": ["todo", "task-tracking", "markdown", "local-first"],
    },
    {
        "slug": "gsc",
        "name": "Google Search Console",
        "version": "1.3.0",
        "source_path": "skills/gsc",
        "changelog": "Modernize read-only OAuth, pagination, retries, validation, freshness metadata, bounded queries, exports, and credential safety.",
        "tags": ["latest"],
        "categories": ["integrations", "research", "productivity"],
        "topics": ["search-console", "seo", "search-analytics", "url-inspection"],
    },
    {
        "slug": "ga4",
        "name": "Google Analytics 4",
        "version": "1.3.0",
        "source_path": "skills/ga4",
        "changelog": "Modernize read-only reporting, OAuth, pagination, retries, validation, key-event terminology, quota visibility, and safe CSV output.",
        "tags": ["latest"],
        "categories": ["integrations", "research", "productivity"],
        "topics": ["google-analytics", "analytics", "reporting", "key-events"],
    },
    {
        "slug": "munger-observer",
        "name": "Munger Observer",
        "version": "1.1.0",
        "source_path": "prompts/munger-observer",
        "changelog": "Rebuild decision review around bounded evidence, counterevidence, uncertainty, alternatives, privacy, and user-verifiable checks.",
        "tags": ["latest"],
        "categories": ["productivity", "knowledge"],
        "topics": ["decision-review", "mental-models", "evidence", "premortem"],
    },
    {
        "slug": "gong",
        "name": "Gong",
        "version": "1.2.0",
        "source_path": "skills/gong",
        "changelog": "Prevent credential leakage, bound pagination and transcript output, handle missing or malformed resources, and clean temporary API state.",
        "tags": ["latest"],
        "categories": ["integrations", "communication", "productivity"],
        "topics": ["gong", "conversation-intelligence", "transcripts", "sales-analytics"],
    },
)
EXPECTED_RELEASES = {
    release["slug"]: (release["version"], release["source_path"])
    for release in EXPECTED_RELEASE_SPECS
}
EXPECTED_BASELINE_VERSIONS = {
    "google-ads": "1.1.0",
    "jira": "1.3.3",
    "context-recovery": "1.2.2",
    "nudocs": "1.2.0",
    "nutrient-openclaw": "1.2.5",
    "todo-tracker": "1.0.0",
    "gsc": "1.2.2",
    "ga4": "1.2.2",
    "munger-observer": "1.0.0",
    "gong": "1.1.0",
}
EXPECTED_PUBLIC_BASELINE = {
    "captured_at": "2026-08-29",
    "publisher": "jdrhyne",
    "source_repository": "jdrhyne/agent-skills",
    "source_commit": "a4d31ad11998a8900bf801ec0daa27ee5cb1a834",
    "notes": [
        "Verification was refreshed with ClawHub CLI 0.23.3.",
        "Registry visibility, publication, rename, merge, transfer, and deletion are not authorized by this manifest.",
        "Unsigned is informational; unavailable provenance is a release-quality gap to fix on the next publication.",
    ],
    "skills": [
        {
            "slug": "google-ads",
            "version": "1.1.0",
            "verification": "fail",
            "security": "suspicious",
            "source_path": "skills/google-ads",
            "source_tree": "8c232974a88b77a61c7c6ab5864fcf8d5f04517b",
            "release_action": "publish-fixed-version",
        },
        {
            "slug": "sysadmin-toolbox",
            "version": "1.1.0",
            "verification": "fail",
            "security": "suspicious",
            "source_path": None,
            "source_tree": None,
            "release_action": "approval-gated-hide-and-deprecate",
        },
        {
            "slug": "context-recovery",
            "version": "1.2.2",
            "verification": "pass",
            "security": "clean",
            "source_path": "skills/context-recovery",
            "source_tree": "c322585c01b0ad649f0be6b7b14c4e90fb440c34",
            "release_action": "publish-hardened-version",
        },
        {
            "slug": "nudocs",
            "version": "1.2.0",
            "verification": "pass",
            "security": "clean",
            "source_path": "skills/nudocs",
            "source_tree": "b09f2b9ce3cb21a906576510a375a36c24f3784a",
            "release_action": "publish-hardened-version",
        },
        {
            "slug": "nutrient-openclaw",
            "version": "1.2.5",
            "verification": "pass",
            "security": "clean",
            "source_path": "skills/nutrient-openclaw",
            "source_tree": "d6f38c6cd6e2bc491dbd7d34550e2e9fef201ce1",
            "release_action": "publish-hardened-version",
        },
        {
            "slug": "jira",
            "version": "1.3.3",
            "verification": "fail",
            "security": "suspicious",
            "source_path": "skills/jira",
            "source_tree": "e9292d72bb6abd64c46cd4e474c5ca9927d4f6b1",
            "release_action": "publish-fixed-version",
        },
        {
            "slug": "todo-tracker",
            "version": "1.0.0",
            "verification": "pass",
            "security": "clean",
            "source_path": "clawdbot/todo-tracker",
            "source_tree": "3ae30d165f5548530abbf219236d773ef0f54187",
            "release_action": "publish-hardened-version",
        },
        {
            "slug": "gsc",
            "version": "1.2.2",
            "verification": "pass",
            "security": "clean",
            "source_path": "skills/gsc",
            "source_tree": "64edfe546120a9f4d60824c6aa88ab9d315e80a7",
            "release_action": "publish-modernized-version",
        },
        {
            "slug": "ga4",
            "version": "1.2.2",
            "verification": "pass",
            "security": "clean",
            "source_path": "skills/ga4",
            "source_tree": "a3f5497d94a13b21b152330ebd4316f55fbd0943",
            "release_action": "publish-modernized-version",
        },
        {
            "slug": "munger-observer",
            "version": "1.0.0",
            "verification": "pass",
            "security": "clean",
            "source_path": "prompts/munger-observer",
            "source_tree": "fdfff308c9a61952da6290128100fbff04832d2d",
            "release_action": "publish-hardened-version",
        },
        {
            "slug": "gong",
            "version": "1.1.0",
            "verification": "pass",
            "security": "clean",
            "source_path": "skills/gong",
            "source_tree": "66916ea53a79fdb62f5c07d8ea44c8442391e5c4",
            "release_action": "publish-hardened-version",
        },
    ],
    "external_replacement": {
        "slug": "nutrient-document-processing-universal",
        "version": "1.1.2",
        "verification": "pass",
        "security": "clean",
        "source_repository": "PSPDFKit-labs/nutrient-agent-skill",
        "source_commit": "4d150575a5bb852306a9b72c78a97a62557651ed",
        "source_path": "nutrient-document-processing",
        "source_tree": "7b96c6bc54b7977d7f79a46d63a67f110d963aaf",
        "release_action": "replace-with-corrected-canonical-package",
    },
}
ALLOWED_CATEGORIES = {
    "integrations",
    "automation",
    "research",
    "development",
    "productivity",
    "communication",
    "creative",
    "knowledge",
    "agents",
    "operations",
    "security",
    "finance",
    "lifestyle",
    "other",
}
RESERVED_TOPICS = {
    "approved",
    "audited",
    "certified",
    "clawhub",
    "community",
    "curated",
    "endorsed",
    "featured",
    "official",
    "officials",
    "openclaw",
    "recommended",
    "staff-pick",
    "trusted",
    "trusted-publisher",
    "verified",
}
COMMON_IGNORE_RULES = ("tests/", "__pycache__/", "*.pyc", "_meta.json")
ANALYTICS_IGNORE_RULES = (
    ".env",
    "__pycache__/",
    "*.pyc",
    "*.py[cod]",
    "client_secret*.json",
    "credentials*.json",
    "token*.json",
    "tests/",
    "_meta.json",
)
EXPECTED_IGNORE_RULES = {
    "skills/google-ads": COMMON_IGNORE_RULES,
    "skills/jira": COMMON_IGNORE_RULES,
    "skills/context-recovery": COMMON_IGNORE_RULES,
    "skills/nudocs": COMMON_IGNORE_RULES,
    "skills/nutrient-openclaw": COMMON_IGNORE_RULES,
    "clawdbot/todo-tracker": COMMON_IGNORE_RULES,
    "skills/gsc": ANALYTICS_IGNORE_RULES,
    "skills/ga4": ANALYTICS_IGNORE_RULES,
    "prompts/munger-observer": COMMON_IGNORE_RULES,
    "skills/gong": COMMON_IGNORE_RULES,
}
PROHIBITED_SLUGS = {
    "sysadmin-toolbox",
    "nutrient-document-processing-universal",
}


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"release workflow contains duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"release JSON contains duplicate key: {key}")
        result[key] = value
    return result


def _load_unique_json(path: Path) -> dict[str, Any]:
    data = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=_unique_json_object
    )
    if not isinstance(data, dict):
        raise ValueError("release JSON root must be an object")
    return data


def load_template(path: Path = DEFAULT_TEMPLATE) -> dict[str, Any]:
    data = _load_unique_json(path)
    validate_template(data)
    return data


def load_public_baseline(path: Path = DEFAULT_BASELINE) -> dict[str, Any]:
    return _load_unique_json(path)


def _semver_tuple(version: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError(f"invalid release semver: {version}")
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def validate_template(data: dict[str, Any]) -> None:
    expected_top_level = {
        "schema_version",
        "release_batch",
        "cli",
        "source",
        "gates",
        "releases",
        "deprecations",
        "prohibited_without_separate_approval",
    }
    if set(data) != expected_top_level:
        raise ValueError("release manifest top-level schema drifted")
    if data.get("schema_version") != 1:
        raise ValueError("release manifest schema_version must be 1")
    if data.get("release_batch") != {
        "id": "agent-skills-clawhub-refresh-2026-08-29",
        "default_mode": "validate",
        "publisher": "jdrhyne",
    }:
        raise ValueError("release batch identity or validation-only default drifted")
    if data.get("cli") != {
        "package": "clawhub",
        "version": "0.23.3",
        "command": ["clawhub", "skill", "publish"],
    }:
        raise ValueError("ClawHub CLI package, version, or canonical command drifted")
    if data.get("source") != {
        "repository": "jdrhyne/agent-skills",
        "commit": COMMIT_SENTINEL,
        "ref": REF_SENTINEL,
    }:
        raise ValueError("release source repository, commit, or ref drifted")

    expected_gates = {
        "required_publish_ref": "refs/heads/main",
        "required_environment": "clawhub-production",
        "release_enabled_variable": "CLAWHUB_RELEASE_ENABLED",
        "release_enabled_value": "true",
        "environment_reviewers_configured_externally": True,
        "publish_confirmation_template": "PUBLISH 10 CLAWHUB SKILLS FROM {sha}",
        "expected_commit_must_match": True,
        "dry_run_before_publish": True,
        "slug_migration_enabled": False,
    }
    if data.get("gates") != expected_gates:
        raise ValueError("release gates drifted")

    releases = data.get("releases")
    if not isinstance(releases, list) or len(releases) != 10:
        raise ValueError("release manifest must contain exactly ten maintained releases")
    if [entry.get("slug") for entry in releases] != list(EXPECTED_RELEASES):
        raise ValueError("release order or slug set drifted")
    required_release_fields = {
        "slug",
        "name",
        "version",
        "source_path",
        "changelog",
        "tags",
        "categories",
        "topics",
    }
    for release in releases:
        if not isinstance(release, dict) or set(release) != required_release_fields:
            raise ValueError("release entry schema drifted")
        slug = release["slug"]
        version, source_path = EXPECTED_RELEASES[slug]
        if release["version"] != version or release["source_path"] != source_path:
            raise ValueError(f"release version or source path drifted for {slug}")
        if slug in PROHIBITED_SLUGS:
            raise ValueError("prohibited stale or deprecated slug entered the release batch")
        if not isinstance(release["name"], str) or not release["name"].strip():
            raise ValueError(f"release name missing for {slug}")
        if not isinstance(release["changelog"], str) or len(release["changelog"]) > 500:
            raise ValueError(f"release changelog invalid for {slug}")
        if release["tags"] != ["latest"]:
            raise ValueError(f"release tags drifted for {slug}")
        categories = release["categories"]
        if (
            not isinstance(categories, list)
            or not 1 <= len(categories) <= 3
            or len(categories) != len(set(categories))
            or set(categories) - ALLOWED_CATEGORIES
        ):
            raise ValueError(f"release categories invalid for {slug}")
        topics = release["topics"]
        if (
            not isinstance(topics, list)
            or not 1 <= len(topics) <= 5
            or len(topics) != len(set(topics))
        ):
            raise ValueError(f"release topics invalid for {slug}")
        for topic in topics:
            if (
                not isinstance(topic, str)
                or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic)
                or len(topic) > 48
                or topic in RESERVED_TOPICS
            ):
                raise ValueError(f"release topic invalid or reserved for {slug}: {topic}")
    if releases != list(EXPECTED_RELEASE_SPECS):
        raise ValueError("release specifications drifted from the immutable ten-entry contract")

    if data.get("deprecations") != [
        {
            "slug": "sysadmin-toolbox",
            "published_version": "1.1.0",
            "plan": "approval-only-deprecation-or-hide",
            "executable_registry_action": False,
            "replacement_in_this_batch": False,
        }
    ]:
        raise ValueError("sysadmin-toolbox must remain one approval-only deprecation plan")
    if data.get("prohibited_without_separate_approval") != [
        "ClawHub migration",
        "ClawHub rename",
        "ClawHub merge",
        "ClawHub hide",
        "ClawHub delete",
        "ClawHub transfer",
    ]:
        raise ValueError("prohibited registry action list or order drifted")


def validate_public_baseline(
    baseline: dict[str, Any], template: dict[str, Any]
) -> None:
    if baseline != EXPECTED_PUBLIC_BASELINE:
        raise ValueError("public baseline immutable snapshot drifted")
    expected_top_level = {
        "captured_at",
        "publisher",
        "source_repository",
        "source_commit",
        "notes",
        "skills",
        "external_replacement",
    }
    if set(baseline) != expected_top_level:
        raise ValueError("public baseline schema drifted")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(baseline.get("captured_at", ""))):
        raise ValueError("public baseline date must use YYYY-MM-DD")
    if baseline.get("publisher") != template["release_batch"]["publisher"]:
        raise ValueError("public baseline publisher drifted from the release manifest")
    if baseline.get("source_repository") != template["source"]["repository"]:
        raise ValueError("public baseline source repository drifted")
    if not re.fullmatch(r"[0-9a-f]{40}", str(baseline.get("source_commit", ""))):
        raise ValueError("public baseline source commit must be a full lowercase SHA")

    skills = baseline.get("skills")
    if not isinstance(skills, list) or len(skills) != 11:
        raise ValueError("public baseline must contain ten maintained skills and sysadmin-toolbox")
    by_slug = {entry.get("slug"): entry for entry in skills if isinstance(entry, dict)}
    if set(by_slug) != set(EXPECTED_RELEASES) | {"sysadmin-toolbox"}:
        raise ValueError("public baseline skill set drifted")
    release_by_slug = {entry["slug"]: entry for entry in template["releases"]}
    for slug, baseline_version in EXPECTED_BASELINE_VERSIONS.items():
        entry = by_slug[slug]
        if entry.get("version") != baseline_version:
            raise ValueError(f"public baseline version drifted for {slug}")
        if entry.get("source_path") != EXPECTED_RELEASES[slug][1]:
            raise ValueError(f"public baseline source path drifted for {slug}")
        if _semver_tuple(release_by_slug[slug]["version"]) <= _semver_tuple(baseline_version):
            raise ValueError(f"target version must advance the public baseline for {slug}")
    sysadmin = by_slug["sysadmin-toolbox"]
    if (
        sysadmin.get("version") != "1.1.0"
        or sysadmin.get("source_path") is not None
        or sysadmin.get("release_action") != "approval-gated-hide-and-deprecate"
    ):
        raise ValueError("sysadmin-toolbox baseline decision drifted")
    external = baseline.get("external_replacement")
    if not isinstance(external, dict) or external.get("slug") != "nutrient-document-processing-universal":
        raise ValueError("external stale universal baseline identity drifted")
    if external["slug"] in release_by_slug:
        raise ValueError("external stale universal slug must not enter this release batch")


def validate_ignore_rules(source_path: str, rules: list[str]) -> None:
    expected = EXPECTED_IGNORE_RULES.get(source_path)
    if expected is None:
        raise ValueError(f"release package has no immutable ignore profile: {source_path}")
    if rules != list(expected):
        raise ValueError(f"release package ignore rules or order drifted: {source_path}")


def validate_package_layout(template: dict[str, Any]) -> None:
    for release in template["releases"]:
        package = REPO_ROOT / release["source_path"]
        if not package.is_dir():
            raise ValueError(f"release package directory missing: {release['source_path']}")
        if not (package / "SKILL.md").is_file():
            raise ValueError(f"release package SKILL.md missing: {release['source_path']}")
        ignore_path = package / ".clawhubignore"
        if not ignore_path.is_file():
            raise ValueError(f"release package .clawhubignore missing: {release['source_path']}")
        rules = ignore_path.read_text(encoding="utf-8").splitlines()
        validate_ignore_rules(release["source_path"], rules)


def canonical_publish_tokens(release: dict[str, Any], *, dry_run: bool) -> list[str]:
    tokens = [
        "clawhub",
        "--no-input",
        "skill",
        "publish",
        release["source_path"],
        "--slug",
        release["slug"],
        "--name",
        release["name"],
        "--owner",
        "jdrhyne",
        "--version",
        release["version"],
        "--changelog",
        release["changelog"],
        "--tags",
        ",".join(release["tags"]),
        "--categories",
        ",".join(release["categories"]),
        "--topics",
        ",".join(release["topics"]),
        "--source-repo",
        "jdrhyne/agent-skills",
        "--source-commit",
        "$GITHUB_SHA",
        "--source-ref",
        "$GITHUB_REF",
        "--source-path",
        release["source_path"],
    ]
    if dry_run:
        tokens.append("--dry-run")
    tokens.append("--json")
    return tokens


def _shell_token(token: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./,:=@+-]+", token) and not token.startswith("$"):
        return token
    return json.dumps(token)


def canonical_publish_line(release: dict[str, Any], *, dry_run: bool) -> str:
    tokens = canonical_publish_tokens(release, dry_run=dry_run)
    rendered: list[str] = []
    for index, token in enumerate(tokens):
        if index and tokens[index - 1] in {"--name", "--changelog"}:
            rendered.append(json.dumps(token))
        else:
            rendered.append(_shell_token(token))
    return " ".join(rendered)


def extract_publish_commands(workflow: str) -> list[list[str]]:
    commands: list[list[str]] = []
    for line in workflow.splitlines():
        if re.match(r"^\s*clawhub\s+--no-input\s+skill\s+publish\b", line):
            commands.append(shlex.split(line.strip()))
    return commands


def _load_unique_workflow(workflow: str) -> dict[str, Any]:
    try:
        document = yaml.load(workflow, Loader=UniqueKeyLoader)
    except (yaml.YAMLError, ValueError) as exc:
        raise ValueError(f"release workflow is not valid unique-key YAML: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
        raise ValueError("release workflow must define a jobs mapping")
    return document


def _expected_document_controls() -> dict[Any, Any]:
    return {
        "name": "ClawHub ten-skill release",
        True: {
            "workflow_dispatch": {
                "inputs": {
                    "mode": {
                        "description": "Validate only, preview all ten skills, or publish after every gate",
                        "required": True,
                        "default": "validate",
                        "type": "choice",
                        "options": ["validate", "dry-run", "publish"],
                    },
                    "expected_source_commit": {
                        "description": "Full 40-character commit expected to be published (required for publish)",
                        "required": False,
                        "type": "string",
                    },
                    "publish_confirmation": {
                        "description": "Exact SHA-bound batch confirmation from the release guide (required for publish)",
                        "required": False,
                        "type": "string",
                    },
                }
            }
        },
        "permissions": {"contents": "read"},
        "concurrency": {
            "group": "clawhub-agent-skills-release",
            "cancel-in-progress": False,
        },
    }


def _expected_job_controls() -> dict[str, dict[str, Any]]:
    return {
        "validate": {"runs-on": "ubuntu-latest", "timeout-minutes": 20},
        "preview": {
            "if": "inputs.mode == 'dry-run' || inputs.mode == 'publish'",
            "needs": "validate",
            "runs-on": "ubuntu-latest",
            "timeout-minutes": 20,
        },
        "publish": {
            "if": "inputs.mode == 'publish'",
            "needs": "preview",
            "runs-on": "ubuntu-latest",
            "timeout-minutes": 20,
            "environment": "clawhub-production",
        },
    }


def _expected_step_surfaces() -> dict[str, list[tuple[str, str]]]:
    return {
        "validate": [
            ("Check out the exact workflow commit", "actions/checkout@v4"),
            ("Set up pinned Python", "actions/setup-python@v5"),
            ("Set up pinned Node.js", "actions/setup-node@v4"),
            ("Install pinned validation tools", "run"),
            ("Verify source and CLI provenance", "run"),
            ("Run offline release validation", "run"),
            ("Render exact release manifest", "run"),
            ("Upload release provenance", "actions/upload-artifact@v4"),
        ],
        "preview": [
            ("Check out the exact workflow commit", "actions/checkout@v4"),
            ("Set up pinned Node.js", "actions/setup-node@v4"),
            ("Install pinned ClawHub CLI", "run"),
            ("Verify preview provenance", "run"),
            ("Preview exact ten-skill batch", "run"),
        ],
        "publish": [
            ("Check out the exact workflow commit", "actions/checkout@v4"),
            ("Set up pinned Node.js", "actions/setup-node@v4"),
            ("Install pinned ClawHub CLI", "run"),
            ("Enforce human publication gates", "run"),
            ("Create owner-only ClawHub auth config", "run"),
            ("Verify ClawHub authentication", "run"),
            ("Publish exact ten-skill batch", "run"),
            ("Remove temporary ClawHub auth config", "run"),
        ],
    }


def _expected_step_metadata() -> dict[tuple[str, str], dict[str, Any]]:
    checkout = {
        "name": "Check out the exact workflow commit",
        "uses": "actions/checkout@v4",
        "with": {
            "ref": "${{ github.sha }}",
            "fetch-depth": 0,
            "persist-credentials": False,
        },
    }
    node = {
        "name": "Set up pinned Node.js",
        "uses": "actions/setup-node@v4",
        "with": {"node-version": "22.16.0"},
    }
    config_env = {"CLAWHUB_CONFIG_PATH": "${{ runner.temp }}/clawhub/config.json"}
    return {
        ("validate", "Check out the exact workflow commit"): checkout,
        ("validate", "Set up pinned Python"): {
            "name": "Set up pinned Python",
            "uses": "actions/setup-python@v5",
            "with": {"python-version": "3.12.7"},
        },
        ("validate", "Set up pinned Node.js"): node,
        ("validate", "Install pinned validation tools"): {"name": "Install pinned validation tools"},
        ("validate", "Verify source and CLI provenance"): {
            "name": "Verify source and CLI provenance",
            "env": {
                "EXPECTED_REPOSITORY": "jdrhyne/agent-skills",
                "EXPECTED_CLAWHUB_VERSION": "0.23.3",
            },
        },
        ("validate", "Run offline release validation"): {"name": "Run offline release validation"},
        ("validate", "Render exact release manifest"): {"name": "Render exact release manifest"},
        ("validate", "Upload release provenance"): {
            "name": "Upload release provenance",
            "uses": "actions/upload-artifact@v4",
            "with": {
                "name": "clawhub-release-provenance-${{ github.sha }}",
                "path": "${{ runner.temp }}/clawhub-release-manifest.json",
                "if-no-files-found": "error",
            },
        },
        ("preview", "Check out the exact workflow commit"): checkout,
        ("preview", "Set up pinned Node.js"): node,
        ("preview", "Install pinned ClawHub CLI"): {"name": "Install pinned ClawHub CLI"},
        ("preview", "Verify preview provenance"): {"name": "Verify preview provenance"},
        ("preview", "Preview exact ten-skill batch"): {"name": "Preview exact ten-skill batch"},
        ("publish", "Check out the exact workflow commit"): checkout,
        ("publish", "Set up pinned Node.js"): node,
        ("publish", "Install pinned ClawHub CLI"): {"name": "Install pinned ClawHub CLI"},
        ("publish", "Enforce human publication gates"): {
            "name": "Enforce human publication gates",
            "env": {
                "EXPECTED_SOURCE_COMMIT": "${{ inputs.expected_source_commit }}",
                "PUBLISH_CONFIRMATION": "${{ inputs.publish_confirmation }}",
                "REQUIRED_CONFIRMATION_PREFIX": "PUBLISH 10 CLAWHUB SKILLS FROM",
                "CLAWHUB_RELEASE_ENABLED": "${{ vars.CLAWHUB_RELEASE_ENABLED }}",
            },
        },
        ("publish", "Create owner-only ClawHub auth config"): {
            "name": "Create owner-only ClawHub auth config",
            "env": {
                "CLAWHUB_PUBLISH_TOKEN": "${{ secrets.CLAWHUB_TOKEN }}",
                **config_env,
            },
        },
        ("publish", "Verify ClawHub authentication"): {
            "name": "Verify ClawHub authentication",
            "env": config_env,
        },
        ("publish", "Publish exact ten-skill batch"): {
            "name": "Publish exact ten-skill batch",
            "env": config_env,
        },
        ("publish", "Remove temporary ClawHub auth config"): {
            "name": "Remove temporary ClawHub auth config",
            "if": "always()",
            "env": config_env,
        },
    }


def _expected_run_bodies(template: dict[str, Any]) -> dict[tuple[str, str], str]:
    preview_lines = "\n".join(
        canonical_publish_line(release, dry_run=True)
        for release in template["releases"]
    )
    publish_lines = "\n".join(
        canonical_publish_line(release, dry_run=False)
        for release in template["releases"]
    )
    return {
        ("validate", "Install pinned validation tools"): (
            "python -m pip install --disable-pip-version-check PyYAML==6.0.2\n"
            "npm install --global clawhub@0.23.3\n"
        ),
        ("validate", "Verify source and CLI provenance"): (
            "set -euo pipefail\n"
            'test "$GITHUB_REPOSITORY" = "$EXPECTED_REPOSITORY"\n'
            'test "$(clawhub --cli-version)" = "$EXPECTED_CLAWHUB_VERSION"\n'
        ),
        ("validate", "Run offline release validation"): (
            "set -euo pipefail\n"
            "python scripts/clawhub_release.py validate\n"
            "python -m unittest discover -s scripts/tests -p 'test_clawhub_release.py' -v\n"
            "./scripts/validate-skills.sh\n"
        ),
        ("validate", "Render exact release manifest"): (
            "python scripts/clawhub_release.py render \\\n"
            '  --commit "$GITHUB_SHA" \\\n'
            '  --ref "$GITHUB_REF" \\\n'
            '  --output "$RUNNER_TEMP/clawhub-release-manifest.json"\n'
        ),
        ("preview", "Install pinned ClawHub CLI"): "npm install --global clawhub@0.23.3",
        ("preview", "Verify preview provenance"): (
            "set -euo pipefail\n"
            'test "$GITHUB_REPOSITORY" = "jdrhyne/agent-skills"\n'
            'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"\n'
            'test "$(clawhub --cli-version)" = "0.23.3"\n'
        ),
        ("preview", "Preview exact ten-skill batch"): f"set -euo pipefail\n{preview_lines}\n",
        ("publish", "Install pinned ClawHub CLI"): "npm install --global clawhub@0.23.3",
        ("publish", "Enforce human publication gates"): (
            "set -euo pipefail\n"
            '[[ "$EXPECTED_SOURCE_COMMIT" =~ ^[0-9a-f]{40}$ ]]\n'
            'test "$GITHUB_REPOSITORY" = "jdrhyne/agent-skills"\n'
            'test "$GITHUB_REF" = "refs/heads/main"\n'
            'test "$(git rev-parse HEAD)" = "$GITHUB_SHA"\n'
            'test "$EXPECTED_SOURCE_COMMIT" = "$GITHUB_SHA"\n'
            'test "$PUBLISH_CONFIRMATION" = "$REQUIRED_CONFIRMATION_PREFIX $GITHUB_SHA"\n'
            'test "$CLAWHUB_RELEASE_ENABLED" = "true"\n'
            'test "$(clawhub --cli-version)" = "0.23.3"\n'
        ),
        ("publish", "Create owner-only ClawHub auth config"): (
            "set -euo pipefail\n"
            'test -n "$CLAWHUB_PUBLISH_TOKEN"\n'
            "umask 077\n"
            'mkdir -p "$(dirname "$CLAWHUB_CONFIG_PATH")"\n'
            'chmod 700 "$(dirname "$CLAWHUB_CONFIG_PATH")"\n'
            "node -e '\n"
            '  const fs = require("node:fs");\n'
            "  const token = process.env.CLAWHUB_PUBLISH_TOKEN;\n"
            "  const configPath = process.env.CLAWHUB_CONFIG_PATH;\n"
            "  if (!token || !configPath) process.exit(1);\n"
            "  fs.writeFileSync(\n"
            "    configPath,\n"
            '    `${JSON.stringify({ registry: "https://clawhub.ai", token }, null, 2)}\\n`,\n'
            '    { encoding: "utf8", mode: 0o600, flag: "wx" },\n'
            "  );\n"
            "  fs.chmodSync(configPath, 0o600);\n"
            "'\n"
            'test "$(stat -c \'%a\' "$CLAWHUB_CONFIG_PATH")" = "600"\n'
        ),
        ("publish", "Verify ClawHub authentication"): "clawhub --no-input whoami",
        ("publish", "Publish exact ten-skill batch"): f"set -euo pipefail\n{publish_lines}\n",
        ("publish", "Remove temporary ClawHub auth config"): (
            "set -euo pipefail\n"
            'rm -f -- "$CLAWHUB_CONFIG_PATH"\n'
            'rmdir -- "$(dirname "$CLAWHUB_CONFIG_PATH")" 2>/dev/null || true\n'
        ),
    }


def validate_workflow_publish_contract(workflow: str, template: dict[str, Any]) -> None:
    forbidden = {
        "stale or deprecated slug": r"(?:sysadmin-toolbox|nutrient-document-processing-universal)",
        "owner migration": r"--migrate-owner\b|--source-owner\b",
        "registry mutation command": r"(?im)^\s*(?:run:\s*)?(?:clawhub|\$\([^\n]*clawhub)[^\n]*\b(?:sync|hide|delete|rename|merge|transfer)\b",
        "legacy publish alias": r"(?im)^\s*(?:run:\s*)?clawhub\s+--no-input\s+publish\b",
        "token command or token argv": r"(?im)^\s*clawhub\b[^\n]*(?:\btoken\b|login[^\n]*--token)",
        "secret value printing": r"(?im)^\s*(?:echo|printf)\b[^\n]*(?:CLAWHUB_PUBLISH_TOKEN|CLAWHUB_TOKEN)|\bconsole\.log\s*\([^\n]*\btoken\b",
        "raw authorization header": r"(?i)authorization\s*:\s*bearer",
        "authenticated curl": r"(?im)^\s*curl\b[^\n]*(?:authorization|token)",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, workflow):
            raise ValueError(f"release workflow contains forbidden {label}")

    document = _load_unique_workflow(workflow)
    controls = {key: value for key, value in document.items() if key != "jobs"}
    if controls != _expected_document_controls():
        raise ValueError("release workflow trigger, input, permission, or concurrency controls drifted")
    expected_job_controls = _expected_job_controls()
    expected_surfaces = _expected_step_surfaces()
    if set(document["jobs"]) != set(expected_surfaces):
        raise ValueError("release workflow job surface drifted")

    step_metadata: dict[tuple[str, str], dict[str, Any]] = {}
    run_bodies: dict[tuple[str, str], str] = {}
    for job_name, expected_surface in expected_surfaces.items():
        job = document["jobs"][job_name]
        if not isinstance(job, dict) or not isinstance(job.get("steps"), list):
            raise ValueError(f"release workflow job shape drifted: {job_name}")
        controls = {key: value for key, value in job.items() if key != "steps"}
        if controls != expected_job_controls[job_name]:
            raise ValueError(f"release workflow job controls drifted: {job_name}")
        actual_surface: list[tuple[str, str]] = []
        for step in job["steps"]:
            if not isinstance(step, dict) or not isinstance(step.get("name"), str):
                raise ValueError("every release workflow step must have an exact name")
            name = step["name"]
            key = (job_name, name)
            if key in step_metadata:
                raise ValueError("release workflow contains duplicate step names")
            step_metadata[key] = {item: value for item, value in step.items() if item != "run"}
            if "run" in step:
                if "uses" in step or not isinstance(step["run"], str):
                    raise ValueError("release workflow run step shape drifted")
                kind = "run"
                run_bodies[key] = step["run"]
            elif isinstance(step.get("uses"), str):
                kind = step["uses"]
            else:
                raise ValueError("release workflow step must use an allowlisted action or run")
            actual_surface.append((name, kind))
        if actual_surface != expected_surface:
            raise ValueError(f"release workflow step surface drifted: {job_name}")

    if step_metadata != _expected_step_metadata():
        raise ValueError("release workflow action, env, if, or with metadata drifted")
    expected_runs = _expected_run_bodies(template)
    if set(run_bodies) != set(expected_runs):
        raise ValueError("release workflow run-step surface drifted")
    for key, expected in expected_runs.items():
        if run_bodies[key] != expected:
            raise ValueError(f"release workflow run body drifted: {key[0]} / {key[1]}")

    commands = extract_publish_commands(workflow)
    if len(commands) != 20:
        raise ValueError("release workflow must contain exactly 20 canonical publish commands")
    expected_commands = [
        canonical_publish_tokens(release, dry_run=True)
        for release in template["releases"]
    ] + [
        canonical_publish_tokens(release, dry_run=False)
        for release in template["releases"]
    ]
    if commands != expected_commands:
        raise ValueError("preview or publish command tokens differ from the canonical manifest")


def validate_deprecation_document(path: Path = DEFAULT_DEPRECATION) -> None:
    text = path.read_text(encoding="utf-8")
    if "approval-only" not in text.lower() or "separate" not in text.lower():
        raise ValueError("sysadmin-toolbox deprecation must remain explicitly approval-only")
    if re.search(
        r"(?im)^\s*(?:\$\s*)?clawhub\b[^\n]*\b(?:hide|delete|skill\s+(?:rename|merge))\b",
        text,
    ):
        raise ValueError("sysadmin-toolbox document contains an executable registry mutation command")


def validate_repository_contract() -> None:
    template = load_template()
    validate_public_baseline(load_public_baseline(), template)
    validate_package_layout(template)
    validate_deprecation_document()
    validate_workflow_publish_contract(DEFAULT_WORKFLOW.read_text(encoding="utf-8"), template)


def _replace_runtime_values(value: Any, commit: str, ref: str) -> Any:
    if isinstance(value, dict):
        return {key: _replace_runtime_values(item, commit, ref) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_runtime_values(item, commit, ref) for item in value]
    if value == COMMIT_SENTINEL:
        return commit
    if value == REF_SENTINEL:
        return ref
    return value


def render_manifest(template: dict[str, Any], commit: str, ref: str) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("source commit must be a full lowercase 40-character SHA")
    if not ref.startswith("refs/") or any(character.isspace() for character in ref):
        raise ValueError("source ref must be an exact refs/... value without whitespace")
    rendered = _replace_runtime_values(template, commit, ref)
    serialized = json.dumps(rendered, sort_keys=True)
    if COMMIT_SENTINEL in serialized or REF_SENTINEL in serialized:
        raise ValueError("runtime provenance sentinels were not fully replaced")
    return rendered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="Validate the offline release contract")
    render = subparsers.add_parser("render", help="Render exact runtime provenance")
    render.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    render.add_argument("--commit", required=True)
    render.add_argument("--ref", required=True)
    render.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    if args.command == "validate":
        validate_repository_contract()
        print("ClawHub release contract is valid")
        return 0

    rendered = render_manifest(load_template(args.template), args.commit, args.ref)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rendered, indent=2) + "\n", encoding="utf-8")
    print(f"Rendered exact release manifest: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
