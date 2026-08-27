# Evaluation set

`github-repository-guardrails.json` is the versioned golden request set for activation precision, privacy, authority boundaries, and repository-governance behavior.

The initial consolidated release records structural validation under `results/2026-08-27-structural.json`. The `0.2.1` result files record local pre-release validation and the published `0.2.0` public-path baseline separately. The Codex CLI smoke result does not claim that `0.2.1` was installed from the public repository. Its `public_candidate_verification` section remains `pending` until an immutable candidate is published and its ref, commit SHA, repository URL, and Codex CLI version are recorded.

Full host-level replay remains incomplete, so the plugin stays a public preview. Add dated results after replaying the unchanged set in each supported host.

Do not rewrite expected outcomes to match a failed run. Change one metadata or instruction field at a time, increment the plugin version when installed behavior changes, and retain before-and-after results.
