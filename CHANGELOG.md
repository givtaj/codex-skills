# Changelog

All notable changes to published plugins are recorded here. Versions follow semantic versioning.

## Unreleased

### Added

- Repository-wide canonical naming, durable-language, public-safety, and golden-request import gates.
- Required global-name and six-month durability evidence for skill pull requests, with a trusted-base PR gate, CODEOWNER routing, and conservative CI checks for objective identity and model-release coupling.
- Exact evaluation-result schema validation and mutation-focused tests for plugin versions, dates, checks, and behavioral-replay metadata.

### Changed

- Excluded native local bookkeeping refs from all-ref publication scans while keeping fetched mirrors under `refs/validation/origin/*` in scope.

### Fixed

- Routed multi-skill plugin evaluation results by declared packaged skill, retaining per-skill version and schema checks and rejecting unknown skill names.
- Restored public-history validation after GitHub generated the PR #5 merge commit with a direct author email by documenting and exempting only that immutable object id; future merges must preserve noreply author metadata.

## skill-opportunity-review 0.1.0 - Unreleased

### Added

- Prepared preview: Finds useful reusable workflows in recent work, checks existing skills, and creates only confirmed proposals.
- Native packaging, golden activation cases, and privacy disclosures.
- Current documented skill discovery, verified legacy-root support, and approved improvements that proceed without redundant confirmation when scope and destination state are unchanged.

### Validation status

- Local preparation only; full host-level replay and installation verification remain pending. No publication is claimed.

## skill-sync 0.1.0 - Unreleased

### Added

- Prepared preview: Compares local skills with a selected GitHub repository and waits for exact confirmation before upload or installation.
- Native packaging, golden activation cases, and privacy disclosures.
- Configurable local skill roots and GitHub destination, with no fixed machine, repository, or removed-host history.
- Descriptor-anchored no-follow manifest scans reject concurrent path substitutions before reading replacement payloads; unsupported hosts return incomplete. Stable strict and Git-compatible hash formats are retained.
- Manifest regression coverage retains directories and symlinks named with bytecode suffixes while excluding ordinary bytecode files; documented host discovery includes ancestor skill roots.

### Validation status

- Local preparation only; full host-level replay and installation verification remain pending. No publication is claimed.

## storage-retention-audit 0.1.0 - Unreleased

### Added

- Prepared preview: Audits storage and project worktrees, traces consumers, and proposes exact cleanup batches with recovery evidence.
- Native packaging, golden activation cases, and privacy disclosures.
- Bundled `project-worktree-audit` to preserve the shared retirement workflow.
- Read-only audit defaults honor explicit user-authorized prerequisites while keeping deletion and cleanup authority separate.

### Validation status

- Local preparation only; full host-level replay and installation verification remain pending. No publication is claimed.

## tempo 0.1.0 - Unreleased

### Added

- Prepared preview: Reviews project work across chats, refreshes comparisons, resumes selected work, and follows through on authorized handoffs.
- Native packaging, golden activation cases, and privacy disclosures.
- Bundled four companion skills; generalized personal review naming into an explicit user preference.
- Explicit output preferences override default maps and reminders. Direct companion entry points share sensitive-title handling, and Refresh uses Tempo's shared baseline procedure.

### Validation status

- Local preparation only; full host-level replay and installation verification remain pending. No publication is claimed.

## terminal-wireframe-sketching 0.1.0 - 2026-09-02

### Added

- Initial public preview of `terminal-wireframe-sketching`.
- Terminal-style interface, navigation, workflow, hierarchy, state, and software-architecture wireframes derived from supplied sketches or relevant context.
- Fidelity and uncertainty rules that preserve source structure, distinguish inference, handle illegible or conflicting evidence, and keep confirmation separate from polished design or implementation.
- Native plugin packaging, Creativity marketplace/catalog entries, privacy disclosure, and labelled activation evaluation cases.

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

## coordinator-mode 0.1.0 - 2026-08-29

### Added

- Initial public preview of `coordinator-mode`, retaining the original skill name as an installable Codex workflow rather than presenting it as a built-in product mode.
- Native plugin packaging, marketplace registration, implicit activation metadata, and labelled direct, indirect, incomplete, follow-up, boundary, negative, and edge requests.
- Bounded delegation, minimum-necessary context, single-writer ownership, prompt-injection resistance, active drift control, capability-aware fallback, corrected-retry limits, and truthful partial-result reporting.
