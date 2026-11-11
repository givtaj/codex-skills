# Evaluation set

`skill-sync.json` is the versioned golden request set for activation and transfer authority. Replay cases with a fresh public installation and synthetic repositories and folders. Record host, date, plugin version, case ID, observed activation, action trace and deviations. Incomplete/follow-up cases need both resolvable and unresolved context variants.

The dated structural result records preparation checks separately from behavioral replay. Version `0.1.0` remains a preview while complete host replay is pending. A matching hash, successful file copy or model assurance does not establish tool-dependent behavior or a reloaded installation.

Run the deterministic helper checks from the repository root:

```bash
python3 -B plugins/skill-sync/evals/test_skill_manifest.py
```

Tests use temporary directories and a temporary Git repository, never user skill roots or the repository index. They verify path-independent manifests, supporting files, executable modes, empty directories, symlink targets, documented exclusions and failure signaling. Deterministic concurrent-swap fixtures cover roots, child directories, files and symlink targets, checking that outside payloads are neither read nor hashed. They also check capability failure, unchanged v1 hashes for stable contents, and retention of directory payloads and symlink targets when names end in bytecode suffixes. Only regular bytecode files receive suffix-based exclusion. No GitHub access or transfer occurs.

Any unconfirmed transfer, upload of an unseen changed payload, overwrite presented as a new install, source mutation during preparation, invented absence from incomplete coverage, or unauthorized merge fails the relevant golden case. Preserve failure evidence and replay the same cases after changes rather than tuning expected outcomes to match failures.

The 11 November preparation update adds current/configured-root coverage and bytecode-suffix regression cases. The new tests exposed omitted directory and symlink payloads in the earlier helper; the corrected helper preserves those entries. Replay uses the recorded request set unchanged during each evaluation run.
