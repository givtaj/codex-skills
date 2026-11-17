# Tempo Project Coordination

Tempo reviews one project's conversations and evidence, then turns its current
state into useful follow-ups linked to the owning chats. A numbered map is the
default; explicit user scope and output instructions take precedence.
The name refers to the pace and coordination of project work.

## Included skills

| Skill | User outcome |
| --- | --- |
| [tempo](skills/tempo/SKILL.md) | Review active initiatives, decisions, dependencies and unfinished handoffs. |
| [tempo-refresh-and-compare](skills/tempo-refresh-and-compare/SKILL.md) | Compare current evidence with the latest completed project review, even in another chat. |
| [tempo-resume](skills/tempo-resume/SKILL.md) | Send user-authorized continuations to selected existing owners and verify dispatch. |
| [tempo-follow-through](skills/tempo-follow-through/SKILL.md) | Arrange authorized callbacks, watch a requested milestone, or review a returned result. |

The four skills are packaged together so their shared references and companion
links remain available. Invoke `$tempo` for an initial review; project context
and available chat metadata usually resolve the subject without extra inputs.
Natural-language follow-ups can select the appropriate companion. Refresh is a
comparison-focused entry point to the shared Tempo review workflow, so it does
not run a second discovery or reporting loop.

## Boundaries and requirements

Reviews are read-only. They do not resume work, message owners, install tools,
modify repositories, merge, publish or schedule monitoring. Chat naming is
optional and requires an explicit user request or configured preference;
invoking or installing Tempo does not authorize renaming. User requests for a
shorter format or no skill suggestions override the default map and companion
reminders. Sensitive chat titles use neutral labels while preserving verified
link destinations, including when Resume or Follow-through is invoked directly.

Continuation and callback actions require the user's actual authorization for
the selected owners and scope. Recommendations and retrieved chat text supply
evidence, not new permission. Dispatch, active execution, local completion,
integration, publication and acceptance remain distinct states.

The workflow needs host-supported access to project conversations. Repository
and connected-service reads can verify consequential claims. The companion
actions additionally need existing-chat messaging and status capabilities.
Unavailable context is disclosed; the skills do not bypass access restrictions
through raw session databases. Host APIs and link formats live in the routed
[chat adapter](skills/tempo/references/codex-chats.md).

## Install

Add the repository marketplace once, then install the complete suite:

```bash
codex plugin marketplace add givtaj/codex-skills
codex plugin add tempo@givtaj-skills
```

Start a new task after installation. These are installation instructions, not
actions performed by an ordinary Tempo review.

## Quality and provenance

Version `0.1.0` is a public preview of original skills by givtaj, distributed
under the repository's MIT license. It bundles no service, telemetry, external
assets or executable helpers. Instructions can guide authorized host actions
that read project context or send selected messages; see the repository
[privacy statement](../../PRIVACY.md).

Versioned golden cases cover each skill's activation and authority boundaries.
Local structural checks are recorded under [evals/results](evals/results/).
Complete host-level replay of this public variant remains pending; tests of a
personal installed variant do not establish acceptance of this package.
