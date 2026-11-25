# Conversation links

Prefer a link supplied by the host or user for the destination conversation. Use the current title as the label when safe for the reader. A step owned in the current conversation can simply say “here.”

When Codex desktop exposes verified conversation metadata without a link, it supports these Markdown destinations:

- Local Codex conversation: `codex://threads/THREAD_ID`.
- Remote Codex conversation: `codex://threads/THREAD_ID?hostId=ENCODED_HOST_ID`.
- ChatGPT conversation: `https://chatgpt.com/c/ENCODED_CONVERSATION_ID`.

Substitute verified identifiers from the destination’s metadata and URL-encode parameters. A project ID, guessed ID, display title, or local label cannot establish a conversation route. Prefer any newer host-provided link. If the host, destination or audience access is unclear, describe where to continue in words. Keep private conversation links out of shareable drafts.
