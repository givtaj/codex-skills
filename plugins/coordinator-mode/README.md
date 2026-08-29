# Coordinator Mode

`coordinator-mode` coordinates genuinely complex engineering work as a small set of bounded lanes, then supervises and verifies their integration.

Despite its name, this is an installable Codex skill workflow rather than a built-in product mode or model setting.

## Use it for

- Multi-component implementation or migration work with substantial independent lanes
- Parallel read-only research, audits, or verification
- Work that needs explicit dependencies, ownership, supervision, and integration
- Recovery from partial lane failures without discarding unaffected results

It is intentionally not triggered for ordinary planning, simple multi-step work, one-file changes, straightforward bug fixes, informational questions, or tightly coupled work that cannot be divided safely.

## Safety and behavior contract

- Delegation never expands the user's authority.
- Every lane receives a concrete goal, exact scope, stop condition, required evidence, and forbidden operations.
- One writer owns each mutable target; shared writes are serialized.
- Agents receive only the context they need, without credentials or unrelated private material.
- The coordinator monitors drift, interrupts unsafe work, and inspects state after interruption.
- Failed attempts are diagnosed before a bounded retry; unaffected results are preserved.
- Completion requires direct inspection and risk-appropriate validation, with partial outcomes labelled truthfully.
- Volatile host APIs and capacity details remain isolated in the routed host-adapter reference.

## Install

Add the repository marketplace once:

```bash
codex plugin marketplace add givtaj/codex-skills
```

Then install this plugin:

```bash
codex plugin add coordinator-mode@givtaj-skills
```

Start a new task after installation. Invoke `$coordinator-mode` explicitly, or let the host select it automatically for requests that match the bounded trigger description.

## Quality evidence

- Skill frontmatter and plugin manifest validation
- Repository marketplace, public-content, and Git-identity validation
- A labelled activation set covering direct, indirect, incomplete, follow-up, boundary, negative, and edge requests under [`evals/coordinator-mode.json`](./evals/coordinator-mode.json)
- Golden cases specifying expected behavior for authority limits, prompt injection, capacity limits, write conflicts, cancellation, retry behavior, and partial failure

Version `0.1.0` is a public preview. The maintainer is publishing this original skill under the repository's MIT license. Complete host-level replay of the unchanged golden request set remains required before a stable release.
