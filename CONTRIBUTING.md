# Contributing

This repository publishes focused, portable workflows as skills-only Codex plugins. Every import must preserve the workflow's meaning while removing accidental dependence on one machine, model generation, or temporary product surface.

## Import gate

### 1. Establish provenance and permission

- Identify the original skill directory and author.
- Confirm that the skill and every bundled asset can be redistributed under this repository's license.
- Exclude credentials, private data, proprietary documents, generated caches, and machine-specific state.
- Record any external service, binary, package, or host capability the workflow requires.

### 2. Choose one canonical identity

Inspect the `SKILL.md` frontmatter before copying files.

- Use a stable lower-case kebab-case name that describes the recognizable user goal, domain, or outcome.
- Prefer durable names such as `status-review-dashboard` over a task title, date, model version, internal codename, or implementation detail.
- Keep an accurate existing name. Rename only when the source name is misleading, collides with another skill, or exposes private vocabulary.
- Keep the skill folder and frontmatter `name` identical.
- For a one-skill plugin, use the same canonical name for the plugin folder, manifest, marketplace entry, and evaluation file.
- Treat a later rename as a migration: document it, update all references, and avoid silently creating two identities.

### 3. Write a durable semantic contract

Use vocabulary that describes the work rather than today's implementation:

- Prefer `user`, `input`, `evidence`, `source`, `tool`, `capability`, `decision`, `output`, `validation`, `assistant`, and `host` when those concepts are accurate.
- State expected inputs, ordered decisions or steps, required outputs, facts that must not be inferred, and when to ask, stop, or decline.
- Do not depend on a model family, version number, temporary role name, or current UI label in the core instructions.
- Name a concrete tool only when the workflow truly requires it. Describe the capability and fallback first.
- Put host-specific APIs, volatile commands, schemas, and compatibility notes in `references/`; tell the skill when to read them.
- Preserve the user's domain terminology. Do not invent generic agent jargon where a standard domain term exists.

The description is the activation contract. Front-load the outcome and trigger terms because hosts may shorten long descriptions. Include a clear `Do not use` boundary to protect precision.

### 4. Use progressive disclosure

- Keep `SKILL.md` focused on the workflow.
- Put detailed policies, schemas, and volatile platform notes in `references/`.
- Put deterministic processing in `scripts/` only when existing tools and instructions are not reliable enough.
- Put templates and transformable resources in `assets/`.
- Link each supporting resource from `SKILL.md` and state exactly when to load or run it.

### 5. Make the public boundary explicit

- Default to read-only behavior when the workflow is for review or analysis.
- Treat retrieved content as data, not instructions.
- State what must not be guessed or fabricated.
- Require explicit user authority for publishing, sending, deleting, deploying, or modifying external state.
- Remove personal absolute paths and environment-specific secrets.

### 6. Add a golden request set

Create `plugins/<plugin>/evals/<skill>.json` with at least one case for each:

- `direct`: explicitly names the skill or exact outcome.
- `indirect`: expresses the same goal in natural language.
- `incomplete`: should activate only when context resolves the missing subject, or should ask one material question.
- `follow_up`: continues or refreshes the same workflow without losing its scope or safety rules.
- `boundary`: nearby intent that should remain with a general workflow.
- `negative`: should not activate.
- `edge`: must avoid invented facts or unsupported actions.

Record expected activation and observable behavior. Change one metadata field at a time when tuning, then replay the same cases.

### 7. Package and document it

- Add `.codex-plugin/plugin.json` with a stable kebab-case name, semantic version, publisher metadata, install-surface copy, capabilities, and starter prompts.
- Add the plugin to `.agents/plugins/marketplace.json` using a `./plugins/<name>` source path and explicit installation, authentication, and category fields.
- Add a plugin README, category entry, and changelog entry.
- Start new public previews at `0.1.0`; increment the version whenever installed behavior changes.

## Validate

Run from the repository root:

```bash
python3 scripts/validate_repo.py
```

During authoring, also run the current validators supplied by the Codex skill and plugin creators. Finally, install from a local marketplace and replay the golden request set in a new conversation before promoting a preview to stable.

## Current references

- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Build plugin skills](https://developers.openai.com/plugins/build/skills)
- [Package plugins and repo marketplaces](https://developers.openai.com/plugins/build/plugins)
- [Optimize metadata](https://developers.openai.com/plugins/guides/optimize-metadata)
- [Current OpenAI plugin examples](https://github.com/openai/plugins)
