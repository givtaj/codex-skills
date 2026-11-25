# Response Pipe

When you come back to the same chat after working on something else, the last lines tell you which plan item finished and what you can do next. Append `$response-pipe` to a prompt to format the ending, or send it by itself for a quick recap.

## Install

Add the marketplace once, then install the plugin:

```bash
codex plugin marketplace add givtaj/codex-skills
codex plugin add response-pipe@givtaj-skills
```

Once the skill is available, use it in the chat where your work lives:

- **One reply.** “Review this draft and end with $response-pipe.”
- **Every work reply in a chat.** “Use $response-pipe throughout this chat.”
- **Returning to existing work.** Send `$response-pipe` by itself in the conversation with the plan or last result.

## Example

Suppose you’re writing an installation guide in this chat. You approved the outline yesterday. Today, send `$response-pipe` and the reply can be as short as this:

> **Where we left off**
>
> We approved S1, the outline for the installation guide. [Guide checklist](#guide-checklist)
>
> **What’s next**
>
> Continue with S2 here. Draft the install, verify and uninstall example. [S2 · Installation example](#s2--installation-example)

You can reply **“Continue with S2”** in the same chat. The assistant can use the existing plan and start drafting.

### Guide checklist

- **S1 · Outline** — approved.

#### S2 · Installation example

Draft a short example using the install, verify and uninstall commands from the outline.

Version `0.1.0` is a preview adapted from the maintainer’s personal workflow under the repository’s MIT license. It needs only the relevant conversation or supplied work notes. It includes no executable, service or external integration. See the [evaluation cases and validation status](evals/README.md).
