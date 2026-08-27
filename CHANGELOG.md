# Changelog

All notable changes to published plugins are recorded here. Versions follow semantic versioning.

## Unreleased

### Added

- Repository-wide canonical naming, durable-language, public-safety, and golden-request import gates.

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
