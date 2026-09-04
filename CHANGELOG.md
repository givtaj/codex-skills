# Changelog

All notable changes to published plugins are recorded here. Versions follow semantic versioning.

## Unreleased

### Added

- Repository-wide canonical naming, durable-language, public-safety, and golden-request import gates.
- Required global-name and six-month durability evidence for skill pull requests, with a trusted-base PR gate, CODEOWNER routing, and conservative CI checks for objective identity and model-release coupling.
- Exact evaluation-result schema validation and mutation-focused tests for plugin versions, dates, checks, and behavioral-replay metadata.

## loose-thread-finder 0.1.0 - 2026-08-29

### Added

- Initial public preview for recovering forgotten project intent, unfinished work, stalled handoffs, and related task families from bounded task history and repository evidence.
- Evidence precedence, continuity classifications, material-risk ranking, one-action handoffs, and explicit boundaries around durable repository truth.
- Read-only scheduled-review behavior with an exact no-material-change sentinel and separately authorized manual task organization.
- Host-adapter guidance and a labelled golden request set covering direct, indirect, incomplete, follow-up, boundary, negative, and edge behavior.

### Validation status

- Local structural, repository, privacy, packaging, and public Git identity checks passed for `0.1.0`.
- Host-level replay of the final candidate remains pending; no superseded activation result is claimed as current evidence. Task reconciliation, organization, scheduled comparison, and complete golden-set replay across supported hosts remain pending.

## github-repository-guardrails 0.2.1 - 2026-08-27

### Fixed

- Bound GitHub Project operations to the resolved host and repository instead of relying on ambient CLI defaults.
- Distinguished an unlinked Project from the absence of an existing Project authority and required complete, explicitly limited discovery before duplicate-sensitive actions.
- Made bundled configuration and lifecycle templates validate their selected options without imposing changelog or integration conventions.
- Hardened public-content validation across Git history, filenames, binary payloads, Git metadata, and additional high-signal credential formats.
- Accepted GitHub system and bot noreply identities while validating contribution commits instead of synthetic pull-request merge identities.

### Validation status

- Local structural, regression, privacy, packaging, and independent review checks passed for `0.2.1`.
- Anonymous HTTPS clone, direct skill download, Git marketplace registration, plugin installation, installed-package validation, and explicit read-only Codex CLI activation passed against immutable candidate `github-repository-guardrails-v0.2.1-rc.1` at commit `db6c8db9e004806664c264e62a2774885068c045`.
- The candidate's [GitHub Actions validation](https://github.com/givtaj/codex-skills/actions/runs/33082734696) passed. Full replay of every golden request across supported hosts remains pending.

## github-repository-guardrails 0.2.0 - 2026-08-27

### Added

- Consolidated public preview for repository-management setup, maintenance, and audit workflows.
- Native plugin packaging, marketplace entry, public-content validation, and activation request set.
- Preserved source MIT notice and provenance from `github-project-maintainer-skills` release `v0.1.1`.

### Changed

- Renamed the imported skill from `github-project-maintainer` to `github-repository-guardrails` before publication in this marketplace to remove GitHub Projects-board ambiguity.
- Split repository discovery from GitHub Projects discovery and made missing Project scope a non-destructive, explicit branch.
- Removed SSH-only transport, mandatory field schemas, fixed work identifiers, and fixed lifecycle assumptions.
- Updated bundled workflow actions to reviewed commit-pinned releases.

## status-review-dashboard 0.1.1 - 2026-08-27

### Added

- A routed evidence and decision model for claim support, source freshness, attention ordering, executable next moves, and sensitive-output minimization.
- Golden requests covering Git evidence boundaries, mixed freshness, sensitive evidence, priority ranking, and persistence or automation non-triggers.

### Changed

- Distinguished mechanically observed repository state from reviewed health, readiness, stage, completion, shipment, deployment, and operational claims.
- Clarified that persistence, recurring automation, site generation, publishing, deployment, and hosting remain separate workflows.

## status-review-dashboard 0.1.0 - 2026-08-27

### Added

- Initial public preview of `status-review-dashboard`.
- Native Codex plugin manifest and repo marketplace entry.
- Activation evaluation cases for direct, indirect, incomplete, follow-up, boundary, negative, and edge requests.
- Capability-based refresh behavior with host-specific details isolated in a reference file.

### Changed

- Renamed the pre-release draft from `compact-dashboard-review` to `status-review-dashboard` before first publication to remove grammatical ambiguity.

## central-projects-tracking 0.1.0 - 2026-08-27

### Added

- Initial public preview for central portfolio tracking across an explicitly approved local projects directory.
- Bounded read-only Git collection, exact evidence-map allowlisting, verified evidence rereads, validated previous-snapshot continuity, private facts, and source/content digests.
- A deterministic offline website builder with Brief, Portfolio, Activity, and System views; search and filters; accessible project drawers; copy actions; privacy-safe Git change plans; responsive styling; and a digest-bound site manifest.
- Reusable site-creation instructions and a copy-ready creation prompt.
- Activation requests covering direct, indirect, incomplete, follow-up, website-creation, boundary, negative, and adversarial edge cases.

### Security

- Scanned repositories remain read-only; the workflow never fetches, executes project code, publishes, deploys, schedules, or exposes raw paths, dirty filenames, Git identities, object ids, logs, or evidence contents.
