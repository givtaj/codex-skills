#!/usr/bin/env python3
"""Validate or finalize a sanitized Central Projects Tracking snapshot."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import os
import re
import stat
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from collect_portfolio_facts import (
    EVIDENCE_ID_RE,
    PROJECT_ID_RE,
    compute_source_digest,
    validate_projects_root,
    within,
)


SCHEMA_VERSION = 2
MAX_SNAPSHOT_BYTES = 512 * 1024
MAX_SANITIZED_STRING_CHARS = 4096
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://", re.IGNORECASE)
FILE_URI_RE = re.compile(
    r"(?i)\bfile:(?://)?(?:/|[A-Za-z]:[\\/])[^\s]*"
)
GIT_OBJECT_RE = re.compile(r"\b[a-f0-9]{40,64}\b", re.IGNORECASE)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9._~-])(?:~[/\\][^\s]*|/(?:[^/\s]+(?:/[^/\s]*)*)?|[A-Za-z]:[\\/][^\s]+)"
)
HTML_RE = re.compile(r"<[^>]+>")
MARKDOWN_RE = re.compile(
    r"(?m)(?:^#{1,6}\s|^>\s|^(?:[-*+]|\d+\.)\s|`{1,3}|\*\*|__|!\[|\[[^\]\r\n]+\]\([^)]+\))"
)
HOSTNAME_RE = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}(?::\d{1,5})?(?:/[^\s]*)?"
)
HOST_PORT_RE = re.compile(
    r"(?i)\b(?=[a-z0-9-]*[a-z])[a-z0-9-]{1,63}:\d{2,5}\b"
)
UNC_PATH_RE = re.compile(r"(?:\\\\|//)[A-Za-z0-9._-]+[\\/][^\s]+")
ENV_ASSIGNMENT_RE = re.compile(
    r"(?i)(?:^|\s)(?:export\s+)?[A-Z_][A-Z0-9_]{1,}\s*=\s*[^\s]+"
)
FILENAME_RE = re.compile(
    r"(?i)\b[A-Za-z0-9][A-Za-z0-9_-]{0,100}\.(?:bak|csv|db|diff|env|go|java|js|json|jsonl|key|log|md|ndjson|patch|pem|php|py|rb|rs|sh|sqlite|toml|trace|ts|tsv|txt|yaml|yml)\b"
)
RAW_ARTIFACT_RE = re.compile(
    r"(?im)(?:^diff --git\s|^@@\s|^---\s+\S|^\+\+\+\s+\S|\brefs/(?:heads|remotes)/|\bcommit\s+[a-f0-9]{7,}\b)"
)
IPV6_CANDIDATE_RE = re.compile(r"(?<![A-Za-z0-9])\[?[0-9A-Fa-f:]{2,}\]?(?![A-Za-z0-9])")
SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bdop_v1_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bnpm_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bpypi-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\b(?:sk|rk)_live_[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\bAuthorization\s*:\s*(?:Basic|Bearer)\s+\S+"),
    re.compile(r"\bssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/=]{40,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)

FACT_ROOT_KEYS = {
    "schemaVersion",
    "collectorVersion",
    "generatedAt",
    "collectionStatus",
    "sourceDigest",
    "projects",
    "skipped",
}
FACT_PROJECT_KEYS = {"id", "collectionStatus", "repository", "evidence", "issues"}
REPOSITORY_KEYS = {
    "state",
    "branch",
    "branchRedacted",
    "hasUpstream",
    "ahead",
    "behind",
    "changeCount",
    "modifiedCount",
    "deletedCount",
    "untrackedCount",
    "conflictedCount",
    "stagedCount",
    "unstagedCount",
    "lastCommit",
    "outgoing",
    "commitSuggestionKinds",
}
COMMIT_KEYS = {"at", "subject"}
OUTGOING_KEYS = {"status", "count", "truncated", "commits"}
EVIDENCE_KEYS = {"id", "required", "status", "sha256", "bytes"}
SKIPPED_KEYS = {
    "hiddenEntryCount",
    "symlinkEntryCount",
    "unsafeNameEntryCount",
    "nonRepositoryEntryCount",
    "unmatchedProjectEntryCount",
}
SNAPSHOT_ROOT_KEYS = {
    "schemaVersion",
    "generatedAt",
    "sourceDigest",
    "contentDigest",
    "scopeLabel",
    "coverage",
    "brief",
    "projects",
    "activity",
}
COVERAGE_KEYS = {
    "currentProjectCount",
    "completeProjectCount",
    "partialProjectCount",
    "missingProjectCount",
}
BRIEF_KEYS = {
    "focusProjectIds",
    "readyProjectIds",
    "decisions",
    "evidenceGaps",
}
SNAPSHOT_PROJECT_KEYS = {
    "id",
    "name",
    "present",
    "stage",
    "health",
    "tone",
    "attention",
    "summary",
    "risk",
    "next",
    "stack",
    "evidence",
    "observedAt",
    "repository",
    "lastActivity",
}
LAST_ACTIVITY_KEYS = {"on", "kind"}
ACTIVITY_KEYS = {"id", "on", "type", "projectId", "note"}
REPOSITORY_STATES = {"clean", "dirty", "unborn", "unavailable"}
OUTGOING_STATES = {"known", "no-upstream", "unborn", "unavailable"}
SUGGESTION_KINDS = (
    "resolve-conflicts",
    "review-initial-commit",
    "commit-staged",
    "stage-tracked",
    "review-untracked",
)
STAGES = {"Unknown", "Idea", "Foundation", "Build", "Integration", "Live"}
TONES = {"danger", "warn", "good", "info", "neutral"}
ACTIVITY_KINDS = {"commit", "evidence", "build", "study", "none"}
ACTIVITY_TYPES = {"COMMIT", "EVIDENCE", "BUILD", "STUDY"}
ACTIVITY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,160}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,159}$")
EVIDENCE_STATES = {"present", "missing", "rejected"}


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def require(self, condition: bool, code: str) -> None:
        if not condition:
            self.errors.append(code)


def exact_keys(v: Validator, value: dict[str, Any], expected: set[str], code: str) -> None:
    v.require(set(value) == expected, code)


def parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def valid_text(value: Any, minimum: int, maximum: int) -> bool:
    return (
        isinstance(value, str)
        and minimum <= len(value) <= maximum
        and value.strip() == value
    )


def valid_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 100000


def walk_strings(value: Any, location: str = "root") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((location, value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk_strings(item, f"{location}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            found.extend(walk_strings(item, f"{location}.{key}"))
    return found


def contains_ipv6(value: str) -> bool:
    for match in IPV6_CANDIDATE_RE.finditer(value):
        candidate = match.group(0).strip("[]")
        if ":" not in candidate:
            continue
        try:
            if ipaddress.ip_address(candidate).version == 6:
                return True
        except ValueError:
            continue
    return False


def append_sanitization_errors(v: Validator, value: Any, root: str) -> None:
    for location, text in walk_strings(value, root):
        if len(text) > MAX_SANITIZED_STRING_CHARS:
            v.errors.append(location + ":unsafe-string")
            continue
        if any(ord(char) < 32 or ord(char) == 127 for char in text):
            v.errors.append(location + ":control")
        is_digest = location.endswith(".sourceDigest") or location.endswith(
            ".contentDigest"
        )
        is_structured_time = (
            location.endswith(".generatedAt")
            or location.endswith(".observedAt")
            or location.endswith(".at")
            or location.endswith(".on")
        )
        is_structured_id = (
            location.endswith(".id")
            or location.endswith(".projectId")
            or ".focusProjectIds[" in location
            or ".readyProjectIds[" in location
        )
        if (
            not is_structured_time
            and (
            ("@" in text and EMAIL_RE.search(text))
            or URL_RE.search(text)
            or FILE_URI_RE.search(text)
            or (not is_digest and GIT_OBJECT_RE.search(text))
            or IPV4_RE.search(text)
            or contains_ipv6(text)
            or ABSOLUTE_PATH_RE.search(text)
            or UNC_PATH_RE.search(text)
            or (not is_structured_id and HOSTNAME_RE.search(text))
            or (
                not is_structured_id
                and ":" in text
                and HOST_PORT_RE.search(text)
            )
            or HTML_RE.search(text)
            or MARKDOWN_RE.search(text)
            or ENV_ASSIGNMENT_RE.search(text)
            or (not is_structured_id and FILENAME_RE.search(text))
            or RAW_ARTIFACT_RE.search(text)
            or any(pattern.search(text) for pattern in SECRET_PATTERNS)
            )
        ):
            v.errors.append(location + ":unsafe-string")


def validate_commit(
    v: Validator,
    value: Any,
    prefix: str,
    generated: datetime | None,
) -> dict[str, Any] | None:
    v.require(isinstance(value, dict), prefix + ":object")
    if not isinstance(value, dict):
        return None
    exact_keys(v, value, COMMIT_KEYS, prefix + ":keys")
    observed = parse_timestamp(value.get("at"))
    v.require(observed is not None, prefix + ":at")
    if observed and generated:
        v.require(observed <= generated, prefix + ":future")
    subject = value.get("subject")
    v.require(
        subject is None or valid_text(subject, 1, 180),
        prefix + ":subject",
    )
    return value


def expected_suggestions(state: Any, counts: dict[str, int]) -> list[str]:
    if state == "unavailable" or counts["changeCount"] == 0:
        return []
    if counts["conflictedCount"]:
        return ["resolve-conflicts"]
    if state == "unborn":
        return ["review-initial-commit"]
    result: list[str] = []
    if counts["stagedCount"]:
        result.append("commit-staged")
    if counts["unstagedCount"]:
        result.append("stage-tracked")
    if counts["untrackedCount"]:
        result.append("review-untracked")
    return result


def validate_repository(
    v: Validator,
    value: Any,
    prefix: str,
    generated: datetime | None = None,
) -> dict[str, Any] | None:
    v.require(isinstance(value, dict), prefix + ":object")
    if not isinstance(value, dict):
        return None
    exact_keys(v, value, REPOSITORY_KEYS, prefix + ":keys")
    state = value.get("state")
    v.require(state in REPOSITORY_STATES, prefix + ":state")
    branch = value.get("branch")
    v.require(
        branch is None
        or (
            isinstance(branch, str)
            and bool(BRANCH_RE.fullmatch(branch))
            and ".." not in branch
        ),
        prefix + ":branch",
    )
    branch_redacted = value.get("branchRedacted")
    v.require(isinstance(branch_redacted, bool), prefix + ":branch-redacted")
    if branch is not None:
        v.require(branch_redacted is False, prefix + ":branch-consistency")
    v.require(isinstance(value.get("hasUpstream"), bool), prefix + ":upstream")
    counts: dict[str, int] = {}
    count_fields = {
        "ahead",
        "behind",
        "changeCount",
        "modifiedCount",
        "deletedCount",
        "untrackedCount",
        "conflictedCount",
        "stagedCount",
        "unstagedCount",
    }
    for field in count_fields:
        item = value.get(field)
        v.require(valid_count(item), prefix + ":" + field)
        counts[field] = item if valid_count(item) else 0
    v.require(
        counts["modifiedCount"]
        + counts["deletedCount"]
        + counts["untrackedCount"]
        + counts["conflictedCount"]
        == counts["changeCount"],
        prefix + ":partition",
    )
    tracked = counts["modifiedCount"] + counts["deletedCount"]
    v.require(counts["stagedCount"] <= tracked, prefix + ":staged")
    v.require(counts["unstagedCount"] <= tracked, prefix + ":unstaged")
    if state in {"clean", "unavailable"}:
        v.require(counts["changeCount"] == 0, prefix + ":zero-worktree")
    if state == "dirty":
        v.require(counts["changeCount"] > 0, prefix + ":dirty-worktree")
    if state in {"unborn", "unavailable"}:
        v.require(value.get("hasUpstream") is False, prefix + ":no-upstream")
    if value.get("hasUpstream") is False:
        v.require(
            counts["ahead"] == 0 and counts["behind"] == 0,
            prefix + ":no-divergence",
        )
    if state == "unavailable":
        v.require(
            branch is None and branch_redacted is False,
            prefix + ":unavailable-branch",
        )

    commit = value.get("lastCommit")
    if state in {"unborn", "unavailable"}:
        v.require(commit is None, prefix + ":last-commit-empty")
    else:
        validate_commit(v, commit, prefix + ":last-commit", generated)

    outgoing = value.get("outgoing")
    v.require(isinstance(outgoing, dict), prefix + ":outgoing")
    if isinstance(outgoing, dict):
        exact_keys(v, outgoing, OUTGOING_KEYS, prefix + ":outgoing-keys")
        outgoing_status = outgoing.get("status")
        v.require(
            outgoing_status in OUTGOING_STATES,
            prefix + ":outgoing-status",
        )
        count = outgoing.get("count")
        truncated = outgoing.get("truncated")
        commits = outgoing.get("commits")
        v.require(isinstance(truncated, bool), prefix + ":outgoing-truncated")
        v.require(
            isinstance(commits, list) and len(commits) <= 8,
            prefix + ":outgoing-commits",
        )
        if isinstance(commits, list):
            for index, outgoing_commit in enumerate(commits):
                validate_commit(
                    v,
                    outgoing_commit,
                    f"{prefix}:outgoing-commit:{index}",
                    generated,
                )
            commit_times = [
                item.get("at")
                for item in commits
                if isinstance(item, dict) and isinstance(item.get("at"), str)
            ]
            v.require(
                commit_times == sorted(commit_times, reverse=True),
                prefix + ":outgoing-newest-first",
            )
        if value.get("hasUpstream") is True:
            v.require(
                outgoing_status == "known",
                prefix + ":outgoing-known-required",
            )
        if outgoing_status == "known":
            v.require(
                value.get("hasUpstream") is True,
                prefix + ":known-upstream",
            )
            v.require(valid_count(count), prefix + ":outgoing-count")
            if valid_count(count) and isinstance(commits, list):
                v.require(count == counts["ahead"], prefix + ":outgoing-ahead")
                v.require(
                    len(commits) == min(count, 8),
                    prefix + ":outgoing-commit-count",
                )
                v.require(
                    truncated is (count > 8),
                    prefix + ":outgoing-truncation",
                )
        else:
            v.require(count is None, prefix + ":outgoing-count-empty")
            v.require(truncated is False, prefix + ":outgoing-not-truncated")
            v.require(commits == [], prefix + ":outgoing-commits-empty")
            if state == "unborn":
                v.require(
                    outgoing_status == "unborn",
                    prefix + ":outgoing-unborn",
                )
            elif state == "unavailable":
                v.require(
                    outgoing_status == "unavailable",
                    prefix + ":outgoing-unavailable",
                )
            elif value.get("hasUpstream") is False:
                v.require(
                    outgoing_status == "no-upstream",
                    prefix + ":outgoing-no-upstream",
                )

    suggestions = value.get("commitSuggestionKinds")
    v.require(
        isinstance(suggestions, list)
        and len(suggestions) == len(set(suggestions))
        and all(item in SUGGESTION_KINDS for item in suggestions),
        prefix + ":suggestions",
    )
    if isinstance(suggestions, list):
        v.require(
            suggestions == expected_suggestions(state, counts),
            prefix + ":suggestions-derived",
        )
    append_sanitization_errors(v, value, prefix)
    return value


def validate_facts(facts: Any) -> list[str]:
    v = Validator()
    v.require(isinstance(facts, dict), "facts:object")
    if not isinstance(facts, dict):
        return v.errors
    exact_keys(v, facts, FACT_ROOT_KEYS, "facts:keys")
    v.require(facts.get("schemaVersion") == SCHEMA_VERSION, "facts:schema-version")
    v.require(facts.get("collectorVersion") == "0.1.0", "facts:collector-version")
    generated = parse_timestamp(facts.get("generatedAt"))
    v.require(generated is not None, "facts:generated-at")
    if generated:
        v.require(generated <= datetime.now(timezone.utc).replace(microsecond=0), "facts:future")
    status = facts.get("collectionStatus")
    v.require(status in {"complete", "partial"}, "facts:collection-status")

    projects = facts.get("projects")
    v.require(isinstance(projects, list) and len(projects) <= 500, "facts:projects")
    project_ids: list[str] = []
    has_issues = False
    if isinstance(projects, list):
        for index, project in enumerate(projects):
            prefix = f"facts:project:{index}"
            v.require(isinstance(project, dict), prefix + ":object")
            if not isinstance(project, dict):
                continue
            exact_keys(v, project, FACT_PROJECT_KEYS, prefix + ":keys")
            project_id = project.get("id")
            valid_id = isinstance(project_id, str) and bool(PROJECT_ID_RE.fullmatch(project_id))
            v.require(valid_id, prefix + ":id")
            if valid_id:
                project_ids.append(project_id)
                prefix = "facts:project:" + project_id
            collection_status = project.get("collectionStatus")
            v.require(collection_status in {"ok", "partial"}, prefix + ":status")
            validate_repository(
                v,
                project.get("repository"),
                prefix + ":repository",
                generated,
            )
            issues = project.get("issues")
            valid_issues = (
                isinstance(issues, list)
                and len(issues) <= 32
                and all(valid_text(item, 1, 80) for item in issues)
                and len(issues) == len(set(issues))
                and issues == sorted(issues)
            )
            v.require(valid_issues, prefix + ":issues")
            if valid_issues:
                has_issues = has_issues or bool(issues)
                v.require((collection_status == "partial") == bool(issues), prefix + ":status-consistency")

            evidence = project.get("evidence")
            v.require(isinstance(evidence, list) and len(evidence) <= 64, prefix + ":evidence")
            evidence_ids: list[str] = []
            if isinstance(evidence, list):
                for evidence_index, item in enumerate(evidence):
                    evidence_prefix = f"{prefix}:evidence:{evidence_index}"
                    v.require(isinstance(item, dict), evidence_prefix + ":object")
                    if not isinstance(item, dict):
                        continue
                    exact_keys(v, item, EVIDENCE_KEYS, evidence_prefix + ":keys")
                    evidence_id = item.get("id")
                    valid_evidence_id = isinstance(evidence_id, str) and bool(
                        EVIDENCE_ID_RE.fullmatch(evidence_id)
                    )
                    v.require(valid_evidence_id, evidence_prefix + ":id")
                    if valid_evidence_id:
                        evidence_ids.append(evidence_id)
                    v.require(isinstance(item.get("required"), bool), evidence_prefix + ":required")
                    evidence_status = item.get("status")
                    v.require(evidence_status in EVIDENCE_STATES, evidence_prefix + ":status")
                    digest = item.get("sha256")
                    size = item.get("bytes")
                    if evidence_status == "present":
                        v.require(isinstance(digest, str) and bool(DIGEST_RE.fullmatch(digest)), evidence_prefix + ":digest")
                        v.require(valid_count(size), evidence_prefix + ":bytes")
                    else:
                        v.require(digest is None and size is None, evidence_prefix + ":withheld")
                v.require(len(evidence_ids) == len(set(evidence_ids)), prefix + ":evidence-ids")
    v.require(len(project_ids) == len(set(project_ids)), "facts:project-ids")

    skipped = facts.get("skipped")
    v.require(isinstance(skipped, dict), "facts:skipped")
    skipped_partial = False
    if isinstance(skipped, dict):
        exact_keys(v, skipped, SKIPPED_KEYS, "facts:skipped-keys")
        for key in SKIPPED_KEYS:
            v.require(valid_count(skipped.get(key)), "facts:skipped:" + key)
        skipped_partial = bool(
            skipped.get("symlinkEntryCount", 0)
            or skipped.get("unsafeNameEntryCount", 0)
            or skipped.get("unmatchedProjectEntryCount", 0)
        )
    v.require((status == "partial") == (has_issues or skipped_partial), "facts:partial-consistency")

    digest = facts.get("sourceDigest")
    v.require(isinstance(digest, str) and bool(DIGEST_RE.fullmatch(digest)), "facts:source-digest")
    if isinstance(digest, str) and DIGEST_RE.fullmatch(digest):
        try:
            v.require(digest == compute_source_digest(facts), "facts:source-digest-mismatch")
        except (KeyError, TypeError, ValueError):
            v.errors.append("facts:source-digest-uncomputable")
    return sorted(set(v.errors))


def unavailable_repository() -> dict[str, Any]:
    return {
        "state": "unavailable",
        "branch": None,
        "branchRedacted": False,
        "hasUpstream": False,
        "ahead": 0,
        "behind": 0,
        "changeCount": 0,
        "modifiedCount": 0,
        "deletedCount": 0,
        "untrackedCount": 0,
        "conflictedCount": 0,
        "stagedCount": 0,
        "unstagedCount": 0,
        "lastCommit": None,
        "outgoing": {
            "status": "unavailable",
            "count": None,
            "truncated": False,
            "commits": [],
        },
        "commitSuggestionKinds": [],
    }


def content_digest(snapshot: dict[str, Any]) -> str:
    material = {
        key: value
        for key, value in snapshot.items()
        if key not in {"generatedAt", "contentDigest"}
    }
    payload = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def snapshot_json_bytes(snapshot: dict[str, Any]) -> bytes:
    return (json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def prospective_final_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    prospective = dict(snapshot)
    prospective["contentDigest"] = content_digest(prospective)
    return prospective


def atomic_snapshot_write(
    path: Path,
    snapshot: dict[str, Any],
    mode: int = 0o600,
) -> None:
    payload = snapshot_json_bytes(snapshot)
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError("snapshot_output_too_large")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix="." + path.name + ".",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def validate_last_activity(
    v: Validator,
    value: Any,
    prefix: str,
    generated: datetime | None,
) -> None:
    v.require(isinstance(value, dict), prefix + ":object")
    if not isinstance(value, dict):
        return
    exact_keys(v, value, LAST_ACTIVITY_KEYS, prefix + ":keys")
    kind = value.get("kind")
    v.require(kind in ACTIVITY_KINDS, prefix + ":kind")
    observed_value = value.get("on")
    observed = parse_date(observed_value) if observed_value is not None else None
    v.require(
        observed_value is None or observed is not None,
        prefix + ":on",
    )
    if kind == "none":
        v.require(observed_value is None, prefix + ":none-date")
    else:
        v.require(observed is not None, prefix + ":required-date")
    if observed and generated:
        v.require(observed <= generated.date(), prefix + ":future")


def validate_activity_records(
    v: Validator,
    value: Any,
    present_ids: set[str],
    generated: datetime | None,
    prefix: str,
) -> None:
    v.require(isinstance(value, list) and len(value) <= 8, prefix + ":list")
    if not isinstance(value, list):
        return
    identifiers: list[str] = []
    ordering: list[tuple[str, str]] = []
    for index, item in enumerate(value):
        item_prefix = f"{prefix}:{index}"
        v.require(isinstance(item, dict), item_prefix + ":object")
        if not isinstance(item, dict):
            continue
        exact_keys(v, item, ACTIVITY_KEYS, item_prefix + ":keys")
        identifier = item.get("id")
        valid_identifier = (
            isinstance(identifier, str)
            and bool(ACTIVITY_ID_RE.fullmatch(identifier))
        )
        v.require(valid_identifier, item_prefix + ":id")
        if valid_identifier:
            identifiers.append(identifier)
        observed = parse_date(item.get("on"))
        v.require(observed is not None, item_prefix + ":on")
        if observed and generated:
            v.require(observed <= generated.date(), item_prefix + ":future")
        activity_type = item.get("type")
        v.require(activity_type in ACTIVITY_TYPES, item_prefix + ":type")
        project_id = item.get("projectId")
        v.require(
            isinstance(project_id, str) and project_id in present_ids,
            item_prefix + ":project",
        )
        v.require(valid_text(item.get("note"), 8, 320), item_prefix + ":note")
        if isinstance(item.get("on"), str) and isinstance(identifier, str):
            ordering.append((item["on"], identifier))
    v.require(
        len(identifiers) == len(set(identifiers)),
        prefix + ":ids-unique",
    )
    v.require(
        ordering == sorted(ordering, reverse=True),
        prefix + ":newest-first",
    )


def validate_previous_snapshot(previous: Any) -> list[str]:
    """Validate a retained snapshot without relying on its unavailable old facts."""
    v = Validator()
    v.require(isinstance(previous, dict), "previous:object")
    if not isinstance(previous, dict):
        return v.errors
    try:
        v.require(
            len(snapshot_json_bytes(previous)) <= MAX_SNAPSHOT_BYTES,
            "previous:serialized-size",
        )
    except (TypeError, ValueError):
        v.errors.append("previous:serialized-size")
    exact_keys(v, previous, SNAPSHOT_ROOT_KEYS, "previous:keys")
    v.require(previous.get("schemaVersion") == SCHEMA_VERSION, "previous:schema-version")
    generated = parse_timestamp(previous.get("generatedAt"))
    v.require(generated is not None, "previous:generated-at")
    if generated:
        v.require(
            generated <= datetime.now(timezone.utc).replace(microsecond=0),
            "previous:future",
        )
    source_digest = previous.get("sourceDigest")
    v.require(
        isinstance(source_digest, str) and bool(DIGEST_RE.fullmatch(source_digest)),
        "previous:source-digest",
    )
    digest = previous.get("contentDigest")
    v.require(
        isinstance(digest, str) and bool(DIGEST_RE.fullmatch(digest)),
        "previous:content-digest",
    )
    if isinstance(digest, str) and DIGEST_RE.fullmatch(digest):
        v.require(
            digest == content_digest(previous),
            "previous:content-digest-mismatch",
        )
    v.require(valid_text(previous.get("scopeLabel"), 1, 100), "previous:scope-label")

    coverage = previous.get("coverage")
    v.require(isinstance(coverage, dict), "previous:coverage")
    if isinstance(coverage, dict):
        exact_keys(v, coverage, COVERAGE_KEYS, "previous:coverage-keys")
        for key in COVERAGE_KEYS:
            v.require(valid_count(coverage.get(key)), "previous:coverage:" + key)

    projects = previous.get("projects")
    v.require(
        isinstance(projects, list) and 1 <= len(projects) <= 500,
        "previous:projects",
    )
    project_ids: list[str] = []
    present_ids: set[str] = set()
    missing_ids: set[str] = set()
    if isinstance(projects, list):
        for index, project in enumerate(projects):
            prefix = f"previous:project:{index}"
            v.require(isinstance(project, dict), prefix + ":object")
            if not isinstance(project, dict):
                continue
            exact_keys(v, project, SNAPSHOT_PROJECT_KEYS, prefix + ":keys")
            project_id = project.get("id")
            if isinstance(project_id, str) and PROJECT_ID_RE.fullmatch(project_id):
                project_ids.append(project_id)
                prefix = "previous:project:" + project_id
            else:
                v.errors.append(prefix + ":id")
            v.require(valid_text(project.get("name"), 1, 100), prefix + ":name")
            present = project.get("present")
            v.require(isinstance(present, bool), prefix + ":present")
            if isinstance(project_id, str) and PROJECT_ID_RE.fullmatch(project_id):
                if present is True:
                    present_ids.add(project_id)
                elif present is False:
                    missing_ids.add(project_id)
            v.require(project.get("stage") in STAGES, prefix + ":stage")
            v.require(valid_text(project.get("health"), 1, 80), prefix + ":health")
            v.require(project.get("tone") in TONES, prefix + ":tone")
            v.require(isinstance(project.get("attention"), bool), prefix + ":attention")
            v.require(valid_text(project.get("summary"), 8, 500), prefix + ":summary")
            v.require(valid_text(project.get("risk"), 8, 800), prefix + ":risk")
            v.require(valid_text(project.get("next"), 8, 800), prefix + ":next")
            v.require(valid_text(project.get("stack"), 1, 160), prefix + ":stack")
            v.require(valid_text(project.get("evidence"), 1, 220), prefix + ":evidence")
            observed = project.get("observedAt")
            observed_date = parse_date(observed) if observed is not None else None
            v.require(observed is None or observed_date is not None, prefix + ":observed-at")
            if observed_date and generated:
                v.require(observed_date <= generated.date(), prefix + ":observed-future")
            repository = validate_repository(
                v,
                project.get("repository"),
                prefix + ":repository",
                generated,
            )
            validate_last_activity(
                v,
                project.get("lastActivity"),
                prefix + ":last-activity",
                generated,
            )
            if present is False and repository is not None:
                v.require(
                    repository == unavailable_repository(),
                    prefix + ":missing-repository",
                )
                v.require(project.get("stage") == "Unknown", prefix + ":missing-stage")
                v.require(project.get("health") == "Unknown", prefix + ":missing-health")
                v.require(project.get("tone") == "neutral", prefix + ":missing-tone")
    v.require(len(project_ids) == len(set(project_ids)), "previous:project-ids-unique")

    if isinstance(coverage, dict) and all(
        valid_count(coverage.get(key)) for key in COVERAGE_KEYS
    ):
        v.require(
            coverage["currentProjectCount"] == len(present_ids),
            "previous:coverage:current",
        )
        v.require(
            coverage["missingProjectCount"] == len(missing_ids),
            "previous:coverage:missing",
        )
        v.require(
            coverage["completeProjectCount"] + coverage["partialProjectCount"]
            == coverage["currentProjectCount"],
            "previous:coverage:partition",
        )

    brief = previous.get("brief")
    v.require(isinstance(brief, dict), "previous:brief")
    if isinstance(brief, dict):
        exact_keys(v, brief, BRIEF_KEYS, "previous:brief-keys")
        focus = brief.get("focusProjectIds")
        valid_focus = (
            isinstance(focus, list)
            and 1 <= len(focus) <= 5
            and all(isinstance(item, str) for item in focus)
            and len(focus) == len(set(focus))
        )
        v.require(valid_focus, "previous:brief-focus")
        if valid_focus:
            v.require(
                all(item in present_ids for item in focus),
                "previous:brief-focus-references",
            )
        ready = brief.get("readyProjectIds")
        valid_ready = (
            isinstance(ready, list)
            and len(ready) <= 3
            and all(isinstance(item, str) for item in ready)
            and len(ready) == len(set(ready))
        )
        v.require(valid_ready, "previous:brief-ready")
        if valid_ready:
            v.require(
                all(item in present_ids for item in ready),
                "previous:brief-ready-references",
            )
        for key, limit in (("decisions", 5), ("evidenceGaps", 8)):
            values = brief.get(key)
            valid_values = (
                isinstance(values, list)
                and len(values) <= limit
                and all(valid_text(item, 8, 320) for item in values)
                and len(values) == len(set(values))
            )
            v.require(valid_values, "previous:brief-" + key)

    validate_activity_records(
        v,
        previous.get("activity"),
        present_ids,
        generated,
        "previous:activity",
    )
    append_sanitization_errors(v, previous, "previous")
    return sorted(set(v.errors))


def validate_snapshot_document(snapshot: Any) -> list[str]:
    """Validate a finalized standalone snapshot before local-site creation."""
    return validate_previous_snapshot(snapshot)


def validate_snapshot(
    snapshot: Any,
    facts: dict[str, Any],
    previous: dict[str, Any] | None = None,
    allow_unfinalized: bool = False,
) -> list[str]:
    v = Validator()
    if previous is not None:
        v.errors.extend(validate_previous_snapshot(previous))
    v.require(isinstance(snapshot, dict), "snapshot:object")
    if not isinstance(snapshot, dict):
        return v.errors
    try:
        prospective = (
            prospective_final_snapshot(snapshot)
            if allow_unfinalized or snapshot.get("contentDigest") is None
            else snapshot
        )
        v.require(
            len(snapshot_json_bytes(prospective)) <= MAX_SNAPSHOT_BYTES,
            "snapshot:serialized-size",
        )
    except (TypeError, ValueError):
        v.errors.append("snapshot:serialized-size")
    exact_keys(v, snapshot, SNAPSHOT_ROOT_KEYS, "snapshot:keys")
    v.require(snapshot.get("schemaVersion") == SCHEMA_VERSION, "snapshot:schema-version")
    generated = parse_timestamp(snapshot.get("generatedAt"))
    v.require(generated is not None, "snapshot:generated-at")
    facts_generated = parse_timestamp(facts.get("generatedAt"))
    no_change_use = (
        previous is not None
        and snapshot == previous
        and snapshot.get("sourceDigest") == facts.get("sourceDigest")
        and not allow_unfinalized
    )
    if no_change_use:
        v.require(
            generated is not None
            and facts_generated is not None
            and generated <= facts_generated,
            "snapshot:no-change-time",
        )
    else:
        v.require(snapshot.get("generatedAt") == facts.get("generatedAt"), "snapshot:facts-time")
    if generated:
        v.require(
            generated <= datetime.now(timezone.utc).replace(microsecond=0),
            "snapshot:future",
        )
    v.require(snapshot.get("sourceDigest") == facts.get("sourceDigest"), "snapshot:source-digest")
    digest = snapshot.get("contentDigest")
    if allow_unfinalized:
        v.require(digest is None, "snapshot:content-digest-unfinalized")
    else:
        v.require(isinstance(digest, str) and bool(DIGEST_RE.fullmatch(digest)), "snapshot:content-digest")
        if isinstance(digest, str) and DIGEST_RE.fullmatch(digest):
            v.require(digest == content_digest(snapshot), "snapshot:content-digest-mismatch")

    fact_projects = {project["id"]: project for project in facts.get("projects", []) if isinstance(project, dict) and isinstance(project.get("id"), str)}
    previous_projects = {
        project.get("id"): project
        for project in (previous.get("projects", []) if isinstance(previous, dict) else [])
        if isinstance(project, dict) and isinstance(project.get("id"), str)
    }
    expected_ids = set(fact_projects) | set(previous_projects)
    v.require(valid_text(snapshot.get("scopeLabel"), 1, 100), "snapshot:scope-label")

    coverage = snapshot.get("coverage")
    v.require(isinstance(coverage, dict), "snapshot:coverage")
    if isinstance(coverage, dict):
        exact_keys(v, coverage, COVERAGE_KEYS, "snapshot:coverage-keys")
        for key in COVERAGE_KEYS:
            v.require(valid_count(coverage.get(key)), "snapshot:coverage:" + key)
        if all(valid_count(coverage.get(key)) for key in COVERAGE_KEYS):
            v.require(
                coverage["currentProjectCount"] == len(fact_projects),
                "snapshot:coverage:current",
            )
            v.require(
                coverage["completeProjectCount"]
                == sum(
                    project.get("collectionStatus") == "ok"
                    for project in fact_projects.values()
                ),
                "snapshot:coverage:complete",
            )
            v.require(
                coverage["partialProjectCount"]
                == sum(
                    project.get("collectionStatus") == "partial"
                    for project in fact_projects.values()
                ),
                "snapshot:coverage:partial",
            )
            v.require(
                coverage["missingProjectCount"]
                == len(set(previous_projects) - set(fact_projects)),
                "snapshot:coverage:missing",
            )

    projects = snapshot.get("projects")
    v.require(isinstance(projects, list) and 1 <= len(projects) <= 500, "snapshot:projects")
    project_ids: list[str] = []
    if isinstance(projects, list):
        for project in projects:
            v.require(isinstance(project, dict), "snapshot:project:object")
            if not isinstance(project, dict):
                continue
            project_id = project.get("id")
            if not isinstance(project_id, str) or not PROJECT_ID_RE.fullmatch(project_id):
                v.errors.append("snapshot:project:id")
                continue
            project_ids.append(project_id)
            prefix = "snapshot:project:" + project_id
            exact_keys(v, project, SNAPSHOT_PROJECT_KEYS, prefix + ":keys")
            v.require(valid_text(project.get("name"), 1, 100), prefix + ":name")
            present = project.get("present")
            v.require(isinstance(present, bool), prefix + ":present")
            v.require(project.get("stage") in STAGES, prefix + ":stage")
            v.require(valid_text(project.get("health"), 1, 80), prefix + ":health")
            v.require(project.get("tone") in TONES, prefix + ":tone")
            v.require(isinstance(project.get("attention"), bool), prefix + ":attention")
            v.require(valid_text(project.get("summary"), 8, 500), prefix + ":summary")
            v.require(valid_text(project.get("risk"), 8, 800), prefix + ":risk")
            v.require(valid_text(project.get("next"), 8, 800), prefix + ":next")
            v.require(valid_text(project.get("stack"), 1, 160), prefix + ":stack")
            v.require(valid_text(project.get("evidence"), 1, 220), prefix + ":evidence")
            observed = project.get("observedAt")
            observed_date = parse_date(observed) if observed is not None else None
            v.require(observed is None or observed_date is not None, prefix + ":observed-at")
            if observed_date and generated:
                v.require(observed_date <= generated.date(), prefix + ":observed-future")
            repository = validate_repository(
                v,
                project.get("repository"),
                prefix + ":repository",
                generated,
            )
            validate_last_activity(
                v,
                project.get("lastActivity"),
                prefix + ":last-activity",
                generated,
            )

            fact_project = fact_projects.get(project_id)
            if fact_project:
                v.require(present is True, prefix + ":current-present")
                if repository is not None:
                    v.require(repository == fact_project.get("repository"), prefix + ":repository-facts")
            elif project_id in previous_projects:
                v.require(present is False, prefix + ":missing-present")
                if repository is not None:
                    v.require(repository == unavailable_repository(), prefix + ":missing-repository")
                v.require(project.get("stage") == "Unknown", prefix + ":missing-stage")
                v.require(project.get("health") == "Unknown", prefix + ":missing-health")
                v.require(project.get("tone") == "neutral", prefix + ":missing-tone")
            else:
                v.errors.append(prefix + ":unknown-project")
    v.require(len(project_ids) == len(set(project_ids)), "snapshot:project-ids-unique")
    v.require(set(project_ids) == expected_ids, "snapshot:project-set")

    brief = snapshot.get("brief")
    v.require(isinstance(brief, dict), "snapshot:brief")
    if isinstance(brief, dict):
        exact_keys(v, brief, BRIEF_KEYS, "snapshot:brief-keys")
        focus = brief.get("focusProjectIds")
        valid_focus = (
            isinstance(focus, list)
            and 1 <= len(focus) <= 5
            and all(isinstance(item, str) for item in focus)
            and len(focus) == len(set(focus))
        )
        v.require(valid_focus, "snapshot:brief-focus")
        if valid_focus:
            v.require(all(item in fact_projects for item in focus), "snapshot:brief-focus-references")
        ready = brief.get("readyProjectIds")
        valid_ready = (
            isinstance(ready, list)
            and len(ready) <= 3
            and all(isinstance(item, str) for item in ready)
            and len(ready) == len(set(ready))
        )
        v.require(valid_ready, "snapshot:brief-ready")
        if valid_ready:
            v.require(
                all(item in fact_projects for item in ready),
                "snapshot:brief-ready-references",
            )
        for key, limit in (("decisions", 5), ("evidenceGaps", 8)):
            values = brief.get(key)
            valid_values = (
                isinstance(values, list)
                and len(values) <= limit
                and all(valid_text(item, 8, 320) for item in values)
                and len(values) == len(set(values))
            )
            v.require(valid_values, "snapshot:brief-" + key)

    validate_activity_records(
        v,
        snapshot.get("activity"),
        set(fact_projects),
        generated,
        "snapshot:activity",
    )
    if previous:
        previous_generated = parse_timestamp(previous.get("generatedAt"))
        if previous_generated and generated:
            v.require(generated >= previous_generated, "snapshot:generated-monotonic")

    append_sanitization_errors(v, snapshot, "root")
    return sorted(set(v.errors))


def validate_input_path(
    path: Path,
    projects_root: Path,
    *,
    require_private_mode: bool = False,
) -> Path:
    if path.is_symlink():
        raise RuntimeError("symlink_input")
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise RuntimeError("unreadable") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise RuntimeError("nonregular_input")
    if within(resolved, projects_root):
        raise RuntimeError("input_inside_projects")
    if require_private_mode and stat.S_IMODE(metadata.st_mode) != 0o600:
        raise RuntimeError("snapshot_permissions")
    return resolved


def load_json(
    path: Path,
    maximum: int,
    *,
    require_private_mode: bool = False,
) -> dict[str, Any]:
    if not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("no_follow_unsupported")
    descriptor: int | None = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError("nonregular_input")
        if require_private_mode and stat.S_IMODE(metadata.st_mode) != 0o600:
            raise RuntimeError("snapshot_permissions")
        if metadata.st_size > maximum:
            raise RuntimeError("unreadable")
        chunks: list[bytes] = []
        consumed = 0
        while True:
            chunk = os.read(descriptor, min(65536, maximum + 1 - consumed))
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > maximum:
                raise RuntimeError("unreadable")
            chunks.append(chunk)
        value = json.loads(b"".join(chunks).decode("utf-8"))
    except RuntimeError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError("unreadable") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)
    if not isinstance(value, dict):
        raise RuntimeError("unreadable")
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--projects-root", required=True, type=Path)
    parser.add_argument("--facts", type=Path)
    parser.add_argument("--previous", type=Path)
    parser.add_argument(
        "--standalone",
        action="store_true",
        help="Validate one finalized snapshot without current facts",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Atomically set contentDigest after every other check passes",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        projects_root = validate_projects_root(args.projects_root)
        snapshot_path = validate_input_path(
            args.snapshot,
            projects_root,
            require_private_mode=True,
        )
        if args.standalone:
            if args.facts or args.previous or args.finalize:
                raise RuntimeError("standalone_options")
            snapshot = load_json(
                snapshot_path,
                MAX_SNAPSHOT_BYTES,
                require_private_mode=True,
            )
            errors = validate_snapshot_document(snapshot)
            if errors:
                print(
                    json.dumps(
                        {"status": "invalid", "errors": errors},
                        separators=(",", ":"),
                    )
                )
                return 3
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "projects": len(snapshot["projects"]),
                        "sourceDigest": snapshot["sourceDigest"],
                        "contentDigest": snapshot["contentDigest"],
                    },
                    separators=(",", ":"),
                )
            )
            return 0
        if args.facts is None:
            raise RuntimeError("facts_required")
        facts_path = validate_input_path(args.facts, projects_root)
        previous_path = (
            validate_input_path(
                args.previous,
                projects_root,
                require_private_mode=True,
            )
            if args.previous
            else None
        )
        facts = load_json(facts_path, 2 * 1024 * 1024)
        snapshot = load_json(
            snapshot_path,
            MAX_SNAPSHOT_BYTES,
            require_private_mode=True,
        )
        previous = (
            load_json(
                previous_path,
                MAX_SNAPSHOT_BYTES,
                require_private_mode=True,
            )
            if previous_path
            else None
        )
    except (RuntimeError, OSError, ValueError) as exc:
        reason = str(exc) if str(exc) else "unreadable"
        print(json.dumps({"status": "failed", "reason": reason}, separators=(",", ":")), file=sys.stderr)
        return 2

    fact_errors = validate_facts(facts)
    if fact_errors:
        print(json.dumps({"status": "invalid", "errors": fact_errors}, separators=(",", ":")))
        return 3
    previous_errors = validate_previous_snapshot(previous) if previous is not None else []
    if previous_errors:
        print(json.dumps({"status": "invalid", "errors": previous_errors}, separators=(",", ":")))
        return 3
    if facts.get("collectionStatus") != "complete":
        print(json.dumps({"status": "partial", "reason": "facts_partial"}, separators=(",", ":")))
        return 3

    errors = validate_snapshot(snapshot, facts, previous, allow_unfinalized=args.finalize)
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, separators=(",", ":")))
        return 3

    if args.finalize:
        snapshot["contentDigest"] = content_digest(snapshot)
        try:
            atomic_snapshot_write(snapshot_path, snapshot, mode=0o600)
        except (OSError, ValueError):
            print(json.dumps({"status": "failed", "reason": "write_failed"}, separators=(",", ":")), file=sys.stderr)
            return 2

    final_errors = validate_snapshot(snapshot, facts, previous)
    if final_errors:
        print(json.dumps({"status": "invalid", "errors": final_errors}, separators=(",", ":")))
        return 3
    print(
        json.dumps(
            {
                "status": "valid",
                "projects": len(snapshot["projects"]),
                "sourceDigest": snapshot["sourceDigest"],
                "contentDigest": snapshot["contentDigest"],
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
