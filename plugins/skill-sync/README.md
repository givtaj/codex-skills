# Skill Sync

Compare local user-created skills with a GitHub repository you choose, see what is missing or different on each side, and approve the exact files before any upload or installation.

## Use it for

- A current two-way inventory of complete skill bundles
- A selected upload or install, with destination and replacement scope shown first
- Preparing a portable public variant while preserving installed originals
- Distinguishing enabled plugin skills, cache-only copies and project-local sources

This workflow does not mirror general repositories, synchronize remote computers, schedule unattended transfers, delete source skills or merge pull requests.

## Install and use

```bash
codex plugin marketplace add givtaj/codex-skills
codex plugin add skill-sync@givtaj-skills
```

Start a new task after installation, then use `$skill-sync` and name the GitHub repository to compare. The plugin's publisher repository is not an automatic sync destination.

The workflow first returns a comparison table. Missing means absent within complete stated coverage; denied reads, truncated trees, invalid bundles and unresolved dependencies remain unknown. An upload or install requires confirmation of a concrete payload and destination. Approval for a reviewed plan is reused without asking again; changed payloads need a refreshed plan. Uploads use a reviewed branch and pull request by default, with merge requiring separate authorization.

## Requirements and privacy

The host needs access to the selected local skill roots and GitHub repository through its existing connector, CLI or HTTPS Git access. The bundled Python 3 manifest helper uses only the standard library, reads explicit skill directories, and makes no network calls or writes. It requires descriptor-relative filesystem operations and no-follow opens; unsupported hosts receive an incomplete result instead of an unsafe fallback. It verifies opened identities before reading and stays anchored to directory descriptors during traversal. It compares contents, relative paths, symlinks and executable status; its Git-compatible mode accounts for empty-directory and file-mode representation limits. A live manifest is not an atomic snapshot or a lock against subsequent edits.

Manifests and receipts can contain local paths, so they remain private. Uploads disclose the reviewed payload to the selected repository's audience. Authentication, system skills, unrelated caches, private runtime data and installed originals are not changed during comparison or public preparation. The helper does not install a plugin's tools or prove that a host has reloaded a skill.

## Quality evidence

[`evals/skill-sync.json`](evals/skill-sync.json) covers all seven request kinds plus incomplete inventories, changed approvals, plugin caches, prompt injection, representation limits, public preparation and unresolved dependencies. [`evals/test_skill_manifest.py`](evals/test_skill_manifest.py) exercises the read-only helper using temporary fixtures, including a temporary Git index.

Version `0.1.0` is a public preview of the maintainer's original skill, distributed under this repository's MIT license. Complete installed-host replay remains pending; structural validation and helper tests are separate evidence and do not prove end-to-end upload or install behavior. See [`evals/README.md`](evals/README.md).
