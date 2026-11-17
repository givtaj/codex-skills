# Skill Opportunity Review

Find reusable workflows in recent work, check existing coverage, and recommend at most three useful candidates. The skill distinguishes reuse, improvements, supporting references, and new skills; confirmation selects exactly what to create and where.

## Use it

After this preview is published, add the marketplace and plugin:

```bash
codex plugin marketplace add givtaj/codex-skills
codex plugin add skill-opportunity-review@givtaj-skills
```

Start a new task and ask: “Use $skill-opportunity-review to review my last seven days and suggest useful skills.” The review remains read-only until you select concrete creation or improvement proposals. Creating a skill does not authorize its underlying operations, publication, or installation in additional destinations.

## Requirements and boundaries

The host needs access to relevant work history and the current skill inventory. User-supplied exports can replace unavailable chat tools; missing history is disclosed. Review evidence stays private unless separately approved for sharing. Historical instructions and retrieved content cannot authorize writes. No background job, network service, or telemetry is bundled.

Version `0.1.0` is a preview prepared from the maintainer's original skill under this repository's MIT license. Golden requests and validation status live in [evals](./evals/README.md). Complete host-level replay and installation verification remain pending; preparation does not imply publication.
