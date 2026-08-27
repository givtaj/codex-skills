# Central Projects Tracking

Central Projects Tracking turns an explicitly approved directory of local projects into a validated evidence snapshot and a complete private local tracking website.

## What it does

- Discovers only immediate child Git repositories under the approved root.
- Collects bounded local Git facts without fetching, executing project code, or publishing dirty filenames.
- Reads only exact evidence files authorized by a separate evidence map.
- Keeps private paths, evidence hashes, and diagnostics separate from website-visible data.
- Verifies evidence again after review so the final snapshot cannot silently mix old hashes with changed content.
- Validates exact schemas, previous-snapshot continuity, coverage, source and content digests, and sensitive-output rules.
- Builds and validates a deterministic offline website tied to the finalized snapshot digests.

## Complete website

The bundled website is not a generic card grid. It includes:

- Brief, Portfolio, Activity, and System views.
- Derived metrics, an architect attention queue, delivery-stage distribution, explicit decisions and evidence gaps, and ready-to-advance next moves.
- Search plus All, Attention, Local work, Clean, and Missing filters.
- Accessible project detail drawers with risk, next action, evidence, branch label, path-free worktree counts, last commit, locally recorded outgoing commits, and deterministic commit suggestions.
- Copyable next actions and relative project labels with keyboard and screen-reader feedback.
- Responsive layouts, visible focus, reduced-motion support, and an explicit snapshot-versus-live-telemetry boundary.

The browser performs no network request. Snapshot strings enter the UI through text nodes, not interpreted HTML.

## Inputs and outputs

The workflow needs:

1. An explicit bounded projects root.
2. A reviewed evidence-map file outside that root.
3. A private temporary workspace outside scanned projects.
4. Optional previous finalized snapshot.
5. Optional absolute path to the previous validated local site outside scanned projects, tied to that snapshot.
6. New snapshot and local-site destinations outside scanned projects.
7. A safe audience/scope label.

The bundled evidence map is a template, not permission to read files. When verified facts are unchanged and no editorial correction was requested, the validated previous snapshot and previous local site remain untouched. Otherwise, complete collection produces private mode-0600 facts, a finalized mode-0600 schema-v2 snapshot, and a new validated local website directory. Partial collection returns bounded reason codes and stops before final snapshot or website creation.

See:

- **skills/central-projects-tracking/references/evidence-policy.md**
- **skills/central-projects-tracking/references/snapshot-contract.md**
- **skills/central-projects-tracking/references/site-creation.md**
- **skills/central-projects-tracking/references/creation-prompt.md**

Sanitized means the snapshot passed the bundled technical checks. It does not mean project identities, priorities, strategy, or the local website are approved for public release.

## Runtime requirements

- A POSIX environment such as Linux, macOS, or WSL.
- Python 3.10 or newer, using only the standard library.
- A local Git executable.
- Read access to the approved root and allowlisted evidence.
- Write access only to private temporary and requested output locations outside scanned projects.

The plugin installs no package, runs no bundled network service, sends no telemetry, and has no remote dependency.

## Authority boundary

The skill creates the validated local website. It does not modify scanned repositories, fetch, run project code, commit, push, schedule, publish, deploy, send a report, or widen access. Those are separately authorized workflows.

## Public-preview status

Version 0.1.0 is structurally validated. Host-level activation and end-to-end behavioral replay remain pending, so it is published as a preview.
