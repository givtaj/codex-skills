# Interactive host adapters

Read this reference only when implementing the dashboard's refresh control. The capability contract is stable; host-specific examples can change.

## Capability contract

A supported inline host should let the visualization request a follow-up turn with plain text. The refresh control must:

1. Detect the capability before enabling the control.
2. Send one follow-up request that identifies the same subject, evidence scope, and period policy.
3. Preserve read-only behavior, source links, evidence labels, and the rule against invented metrics.
4. Show a pending state and prevent duplicate requests.
5. Treat successful dispatch as a request, not proof that the dashboard has refreshed.
6. Provide a disabled-state explanation when the capability is absent.

Use the host's current documented interface. Do not infer an API from an old example.

## OpenAI inline visualization adapter

At the time this reference was written, an OpenAI inline visualization may expose `window.openai.sendFollowUpMessage`. Feature-detect the function at runtime before calling it. If the host exposes a documented successor, use that successor while preserving the capability contract above.

Send a concise request equivalent to:

> Rescan the same subject and evidence sources through the current date. Update this dashboard in place, preserve direct links and evidence labels, remain read-only, and do not publish or deploy.

If the function is unavailable, disable the button and show `Ask the assistant to refresh this dashboard.`
