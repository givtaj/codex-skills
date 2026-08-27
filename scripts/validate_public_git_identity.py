#!/usr/bin/env python3
"""Reject public Git objects that expose a direct email address."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Sequence


_GITHUB_LOGIN = r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
NOREPLY_RE = re.compile(
    rf"^(?:noreply@github\.com|(?:[0-9]+\+)?{_GITHUB_LOGIN}(?:\[bot\])?"
    r"@users\.noreply\.github\.com)$",
    re.IGNORECASE,
)
LEGACY_COMMIT_EXEMPTIONS = {
    "2812135ecf2899a8381d2711af33e0c233f77ad0",
    "c6f813cd204c37cafc0fd9f5221bfad81e970b81",
}
# Exempt the immutable annotated-tag object, not a tag ref that can be moved.
LEGACY_TAG_OBJECT_EXEMPTIONS = {
    "85d7b564961bcbbc7f47325f8df18fd5ab49b4fb",
}


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


def require_complete_history() -> None:
    if git("rev-parse", "--is-shallow-repository") == "true":
        raise ValueError(
            "default all-ref validation requires a complete Git history; fetch with "
            "--unshallow or validate an intentional contribution range with --commit-range"
        )


def default_commit_revisions() -> list[str]:
    """Return commit roots visible through publishable refs and the checkout."""

    ref_lines = git(
        "for-each-ref",
        "--format=%(refname)%00%(objecttype)%00%(*objecttype)",
        "refs/heads",
        "refs/remotes",
        "refs/tags",
    ).splitlines()
    revisions: set[str] = set()
    for line in ref_lines:
        if not line:
            continue
        ref_name, object_type, peeled_object_type = line.split("\x00", 2)
        if object_type == "commit" or peeled_object_type == "commit":
            revisions.add(ref_name)

    # A pull_request checkout can leave its synthetic merge commit detached and
    # therefore absent from every ref namespace. Include it for the safe default;
    # callers can select the contribution itself with --commit-range.
    head = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", "HEAD^{commit}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if head.returncode == 0:
        revisions.add(head.stdout.strip())

    return sorted(revisions)


def commits_for(revisions: Sequence[str]) -> list[str]:
    if not revisions:
        return []
    for revision in revisions:
        if not revision or revision.startswith("-") or "\n" in revision:
            raise ValueError(f"invalid commit revision: {revision!r}")
    return git("rev-list", *revisions, "--").splitlines()


def validate_commits(revisions: Sequence[str]) -> int:
    commit_count = 0
    for commit in commits_for(revisions):
        if commit in LEGACY_COMMIT_EXEMPTIONS:
            continue
        fields = git("show", "-s", "--format=%an%x00%ae%x00%cn%x00%ce", commit).split(
            "\x00"
        )
        if len(fields) != 4 or not fields[0].strip() or not fields[2].strip():
            raise ValueError(f"commit {commit[:12]} is missing author or committer identity")
        require_noreply(f"commit {commit[:12]} author", fields[1].strip())
        require_noreply(f"commit {commit[:12]} committer", fields[3].strip())
        commit_count += 1
    return commit_count


def validate_annotated_tags() -> int:
    tag_lines = git(
        "for-each-ref",
        "--format=%(refname)%00%(objectname)%00%(objecttype)%00%(taggeremail)",
        "refs/tags",
    )
    tag_count = 0
    for line in tag_lines.splitlines():
        if not line:
            continue
        ref_name, object_id, object_type, tagger = line.split("\x00", 3)
        if object_type != "tag" or object_id in LEGACY_TAG_OBJECT_EXEMPTIONS:
            continue
        tag_name = ref_name.removeprefix("refs/tags/")
        match = re.search(r"<([^<>]+)>\s*$", tagger)
        if match is None:
            raise ValueError(f"annotated tag {tag_name} is missing a tagger email")
        require_noreply(f"annotated tag {tag_name} tagger", match.group(1))
        tag_count += 1
    return tag_count


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate public commit and annotated-tag Git identities."
    )
    parser.add_argument(
        "--commit-range",
        action="append",
        default=[],
        metavar="REVISION",
        help=(
            "Git revision or range to validate with git rev-list; repeat to add roots. "
            "When omitted, local branches, remote branches, tags, and HEAD are validated. "
            "For a pull-request contribution without its synthetic merge, pass a range "
            "such as HEAD^1..HEAD^2."
        ),
    )
    parser.add_argument(
        "--skip-tags",
        action="store_true",
        help="Skip annotated-tag identity checks (useful for a contribution-only range).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.commit_range:
            revisions = args.commit_range
        else:
            require_complete_history()
            revisions = default_commit_revisions()
        commit_count = validate_commits(revisions)
        tag_count = 0 if args.skip_tags else validate_annotated_tags()
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            detail = exc.stderr.strip()
        else:
            detail = str(exc)
        print(f"public Git identity validation failed: {detail}", file=sys.stderr)
        return 1

    print(
        f"Validated public Git identity for {commit_count} non-legacy commit(s) "
        f"and {tag_count} non-legacy annotated tag(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
