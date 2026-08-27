# Status Review Dashboard

`status-review-dashboard` creates a compact, evidence-backed visual review that helps a user understand current state and decide what matters next.

## Use it for

- Project health
- Release readiness
- Workflow operations
- Learning progress
- Weekly or other periodic activity reviews

It is intentionally narrower than a general data-visualization skill. A standalone chart, a prose-only update, critique of an existing dashboard, and a published website belong to other workflows.

## Behavior contract

- Inspect direct evidence before composing metrics.
- Separate verified outcomes from active, blocked, stale, unknown, and planning-only work.
- Link important claims to resolvable sources.
- Keep external systems read-only unless the user explicitly asks for changes.
- Render interactively when the host supports it; otherwise return the same hierarchy in Markdown.

The core instructions use capability-based vocabulary. Current host APIs are isolated under the skill's `references/` directory so implementation details can evolve without changing the workflow's meaning.

## Quality evidence

- Skill frontmatter and plugin manifest validation
- Repository marketplace validation
- A labelled activation set covering direct, indirect, incomplete, follow-up, boundary, negative, and edge requests under [`evals/status-review-dashboard.json`](./evals/status-review-dashboard.json)

The initial `0.1.x` line is a public preview. Promote it only after representative host-level prompt replays confirm both activation precision and workflow behavior.
