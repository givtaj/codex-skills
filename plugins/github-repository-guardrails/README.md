# GitHub Repository Guardrails

`github-repository-guardrails` establishes, maintains, or audits a coherent repository-management system while preserving conventions that already work.

## Use it for

- Repository-management setup and reconciliation
- Plans, tasks, status, outcomes, ownership, and review conventions
- Optional GitHub issue and Project traceability
- Quality, delivery, operational, and governance guardrails when the repository needs them
- Read-only audits for duplicate authorities, drift, missing evidence, and unsafe configuration

It is intentionally narrower than a general GitHub or coding skill. Ordinary implementation, one-off issue edits, pull-request review, and GitHub CLI questions belong to their normal workflows.

## Safety contract

- Inspect repository instructions and existing authorities first.
- Never read or persist token values, private-key material, transcripts, raw authentication output, or unrelated private data.
- Keep repository discovery separate from GitHub Projects access so a missing Project scope does not erase other evidence.
- Preserve the repository's Git protocol, identifiers, status model, fields, and definition of done unless the user explicitly chooses a migration.
- Preview local changes separately from GitHub mutations and apply only the authorized portion.
- Keep new Projects private unless the user explicitly chooses another supported visibility.

The plugin bundles instruction and template files only. It has no server, telemetry, analytics, or embedded credentials. GitHub operations use the credentials and permissions already available to the user's host environment.

## Maturity and provenance

Version `0.2.1` is an unreleased public-preview candidate. Its local structural and regression checks pass, and the published `0.2.0` artifact previously passed the public clone/install/load smoke path. No immutable public `0.2.1` candidate has been tested yet. Public-candidate verification and full replay of every golden request across supported hosts remain pending.

This plugin was adapted from the public [`github-project-maintainer-skills`](https://github.com/givtaj/github-project-maintainer-skills) release `v0.1.1` at commit `55bb780`. It was renamed before publication here because the original name could be mistaken for a GitHub Projects-board-only workflow. The original MIT notice is preserved in [`SOURCE_LICENSE`](./SOURCE_LICENSE).

## Install

```bash
codex plugin marketplace add givtaj/codex-skills
codex plugin add github-repository-guardrails@givtaj-skills
```

Start a new task after installation. Invoke it explicitly as `$github-repository-guardrails`, or let the host select it for a matching repository-governance request.
