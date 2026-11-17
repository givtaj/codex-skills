# Host discovery and authoring

Read this when locating existing skills or resolving a proposed write destination. Prefer the host's current skill catalog and supported history tools; check current tool schemas before use.

For filesystem-backed Codex skills, inspect the current user root, normally `~/.agents/skills`, and `.agents/skills` folders from the current working directory up to the repository root. Include explicitly configured or legacy roots only when the current host confirms they are recognized. Use bounded discovery such as `rg --files --hidden -g SKILL.md` within those known roots. Include enabled plugins through their supported inventory; a cache directory alone does not establish installation. Read full matching instructions before judging overlap.

Use the destination supplied by the user. Otherwise use a verified configured user skill root, or Codex's documented default `~/.agents/skills` when there is no override. Do not infer a skill-root override merely from `CODEX_HOME`; older locations such as `~/.codex/skills` require current host evidence or an explicit user choice. Check the [current discovery documentation](https://learn.chatgpt.com/docs/build-skills#where-to-save-skills) if host behavior is uncertain. Display resolved source and installation paths separately in each proposal; do not create either until that proposal is confirmed. If the host has no filesystem skill support, provide a proposal and disclose that limitation.

After approval, use the available skill-creator workflow and its current validation commands. If unavailable, author the standard `SKILL.md` folder described by the main workflow. Supported chat exports can supply history when tools are missing; never inspect hidden session databases as a fallback.
