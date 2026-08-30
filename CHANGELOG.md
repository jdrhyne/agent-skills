# Changelog

## [Unreleased]

### Added

- feat(skills): add a tested TweetClaw workflow for bounded X research and approval-gated account actions.
- feat(release): add a schema-versioned ten-skill ClawHub manifest with exact source provenance and bounded catalog metadata.
- feat(release): add manual validation, dry-run preview, and independently gated production publication jobs.
- test(release): add fail-closed structural, token-level, authentication-config, and adversarial release regression coverage.

### Changed

- fix(skills): harden Google Ads, Jira, Context Recovery, Nudocs, Nutrient OpenClaw, Todo Tracker, GSC, GA4, Munger Observer, and Gong for their planned versions.
- chore(packaging): exclude tests, Python caches, compiled Python, and stale local ClawHub metadata from all ten release packages.
- docs(release): record public baselines, external reviewer requirements, SHA-bound confirmation, and the approval-only sysadmin-toolbox deprecation boundary.

### Security

- security(release): keep registry credentials out of arguments and output, require an owner-only temporary config, and remove it after gated publication.
- security(release): reject unreviewed jobs, steps, command aliases, computed executables, stale slugs, migrations, and destructive registry commands.
