# Current Codex collaboration adapter

Read this reference only when delegating work. These names, signatures, and limits describe the current Codex host and may change. Recheck the live tool registry and available capacity before dispatch.

## Capability mapping

- `spawn_agent` starts a child with a bounded `task_name` and `message`. Optional `fork_turns`, `model`, and `reasoning_effort` settings depend on the current host contract. There is no role parameter; express explorer, writer, or verifier responsibility through the task name and brief.
- Prefer `fork_turns: "none"` or a small positive turn count when a self-contained brief is enough. Use full history only when the lane genuinely requires it. In the current host, full-history forks inherit the parent's model and reasoning effort, while overrides require limited or no inherited turns.
- `send_message` delivers information to an existing worker but does not start a new turn when that worker is idle.
- `followup_task` delivers a correction or continuation and starts a turn when the worker is idle.
- `interrupt_agent` stops the current turn and leaves the worker reusable. It does not undo filesystem or external writes, so inspect shared state after interruption.
- `list_agents` inventories current worker state. `wait_agent` supports event-driven waiting; prefer a meaningful wait over repeated unchanged polling.

All current child agents share the coordinator's filesystem and see edits immediately. Single-writer ownership is therefore mandatory even when the host reports multiple available slots.

Capacity is session-specific. Count the coordinator and every descendant against the live tree-wide limit, keep the coordinator free to supervise, avoid marginal lanes, and prefer a shallow delegation tree. If collaboration is unavailable or full, continue safe work locally rather than inventing workers or waiting without purpose.

Separate app tasks or remote workspaces are user-visible workflows with their own state and authority. They are not substitutes for child-agent role parameters. Create or move them only when the user explicitly requested that workflow.

An isolated local worktree can be an in-scope implementation mechanism only when the current host permits it and the coordination contract already authorizes the repository, branch, and write scope. Preserve existing worktrees and user changes, and keep one writer per branch and checkout.
