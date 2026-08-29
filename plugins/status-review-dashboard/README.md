# Status Review Dashboard

`status-review-dashboard` creates a compact, evidence-backed visual review that helps a user understand current state and decide what matters next.

## Use it for

- Project health
- Release readiness
- Workflow operations
- Learning progress
- Weekly or other periodic activity reviews

It is intentionally narrower than a general data-visualization or project-portfolio pipeline. A standalone chart, a prose-only update, critique of an existing dashboard, persisted snapshot, recurring automation, generated site, and publishing or deployment belong to other workflows.

## Behavior contract

- Inspect direct evidence before composing metrics.
- Keep mechanical repository facts separate from health, readiness, stage, completion, shipment, deployment, and other reviewed judgments.
- Separate verified outcomes from active, blocked, stale, unknown, and planning-only work.
- Distinguish the dashboard's generated-at time from the observed-at time of consequential evidence.
- Link important claims to resolvable sources.
- Rank attention by verified blockers, unresolved decisions, integration or local-work risk, stale evidence, then new or unreviewed unknowns.
- Express priority items as current state, evidence, specific risk, and one executable next move.
- Summarize sensitive evidence without reproducing raw logs, diffs, path or filename inventories, secrets, or private records.
- Keep external systems read-only unless the user explicitly asks for changes.
- Render interactively when the host supports it; otherwise return the same hierarchy in Markdown.

The core instructions use capability-based vocabulary. Current host APIs are isolated under the skill's `references/` directory so implementation details can evolve without changing the workflow's meaning.

## Quality evidence

- Skill frontmatter and plugin manifest validation
- Repository marketplace validation
- A labelled activation set covering direct, indirect, incomplete, follow-up, boundary, negative, and edge requests under [`evals/status-review-dashboard.json`](./evals/status-review-dashboard.json)

The initial `0.1.x` line is a public preview. Promote it only after representative host-level prompt replays confirm both activation precision and workflow behavior.
