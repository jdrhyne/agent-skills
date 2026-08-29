# Jira CLI adapter

Read this file only when the configured `jira` CLI is the selected backend.

## Establish the current CLI contract

Before constructing a command:

1. Resolve the executable with `command -v jira`.
2. Inspect `jira version` and the relevant `--help` output.
3. Confirm that the installed version supports the intended operation and input method.
4. Use the CLI's existing authenticated configuration. If authentication fails, stop and ask the user to complete `jira init` interactively; never ask them to paste a token.

Do not infer flag support from this reference. The CLI evolves, and server-specific workflows and fields are authoritative.

## Read operations

Common read-only shapes include:

```bash
jira issue view PROJ-123
jira issue view PROJ-123 --raw
jira issue list --plain --no-headers
jira sprint list --state active
jira project list
jira me
```

Validate issue keys before passing them. Inspect help before adding filters, columns, pagination, or JQL flags. State the result limit and paginate only as far as the user's request requires.

## Preparing a write

The shared mutation contract in `SKILL.md` applies before any CLI write.

- Fetch the current issue with structured/raw output when available.
- Inspect project and operation help for required fields.
- For transitions, inspect the issue's valid next states; do not guess a universal status name.
- For assignments, use the identifier form accepted by this configured CLI and verify the resolved account.
- Present the exact command semantics and current/proposed diff, but omit authentication material and protected local paths.

After approval, invoke the executable directly with each validated value as a separate argument. Do not assemble a command string for `eval`, `sh -c`, or another shell interpreter.

## Multi-line and untrusted text

Never use command substitution or string concatenation to embed a description, comment, JQL value, or issue content into a command.

When the installed CLI supports stdin or a template/file flag:

1. Create a task-specific temporary file with mode `0600`.
2. Write exactly the approved content.
3. Pass the file path as one argument, or provide the content on stdin.
4. Remove the temporary file after the command completes.

If the CLI has no non-interpolating input path for the required content, use a capable authenticated connector or stop. Do not downgrade to an inline token or raw REST command.

## Mutation-specific checks

### Create

- Search for likely duplicates.
- Discover project, issue type, required fields, and allowed values.
- Show every proposed field; optional fields not shown must remain unset.
- Do not use non-interactive mode until all required fields are known.

### Edit or assign

- Read each affected field first.
- Show full current and proposed values.
- Do not combine an assignment, field edit, or comment unless each was requested and displayed.

### Transition

- Fetch current state and available transitions immediately before approval.
- Show the selected transition and any resolution or field changes it performs.
- Do not attach a comment automatically.

### Comment, link, or sprint mutation

- Treat each as a representational write.
- Resolve exact targets and relationship direction.
- Show the precise comment or relationship before approval.

## Verification and errors

Re-read the issue after each approved write. If a batch partially fails, stop, report completed and untouched keys separately, and generate a new diff before retrying.

Authentication, permission, required-field, or workflow errors are not reasons to expose credentials, broaden access, or add hidden fields. Report the error and the narrowest user-controlled remediation.
