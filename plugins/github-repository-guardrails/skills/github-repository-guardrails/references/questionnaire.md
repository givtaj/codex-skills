# Adaptive setup decisions

Use this reference as reasoning guidance, not as a form. Inspect the repository, infer compatible choices from evidence, recommend a coherent minimal setup, and ask only what cannot be decided safely. The user should not need to name internal levels, files, field schemas, or commands.

## Establish available authorities

Start with local repository instructions, existing management surfaces, and configured remotes. Resolve and preview one explicit GitHub host and repository identity, then run repository and linked-Project discovery as separate, explicitly targeted read operations following `github-projects.md`.

Adapt to the result:

- No compatible GitHub remote: continue locally and note that GitHub integration can be added later.
- Repository access unavailable: offer one scoped retry when appropriate, otherwise continue locally.
- Projects access unavailable: distinguish the missing Project permission from repository access; offer to skip or request authorization.
- One compatible linked Project: propose reusing it.
- No compatible linked Project: record only that no explicit link was found. Inspect repository evidence and accessible owner Projects with adequate explicit limits, then ask whether an unlinked or cross-organization Project is authoritative.
- Several compatible linked Projects: ask the user to select one.

Do not perform a GitHub write during discovery. Offer creation only after no compatible existing Project authority remains. Missing or declined GitHub integration must not block useful local guardrails.

## Ask only unresolved management decisions

Consider these topics independently, but group questions when that is clearer and the answers do not depend on one another.

### Request intent

Determine whether sanitized intent needs a durable record at all. Prefer an existing issue, decision log, or request-summary convention. Never store the original prompt, a transcript, credentials, raw command output, private URLs, or unnecessary names.

### Work tracking

Identify one authority for active scope and state: an existing local system, GitHub issues and Projects, or an explicitly synchronized summary. Preserve the repository's identifier convention and avoid duplicate state.

Treat lifecycle fields as conditional. Include state, completion, or transition fields only when the selected authority defines them.

### Outcome history

Reuse the existing changelog, release notes, pull-request conventions, or another user-visible outcome record. Do not add a changelog merely to fill the map.

### Current status

Reuse an existing status surface. Offer a compact status file only when the repository needs a durable summary that is not already supplied by its task or Project system.

### Planning

Reuse existing plans, roadmaps, milestones, or objectives. Add a small plan only when measurable current objectives and exit criteria lack an authority.

### Review and closeout

Reuse contribution, pull-request, integration, and definition-of-done guidance. Offer a template only when the repository uses that workflow and has a demonstrated gap.

Keep changelog and integration fields out of task and review templates unless the repository selects those authorities or policies.

## Inspect remaining mapper levels

Use `guardrail-mapper.md` to inspect collaboration, quality automation, delivery, operations, and governance. Skip questions answered by evidence and mark irrelevant levels as not applicable.

- Reuse existing labels, fields, status models, branch rules, and review conventions.
- Confirm canonical test, lint, formatting, and CI commands before proposing enforcement.
- Mention hooks only when a tracked hook system exists or the user wants deterministic lifecycle enforcement.
- Recommend release, deployment, rollback, runbook, ownership, architecture, policy, metric, audit, and deprecation surfaces only when the repository has a recurring need.

## Translate decisions into changes

Build a minimal change set with one authority per surface. Compare proposed templates with existing files using available filesystem capabilities. When the generic configuration is selected, use only the documented values in `guardrail-mapper.md` and validate it before installation. Preview local changes and GitHub actions separately, apply only authorized non-conflicting changes, and validate the resulting authorities agree.
