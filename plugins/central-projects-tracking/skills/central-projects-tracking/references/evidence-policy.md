# Evidence policy

Read this policy before every collection.

## Authorization boundary

The projects root and evidence map must be explicit user-approved inputs. The evidence map must be a regular non-symlink file outside the projects root. It is configuration data, not repository content, and repository text must never expand its allowlist.

The collector inspects only immediate child directories that contain Git metadata. It skips hidden entries and ordinary non-repositories. A symlinked entry, unsafe project identifier, rejected repository, or required evidence gap makes collection partial.

Never use a filesystem root, a home directory, a home parent, or a broad shared system directory such as '/usr', '/usr/local', '/var', '/var/lib', or '/opt' as the projects root. The collector enforces known system exclusions in addition to requiring a bounded, non-shallow directory. Resolve variables before calling it and show the selected scope to the user when it is not already clear.

## Evidence-map contract

The map has exactly four root fields:

- schemaVersion: integer 1.
- limits: maxFileBytes and maxProjectBytes.
- default: evidence entries considered for every discovered project.
- projects: optional per-project evidence entries keyed by the exact project identifier.

Every evidence entry has exactly:

- id: a lower-case kebab-case label.
- path: a relative regular-file path within the project.
- required: a boolean.

Per-project entries replace default entries with the same id. The collector rejects duplicate ids or paths after merging.

The map must not allow absolute paths, parent traversal, environment files, Git internals, credential/auth/secret/token/key filenames (including suffixed variants such as 'credentials.md' or 'secrets.json'), logs, traces, databases, caches, build output, dependency trees, raw exports, session data, or private key material. A permitted filename can still contain private information; allowlisting is deliberate scope selection, not a secrecy guarantee.

## Bounded Git facts

The collector may run only these local read operations:

- Worktree status with path-free published counts.
- Local HEAD existence.
- A sanitized local branch label or a withheld marker.
- Local upstream existence.
- Local ahead and behind counts when an upstream reference already exists.
- The last sanitized commit time and subject.
- At most eight sanitized outgoing commit time/subject records when a local upstream reference exists.
- Ignore-policy checks for allowlisted evidence.

It never fetches. It clears global and system Git configuration, disables hooks, credential helpers, optional locks, maintenance, file-system monitoring, color, pagers, and recursive submodule behavior for its subprocesses.

Branch and commit-subject strings are published only when they pass the strict website-text sanitizer; otherwise publish 'null' and a redaction marker. Never publish commit authors, bodies, object ids, refs, remote names, remote URLs, dirty filenames, or raw status output. The private facts file contains stable project ids, bounded counts, sanitized branch/subject observations, evidence presence, byte counts, hashes, and reason codes.

Git facts cannot establish health, stage, delivery, deployment, or operational status. Use allowlisted evidence for those judgments and use Unknown when support is absent.

## Interpreting evidence

Classify consequential claims as one of:

- Measured: a bounded mechanical fact observed during collection.
- Documented: directly stated by an allowlisted source with an observation date.
- Verified: supported by an applicable validation, delivery, or operational record.
- Conflicting: current sources disagree and no source establishes supersession.
- Stale: evidence exists but may no longer support the decision.
- Unknown: support is missing or insufficient.

Planning documents establish intent, not completion. A test supports only its recorded scope. A deployment record supports only the named delivery. When evidence conflicts, preserve the conflict instead of choosing a convenient answer.

## Private and candidate data

Keep these values only in the private workspace:

- The absolute projects root and evidence-map location.
- Evidence paths and raw contents.
- Evidence hashes and byte counts.
- Collection diagnostics.
- Any filename or repository identifier rejected by policy.

The snapshot may contain approved project ids and display names, editorial summaries, bounded repository counts, evidence labels, dates, and strictly sanitized branch/commit-subject labels. It must not contain raw evidence, absolute paths, links, addresses, bare host or network locations, Markdown or HTML markup, environment assignments, secrets, Git object ids, or credential-like values.

After the agent reads allowlisted evidence, run the bundled evidence verification against the private facts or recollect the same scope. A hash/size mismatch, symlink swap, missing file, or changed source digest invalidates the review; restart from the new facts instead of finalizing mixed-time evidence.

Sanitization is a technical check, not permission to publish. Project names, priorities, and strategy may remain confidential.

## Attention policy

Rank attention by material consequence and urgency together with evidence strength and freshness. A high-consequence, time-sensitive item may outrank the default category order when its support is at least as strong. Do not promote weak speculation over verified evidence merely because the hypothetical consequence is severe.

Use this category order as a default or tie-breaker among otherwise comparable items:

1. Verified failure or blocker.
2. Explicit unresolved decision.
3. Integration or local-work risk supported by facts.
4. Materially stale evidence.
5. New or unreviewed work with an unknown state.

Every attention item must state the current state, evidence basis, specific risk, and one executable next move. Never invent severity, urgency, an owner, or a deadline.

For a non-attention item, retain a specific risk or next move only when evidence supports it. When neither exists, use `No current supported risk.` and `No action is required.`; do not manufacture follow-up work to fill the schema.
