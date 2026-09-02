# givtaj Codex Skills

A public collection of focused, independently installable skills for ChatGPT and Codex. Published skills are packaged as native Codex plugins and exposed through one GitHub-backed repository marketplace.

The library borrows the useful parts of a well-organized skills collection: clear categories, explicit maturity, focused skills, and one readable catalog. It keeps Codex packaging native so people can install only the capabilities they want.

## Install

Add the marketplace once:

```bash
codex plugin marketplace add givtaj/codex-skills
```

The command registers this repository as a custom source; it does not submit the plugins to OpenAI's universal Plugins Directory. Availability can vary by product surface and workspace policy.

Then install a plugin:

```bash
codex plugin add status-review-dashboard@givtaj-skills
codex plugin add github-repository-guardrails@givtaj-skills
codex plugin add central-projects-tracking@givtaj-skills
codex plugin add terminal-wireframe-sketching@givtaj-skills
```

Start a new task after installation so the new skill is loaded. Invoke a skill explicitly by name, or let the host select it when the request matches its description.

## Catalog

| Plugin | Category | Maturity | What it does |
| --- | --- | --- | --- |
| [`status-review-dashboard`](./plugins/status-review-dashboard/) | Productivity · Project operations | Public preview `0.1.1` | Creates compact, evidence-based status-review dashboards. Results are interactive when the host supports that capability and preserve the same hierarchy in Markdown otherwise. |
| [`github-repository-guardrails`](./plugins/github-repository-guardrails/) | Developer tools · Project operations | Public preview `0.2.1` | Establishes, maintains, and audits repository-management authorities with optional GitHub issue and Project traceability. |
| [`central-projects-tracking`](./plugins/central-projects-tracking/) | Productivity · Project operations | Public preview `0.1.0` | Builds a validated portfolio snapshot and complete private local tracking website across approved repositories, without mutating or fetching them. |
| [`terminal-wireframe-sketching`](./plugins/terminal-wireframe-sketching/) | Creativity | Public preview `0.1.0` | Turns rough sketches, design context, workflows, and software architecture into compact terminal-style wireframes for confirmation. |

The marketplace category is the install-surface category. The catalog may cross-list a plugin under other relevant domains without duplicating its files.

## Maturity model

- **Published preview:** Listed in `.agents/plugins/marketplace.json`, structurally validated, independently installable, and awaiting complete host-level request replay.
- **Stable:** Published and validated against its labelled direct, indirect, incomplete, follow-up, boundary, negative, and edge request set on supported hosts.
- **Incubating:** Kept under `incubator/` while its trigger behavior or workflow is still changing. Not installable from the marketplace.
- **Deprecated:** Kept under `deprecated/` only when historical context or migration guidance remains useful.

## Repository layout

```text
.agents/plugins/marketplace.json   Marketplace catalog
plugins/<plugin>/                  Published, independently installable plugins
catalog/                           Human-readable category indexes
incubator/                         Unreleased work
deprecated/                        Retired work and migration notes
scripts/validate_repo.py           Portable repository validation
CONTRIBUTING.md                    Skill import and quality standard
```

Each published plugin owns its manifest and one or more skills:

```text
plugins/<plugin>/
├── .codex-plugin/plugin.json
└── skills/<skill>/
    ├── SKILL.md
    └── agents/openai.yaml          Optional UI metadata
```

## Add a skill

1. Follow the canonical naming and durable-language import gate in [`CONTRIBUTING.md`](./CONTRIBUTING.md).
2. Package an independent workflow as its own plugin under `plugins/<plugin-name>/`.
3. Add a labelled direct, indirect, incomplete, follow-up, boundary, negative, and edge request set under `plugins/<plugin-name>/evals/`.
4. Add one marketplace entry using `./plugins/<plugin-name>` as its source path and update the category catalog and changelog.
5. Run the repository tests and validators plus the current Codex skill and plugin validators.
6. Install from a local marketplace and replay the golden request set before promoting a preview to stable.

## Verify a checkout

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_repo.py
python3 scripts/validate_public_git_identity.py
```

The public repository also uses GitHub secret scanning and push protection. Local and CI checks remain required because platform scanning is a defense in depth, not a substitute for review.

## Quality model

The repository follows current OpenAI guidance: one recognizable user goal per skill, concise trigger descriptions with explicit boundaries, progressive disclosure for supporting resources, stable plugin identities, and labelled activation tests. Repository policy requires every skill pull request to include a maintainer-reviewed global-name rationale and six-month durability rationale. Host-specific implementation details live in references so the core workflow remains understandable across model and product generations; automated validation catches objective violations but does not replace semantic review. The checks become merge-blocking only when the documented `main` ruleset and CODEOWNER review requirements are enabled on GitHub.

See the [OpenAI skill guide](https://learn.chatgpt.com/docs/build-skills), [plugin packaging and marketplace guide](https://developers.openai.com/plugins/build/plugins), and [metadata evaluation guide](https://developers.openai.com/plugins/guides/optimize-metadata).

## Update

Refresh marketplace sources:

```bash
codex plugin marketplace upgrade givtaj-skills
```

Reinstall the plugin if its installed copy needs refreshing:

```bash
codex plugin add status-review-dashboard@givtaj-skills
codex plugin add github-repository-guardrails@givtaj-skills
codex plugin add central-projects-tracking@givtaj-skills
codex plugin add terminal-wireframe-sketching@givtaj-skills
```

## License

[MIT](./LICENSE)

See also [Privacy](./PRIVACY.md), [Security](./SECURITY.md), [Support](./SUPPORT.md), and [Changelog](./CHANGELOG.md).
