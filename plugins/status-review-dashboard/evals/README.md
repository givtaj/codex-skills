# Evaluation set

`status-review-dashboard.json` is the versioned golden request set for activation precision and workflow invariants.

The initial release records structural validation under `results/2026-08-27-structural.json`. Host-level prompt replay is intentionally marked pending, so version `0.1.0` remains a public preview. Add dated results here after replaying the unchanged set in each supported host. Record the host, date, skill version, case ID, observed activation, invariant outcome, and any deviation.

Do not rewrite expected outcomes to match a failed run. Change one metadata or instruction field at a time, increment the plugin version when installed behavior changes, and retain the before-and-after result.
