#!/usr/bin/env python3
"""Require explicit naming and durability evidence for pull requests that change skills."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


SHA_RE = re.compile(r"^[0-9a-f]{40,64}$")
SKILL_CONTRIBUTION_PATH_RE = re.compile(
    r"(?:^|/)SKILL\.md$|(?:^|/)skills/[^/]+(?:/|$)"
)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
WORD_RE = re.compile(r"[^\W_]+(?:['’\N{HYPHEN}-][^\W_]+)*", re.UNICODE)
REVIEW_BLOCKS = {
    "global-name": "global-name rationale",
    "six-month": "six-month durability rationale",
}
ATTESTATIONS = {
    "global-name": "global-name attestation",
    "six-month": "six-month durability attestation",
}
MINIMUM_RATIONALE_CHARACTERS = 40
MINIMUM_RATIONALE_WORDS = 8
MINIMUM_UNIQUE_RATIONALE_WORDS = 5


class PullRequestContractError(Exception):
    pass


def changed_paths_require_skill_review(
    paths: list[str], skill_roots: set[str] | None = None
) -> bool:
    roots = skill_roots or set()
    return any(
        SKILL_CONTRIBUTION_PATH_RE.search(path) is not None
        or any(not root or path == root or path.startswith(f"{root}/") for root in roots)
        for path in paths
    )


def strip_fenced_code_blocks(text: str) -> str:
    """Remove Markdown fenced blocks so copied template examples cannot satisfy the gate."""

    kept_lines: list[str] = []
    fence_character = ""
    fence_length = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if fence_character:
            closing = stripped.rstrip()
            if (
                closing.startswith(fence_character * fence_length)
                and not closing.strip(fence_character).strip()
            ):
                fence_character = ""
                fence_length = 0
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_character = stripped[0]
            fence_length = len(stripped) - len(stripped.lstrip(fence_character))
            continue
        kept_lines.append(line)
    return "".join(kept_lines)


def normalize_rationale(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) not in {"Cf", "Cc", "Cs", "Co", "Cn"}
        or character in "\n\t"
    )
    return " ".join(normalized.split())


def rationale_is_substantive(text: str) -> bool:
    normalized = normalize_rationale(text)
    words = WORD_RE.findall(normalized)
    unique_words = {word.casefold() for word in words}
    return (
        len(normalized) >= MINIMUM_RATIONALE_CHARACTERS
        and len(words) >= MINIMUM_RATIONALE_WORDS
        and len(unique_words) >= MINIMUM_UNIQUE_RATIONALE_WORDS
    )


def extract_review_block(body: str, key: str) -> str:
    start = f"<!-- skill-contract:{key}:start -->"
    end = f"<!-- skill-contract:{key}:end -->"
    if body.count(start) != 1 or body.count(end) != 1:
        return ""
    start_index = body.find(start)
    end_index = body.find(end, start_index + len(start))
    if start_index < 0 or end_index < 0:
        return ""
    content = body[start_index + len(start) : end_index]
    return HTML_COMMENT_RE.sub("", content).strip()


def has_checked_attestation(body: str, key: str) -> bool:
    raw_marker = f"<!-- skill-contract:{key}-attested -->"
    if body.count(raw_marker) != 1:
        return False
    marker = re.escape(raw_marker)
    return re.search(rf"(?im)^\s*-\s*\[[xX]\]\s*{marker}", body) is not None


def validate_skill_review_body(body: str) -> None:
    body = strip_fenced_code_blocks(body)
    failures: list[str] = []
    for key, label in REVIEW_BLOCKS.items():
        rationale = extract_review_block(body, key)
        if not rationale_is_substantive(rationale):
            failures.append(f"missing or insufficient {label}")
    for key, label in ATTESTATIONS.items():
        if not has_checked_attestation(body, key):
            failures.append(f"unchecked {label}")
    if failures:
        raise PullRequestContractError(
            "skill contribution contract failed: " + "; ".join(failures)
        )


def changed_paths(base_sha: str, head_sha: str) -> list[str]:
    if SHA_RE.fullmatch(base_sha) is None or SHA_RE.fullmatch(head_sha) is None:
        raise PullRequestContractError("invalid contribution commit identity")
    result = subprocess.run(
        [
            "git",
            "diff",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            "--name-only",
            "-z",
            f"{base_sha}...{head_sha}",
            "--",
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise PullRequestContractError("unable to inspect contribution paths")
    try:
        return [part.decode("utf-8", errors="strict") for part in result.stdout.split(b"\0") if part]
    except UnicodeDecodeError as exc:
        raise PullRequestContractError("contribution contains a non-UTF-8 path") from exc


def skill_roots(commit_sha: str) -> set[str]:
    """Find every directory containing SKILL.md without checking out contribution data."""

    if SHA_RE.fullmatch(commit_sha) is None:
        raise PullRequestContractError("invalid contribution commit identity")
    result = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", commit_sha, "--"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise PullRequestContractError("unable to inspect contribution tree")
    roots: set[str] = set()
    try:
        paths = [
            part.decode("utf-8", errors="strict")
            for part in result.stdout.split(b"\0")
            if part
        ]
    except UnicodeDecodeError as exc:
        raise PullRequestContractError("contribution contains a non-UTF-8 path") from exc
    for path in paths:
        if path == "SKILL.md":
            roots.add("")
        elif path.endswith("/SKILL.md"):
            roots.add(path[: -len("/SKILL.md")])
    return roots


def load_pull_request_body(event_path: Path) -> str:
    try:
        payload = json.loads(event_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PullRequestContractError("unable to read pull-request event") from exc
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, dict) and "body" in payload:
        pull_request = payload
    if not isinstance(pull_request, dict):
        raise PullRequestContractError("input does not contain a pull request")
    body = pull_request.get("body")
    return body if isinstance(body, str) else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", type=Path, required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        paths = changed_paths(args.base, args.head)
        roots = skill_roots(args.base) | skill_roots(args.head)
        if not changed_paths_require_skill_review(paths, roots):
            print("No skill contribution; semantic contract review is not required.")
            return 0
        validate_skill_review_body(load_pull_request_body(args.event))
    except PullRequestContractError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Validated global-name and six-month durability contribution evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
