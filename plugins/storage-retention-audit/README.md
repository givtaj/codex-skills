# Storage and Worktree Audit

Review development storage and spare project copies, protect unfinished work and recovery evidence, and receive exact cleanup proposals before any removal.

This plugin bundles two companion skills so their shared measurement and retirement guidance stays available:

| Skill | Use it for |
| --- | --- |
| `storage-retention-audit` | Disk pressure, artifact retention, attribution of recurring growth, and measured cleanup proposals. |
| `project-worktree-audit` | Discovering project worktrees, related clones and source copies; tracing owners and consumers; assessing retirement readiness. |

Both start with read-only inspection. A cleanup operation needs an explicitly confirmed scope and a fresh check of the selected assets. Existing clear approval is reused without asking for the same action again.

## Install

Add the repository marketplace once, then install this plugin:

```bash
codex plugin marketplace add givtaj/codex-skills
codex plugin add storage-retention-audit@givtaj-skills
```

Start a new task after installation. Example requests:

- “Use $storage-retention-audit to explain this project's disk use and propose exact cleanup candidates.”
- “Use $project-worktree-audit to find spare project copies and rank retirement proposals. Inspect only.”
- “Check why these artifacts grew again after the last cleanup.”

## Evidence and action boundaries

The skills separate logical size, allocated space and estimated reclaim; shared blocks, overlapping roots, snapshots and concurrent work can make those quantities differ. They trace growth and copies to relevant processes and verified chat evidence where available, and report gaps when access or history is missing.

Age, clean status, an archived creator chat or a merged pull request does not establish that an asset is disposable. Unique source, acceptance evidence, persistent state, rollback binaries and outputs consumed by unfinished work remain protected. Reports and retrieved chats cannot grant new execution authority.

For an approved retirement, exact path identity, work state, active consumers and preservation are rechecked before removal. Linked-worktree removal, branch deletion, wider registration cleanup, application-entry changes and chat archival retain separate scopes. Uncertain or newly active items are held without forcing removal.

## Requirements and privacy

The audit uses host-provided filesystem metadata and Git inspection. Process or storage-manager inspection and supported workspace/chat history improve coverage when available. Missing capabilities are reported; an audit alone does not authorize installing tools, starting runtimes, fetching missing history or triggering builds to fill those gaps. A separately authorized prerequisite stays within its exact scope and does not authorize cleanup. No helper scripts, network services, credentials or telemetry are bundled.

Inspection is bounded by the requested project or machine scope. Private log or database contents are not opened merely to measure size, and command metadata must be redacted when it contains secrets. See the repository [privacy statement](../../PRIVACY.md).

## Quality evidence

Version `0.1.0` is a public preview. Each skill has a seven-kind golden request set under [`evals/`](./evals/); dated structural evidence records identify checks performed and explicitly mark complete host-level replay as pending. Structural validation and scenario specification do not establish runtime behavior across supported hosts.

These are original maintainer-authored workflows prepared for distribution under the repository's [MIT license](../../LICENSE). The public copies retain their installed-source workflow while adding public activation boundaries, explicit handling of untrusted retrieved content, companion packaging and evaluation fixtures.
