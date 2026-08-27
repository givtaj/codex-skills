# GitHub CLI and GitHub Projects

This reference contains volatile command and schema details. Check the installed `gh` help before a write, use validated arguments rather than concatenated shell text, and retain only the minimum selected fields in ephemeral task state.

## Access model

Derive `GITHUB_HOST` and the repository from the configured remote. GitHub CLI can use stored credentials or environment-token authentication; never display either. Treat these capabilities independently:

- Repository metadata and issue access.
- GitHub Projects read access, which can require `read:project`.
- GitHub Projects write access, which can require `project`.

If Projects access is missing, report that precise limitation. Offer to skip Projects or ask whether the user wants to update authentication. Never run `gh auth refresh` or otherwise change stored scopes without explicit authorization.

## Split discovery

Run repository discovery first so a Project-scope failure cannot hide otherwise accessible metadata. From the target repository, use selected JSON fields equivalent to:

```text
gh repo view --json nameWithOwner,visibility,defaultBranchRef
```

Then query linked Projects separately:

```text
gh repo view --json projectsV2 --jq '{projects:(.projectsV2.Nodes // [])}'
```

`Nodes` is intentionally capitalized in the current GitHub CLI JSON shape. Filter closed Projects after parsing the selected fields. Do not count the `projectsV2` wrapper as a Project.

Apply this routing:

- No compatible GitHub remote or no repository access: continue with local-only guardrails.
- Projects access unavailable: explain that repository discovery succeeded, then offer to skip or request authorization for the needed scope.
- No compatible open linked Project: offer a creation-and-linking preview.
- One compatible open linked Project: propose reusing it.
- Several compatible open linked Projects: ask the user to select one.

Discovery is read-only. Project creation, linking, visibility, fields, and item changes are separate mutations.

## Project creation and visibility

After the user authorizes the exact external actions, use argument-safe invocations equivalent to:

```text
gh project create --owner GITHUB_OWNER --title PROJECT_TITLE --format json
gh project link PROJECT_NUMBER --owner GITHUB_OWNER --repo REPOSITORY_NAME
```

Treat Project visibility as a separate privacy decision. Do not infer it from repository visibility. Keep a newly created Project private unless the user explicitly chooses another supported visibility, then use `gh project edit` or the host's supported equivalent.

Extract only the identifiers needed for the current task. Do not copy raw responses or discovered private URLs into generic configuration or public artifacts.

## Reuse fields before creating them

List all relevant fields with an explicit limit large enough for the Project, then inspect names, types, options, and built-in fields. Prefer the built-in `Status` as the single state authority unless the repository already uses another compatible convention.

Do not impose a universal `Stage`, `Priority`, `Size`, `Effort`, start-date, or target-date schema. Issue-level fields and Project fields can overlap. Propose a new field only when all of these are true:

1. The workflow has a concrete need for it.
2. No compatible existing issue or Project field already owns that meaning.
3. The proposed name, type, and options match the repository's vocabulary.
4. The user approves the exact field creation.

Use `gh project field-create` only after those checks. Stop on a same-name incompatible field; never replace, duplicate, or normalize it silently.

## Work items

Search open and closed issues before creating a new one. When an issue is the chosen scope authority, build its body in a temporary file outside the repository and pass the file as a single argument. Add the resulting issue URL to the selected Project only after the user authorizes both writes.

Preserve the repository's identifier and lifecycle conventions. Do not require a `GH-` prefix, draft-item prohibition, custom status mapping, close reason, or definition of done unless the repository already uses it or the user explicitly adopts it.

Resolve item, field, and option identifiers immediately before an update. Keep them in ephemeral task state and select only the response fields required to verify the change.

## Audit boundary

Audit mode may use read operations such as repository discovery, `gh issue view`, `gh project field-list`, and `gh project item-list`. It must not create, edit, add, delete, close, reopen, archive, link, or change authentication.

## Current primary references

- [GitHub CLI manual](https://cli.github.com/manual/)
- [Using the API to manage Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)
- [Best practices for Projects](https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects)
- [Managing Project visibility](https://docs.github.com/en/issues/planning-and-tracking-with-projects/managing-your-project/managing-visibility-of-your-projects)
