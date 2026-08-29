# Local website creation

Use this guide only after producing a complete, finalized schema-v2 snapshot. Website creation is part of Central Projects Tracking. Hosting, deployment, scheduling, committing, and sending remain separate actions that require their own authority.

## Product contract

The local site must provide the complete Central Projects Tracking experience:

1. **Brief** — generated time and evidence boundary, derived metrics, architect attention queue, construction-stage distribution, source-integrity status, explicit decisions, evidence gaps, and ready-to-advance next moves.
2. **Portfolio** — one row per current or retained missing project; search across project, summary, stack, stage, and health; All, Attention, Local work, Clean, and Missing filters; result count and empty state.
3. **Activity** — at most eight newest-first commit/evidence/build/study events plus freshest commit, freshest evidence, and longest-quiet summaries. State clearly that activity is evidence, not completion.
4. **System** — what local evidence is connected, what runtime telemetry is not connected, what data is excluded, and the refresh model. Never invent CPU, memory, service, network, CI, or deployment readings.
5. **Project details** — an accessible modal drawer with summary, risk, next move, evidence label, stage, health, stack, branch label, worktree counts, last evidence, last commit, locally recorded outgoing commits, and deterministic commit suggestions.
6. **Interaction** — open details from queues, rows, and next-move cards; close by button, backdrop, or Escape; '/' opens Portfolio and focuses search; copy the next action and relative project label with Clipboard API plus a bounded fallback and an 'aria-live' result.
7. **Quality** — responsive desktop/mobile layouts, visible focus, skip link, 'aria-current', 'aria-pressed', semantic dialog labels, reduced-motion support, no external runtime dependencies, and no data insertion through HTML strings.

The bundled static template implements this contract with no package installation. It deliberately uses a generic Central Projects Tracking identity rather than copying a private environment name, server label, absolute path, or deployment URL.

## Build a fresh local artifact

Resolve explicit paths first:

- 'PROJECTS_ROOT': approved bounded directory containing immediate project children.
- 'FINAL_SNAPSHOT': finalized schema-v2 snapshot outside the projects root.
- 'SITE_OUTPUT': a new, nonexistent directory outside the projects root.

Run from the skill directory:

~~~bash
TRACKING_PYTHON=ABSOLUTE_COMPATIBLE_PYTHON
"$TRACKING_PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 2)'
"$TRACKING_PYTHON" scripts/build_tracking_site.py FINAL_SNAPSHOT \
  --projects-root PROJECTS_ROOT \
  --output-dir SITE_OUTPUT
~~~

The builder refuses symlinked inputs, a snapshot or output inside the scanned root, an existing output, an invalid snapshot, template drift, extra files, and manifest mismatch. It reserves the new output directory exclusively with mode 0700, writes only new mode-0600 files, validates the result, and removes its own incomplete directory on failure.

Validate again at the handoff boundary:

~~~bash
"$TRACKING_PYTHON" scripts/validate_tracking_site.py SITE_OUTPUT \
  --snapshot FINAL_SNAPSHOT \
  --projects-root PROJECTS_ROOT
~~~

Both commands use Python's standard library only. Resolve `TRACKING_PYTHON` to one absolute host-provided Python 3.10+ executable and reuse it; do not assume bare `python3` is compatible. If none is available, stop when the version check returns 2. The supported runtime is a POSIX environment such as Linux, macOS, or WSL with Python 3.10+ and Git available for collection.

## Preview and inspect

For a private local preview, serve the output on a loopback-only address with an available local HTTP server. Do not bind it to a public interface by default. Verify:

- all four views render;
- search, filters, keyboard shortcut, drawers, and both copy actions work;
- small and large viewport layouts remain readable;
- no absolute source path, private fact, raw filename, secret, starter copy, or invented live reading appears;
- the project totals and displayed records match the finalized snapshot;
- 'site-manifest.json' still validates after the preview.

Visual/browser QA is an additional verification layer; it never replaces the snapshot and artifact validators.

## Adapting to an existing React or Sites project

When the user explicitly asks to integrate this surface into an existing website, preserve that project's package manager, lockfile, architecture, hosting identity, privacy policy, and working experience. Treat the bundled HTML/CSS/JavaScript as the behavior and visual contract, not as authority to replace the existing site.

Map the validated snapshot into the project's client data boundary and reproduce every product-contract item above. Derive counters from project records. Keep the snapshot outside server logs and APIs that are not needed. Test the existing build and rendered route, and verify that sensitive source paths and private facts do not enter the built output.

Do not create a generic social-preview image. If publication is later authorized and the site lacks a suitable card, create a site-specific image and metadata only in the separately authorized hosting workflow.

## Handoff

Report the local artifact, snapshot generated time, project coverage, attention count, validation result, and any incomplete evidence. Say explicitly:

- the site is a point-in-time evidence snapshot, not live monitoring;
- locally recorded upstream state was observed without fetching;
- sanitized does not mean approved for public release;
- no commit, push, automation, hosting, deployment, or message was performed.
