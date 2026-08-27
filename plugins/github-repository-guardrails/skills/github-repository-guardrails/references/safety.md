# Safety and public-data boundary

## Public-package contract

Keep these values as placeholders in reusable content:

- `GITHUB_HOST`
- `GITHUB_OWNER`
- `REPOSITORY_NAME`
- `PROJECT_NUMBER`
- `ISSUE_NUMBER`
- `PROJECT_URL`
- `WORK_ID`

Do not copy account names, private repository names or URLs, issue data, Project identifiers, prompts from another project, absolute personal paths, tokens, key material, or raw `gh` output into reusable skill files, examples, logs, or public artifacts. A target repository may retain its own non-secret identifiers only when its existing conventions or an explicit user decision require them.

## Prompt logging

Record intent, scope, and decisive constraints—not transcripts. Remove credentials, personal data, private URLs, names that are unnecessary to the task, and copied command output. When sanitization would remove essential meaning, ask the user for a safe summary.

## GitHub credentials and host

Derive the GitHub host from the selected repository remote. Use `gh auth status --active --hostname GITHUB_HOST` only as an exit-status check and discard its output. Environment-token authentication is valid in headless and automation contexts; do not remove it merely to prefer stored credentials. Never run token-display commands, dump environment variables, inspect credential stores, or read private-key material.

Treat authentication, repository access, and GitHub Projects scope as separate checks. A failed Project query can mean missing `read:project` permission even when repository access works. Never change stored authentication or add scopes without explicit user authorization.

Preserve the selected repository's configured Git transport and authentication method. Do not rewrite remotes or require SSH or HTTPS unless the user asks for that change.

## Filesystem reconciliation

Preview all selected files before writing. Create missing files, preserve identical files, append only a clearly marked instruction block when that is the selected strategy, and stop on ambiguous differences. Reject symbolic links, paths outside the target repository, and path traversal. A conflict means no setup writes until the user chooses how to resolve it.
