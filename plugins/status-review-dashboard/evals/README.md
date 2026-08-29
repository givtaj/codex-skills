# Evaluation set

`status-review-dashboard.json` is the versioned golden request set for activation precision and workflow invariants.

The initial release records structural validation under `results/2026-08-27-structural.json`; the v0.1.1 evidence-model update is recorded under `results/2026-08-27-structural-v0.1.1.json`. Host-level prompt replay is intentionally marked pending, so the `0.1.x` line remains a public preview. Add dated results here after replaying the unchanged set in each supported host. Record the host, date, skill version, case ID, observed activation, invariant outcome, and any deviation.

Do not rewrite expected outcomes to match a failed run. Change one metadata or instruction field at a time, increment the plugin version when installed behavior changes, and retain the before-and-after result.
