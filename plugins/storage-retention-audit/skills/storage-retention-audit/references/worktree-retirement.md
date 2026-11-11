# Worktree retirement

Use this guide to assess a specific worktree and prepare a scoped retirement proposal. Keep the assessment read-only. Use the parent skill to measure space and handle approval for cleanup.

## Identify what exists and who uses it

Record the observation time and check each surface independently. One missing or stale record can coexist with live work on another surface.

| Surface | What to verify |
| --- | --- |
| Checkout directory | Resolve the exact path and repository identity. Check whether the directory exists, whether any path component is a symlink, and whether it contains nested repositories or mounts that need separate handling. |
| Git worktree registration | Use Git's worktree listing to confirm the registered path, HEAD, attached branch or detached state, and lock or missing-path status. Distinguish the main checkout from linked worktrees. |
| Branch and refs | Record the exact revision, local refs, and any verified upstream or PR head. Check whether another worktree uses the branch and whether the revision depends on refs that could disappear. |
| Codex workspace and chat | Use supported app or task interfaces to find the associated chat, activity, workspace entry and owner. Record which associations were verified and which remain unknown. |

Check active sessions, builds, services, processes and open files in scope. Look for references in configurations, scripts, symlinks, project records and relevant handoffs. Establish who owns active or unfinished work and whether another checkout still depends on the directory. Recent activity, missing tool access and stale app entries can leave ownership or dependencies unresolved. Keep those items in the proposal as unknown or retain until resolved.

## Account for work and evidence

Inspect the HEAD, staged and unstaged changes, untracked files, and relevant ignored outputs. Inventory distinct evidence, fixtures, databases, frozen binaries, local refs and archives that a clean Git status would miss. Use bounded metadata checks and relevant project references to identify them without dumping private contents. Check submodules or nested repositories when they hold part of the work.

Classify meaningful work against the intended base and any claimed successor. Use commit ancestry for original commits, and verified merge metadata plus targeted tree or patch comparison for squash, rebase or cherry-pick cases. Use the repository state review workflow for a deeper integration assessment if needed.

| Finding | Evidence to retain in the assessment |
| --- | --- |
| Integrated | The intended base contains the commits or a verified integration result. Record the revision and check for distinct files outside that history. |
| Patch equivalent | Targeted comparison shows the same changes under different commit IDs. Record the matched content and any remaining context or behavior uncertainty. |
| Successor only | A retained successor contains the work. Record its exact path and revision, verify matching content, and establish that it will remain recoverable. |
| Unique | Identify the work or evidence available only here. Keep it in place or establish a verified preservation path before removal. |
| Unknown | Record the missing reference, inaccessible data or ambiguous comparison and the evidence needed to resolve it. |

## Preserve and propose

For any item that needs preservation, identify the files, refs, revisions, index state and metadata required to reconstruct it. Choose a preservation destination outside the removal set. For an approved preservation step, verify the retained contents against the source and test restoration in an isolated location where recovery is required. Record the destination, verification evidence and restore instructions. Describe a same-disk copy as local preservation. Claim off-host recovery only to the extent the remote copy and restoration were verified.

Give the user the exact directory and proposed action, the records or refs affected by that action, any required preservation, protected paths, and the expected reclaim range. Treat branch deletion, Git registration pruning or repair, Codex archiving or entry removal, stopping active processes, and remote changes as distinct operations. If a supported tool bundles effects, include those effects in the proposal before requesting approval. An absent checkout with a leftover registration or app entry needs its own scoped disposition.

## Verify an approved retirement

Immediately before execution, recheck the target path, repository identity, HEAD, and staged, unstaged, untracked and relevant ignored content. Recheck active use, dependencies and preservation evidence. If the target changed or someone resumed work, pause the affected item and resolve the discrepancy. Use the supported Git or app operation for the confirmed scope. If only a broader operation is available, report the remaining record and what would be needed to retire it safely.

Read back the checkout path, Git registration, branch and Codex entry separately. Verify the expected change on each affected surface, the retained recovery evidence, and the protected checkouts, refs and important uncommitted data. Report any active concurrent changes without reversing someone else's work. Name the actions completed, the records that still need attention and the location of any verified recovery copy. Use the parent audit's measurement rules when attributing reclaimed space.
