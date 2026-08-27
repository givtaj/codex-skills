# Evidence and decision model

Read this reference when a review mixes evidence types or observation times, ranks multiple attention items, or summarizes sources that may contain sensitive detail.

## Keep facts and judgments separate

- **Repository facts** include branch state, worktree state, commit activity, and ahead or behind counts. Report only what was observed. These facts do not establish health, readiness, stage, completion, shipment, deployment, or operational success.
- **Validation evidence** includes a scoped test, build, check, or CI result with its observed time and applicable revision or artifact when available. It supports only the validated scope and does not prove deployment or broader product quality.
- **Delivery and operational evidence** includes release artifacts, deployment records, runtime checks, or monitored outcomes. Use it for shipment, rollout, or operational claims only when the source directly supports the claim and is current enough for the decision.
- **Planning evidence** includes issues, roadmaps, proposals, and notes. It establishes intent or an open decision, not completed work.
- **Editorial judgments** include health, readiness, stage, risk, and priority. Label them as inferred or reviewed, preserve their evidence basis, and use `unknown` when the basis is insufficient.

When sources conflict, show the claim as conflicting or unknown. Do not choose the more favorable or more recent statement unless the evidence establishes that it supersedes the other source.

## Represent freshness honestly

The dashboard's generated-at time describes when the review was composed. A source's observed-at time describes when its evidence was captured. Show the relevant observed-at time for a consequential claim when sources have different freshness, and label stale or undated evidence instead of allowing the generated-at time to imply freshness.

## Rank attention and next moves

Order attention items by this hierarchy:

1. Verified failure or blocker.
2. Explicit unresolved decision.
3. Integration or local-work risk supported by repository or workflow evidence.
4. Stale evidence that could change a decision.
5. New or unreviewed work whose state remains unknown.

Within a level, prefer the item with the clearest consequence and strongest current evidence. Do not invent severity to break a tie.

Structure each priority row as:

`Current state → Evidence → Specific risk → One executable next move`

The next move should begin with a concrete action, identify its target, and make the useful completion signal clear. Do not invent an owner or deadline. If a field is unsupported, mark it `unknown` and make evidence collection the next move when that is decision-relevant.

## Minimize sensitive output

Treat raw logs, diffs, path or filename inventories, credentials, secrets, environment values, and private records as evidence to inspect, not dashboard content to reproduce. Extract only the minimum non-sensitive fact needed for the decision. Never copy secret values or private record contents. Prefer a safe source label and a host-provided resolvable link; omit or withhold the link when its locator would expose sensitive information.
