# Reusable creation prompt

Use this prompt as a starting point after installing the plugin. Replace every placeholder; unresolved placeholders are not authority.

~~~text
Use $central-projects-tracking to create a complete local Central Projects Tracking website.

Approved projects root: <absolute bounded projects directory>
Evidence map: <absolute path to the reviewed evidence-map JSON outside that root>
Private workspace: <new private temporary directory outside the projects root>
Previous finalized snapshot: <absolute path, or say none>
Previous local site: <absolute path, or say none>
Final snapshot: <new path outside the projects root>
Local site output: <new nonexistent directory outside the projects root>
Audience/scope label: <safe portfolio label>

Keep every project repository read-only. Collect only bounded local Git facts and exact allowlisted evidence; do not fetch or run project code. Preserve unknown or conflicting states instead of guessing. Verify evidence hashes and sizes after review, validate the previous snapshot before relying on it, finalize the new schema-v2 snapshot, then deterministically build and validate the complete four-view website.

The site must include Brief, Portfolio, Activity, and System views; derived metrics; attention and ready queues; decision and evidence-gap panels; stage distribution; search and signal filters; accessible project drawers; copyable next actions and relative project labels; path-free Git change counts; locally recorded outgoing commits; deterministic commit suggestions; responsive and reduced-motion behavior; and explicit evidence/privacy/runtime limits.

Stop after the validated local website. Do not commit, push, schedule, publish, deploy, send, or widen access. Report partial evidence rather than producing a complete artifact when a required source or integrity check fails.
~~~

For a refresh, reuse only paths and audience decisions that the current task context explicitly supplies. If the new 'sourceDigest' equals the separately validated previous snapshot and no editorial correction was requested, leave the prior snapshot and site untouched.
