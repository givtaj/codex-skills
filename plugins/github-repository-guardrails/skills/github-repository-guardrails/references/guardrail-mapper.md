# Guardrail mapper

Inventory every level from 0 through 5 during setup and audit. Level 0 is mandatory. Higher levels are not a score and are never installed automatically: reuse what exists, recommend only useful gaps, and ask the user before changing anything.

During setup, use this map as an internal checklist, not a menu. After the repository-instruction safety precheck, resolve and preview one explicit GitHub host and repository identity. Inspect repository metadata first and explicitly linked Projects separately so missing Project scope does not erase the local or repository result. A zero-link result is not evidence that no Project authority exists: inspect accessible candidates and ask about unlinked or cross-organization authority before proposing creation. Ask only the unresolved management decisions that matter to the user's requested outcome.

Keep the discovery result in ephemeral task state as: `level`, `surface`, `detected authority`, `gap`, `recommendation`, and `user decision`. Show a concise summary, but do not save raw discovery or GitHub output.

## Mapping rules

1. Follow repository-specific links from `AGENTS.md`, `README.md`, and `CONTRIBUTING.md`.
2. Reuse a compatible authority instead of creating a parallel system.
3. Stop and ask when several files or services compete as the authority.
4. Recommend one small addition when a useful surface is missing.
5. Skip surfaces that do not fit the repository.

## Level map

| Level | Purpose | Mapper lanes |
| --- | --- | --- |
| **0 — Discover safely** | Understand before changing | Repository instructions, Git remote, available GitHub access, existing tools/files, default branch, secrets rules |
| **1 — Project memory** | Preserve intent and current state | Prompts, tasks, changelogs, plans, status, basic ownership |
| **2 — Collaboration** | Connect work across GitHub | GitHub Projects, issues, PRs, templates, labels, milestones, work identifiers, traceability, branch/merge policy |
| **3 — Quality automation** | Enforce repository health | CI, tests, linting, formatting, hooks, required checks, dependency/security management, maintenance automation |
| **4 — Delivery and operations** | Manage shipped software | Release lanes, versions, artifacts/packages, deployments, environments, rollback, runbooks, operational ownership |
| **5 — Mature governance** | Preserve long-term decisions | Architecture records, policy documents, metrics, audit history, lifecycle/deprecation rules |

## Level 0 — Discover safely

- **Repository instructions:** inspect applicable `AGENTS.md`, `README.md`, `CONTRIBUTING.md`, and linked guidance from the repository root toward the working directory. Preserve nested precedence.
- **Git remote:** inspect configured remotes locally, select one when several are plausible, derive its host and explicit `[HOST/]OWNER/REPO` identity, then preview and pass that target to GitHub operations. Keep selected identifiers in ephemeral state unless the target repository deliberately records them.
- **Safe GitHub authentication:** follow `safety.md`; use status only as a non-disclosing capability check. Never request, display, or dump a token.
- **Existing tools/files:** inventory manifests, task runners, `Makefile`, `.github/`, `scripts/`, `docs/`, repository configuration, and existing management commands before proposing anything.
- **Default branch:** discover it with an explicitly targeted, narrow repository-metadata query following `github-projects.md`, or use the remote HEAD. Never assume the branch is named `main`.
- **Secrets rules:** inspect safety instructions, `.gitignore`, `SECURITY.md`, secret-scanner configuration, and documented sensitive paths. Never open secret values, `.env` files, key material, or credential stores.

## Level 1 — Project memory

- **Request intent:** look for existing request summaries, decision logs, and issue intake. Recommend a new ledger only when retaining sanitized intent solves a recurring need; never retain transcripts.
- **Tasks:** look for `TASKS.md`, `TODO.md`, backlog files, GitHub issues, and Project items. Identify one task authority and its state model.
- **Changelogs:** look for `CHANGELOG.md`, `CHANGES.md`, release notes, release tooling, and PR conventions. Learn what counts as a user-visible outcome.
- **Plans:** look for `PLAN.md`, `ROADMAP.md`, `docs/plans/`, milestones, objectives, and exit criteria. Do not copy the full backlog into a plan.
- **Status:** look for `PROJECT_STATUS.md`, `STATUS.md`, dashboards, and generated summaries. Keep active work, blockers, and recent outcomes concise.
- **Basic ownership:** look for `.github/CODEOWNERS`, maintainers files, contribution docs, and package ownership metadata. Ask before inventing owners.

## Level 2 — Collaboration

- **GitHub Projects:** discover explicitly linked Projects at runtime when access is available. Reuse a compatible authority, inspect and ask about unlinked or cross-organization authority when none is linked, and ask for selection when several candidates remain. Suggest creation only after existing authority has been ruled out.
- **Issues:** inspect issue conventions, open and closed work, required fields, and whether issues are the scope authority. Use the explicit repository identity and adequate pagination or limits before concluding that no duplicate exists.
- **PRs:** inspect pull-request conventions, review expectations, merge evidence, and integration rules using the explicit repository identity and adequate pagination or limits for any enumeration.
- **Templates:** inspect `.github/ISSUE_TEMPLATE/`, pull-request templates, contribution forms, and repository-specific generators before offering bundled templates.
- **Labels:** inspect labels and their meanings with narrow `gh` queries. Reuse the existing taxonomy; never create a competing set silently.
- **Milestones:** inspect open milestones and their purpose. Use them only when the repository already plans releases or objectives that way.
- **Work identifiers:** detect and preserve the repository's issue or local identifier convention. Use one identifier consistently and never invent an issue number.
- **Traceability:** map the selected identifier across prompt intent, task, issue, Project item, branch, PR, changelog, release, and deployment where those surfaces exist.
- **Branch/merge policy:** inspect the default branch, naming conventions, repository rulesets, branch protection, required reviews, merge method, and deletion policy before proposing changes.

## Level 3 — Quality automation

- **CI:** inspect `.github/workflows/` and other CI configuration. Identify canonical checks and reuse them.
- **Tests:** find documented test commands, test directories, manifests, and coverage policy. Do not introduce a new framework merely to add a lane.
- **Linting:** find established linters and their configuration. Reuse the repository's command and scope.
- **Formatting:** find formatter configuration and check/fix commands. Keep automated formatting separate from semantic changes.
- **Hooks:** inspect established pre-commit, package-manager, task-runner, tracked Git-hook, and assistant-host hook configuration. Never modify untracked `.git/hooks` or add a hook framework silently.
- **Required checks:** inspect rulesets, branch protection, required status checks, and merge queues through narrow, explicitly targeted, read-only GitHub queries. Use adequate pagination or limits for any enumeration. Confirm before changing enforcement.
- **Dependency management:** inspect manifests, lockfiles, Dependabot/Renovate configuration, update policy, and dependency review.
- **Security management:** inspect code/secret scanning, security workflows, advisories policy, dependency checks, and `SECURITY.md`. Never read secrets to prove they are protected.
- **Maintenance automation:** inspect scheduled workflows, bots, stale-item handling, cleanup jobs, generated-file updates, and recurring repository maintenance.

## Level 4 — Delivery and operations

- **Release lanes:** inspect release workflows, release documentation, changelog promotion, approval gates, and release branches.
- **Versions:** inspect manifests, version files, tags, and versioning policy. Identify the single version authority.
- **Artifacts/packages:** inspect build outputs, package metadata, registries, container publishing, attestations, signing, and retention rules.
- **Deployments:** inspect deployment workflows, infrastructure configuration, deployment commands, promotion rules, and verification steps.
- **Environments:** inspect GitHub Environments and documented development, staging, and production boundaries, including approvals and protected secrets without reading their values.
- **Rollback:** find rollback or recovery commands, artifact selection rules, database constraints, and verification steps. Recommend a runbook when rollback is possible but undocumented.
- **Runbooks:** inspect `RUNBOOK.md`, `docs/runbooks/`, operations docs, incident procedures, and service-specific playbooks.
- **Operational ownership:** identify who approves releases, owns deployments and environments, responds to incidents, and maintains runbooks. Reuse existing ownership and escalation paths.

## Level 5 — Mature governance

- **Architecture records:** inspect `docs/decisions/`, ADRs, architecture notes, and design records. Preserve decisions and rejected alternatives without duplicating project plans.
- **Policy documents:** inspect governance, contribution, security, support, compliance, and repository policy documents. Determine which are authoritative.
- **Metrics:** inspect health dashboards, delivery/quality measures, service objectives, and reporting automation. Recommend metrics only when they drive a decision.
- **Audit history:** inspect audit reports, change approvals, release/deployment evidence, and retained verification records. Avoid storing raw sensitive output.
- **Lifecycle/deprecation rules:** inspect support windows, deprecation notices, migration policy, archival criteria, end-of-life procedures, and ownership transfer rules.

## Authority boundaries

- A GitHub Project owns dynamic portfolio state only when the repository has selected it as that authority.
- An issue owns scope, acceptance criteria, and discussion when enabled.
- A local task file may summarize work but must not silently disagree with GitHub.
- A prompt log owns sanitized intent, not transcripts or task state.
- A changelog owns user-visible outcomes, not command history.
- A plan owns current objectives; a status file owns the current view.
- CI, hooks, and required checks enforce rules; they do not become documentation authorities.
- Release, deployment, and rollback records describe delivery; they do not replace project memory.
- Architecture and policy records preserve durable decisions; they do not become another backlog.

## Bundled starting points

When the core configuration is selected, use this version-1 contract:

- `schema_version`: exactly `1`.
- `repository`: exactly `self`, meaning the containing repository must still be resolved to an explicit runtime GitHub identity.
- `project_authority`: `discover` or `disabled`. `discover` requires authority discovery; it does not assert that a Project is linked or selected.
- `surfaces`: a comma-separated, duplicate-free subset of `core,intent,tasks,outcomes,planning,status,issues,projects,review,ci`; `core` is required.
- `strictness`: `advisory`, `standard`, or `strict`, selected to match existing enforcement rather than assumed.

Reject missing, duplicate, unknown, or placeholder values before installing the configuration or its audit workflow. Do not add lifecycle, changelog, or integration fields merely because their surfaces are available; include them only when the repository selected the corresponding authority or policy.

| Desired outcome | Starting point |
| --- | --- |
| Durable agent instructions | `assets/guardrails/core/AGENTS.md` |
| Sanitized prompt intent | `assets/guardrails/traceability/docs/prompts.md` |
| Local task contracts | `assets/guardrails/traceability/TASKS.md` |
| User-visible outcome history | `assets/guardrails/outcomes/CHANGELOG.md` |
| Measurable objectives | `assets/guardrails/planning/PLAN.md` |
| Current work and blockers | `assets/guardrails/status/PROJECT_STATUS.md` |
| Issue intake | `assets/guardrails/github/.github/ISSUE_TEMPLATE/work-item.yml` |
| PR closeout | `assets/guardrails/review/.github/pull_request_template.md` |
| Basic local audit in CI | `assets/guardrails/ci/.github/workflows/guardrails-audit.yml` |

For labels, milestones, branch policies, test/lint/format tools, hooks, dependency/security automation, releases, deployments, runbooks, and governance, adapt the repository's existing system. There is no universal template.
