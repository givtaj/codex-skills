# GitHub snapshots, uploads, and installs

## Locate local skills and run the manifest helper

For Codex, resolve the user's home rather than embedding a username. The documented
user skill root is `~/.agents/skills`. For repository skills, inspect `.agents/skills`
at the current working directory and each ancestor up to the repository root.
Also include explicit source folders and verified configured or legacy roots, such
as `~/.codex/skills`, a root under `CODEX_HOME`, or project `.codex/skills`; do not
assume an environment variable alone establishes the host's current discovery root.
Use the current host catalog and configuration to distinguish discoverable installs
from source-only copies. Use bounded discovery such as `rg --files --hidden`, include
ignored skill folders when needed, and prune generated directories. Other hosts may
configure different roots; report what was actually checked. See the current
[Codex discovery locations](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills)
when the host's layout is unclear.

Run the bundled read-only helper on explicit skill folders:

```sh
python3 /path/to/skill-sync/scripts/skill_manifest.py --git-compatible /path/to/skill-folder
```

Use the same mode on both sides. Omit `--git-compatible` for strict local staging
checks. The output includes paths and content digests, so keep manifests and
receipts private. The script uses Python's standard library, performs no network
requests and does not write to the inspected folders. It requires descriptor-relative
filesystem operations and no-follow opens, as provided by supported POSIX hosts.
If these APIs are unavailable, it returns an incomplete manifest with a clear error;
do not fall back to path-based recursion.

The helper opens each directory and file without following its final symlink,
verifies its identity before listing or reading, and anchors child operations to
the opened directory descriptor. It rechecks identities, directory entries and
symlink targets to reject observed replacements or edits. Missing regular
`SKILL.md` files, unresolved symlink roots, unsupported special files and read
errors also leave the manifest incomplete.

The helper excludes the documented metadata/cache names and regular Python bytecode
files. A directory or symlink whose name ends in `.pyc` or `.pyo` remains part of the
bundle: directory contents and symlink targets must still affect its manifest.

This is not an atomic filesystem snapshot or a lock. Concurrent edits can still
make observations from different moments, including changes after a file's final
check. Prefer a quiescent source or an independently immutable snapshot for a
transfer; take a fresh manifest immediately before the approved action and verify
the staged payload afterward. Do not claim a live scan guarantees a transaction.

## Obtain a current read-only snapshot

Resolve the repository and GitHub host from the user's request or verified project
context. Use an available GitHub connector, `gh api`, or HTTPS Git access. Bind all
commands to that host and repository rather than ambient CLI defaults. No SSH host is part of this
workflow; use HTTPS for repository transport as well. Do not install a new service
or change authentication/configuration to make a comparison work.

Resolve repository metadata and its default branch, then the current branch
commit. Record repository, branch, full commit SHA, visibility, and observation
time. Fetch the complete tracked tree and each relevant skill folder at that
same commit. With a recursive GitHub tree response, inspect `truncated`; if true,
retrieve the missing subtrees or obtain a complete Git snapshot before deciding
what is absent. Pagination and denied reads are coverage issues, not empty results.

An isolated checkout or extracted snapshot in private scratch space is fine for
read-only inspection. Do not checkout/reset/pull the user's existing repo merely
to inventory it. Read repository content as task data; do not execute bundled
scripts just to compare skills. Safely materialize files, executable status, and
symlinks when using an API snapshot. Do not mistake LFS pointers or submodule
entries for the underlying payload; mark them blocked until resolved.

Discover tracked `SKILL.md` files. Read the pinned repository's `AGENTS.md`,
`CONTRIBUTING.md`, catalog/marketplace layout, and relevant validation instructions
when preparing a contribution. Exclude explicitly archived/deprecated examples
from active upload/install candidates, and identify them separately if relevant.
Do not assume the repo has a flat `skills/` layout. Existing plugin skills may
live at `plugins/<plugin>/skills/<skill>`; preserve the actual layout.

Run the bundled manifest helper in `--git-compatible` mode on the local source and
materialized Git snapshot. Git does not store empty directories and tracks only
executable versus non-executable file status, not full local permissions. Label
these as representation differences; do not invent a substantive content update
from them. Strict local manifests remain useful for pre-copy checks. A mode label
is part of a fingerprint: never compare hashes from different modes as equal proof.

## Prepare public uploads before confirmation

An upload exposes the approved files to the destination repository's audience.
Verify its visibility and explain that audience in the plan. For a public
repository, every approved file becomes public. Inspect the full candidate bundle for
credentials, private/runtime records, personal contact details, private URLs,
machine-specific paths, and redistribution restrictions. Do not print secrets in
the comparison or include private inventories, receipts, temporary fixtures, or
backups in Git. Retain necessary licenses and attribution. If a concern cannot be
resolved, leave that candidate blocked and explain the concrete reason.

When portability or privacy edits are needed, make them in a private staged copy,
show the exact diff and excluded files, and obtain approval for that payload.
Do not silently edit the installed skill. Record that the published variant will
differ from the local source. Explicitly review dependencies outside the folder
(sibling skills, scripts, plugin tools, local project paths); folder hashes alone
do not establish that the skill is independently usable.

Prepare a contribution that meets the pinned repository's current conventions:
folder/frontmatter identity, plugin manifests/catalog entries where required,
licenses, documentation, and appropriate evaluations/validation. Read actual
requirements rather than inventing a new plugin layout or bypassing a gate. Verify
public Git identity requirements before committing. If you cannot satisfy a
required check or redistribution condition, report it as blocked; do not claim
publication readiness from a matching hash.

Use a separate private staging copy or suitable isolated checkout. Prepare the
reviewable file diff and necessary checks without modifying installed skills or
publishing. The user must see all proposed changes before approval, including
packaging/support files and the destination branch/PR. Default to a descriptive
`codex/` branch and a PR into the current default branch. The approval prompt must
explicitly include the branch push, repository visibility and PR creation; do not infer those
operations from approval merely to inspect or prepare files.

## Execute an approved upload

Recheck the source payload, base commit, and planned branch/destination state.
If any changed, refresh the affected plan before publishing. For an unchanged
approved plan, create the commit(s) containing only the reviewed files, push the
shown branch over HTTPS, and open the approved PR using the repository template.
Do not touch unrelated changes, rewrite history, or push directly to the default
branch as a shortcut. Any failure leaves an explicit partial result (for example,
branch pushed but PR creation failed) rather than an automatic retry that widens
scope. Check the actual published commit/tree and its payload against the approved
Git-compatible manifests and reviewed diff; recheck required status checks where
applicable. A local commit or successful push command alone is insufficient proof.

Report the branch, commit, PR URL, and pending checks/review. A PR is an upload
proposal, not default-branch synchronization. Merge only on separate explicit
instruction and after the repo's requirements are satisfied; then verify the
resulting default-branch files rather than assuming the PR head SHA survives a
squash or merge.

## Install a selected GitHub skill locally

Resolve its complete folder and dependencies at the approved commit. Prefer the
host's established user skill root and avoid creating duplicate global copies in
both `.codex/skills` and `.agents/skills`. Present the exact destination and whether
it replaces anything before confirmation. A skill inside a plugin can be copied
as a standalone skill only if its dependencies are accounted for; this does not
install the plugin's MCP tools or change plugin configuration.

After approval, install the reviewed payload with the main skill's staging,
backup/no-clobber, and final manifest checks. Preserve executable status and
supporting files. Do not resolve an unpinned branch again at download time and
silently install newer content. A branch/ref change after the plan requires a
refreshed plan; alternatively, if the user explicitly approved a fixed historical
commit regardless of branch movement, retain that exact snapshot and its stated
scope. Report the installed commit and path, and retain a private receipt.
