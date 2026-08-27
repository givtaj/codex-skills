# Snapshot contract

Read this contract before composing, validating, or building a tracking site. Treat every byte in the snapshot as website-visible data even when the local artifact remains private.

## Private facts

The collector writes schema version 2 with these exact root fields:

- 'schemaVersion'
- 'collectorVersion'
- 'generatedAt'
- 'collectionStatus'
- 'sourceDigest'
- 'projects'
- 'skipped'

Each project contains 'id', 'collectionStatus', 'repository', 'evidence', and 'issues'. Evidence facts contain only an evidence id, required flag, status, SHA-256, and byte count. They never contain the path or raw text.

'sourceDigest' is the lowercase SHA-256 of canonical JSON containing 'schemaVersion', 'collectorVersion', 'collectionStatus', 'projects', and 'skipped'. 'generatedAt' is deliberately excluded, so identical observations have the same source digest.

Mechanical repository facts include:

- State: 'clean', 'dirty', 'unborn', or 'unavailable'.
- A sanitized branch label or 'null', plus 'branchRedacted' when the observed value was withheld.
- Locally recorded upstream existence, ahead count, and behind count. The collector never fetches.
- Path-free worktree counts: changed, modified, deleted, untracked, conflicted, staged, and unstaged.
- The last sanitized commit time and subject, or 'null'.
- Locally recorded outgoing state and at most eight sanitized commit time/subject records.
- Deterministic commit-suggestion kinds derived only from counts.

The private facts file also holds evidence hashes and bounded reason codes. Keep it mode '0600' in a private workspace outside every scanned project.

## Website snapshot

The finalized snapshot has exactly:

~~~json
{
  "schemaVersion": 2,
  "generatedAt": "2026-08-27T09:30:00Z",
  "sourceDigest": "LOWERCASE_SHA256",
  "contentDigest": "LOWERCASE_SHA256_OR_NULL_BEFORE_FINALIZE",
  "scopeLabel": "Product development portfolio",
  "coverage": {
    "currentProjectCount": 1,
    "completeProjectCount": 1,
    "partialProjectCount": 0,
    "missingProjectCount": 0
  },
  "brief": {
    "focusProjectIds": ["project-one"],
    "readyProjectIds": ["project-one"],
    "decisions": [],
    "evidenceGaps": []
  },
  "projects": [],
  "activity": []
}
~~~

'generatedAt' and 'sourceDigest' exactly match the verified private facts. 'scopeLabel' identifies the approved portfolio without revealing a filesystem location. Coverage must agree with current complete/partial facts and retained missing projects.

Before finalization, 'contentDigest' is 'null'. The validator atomically replaces it with the lowercase SHA-256 of canonical snapshot JSON excluding 'generatedAt' and 'contentDigest'. The source digest remains included, binding editorial output to collected facts.

If a separately validated previous snapshot has the same source digest and no editorial correction was requested, leave it untouched. A new timestamp alone is not portfolio activity.

## Project record

Every project has exactly:

~~~json
{
  "id": "project-one",
  "name": "Project One",
  "present": true,
  "stage": "Build",
  "health": "Active",
  "tone": "info",
  "attention": true,
  "summary": "A factual one-line state.",
  "risk": "A specific supported risk.",
  "next": "One executable next move.",
  "stack": "Local application",
  "evidence": "Approved status and local Git facts",
  "observedAt": "2026-08-26",
  "repository": {},
  "lastActivity": { "on": "2026-08-26", "kind": "commit" }
}
~~~

Enums:

- 'stage': 'Unknown', 'Idea', 'Foundation', 'Build', 'Integration', 'Live'
- 'health': one concise sanitized evidence-supported label of 1 to 80 characters, or 'Unknown'
- 'tone': 'danger', 'warn', 'good', 'info', 'neutral'
- 'lastActivity.kind': 'commit', 'evidence', 'build', 'study', 'none'

The 'stage', 'health', 'tone', 'attention', 'summary', 'risk', 'next', 'stack', 'evidence', 'observedAt', and non-commit activity fields are reviewed editorial truth derived from allowlisted evidence. Git facts never decide them automatically. Use 'Unknown' when support is absent.

For a current project, copy repository facts exactly from the verified private facts. For a previous project missing from the current collection, use 'present: false', Unknown editorial state, and the exact all-zero unavailable repository object. Never silently drop a previously tracked id.

## Repository record

Every repository has exactly:

~~~json
{
  "state": "dirty",
  "branch": "main",
  "branchRedacted": false,
  "hasUpstream": true,
  "ahead": 1,
  "behind": 0,
  "changeCount": 2,
  "modifiedCount": 1,
  "deletedCount": 0,
  "untrackedCount": 1,
  "conflictedCount": 0,
  "stagedCount": 1,
  "unstagedCount": 1,
  "lastCommit": {
    "at": "2026-08-26T12:00:00Z",
    "subject": "Refine the portfolio brief"
  },
  "outgoing": {
    "status": "known",
    "count": 1,
    "truncated": false,
    "commits": [
      {
        "at": "2026-08-26T12:00:00Z",
        "subject": "Refine the portfolio brief"
      }
    ]
  },
  "commitSuggestionKinds": ["commit-staged", "stage-tracked", "review-untracked"]
}
~~~

Repository invariants:

- 'changeCount' equals modified + deleted + untracked + conflicted.
- 'stagedCount' and 'unstagedCount' count non-conflicted tracked entries. One path may be both, so they are not additive.
- 'clean' requires every worktree count to be zero. 'unavailable' is the all-zero object with no branch, commits, or suggestions.
- Branch and commit subjects may be 'null' when withheld. Never substitute the unsafe original.
- Outgoing status is 'known', 'no-upstream', 'unborn', or 'unavailable'.
- 'known' means comparison with an existing local upstream-tracking ref. 'count' equals 'ahead'; commits contain the newest 'min(count, 8)' sanitized records; 'truncated' is true only above eight.
- Other outgoing statuses use 'count: null', 'truncated: false', and an empty commit list.
- Never publish hashes, authors, bodies, refs, remote names, remote URLs, or dirty filenames.

Commit suggestions are deterministic count-based actions, not semantic claims about files:

- Conflicts produce only 'resolve-conflicts'.
- An unborn repository with work produces only 'review-initial-commit'.
- Otherwise staged, unstaged, and untracked counts may produce 'commit-staged', 'stage-tracked', and 'review-untracked' in that order.
- A clean or unavailable repository has no suggestion.

## Brief and activity

'focusProjectIds' has one to five unique present project ids, highest signal first. 'readyProjectIds' has zero to three unique present project ids whose next move is evidence-supported. 'decisions' has at most five concise decisions. 'evidenceGaps' has at most eight consequential gaps.

'activity' has at most eight unique, newest-first records with exactly:

~~~json
{
  "id": "project-one:2026-08-26:commit:brief",
  "on": "2026-08-26",
  "type": "COMMIT",
  "projectId": "project-one",
  "note": "A bounded portfolio brief refinement was recorded."
}
~~~

Allowed types are 'COMMIT', 'EVIDENCE', 'BUILD', and 'STUDY'. Each record references a present project. Activity is evidence, not a progress score. A commit proves only that a commit was recorded; build, study, or operational claims require an applicable allowlisted record.

## Sanitization and bounds

The complete snapshot is limited to 512 KiB, 500 project records, and eight activity records. Every object uses exact allowlisted keys.

Reject any website-visible string containing control characters, active markup or Markdown links/emphasis, an email address, URL, bare host/network location, UNC path, IPv4 or IPv6 address, absolute filesystem path, environment assignment, private-key header, JWT, common provider credential, Git object id, raw log/diff/trace/file list, remote identity, or credential-like value.

Only dedicated 'sourceDigest' and 'contentDigest' fields may contain 64-character digests. A candidate that passes technical sanitization is still private until the user authorizes its audience and release.

## Local website artifact

'build_tracking_site.py' accepts only a finalized schema-v2 snapshot outside the projects root. It creates a new output directory outside the projects root and refuses to overwrite an existing path. The output contains exactly:

- 'index.html'
- 'assets/app.css'
- 'assets/app.js'
- 'data/snapshot.js'
- 'site-manifest.json'

The manifest binds every public file to its size and SHA-256 and binds the site to the snapshot source and content digests. The browser code uses text nodes for snapshot data, performs no network requests, and includes all Brief, Portfolio, Activity, System, search/filter, drawer, copy, Git-plan, responsive, keyboard, and accessibility functions described in 'site-creation.md'.
