# Changelog

All notable changes to published plugins are recorded here. Versions follow semantic versioning.

## Unreleased

### Added

- Repository-wide canonical naming, durable-language, public-safety, and golden-request import gates.

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

## status-review-dashboard 0.1.0 - 2026-08-27

### Added

- Initial public preview of `status-review-dashboard`.
- Native Codex plugin manifest and repo marketplace entry.
- Activation evaluation cases for direct, indirect, incomplete, follow-up, boundary, negative, and edge requests.
- Capability-based refresh behavior with host-specific details isolated in a reference file.

### Changed

- Renamed the pre-release draft from `compact-dashboard-review` to `status-review-dashboard` before first publication to remove grammatical ambiguity.
