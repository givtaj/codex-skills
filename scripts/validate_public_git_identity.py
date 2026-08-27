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
OBJECT_ID_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "--no-replace-objects", *args],
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


def ref_object_records() -> list[tuple[str, str]]:
    """Return object IDs and types without using untrusted ref names as revisions."""

    records: list[tuple[str, str]] = []
    lines = git(
        "for-each-ref",
        "--format=%(objectname)%00%(objecttype)",
        "refs",
    ).splitlines()
    for line in lines:
        if not line:
            continue
        fields = line.split("\x00")
        if len(fields) != 2 or OBJECT_ID_RE.fullmatch(fields[0]) is None:
            raise ValueError("malformed Git ref object metadata")
        records.append((fields[0], fields[1]))
    return records


def peel_commit(object_id: str) -> str | None:
    result = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "rev-parse",
            "--verify",
            "--quiet",
            f"{object_id}^{{commit}}",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    if OBJECT_ID_RE.fullmatch(commit) is None:
        raise ValueError("malformed peeled commit object ID")
    return commit


def default_commit_revisions() -> list[str]:
    """Return commit roots visible through every local ref and the checkout."""

    revisions: set[str] = set()
    for object_id, _object_type in ref_object_records():
        commit = peel_commit(object_id)
        if commit is not None:
            revisions.add(commit)

    # A pull_request checkout can leave its synthetic merge commit detached and
    # therefore absent from every ref namespace. Include it for the safe default;
    # callers can select the contribution itself with --commit-range.
    head = subprocess.run(
        [
            "git",
            "--no-replace-objects",
            "rev-parse",
            "--verify",
            "--quiet",
            "HEAD^{commit}",
        ],
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
            raise ValueError("invalid commit revision argument")
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


def parse_tag_object(object_id: str) -> tuple[str, str, str | None]:
    raw = git("cat-file", "tag", object_id)
    headers = raw.partition("\n\n")[0]
    target_id: str | None = None
    declared_type: str | None = None
    tagger_email: str | None = None
    for line in headers.splitlines():
        if line.startswith("object "):
            target_id = line.removeprefix("object ")
        elif line.startswith("type "):
            declared_type = line.removeprefix("type ")
        elif line.startswith("tagger "):
            match = re.search(r"<([^<>]+)>\s+\d+\s+[+-]\d{4}$", line)
            if match is not None:
                tagger_email = match.group(1)
    if (
        target_id is None
        or OBJECT_ID_RE.fullmatch(target_id) is None
        or declared_type is None
    ):
        raise ValueError(f"annotated tag object {object_id[:12]} is malformed")
    actual_type = git("cat-file", "-t", target_id)
    if actual_type != declared_type:
        raise ValueError(f"annotated tag object {object_id[:12]} has a target type mismatch")
    return target_id, actual_type, tagger_email


def validate_annotated_tags() -> int:
    tag_count = 0
    pending = [object_id for object_id, object_type in ref_object_records() if object_type == "tag"]
    visited: set[str] = set()
    while pending:
        object_id = pending.pop()
        if object_id in visited:
            continue
        visited.add(object_id)
        target_id, target_type, tagger_email = parse_tag_object(object_id)
        if target_type == "tag":
            pending.append(target_id)
        if object_id not in LEGACY_TAG_OBJECT_EXEMPTIONS:
            if tagger_email is None:
                raise ValueError(
                    f"annotated tag object {object_id[:12]} is missing a tagger email"
                )
            require_noreply(
                f"annotated tag object {object_id[:12]} tagger",
                tagger_email,
            )
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
            "When omitted, all locally available refs and HEAD are validated. "
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
        detail = (
            "Git inspection command failed"
            if isinstance(exc, subprocess.CalledProcessError)
            else str(exc)
        )
        print(f"public Git identity validation failed: {detail}", file=sys.stderr)
        return 1

    print(
        f"Validated public Git identity for {commit_count} non-legacy commit(s) "
        f"and {tag_count} non-legacy annotated tag(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
