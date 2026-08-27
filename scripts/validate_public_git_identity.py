#!/usr/bin/env python3
"""Reject a new public commit or annotated tag that exposes a direct email."""

from __future__ import annotations

import re
import subprocess
import sys


NOREPLY_RE = re.compile(
    r"^(?:[0-9]+\+)?[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?@users\.noreply\.github\.com$"
)
LEGACY_COMMIT_EXEMPTIONS = {
    "2812135ecf2899a8381d2711af33e0c233f77ad0",
    "c6f813cd204c37cafc0fd9f5221bfad81e970b81",
}
LEGACY_TAG_EXEMPTIONS = {"status-review-dashboard-v0.1.0"}


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def require_noreply(label: str, email: str) -> None:
    if NOREPLY_RE.fullmatch(email) is None:
        raise ValueError(f"{label} must use a GitHub-provided noreply address")


def main() -> int:
    try:
        commit_count = 0
        for commit in git("rev-list", "HEAD").splitlines():
            if commit in LEGACY_COMMIT_EXEMPTIONS:
                continue
            fields = git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", commit).split("\x00")
            if len(fields) != 4 or not fields[0].strip() or not fields[2].strip():
                raise ValueError(f"commit {commit[:12]} is missing author or committer identity")
            require_noreply(f"commit {commit[:12]} author", fields[1].strip())
            require_noreply(f"commit {commit[:12]} committer", fields[3].strip())
            commit_count += 1

        tag_lines = git(
            "for-each-ref",
            "--format=%(refname:short)%00%(objecttype)%00%(taggeremail)",
            "refs/tags",
        )
        tag_count = 0
        for line in tag_lines.splitlines():
            if not line:
                continue
            tag_name, object_type, tagger = line.split("\x00", 2)
            if object_type != "tag" or tag_name in LEGACY_TAG_EXEMPTIONS:
                continue
            match = re.search(r"<([^<>]+)>\s*$", tagger)
            if match is None:
                raise ValueError(f"annotated tag {tag_name} is missing a tagger email")
            require_noreply(f"annotated tag {tag_name} tagger", match.group(1))
            tag_count += 1
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"public Git identity validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        f"Validated public Git identity for {commit_count} non-legacy commit(s) "
        f"and {tag_count} non-legacy annotated tag(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
