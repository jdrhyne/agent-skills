# `sysadmin-toolbox` approval-only deprecation plan

The public `jdrhyne/sysadmin-toolbox` version `1.1.0` fails the captured ClawHub verification baseline because ordinary routing can surface destructive, disruptive, and offensive-security commands without adequate authorization boundaries. Its bundled refresh helper also replaced references from an unpinned upstream branch.

The source was intentionally removed from this repository in commit `885b846`. Do not restore, package, publish, migrate, rename, merge, hide, or delete it as part of the ten-skill release batch.

## Separate approval gate

Any registry visibility change is an approval-only follow-up. It requires a separate user decision after the operator re-reads the exact publisher, slug, current version, present visibility, intended outcome, and recovery path at action time. This document intentionally contains no executable registry mutation command.

The release workflow and manifest cannot perform this deprecation. A future approved task must construct and review the exact operation from the then-current ClawHub CLI documentation; approval of the ten maintained releases does not authorize that task.

## Replacement boundary

A future replacement may cover defensive inventory, diagnostics, backup verification, patch planning, and read-only incident triage. It must not:

- auto-refresh from a moving branch;
- expose exploit or persistence instructions during ordinary administration;
- run disruptive, destructive, or privilege-changing commands without an exact preview and action-time approval;
- infer authorization for penetration testing from a generic troubleshooting request;
- embed copied command catalogs whose provenance and license cannot be verified.

The replacement is a separate design and release decision, not part of this batch.
