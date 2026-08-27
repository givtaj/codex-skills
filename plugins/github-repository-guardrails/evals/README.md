# Evaluation set

`github-repository-guardrails.json` is the versioned golden request set for activation precision, privacy, authority boundaries, and repository-governance behavior.

The initial consolidated release records structural validation under `results/2026-08-27-structural.json`. Version `0.2.1` adds a public-consumer Codex CLI smoke result under `results/2026-08-27-v0.2.1-codex-cli.json`. Full host-level replay remains incomplete, so the plugin stays a public preview. Add dated results after replaying the unchanged set in each supported host.

Do not rewrite expected outcomes to match a failed run. Change one metadata or instruction field at a time, increment the plugin version when installed behavior changes, and retain before-and-after results.
