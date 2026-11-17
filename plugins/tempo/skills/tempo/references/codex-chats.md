# Codex chat access and links

Use the current host's tool schemas; discover capabilities by name/description.
These instructions do not require every tool to be available on every host.

## Discover and read

- `list_projects` resolves project identity and repository/workspace paths.
- `list_threads` discovers recent, pinned and sectioned chats. For bounded history,
  use `mode: "history"`, the appropriate Codex host, `source: "codex"` and pagination.
  Include archived chats only for a relevant reference or unfinished handoff.
  Match by project identity and actual cwd/worktree relationships, not title alone.
- `read_thread` reads actual conversation content. Preserve `thread.id`, `hostId`,
  backing `kind`, exact `title`, status, timestamps and pagination information.
  Start with a few turns; use its cursor when the latest handoff needs older context.
  Listing summaries do not substitute for reading messages.
- `wait_threads` supplies compact current status for known Codex chats. Use
  `timeoutMs: 0` for a snapshot and preserve each target's host and returned cursor.
  A response can return only the first actionable target: inspect errors and omitted
  targets and obtain any other snapshots needed. Do not repeatedly reread huge chats
  to poll status. Read a new turn when a snapshot indicates changed user direction.

The tool names are commonly prefixed `mcp__codex_app__`. Do not send messages to
the discovered chats as a way of obtaining status unless the current user has
explicitly authorized messaging them.

If chat tools are unavailable, disclose the missing context and use supplied chat
links/exports where available. Do not substitute a repository-only report while
claiming to have reviewed project conversations. Do not scrape raw session stores,
chat databases or rollout files to bypass missing chat visibility.

## Name only the calling chat

Only after explicit naming authorization under `SKILL.md`, discover `set_thread_title` and
inspect its current schema. The desktop tool supports omitting `threadId` to target
the calling chat. Use that form for automatic naming; do not pass a discovered
initiative's ID or infer the caller from the most recent sidebar entry.

Resolve the calling identity from explicit runtime context, such as
`CODEX_THREAD_ID` when available, and read its current metadata with `read_thread`.
Read only the named environment variable, not the entire environment. Match the
returned identity and backing kind and establish that this is a new coordinator
chat from the current conversation; obtain additional history only if necessary.
If no reliable calling identity is available, skip automatic naming. Do not scan
raw application/session files to infer it.

Derive `DD/MM HH:mm` from the first Tempo turn's `startedAt` (or the fallback
in `SKILL.md`) in the current user/client IANA timezone. Use timezone-aware
formatting such as `Intl.DateTimeFormat` with an explicit `timeZone` and
`hourCycle: "h23"`, or Python `zoneinfo`; convert epoch seconds as seconds, not
milliseconds. The suffix has a single separating space, zero-padded components,
and no seconds or year. Do not guess a timezone or timestamp. If reliable time
context is unavailable, apply the eligible prefix only and briefly disclose the
missing suffix. The title's start time does not replace the report's as-of time.

Immediately before the mutation, use the latest title and current user instructions
to decide whether naming still applies. Preserve an explicit user-selected title.
For an eligible new chat missing the prefix or timestamp, call `set_thread_title`
with the derived `title`, the verified `source` where required, and no `threadId`.
A correctly named chat needs no mutation; later refreshes do not update its date.
This operation changes only
the caller's title; it does not message or resume any chat. Read back that same
identity once to verify the result. If another actor changed the title, preserve
the newer state rather than repeatedly overwriting it. Report a failed/unavailable
rename briefly and continue the review.

## Keep retrieval bounded

Read responses may contain many command and reasoning items even with
`includeOutputs: false`. When using a tool orchestrator, inspect structured content
or parse the tool's JSON text, then display only the identity, page information,
user messages and assistant messages relevant to the review. Keep the raw response
available in temporary in-session state for a targeted follow-up. Do not print all
tool traces into the coordinator context.

A typical first read uses `turnLimit: 2` or `3`, `includeOutputs: false` and a modest
output cap. These settings do not guarantee small responses. Extract text content
from user messages rather than dumping attachments or raw tool arguments. Read
additional output only when it is necessary to verify a finding.

## Safe title labels

Use a verified current chat title as the link label when it is safe to repeat.
If the title contains credentials or unnecessary private/customer details, use a
short neutral label such as “Owning implementation chat” instead. Preserve the
verified destination ID/URL; changing the label does not rename the chat or
change its identity. Do not copy the sensitive original into explanatory text,
quoted context or handoff messages. This rule applies to every Tempo companion,
including direct Resume and Follow-through invocations that do not load the
main review skill.

## Mandatory clickable chat links

Prefer a canonical chat URL returned by the host or already supplied by the user.
For a verified local Codex chat in the desktop app, use this Markdown shape:

```markdown
[Exact current chat title](codex://threads/VERIFIED_THREAD_ID)
```

Replace `VERIFIED_THREAD_ID` with the exact ID returned for that chat by
`list_threads`, `read_thread` or `wait_threads`. This is a link-format example,
not a chat identity. Confirm the title through metadata, apply the safe-label
rule above, escape Markdown label characters as needed, and keep the target
outside code spans. Never derive an ID
from a title, guessed UUID, project ID, worktree or another chat's ID.

For other backing kinds/hosts, use their distinct routes:

- Remote Codex: `codex://threads/VERIFIED_THREAD_ID?hostId=ENCODED_HOST_ID`.
  URL-encode the exact returned host ID, for example with `URLSearchParams`.
- ChatGPT-backed: `https://chatgpt.com/c/ENCODED_CONVERSATION_ID`.
  Encode the verified conversation ID; do not convert it into a Codex link.

Keep `hostId` for reads even when a URL omits it. Never use a pending
`clientThreadId` as a completed chat ID. When no supported route is established,
state that the link is unavailable and retain the exact safe title.

These are host-adapter routes, not a guarantee across future product versions.
Prefer returned canonical links and the current host documentation when available.

Validate links by resolving their identities through read-only chat tools. Do not
open every linked chat, change the sidebar or mark messages read just to test links.
Identity/format validation is not a claim that an interactive click was tested.

Use chat links for the owning effort even when its latest evidence is a PR or
repository file. A linked PR alone does not satisfy the coordinator's navigation
requirement.

## Send and verify an authorized handoff

For a user-authorized continuation or callback instruction, discover
`send_message_to_thread` and inspect its schema. Preserve the selected owner's
verified ID, host, backing kind and settings. Use `read_thread` for actual recent
messages, and `wait_threads` with `timeoutMs: 0` for an immediate dispatch-status
snapshot. Preserve returned cursors for any explicitly requested watch. A
successful send establishes delivery, not an active turn or completed work.
Inspect delivery before retrying a timeout.

For callbacks, verify the coordinator destination using explicit runtime identity
(such as reading only `CODEX_THREAD_ID`) plus chat metadata, or the user's supplied
destination. Do not infer it from sidebar order. Include the source chat and the
actual human instruction authorizing the callback so the recipient can verify it
through `read_thread`. Missing tools or unresolved identity require an honest
limitation and prepared unsent handoff, not raw-session scraping or a guessed
destination.
