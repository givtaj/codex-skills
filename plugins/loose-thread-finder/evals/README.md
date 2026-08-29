# Evaluation set

`loose-thread-finder.json` is the versioned golden request set for activation precision, evidence boundaries, task-family reconciliation, safe organization, and quiet scheduled-review behavior.

The initial release records structural validation under `results/2026-08-29-structural.json`. An earlier local activation smoke test targeted a superseded build and is intentionally not retained as evidence for this candidate. Task reconciliation, organization, scheduled comparison, and the complete golden set remain pending on representative supported hosts, so the `0.1.x` line remains a public preview.

For each replay, record the host, date, plugin version, case IDs, observed activation, workflow outcome, and any deviation. Do not rewrite expected outcomes to match a failed run. Make one focused instruction or metadata change at a time, increment the plugin version when installed behavior changes, and retain before-and-after evidence.
