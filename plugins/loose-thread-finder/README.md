# Loose Thread Finder

**Find what got lost. Pick up what matters.**

`loose-thread-finder` recovers forgotten project intent and unfinished work from bounded task history and repository evidence. It reconnects related task families, separates verified facts from weak activity signals, and returns a focused attention list with evidence-backed next actions.

It operates on one resolved project or tightly related project family. Generic workspace-wide questions about which projects need attention belong to a portfolio-tracking workflow.

## Use it for

- Finding important work that fell out of recent attention
- Resuming an old project without trusting a task title or stale summary
- Reconnecting parent, handoff, review, and monitor tasks
- Detecting drift between current direction, repository authority, and implementation
- Running a quiet weekly continuity review that reports only material change
- Organizing reviewed tasks when the user explicitly asks for sidebar changes

## The anti-forgetting model

Loose Thread Finder is the continuity controller between five separate layers:

`attention queue → repository wiki → keeper → portfolio dashboard → CLI next-action runner`

It audits and routes gaps between those layers. An explicit schedule request may use it to define the fixed read-only review prompt, while the host's separately authorized native automation performs the schedule action. It does not create a wiki, build a portfolio site, operate a keeper, or execute a CLI action.

## Behavior and authority contract

- Current user direction outranks accepted repository authority, verified implementation evidence, task content, and task metadata signals, in that order.
- Task titles, summaries, timestamps, section placement, shared repository identity, and self-asserted relationships are discovery signals; consequential relationships require independent effort-level evidence or current user confirmation.
- A conversation can recover intent but does not automatically become durable repository truth.
- A clean worktree, recent commit, or passing checker does not prove health, completion, publication, deployment, or continuity.
- The sidebar is an attention index, not durable memory.
- Reviews are read-only by default. Only the current user's direct, operation-specific request may create a sidebar section or move, rename, or reorder resolved in-scope tasks; broad organization requests receive recommendations only.
- Archiving, deleting, messaging, repository changes, host-native scheduling, and executing project work remain separately authorized actions.
- Any task mutation stays bound to the resolved task's originating host and host-exposed account, workspace, or project selectors; ambiguous origins stop for clarification.
- A finding is not an executable target. Any implementation or operations workflow must independently resolve the exact project, target, action, completion signal, mutation scope, and current authorization.
- Sensitive evidence is minimized; raw logs, private records, path inventories, credentials, and unrelated personal content are not reproduced.

## Manual and scheduled use

A manual review can investigate the current task landscape and perform an exact task-organization operation when the current user directly requests it. An already-authorized scheduled review remains read-only. It returns `CONTINUITY_OK — no material change.` only after a successful same-scope comparison with adequate source coverage and no unresolved material thread; a first run establishes a baseline, while unchanged unresolved attention is carried forward without repeating the full report.

On an explicit request to schedule this review, the skill supplies the stable read-only scope and prompt; schedule creation or changes remain delegated to the host's native automation workflow.

## Quality evidence

- Skill frontmatter and plugin manifest validation
- Repository marketplace, catalog, privacy, and public Git identity validation
- A labelled golden set covering direct, indirect, incomplete, follow-up, boundary, negative, and edge requests under [`evals/loose-thread-finder.json`](./evals/loose-thread-finder.json)

The initial `0.1.x` line is a public preview. Promote it only after the complete golden set passes representative host-level replay.
