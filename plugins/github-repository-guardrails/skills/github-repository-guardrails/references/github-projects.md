# GitHub CLI and GitHub Projects

This reference contains volatile command and schema details. Check the installed `gh` help before a write, use validated arguments rather than concatenated shell text, and retain only the minimum selected fields in ephemeral task state.

## Bind the target explicitly

Resolve the selected Git remote to these ephemeral values before GitHub access:

- `GITHUB_HOST`: the exact GitHub host.
- `GITHUB_OWNER` and `REPOSITORY_NAME`: the repository coordinates.
- `REPOSITORY_SELECTOR`: the explicit `[HOST/]OWNER/REPO` selector accepted by the installed GitHub CLI.
- `PROJECT_OWNER`: the independently resolved owner of a selected Project; it need not equal `GITHUB_OWNER`.

Preview `GITHUB_HOST` and `REPOSITORY_SELECTOR` to the user before a write. If multiple remotes are plausible, stop and ask which repository is in scope.

Bind each invocation to the resolved host for that process. In current GitHub CLI syntax, prefix every command with `GH_HOST=GITHUB_HOST`; do not export it as unrelated shell-session state. Pass `REPOSITORY_SELECTOR` to every repository, issue, and pull-request command using its explicit repository argument or `--repo` flag. Never let those commands infer the repository from the working directory. Examples below are argument shapes, not shell text to concatenate:

```text
GH_HOST=GITHUB_HOST gh repo view REPOSITORY_SELECTOR ...
GH_HOST=GITHUB_HOST gh issue list --repo REPOSITORY_SELECTOR ...
GH_HOST=GITHUB_HOST gh pr list --repo REPOSITORY_SELECTOR ...
```

Every `gh project` invocation, including reads, creation, linking, field or item operations, and edits, must carry the same process-scoped `GH_HOST=GITHUB_HOST` binding. For a Projects GraphQL or REST fallback, bind `gh api` to the same host with the installed CLI's explicit host option or the same process-scoped environment value. Do not rely on the active account's default host.

## Access model

GitHub CLI can use stored credentials or environment-token authentication; never display either. Treat these capabilities independently:

- Repository metadata and issue access.
- GitHub Projects read access, which can require `read:project`.
- GitHub Projects write access, which can require `project`.

Use `gh auth status --active --hostname GITHUB_HOST` only as an exit-status check and discard its output. If Projects access is missing, report that precise limitation. Offer to skip Projects or ask whether the user wants to update authentication. Never run `gh auth refresh` or otherwise change stored scopes without explicit authorization.

## Split discovery

Run repository discovery first so a Project-scope failure cannot hide otherwise accessible metadata. Query the explicit target with selected JSON fields equivalent to:

```text
GH_HOST=GITHUB_HOST gh repo view REPOSITORY_SELECTOR --json nameWithOwner,visibility,defaultBranchRef
```

Then query explicitly linked Projects separately, still against the same target and host:

```text
GH_HOST=GITHUB_HOST gh repo view REPOSITORY_SELECTOR --json projectsV2 --jq '{projects:(.projectsV2.Nodes // [])}'
```

`Nodes` is intentionally capitalized in the current GitHub CLI JSON shape. Filter closed Projects after parsing the selected fields. Do not count the `projectsV2` wrapper as a Project.

Treat this repository-view query as an initial signal unless the returned connection proves that all linked nodes were fetched. For setup or audit conclusions, compare the node count with an exposed total when available; otherwise use an explicitly host-bound GraphQL query with a declared page size, cursor pagination, and termination on `hasNextPage=false`. Never infer that no link exists from a possibly truncated connection.

Apply this routing:

- No compatible GitHub remote or no repository access: continue with local-only guardrails.
- Projects access unavailable: explain that repository discovery succeeded, then offer to skip or request authorization for the needed scope.
- One compatible open linked Project: propose it as a candidate authority.
- Several compatible open linked Projects: present selected evidence and ask the user to choose.
- No compatible open linked Project: record only that no explicit link was found, then continue with authority discovery below. Do not offer creation yet.

Discovery is read-only. Project creation, linking, visibility, fields, and item changes are separate mutations.

## Distinguish linkage from authority

A Project can govern work without being explicitly linked to the repository. Before concluding that no Project authority exists:

1. Inspect repository instructions, management configuration, issue or pull-request conventions, and other selected local evidence for an existing Project authority.
2. Enumerate accessible Projects for `GITHUB_OWNER` with an explicit adequate limit. Inspect only plausible candidates, with bounded field and item queries.
3. Ask whether a user-owned, unlinked, or cross-organization Project is authoritative. If the user identifies another owner, inspect that `PROJECT_OWNER` with the same host binding and explicit limits.
4. Treat inaccessible or unsearched owners as uncertainty, not proof that no Project exists.

Current GitHub CLI argument shapes include:

```text
GH_HOST=GITHUB_HOST gh project list --owner PROJECT_OWNER --closed --limit PROJECT_SCAN_LIMIT --format json
GH_HOST=GITHUB_HOST gh project field-list PROJECT_NUMBER --owner PROJECT_OWNER --limit FIELD_SCAN_LIMIT --format json
GH_HOST=GITHUB_HOST gh project item-list PROJECT_NUMBER --owner PROJECT_OWNER --limit ITEM_SCAN_LIMIT --format json
```

When supported, a narrow item query can reduce the candidate set, but its limit must still be explicit and sufficient for the claim being made. Reuse or offer to link a compatible unlinked authority. Offer creation only after repository evidence, accessible candidates, and the user's cross-organization knowledge leave no compatible authority.

## Complete enumeration and duplicate checks

The current CLI defaults for issue and Project lists are bounded and are not evidence of completeness. Choose explicit limits from an observed total or a conservative bound suitable for the repository. Compare returned counts with `totalCount` when the command exposes it. If a result reaches its limit without a confirming total, increase the limit or use an explicitly host-bound paginated API query. If complete enumeration is impractical, label the result partial and state the inspected bound.

Use explicit target and limit arguments equivalent to:

```text
GH_HOST=GITHUB_HOST gh issue list --repo REPOSITORY_SELECTOR --state all --search SEARCH_QUERY --limit ISSUE_SCAN_LIMIT --json number,title,state,url
GH_HOST=GITHUB_HOST gh pr list --repo REPOSITORY_SELECTOR --state all --limit PR_SCAN_LIMIT --json number,title,state,url
GH_HOST=GITHUB_HOST gh project list --owner PROJECT_OWNER --closed --limit PROJECT_SCAN_LIMIT --format json
GH_HOST=GITHUB_HOST gh project field-list PROJECT_NUMBER --owner PROJECT_OWNER --limit FIELD_SCAN_LIMIT --format json
GH_HOST=GITHUB_HOST gh project item-list PROJECT_NUMBER --owner PROJECT_OWNER --limit ITEM_SCAN_LIMIT --format json
```

Search open and closed issues before creating a new one. A duplicate search must cover enough issues to support the conclusion; a default-size first page is never sufficient for a repository-wide "no duplicate" claim. Apply the same completeness rule to audit inventories of issues, pull requests, Projects, fields, and items.

## Project creation and visibility

After the user authorizes the exact external actions and existing authority has been ruled out, use argument-safe invocations equivalent to:

```text
GH_HOST=GITHUB_HOST gh project create --owner PROJECT_OWNER --title PROJECT_TITLE --format json
GH_HOST=GITHUB_HOST gh project link PROJECT_NUMBER --owner PROJECT_OWNER --repo REPOSITORY_NAME
```

`gh project link` uses a repository-name argument in the current CLI. Before invoking it, preview the already resolved `REPOSITORY_SELECTOR`, verify the installed command's owner constraints, and do not assume that a cross-organization link is supported. The process-scoped host binding remains mandatory.

Treat Project visibility as a separate privacy decision. Do not infer it from repository visibility. Keep a newly created Project private unless the user explicitly chooses another supported visibility, then use a host-bound `gh project edit` or the host's supported equivalent.

Extract only the identifiers needed for the current task. Do not copy raw responses or discovered private URLs into generic configuration or public artifacts.

## Reuse fields before creating them

List all relevant fields with an explicit adequate limit, then inspect names, types, options, and built-in fields. Prefer the built-in `Status` as the single state authority unless the repository already uses another compatible convention.

Do not impose a universal `Stage`, `Priority`, `Size`, `Effort`, start-date, or target-date schema. Issue-level fields and Project fields can overlap. Propose a new field only when all of these are true:

1. The workflow has a concrete need for it.
2. No compatible existing issue or Project field already owns that meaning.
3. The proposed name, type, and options match the repository's vocabulary.
4. The user approves the exact field creation.

Use a host-bound `gh project field-create` only after those checks. Stop on a same-name incompatible field; never replace, duplicate, or normalize it silently.

## Work items

When an issue is the chosen scope authority, build its body in a temporary file outside the repository and pass the file as a single argument. Create, view, edit, close, or reopen it only with the explicit `REPOSITORY_SELECTOR` and host binding. Add the resulting issue URL to the selected Project only after the user authorizes both writes, and bind the `gh project item-add` operation to `GITHUB_HOST`.

Preserve the repository's identifier and lifecycle conventions. Do not require a `GH-` prefix, draft-item prohibition, custom status mapping, close reason, or definition of done unless the repository already uses it or the user explicitly adopts it.

Resolve item, field, and option identifiers immediately before an update. Keep them in ephemeral task state and select only the response fields required to verify the change.

## Audit boundary

Audit mode may use explicitly targeted, host-bound read operations such as:

```text
GH_HOST=GITHUB_HOST gh issue view ISSUE_NUMBER --repo REPOSITORY_SELECTOR --json number,title,state,url
GH_HOST=GITHUB_HOST gh pr view PULL_REQUEST_NUMBER --repo REPOSITORY_SELECTOR --json number,title,state,url
GH_HOST=GITHUB_HOST gh project field-list PROJECT_NUMBER --owner PROJECT_OWNER --limit FIELD_SCAN_LIMIT --format json
GH_HOST=GITHUB_HOST gh project item-list PROJECT_NUMBER --owner PROJECT_OWNER --limit ITEM_SCAN_LIMIT --format json
```

Enumerations must follow the completeness rules above. Audit mode must not create, edit, add, delete, close, reopen, archive, link, or change authentication.

## Current primary references

- [GitHub CLI manual](https://cli.github.com/manual/)
- [Using the API to manage Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [Best practices for Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects)
- [Managing Project visibility](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-visibility-of-your-projects)
