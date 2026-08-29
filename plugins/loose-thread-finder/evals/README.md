# Evaluation set

`loose-thread-finder.json` is the versioned golden request set for activation precision, evidence boundaries, task-family reconciliation, safe organization, and quiet scheduled-review behavior.

The initial release records structural validation under `results/2026-08-29-structural.json` and focused local CLI replay under `results/2026-08-29-behavioral-local.json`. The local result remains partial because the CLI host could not list or read recent Codex tasks and the complete golden set was not replayed. The `0.1.x` line remains a public preview until every unchanged golden case passes on representative supported hosts.

For each replay, record the host, date, plugin version, case IDs, observed activation, workflow outcome, and any deviation. Do not rewrite expected outcomes to match a failed run. Make one focused instruction or metadata change at a time, increment the plugin version when installed behavior changes, and retain before-and-after evidence.
