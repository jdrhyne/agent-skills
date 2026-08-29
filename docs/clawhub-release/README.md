# ClawHub ten-skill release gate

The `ClawHub ten-skill release` workflow is manual and defaults to validation only. Its schema-versioned source of truth is `release-manifest.template.json`, which records exactly ten maintained package slugs, versions, source paths, display names, changelogs, categories, and topics.

## Modes

- `validate` runs offline repository and release-contract checks, renders SHA-bound provenance, and does not call ClawHub authentication or publication commands.
- `dry-run` runs validation first, then previews all ten canonical publications with ClawHub's `--dry-run` mode at the exact workflow commit and ref. It cannot publish.
- `publish` can start only after the same workflow run's validation and ten-command preview jobs succeed. It then passes through the named production environment and the remaining human gates.

The workflow pins Python `3.12.7`, PyYAML `6.0.2`, Node.js `22.16.0`, and ClawHub CLI `0.23.3`. The validator rejects workflow drift, extra jobs or steps, duplicate YAML keys, noncanonical ClawHub command forms, and any mismatch in the 20 preview/publish command token lists.

## External GitHub configuration required before publication

An administrator must separately configure all of the following:

- Create the `clawhub-production` GitHub environment and configure required reviewers who are independent of the publishing operator. Merely naming the environment in workflow YAML does not add reviewer protection; environments without configured required reviewers do not provide this approval gate.
- Set the repository or `clawhub-production` environment variable `CLAWHUB_RELEASE_ENABLED` to exactly `true`. A missing value or any other value fails closed.
- Store the ClawHub credential as the `CLAWHUB_TOKEN` secret for the `clawhub-production` environment. Do not place it in an input, command argument, log, artifact, or manifest.

The future operator must select `publish`, enter the exact full 40-character workflow SHA as `expected_source_commit`, and enter `PUBLISH 10 CLAWHUB SKILLS FROM <same-full-sha>` as `publish_confirmation`. The publish job checks the repository, `refs/heads/main`, checked-out commit, both SHA inputs, the exact confirmation, release enablement, and CLI version.

The gated job writes `{ "registry": "https://clawhub.ai", "token": ... }` to a temporary mode-`600` file selected by `CLAWHUB_CONFIG_PATH`, verifies authentication with `whoami`, stops on the first failed publication, and removes the config in an always-run cleanup step. It never places the token on the command line or prints it.

The ten publications are sequential, not transactional. If a call fails after earlier versions were accepted, stop and record the exact successful and failed slugs. Do not rerun the whole batch or advance versions automatically; first re-read current registry state and prepare a separately reviewed recovery plan for only the unfinished entries.

## Package and provenance boundary

Every package directory must contain `SKILL.md` and `.clawhubignore`. The ignore contract excludes tests, Python bytecode caches, compiled Python files, and the stale local `_meta.json` installation record from publication. Runtime provenance replaces the manifest's commit and ref sentinels with the exact `github.sha` and `github.ref`; package paths cannot be substituted.

`public-baseline.json` remains the captured comparison for publisher, repository, public versions, and source paths. The historical `nutrient-document-processing-universal` package is external to this batch and cannot be republished or migrated by this workflow.

`sysadmin-toolbox@1.1.0` is not a release candidate. Its [approval-only deprecation plan](sysadmin-toolbox.md) contains no executable registry mutation command. Publishing the maintained batch does not authorize a hide, delete, rename, merge, transfer, migration, or replacement.

## Offline validation

```bash
python3 scripts/clawhub_release.py validate
python3 -m unittest discover -s scripts/tests -p 'test_clawhub_release.py' -v
./scripts/validate-skills.sh
```

These commands perform no ClawHub authentication, registry publication, visibility change, or paid service operation.
