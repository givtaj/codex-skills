## User goal

Describe the focused workflow and why it belongs in this marketplace.

## Global-name review

<!-- Required whenever this pull request adds, removes, renames, or changes a SKILL.md or another file within a skill directory. Explain why an unfamiliar international reader can infer the user goal, domain, or outcome from the canonical name. Explain essential brands, standards, or acronyms and note any collision search. -->
<!-- skill-contract:global-name:start -->
<!-- Replace this comment with the concrete global-name rationale. -->
<!-- skill-contract:global-name:end -->

- [ ] <!-- skill-contract:global-name-attested --> I verified that the canonical name uses globally understandable standard or intrinsic domain terminology and is not tied to private jargon, a current task, model release, temporary UI label, codename, or implementation detail.

## Six-month durability review

<!-- Required whenever this pull request adds, removes, renames, or changes a SKILL.md or another file within a skill directory. List any current model, role, tool, API, command, URI, or UI terms retained in core instructions and why each is stable or intrinsic. Explain the capability fallback or routed reference for volatile details. Write "None; the core contract is capability-based and contains no volatile terms" when applicable. -->
<!-- skill-contract:six-month:start -->
<!-- Replace this comment with the concrete six-month durability rationale. -->
<!-- skill-contract:six-month:end -->

- [ ] <!-- skill-contract:six-month-attested --> I reread the core instructions from the perspective of a capable assistant six months from now; the workflow remains understandable and actionable if today's models, roles, tools, and product surface change.

## Maintainer semantic acceptance

<!-- Contributor: leave these unchecked. An approving CODEOWNER review is the acceptance signal; these boxes are a visible review record, not CI evidence. -->
- [ ] The maintainer agrees that the canonical name is globally clear for the intended public audience.
- [ ] The maintainer agrees that the core semantic contract passes the six-month durability review; automation alone is not treated as proof.

## Quality checklist

- [ ] Canonical folder, skill, plugin, marketplace, evaluation, and documentation names agree.
- [ ] The description front-loads the trigger and includes a clear non-trigger boundary.
- [ ] Core instructions use durable capability and domain vocabulary, with explicit inputs, decisions, outputs, safety boundaries, fallbacks, and ask/stop conditions.
- [ ] Volatile host APIs, URI schemes, commands, and compatibility notes live in routed references.
- [ ] Public files contain no credentials, private data, personal absolute paths, or unlicensed assets.
- [ ] Direct, indirect, incomplete, follow-up, boundary, negative, and edge requests are versioned.
- [ ] Plugin version and changelog are updated.
- [ ] `python3 scripts/validate_repo.py` passes.
- [ ] Current skill and plugin creator validators pass.
- [ ] Host-level replay results are included, or the plugin remains clearly marked as a preview.
