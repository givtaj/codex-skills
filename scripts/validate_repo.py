#!/usr/bin/env python3
"""Validate portable invariants for the public plugin marketplace."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import unicodedata
from collections.abc import Iterator
from datetime import date
from pathlib import Path

try:
    from .validate_public_git_identity import (
        LEGACY_COMMIT_EXEMPTIONS,
        LEGACY_TAG_OBJECT_EXEMPTIONS,
        NOREPLY_RE,
    )
except ImportError:
    from validate_public_git_identity import (  # type: ignore[no-redef]
        LEGACY_COMMIT_EXEMPTIONS,
        LEGACY_TAG_OBJECT_EXEMPTIONS,
        NOREPLY_RE,
    )


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_CANONICAL_NAME_LENGTH = 64
SCAFFOLD_SKILL_NAMES = {
    "example-skill",
    "my-skill",
    "sample-skill",
    "test-skill",
    "untitled-skill",
}
FULL_DATE_NAME_RE = re.compile(
    r"(?:^|-)(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12][0-9]|3[01])(?:-|$)"
)
DATED_PERIOD_NAME_RE = re.compile(
    r"(?ix)(?:^|-)"
    r"(?:"
    r"(?:daily|weekly|monthly|quarterly)(?:-[a-z0-9]+){0,3}-(?:19|20)[0-9]{2}"
    r"|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
    r"dec(?:ember)?)-(?:19|20)[0-9]{2}"
    r"|q[1-4]-(?:19|20)[0-9]{2}"
    r")(?:-|$)"
)
WORK_ITEM_NAME_RE = re.compile(
    r"(?:^|-)(?:task|issue|pr|pull-request|thread)-(?:[0-9]+|[0-9a-f]{8,})(?:-|$)"
)
UUID_NAME_RE = re.compile(
    r"(?:^|-)[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}(?:-|$)"
)
SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-((?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
OBJECT_ID_BYTES_RE = re.compile(rb"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
MODEL_VERSION_RE = re.compile(
    r"(?ix)\b(?:"
    r"(?:gpt|chatgpt)[\s_-]*[0-9]+(?:[.-][0-9]+)*"
    r"|claude(?:[\s_-]+(?:opus|sonnet|haiku))?[\s_-]*[0-9]+(?:[.-][0-9]+)*"
    r"|gemini[\s_-]*[0-9]+(?:[.-][0-9]+)*(?:[\s_-]+(?:pro|flash|ultra|thinking|model))"
    r"|llama[\s_-]*[0-9]+(?:[.-][0-9]+)*"
    r"|codex(?:[\s_-]+(?:spark|[0-9]+(?:[.-][0-9]+)*))"
    r"|openai[\s_-]+o[1-9]"
    r"|o[1-9][\s_-]+(?:mini|pro|max|reasoning|model)"
    r"|o[1-9](?:[\s_-]+[a-z0-9]+){0,3}[\s_-]+(?:agent|assistant|reviewer|reasoner)"
    r"|(?:sol|terra|luna)[\s_-]+(?:ultra|model)"
    r")\b"
)
LOWERCASE_O_MODEL_INSTRUCTION_RE = re.compile(
    r"\b(?i:use|run|ask|delegate(?:\s+to)?|select|choose|require(?:s|d)?)\b"
    r"[^\n.!?]{0,48}\bo[1-9]\b"
)
MODEL_REASONING_BINDING_RE = re.compile(
    r"(?ix)\b(?:sol|terra|luna)\b[^\n.!?]{0,48}"
    r"\b(?:minimal|low|medium|high|xhigh|max|ultra)\s+reasoning\b"
)
PERSONAL_PATH_CANDIDATE_RE = re.compile(
    r"file:///(?P<file_root>Users|home)/(?P<file_user>[^/\\\s`\"'<>:]+)"
    r"|(?<![A-Za-z0-9:/])/(?P<unix_root>Users|home)/"
    r"(?P<unix_user>[^/\\\s`\"'<>:]+)"
    r"|(?<![A-Za-z0-9])(?P<windows_drive>[A-Z]):\\Users\\"
    r"(?P<windows_user>[^\\/\s`\"'<>:]+)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PRIVATE_KEY_MARKER_RE = re.compile(
    "-----BEGIN "
    + r"(?:(?:OPENSSH|RSA|DSA|EC|ENCRYPTED) PRIVATE KEY|PRIVATE KEY|PGP PRIVATE KEY BLOCK)-----"
)
SENSITIVE_TEXT_PATTERNS = {
    "GitHub token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "GitLab access token": re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    "npm access token": re.compile(r"\bnpm_[A-Za-z0-9]{36,}\b"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(
        r"\b(?:xox[baprs]-[A-Za-z0-9-]{20,}|xapp-[A-Za-z0-9-]{20,})\b"
    ),
    "Stripe secret key": re.compile(
        r"\b(?:(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}|whsec_[A-Za-z0-9]{16,})\b"
    ),
    "JSON Web Token": re.compile(
        r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{10,}\b"
    ),
    "private key": PRIVATE_KEY_MARKER_RE,
}
GENERIC_HOME_USERS = {
    "app",
    "build",
    "ci",
    "demo",
    "deploy",
    "developer",
    "example",
    "me",
    "runner",
    "sample",
    "shared",
    "test",
    "ubuntu",
    "user",
    "user-name",
    "user_name",
    "username",
    "your-name",
    "your-user",
    "your_name",
    "your_user",
    "yourname",
}
RESERVED_EMAIL_DOMAINS = {"example.com", "example.net", "example.org"}
RESERVED_EMAIL_SUFFIXES = (".invalid", ".localhost", ".test")
UTF16_SCAN_CHUNK_BYTES = 256 * 1024
UTF16_SCAN_OVERLAP_BYTES = 1024
INSTALL_POLICIES = {"AVAILABLE", "INSTALLED_BY_DEFAULT", "NOT_AVAILABLE"}
AUTH_POLICIES = {"ON_INSTALL", "ON_USE"}
MARKETPLACE_CATEGORIES = {
    "Business & Operations",
    "Communication",
    "Creativity",
    "Data & Analytics",
    "Developer Tools",
    "Education & Research",
    "Finance",
    "Productivity",
    "Security",
}
REQUIRED_EVAL_KINDS = {
    "direct",
    "indirect",
    "incomplete",
    "follow_up",
    "boundary",
    "negative",
    "edge",
}
EXPECTED_ACTIVATIONS = {
    "activate",
    "activate_if_context_supplies_subject",
    "do_not_activate",
}
REQUIRED_PLUGIN_INTERFACE_STRINGS = {
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "websiteURL",
    "privacyPolicyURL",
}
REQUIRED_AGENT_FIELDS = {
    "display_name",
    "short_description",
    "default_prompt",
}
ALLOWED_PLUGIN_FIELDS = {
    "id",
    "name",
    "version",
    "description",
    "skills",
    "apps",
    "mcpServers",
    "interface",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
}
ALLOWED_AUTHOR_FIELDS = {"name", "email", "url"}
ALLOWED_PLUGIN_INTERFACE_FIELDS = {
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "websiteURL",
    "privacyPolicyURL",
    "termsOfServiceURL",
    "brandColor",
    "composerIcon",
    "logo",
    "logoDark",
    "screenshots",
    "defaultPrompt",
    "default_prompt",
}
ALLOWED_SKILL_FRONTMATTER_FIELDS = {
    "name",
    "description",
    "license",
    "allowed-tools",
    "metadata",
}
ALLOWED_MARKETPLACE_FIELDS = {"name", "interface", "plugins"}
ALLOWED_MARKETPLACE_INTERFACE_FIELDS = {"displayName"}
ALLOWED_MARKETPLACE_ENTRY_FIELDS = {"name", "source", "policy", "category"}
ALLOWED_MARKETPLACE_SOURCE_FIELDS = {"source", "path"}
ALLOWED_MARKETPLACE_POLICY_FIELDS = {"installation", "authentication", "products"}
EVAL_RESULT_KEYS = {
    "schema_version",
    "skill",
    "plugin_version",
    "date",
    "scope",
    "status",
    "checks",
    "behavioral_replay",
}
EVAL_RESULT_SCOPES = {"structural", "behavioral"}
EVAL_RESULT_STATUSES = {"passed", "partial", "failed"}
STRUCTURAL_REPLAY_KEYS = {"status", "reason"}
BEHAVIORAL_REPLAY_BASE_KEYS = {"status", "host", "case_ids"}
BEHAVIORAL_REPLAY_REASON_KEYS = BEHAVIORAL_REPLAY_BASE_KEYS | {"reason"}
RELEASE_STRUCTURAL_RESULT_KEYS = EVAL_RESULT_KEYS | {
    "tested_artifact",
    "public_candidate_verification",
}
RELEASE_SMOKE_RESULT_KEYS = RELEASE_STRUCTURAL_RESULT_KEYS | {"result_context"}
RELEASE_SCOPE_RE = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")
COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
PUBLIC_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$")
RELEASE_ARTIFACT_KEYS = {
    "release_state",
    "plugin_version",
    "candidate_ref",
    "commit_sha",
    "repository_url",
    "note",
}
RELEASE_SMOKE_ARTIFACT_KEYS = RELEASE_ARTIFACT_KEYS | {"codex_cli_version"}
RELEASE_CANDIDATE_KEYS = {
    "status",
    "candidate_ref",
    "commit_sha",
    "repository_url",
    "codex_cli_version",
    "github_actions_run_url",
    "note",
}
RELEASE_SMOKE_CANDIDATE_KEYS = RELEASE_CANDIDATE_KEYS | {
    "plugin_version",
    "passed_checks",
}
RELEASE_SMOKE_REPLAY_KEYS = {"status", "passed", "pending", "note"}
RELEASE_STRUCTURAL_REPLAY_KEYS = {"status", "result"}
SYNTHETIC_MERGE_ENV = "VALIDATION_SYNTHETIC_MERGE_SHA"
CONTRIBUTION_BASE_ENV = "VALIDATION_CONTRIBUTION_BASE_SHA"
CONTRIBUTION_HEAD_ENV = "VALIDATION_CONTRIBUTION_HEAD_SHA"
PUBLISHED_REF_NAMESPACE = "refs/validation/origin"


class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(sanitize_diagnostic(message))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def normalize_portability_text(value: str) -> str:
    """Normalize punctuation variants before applying narrow portability checks."""

    normalized = unicodedata.normalize("NFKC", value)
    normalized = "".join(character for character in normalized if unicodedata.category(character) != "Cf")
    return "".join(
        "-"
        if unicodedata.category(character) == "Pd" or character == "\N{MINUS SIGN}"
        else character
        for character in normalized
    )


def validate_canonical_name(value: object, label: str) -> str:
    """Reject objective identity hazards; semantic global clarity remains a review decision."""

    require(
        isinstance(value, str) and NAME_RE.fullmatch(value) is not None,
        f"{label}: invalid name",
    )
    require(
        len(value) <= MAX_CANONICAL_NAME_LENGTH,
        f"{label}: canonical name exceeds {MAX_CANONICAL_NAME_LENGTH} characters",
    )
    require(value not in SCAFFOLD_SKILL_NAMES, f"{label}: replace the scaffold name")
    require(
        FULL_DATE_NAME_RE.search(value) is None and DATED_PERIOD_NAME_RE.search(value) is None,
        f"{label}: canonical name must not be bound to a calendar date or reporting period",
    )
    require(
        WORK_ITEM_NAME_RE.search(value) is None and UUID_NAME_RE.search(value) is None,
        f"{label}: canonical name must not be bound to a task, issue, pull request, or thread",
    )
    require(
        MODEL_VERSION_RE.search(normalize_portability_text(value)) is None,
        f"{label}: canonical name must not be bound to a model release",
    )
    return value


def validate_core_skill_language(text: str, label: str) -> None:
    """Block unmistakably volatile core bindings while allowing routed compatibility notes."""

    normalized = normalize_portability_text(text)
    require(
        MODEL_VERSION_RE.search(normalized) is None,
        f"{label}: model release belongs in a routed reference",
    )
    require(
        LOWERCASE_O_MODEL_INSTRUCTION_RE.search(normalized) is None
        and MODEL_REASONING_BINDING_RE.search(normalized) is None,
        f"{label}: model-specific execution instruction belongs in a routed reference",
    )
    normalized_casefold = normalized.casefold()
    require(
        "window.openai" not in normalized_casefold,
        f"{label}: host API belongs in a routed reference",
    )
    require(
        "codex://" not in normalized_casefold,
        f"{label}: host URI belongs in a routed reference",
    )


def reject_unknown_fields(payload: dict, allowed: set[str], label: str) -> None:
    unknown = sorted(set(payload) - allowed)
    require(not unknown, f"{label}: unsupported field(s) {unknown}")


def require_https_url(value: object, label: str) -> None:
    require(
        isinstance(value, str) and value.startswith("https://") and len(value) > len("https://"),
        f"{label}: expected an absolute HTTPS URL",
    )


def validate_plugin_asset(plugin_dir: Path, raw_path: object, label: str, *, png: bool = False) -> None:
    require(isinstance(raw_path, str) and raw_path.startswith("./assets/"), f"{label}: invalid asset path")
    if png:
        require(raw_path.lower().endswith(".png"), f"{label}: screenshot must be a PNG file")
    target = (plugin_dir / raw_path).resolve()
    require(target.is_relative_to(plugin_dir.resolve()), f"{label}: asset escapes plugin directory")
    require(target.is_file(), f"{label}: asset file does not exist")


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def has_personal_absolute_path(text: str) -> bool:
    """Return true for a likely machine-specific home directory.

    Explicit documentation placeholders are portable and therefore allowed.
    The conservative allowlist is intentionally limited to unmistakably generic
    account names; arbitrary names under a user-home root remain rejected.
    """

    for match in PERSONAL_PATH_CANDIDATE_RE.finditer(text):
        if not is_generic_home_match(match):
            return True
    return False


def home_username(match: re.Match[str]) -> str:
    return (
        match.group("file_user")
        or match.group("unix_user")
        or match.group("windows_user")
        or ""
    )


def is_generic_home_match(match: re.Match[str]) -> bool:
    username = home_username(match)
    normalized = username.casefold().rstrip(".,;)")
    return normalized in GENERIC_HOME_USERS or any(
        marker in username for marker in ("$", "%", "{", "}")
    )


def is_allowed_public_email(email: str) -> bool:
    """Allow only non-personal documentation or GitHub noreply addresses."""

    normalized = email.casefold()
    if NOREPLY_RE.fullmatch(normalized) is not None:
        return True
    domain = normalized.rsplit("@", 1)[-1].rstrip(".")
    if domain in RESERVED_EMAIL_DOMAINS:
        return True
    if any(domain.endswith(f".{reserved}") for reserved in RESERVED_EMAIL_DOMAINS):
        return True
    return domain.endswith(RESERVED_EMAIL_SUFFIXES)


def sanitize_diagnostic(message: str) -> str:
    """Redact secret-shaped dynamic data before it can reach an exception or log."""

    sanitized = re.sub(r"[\x00-\x1f\x7f]", "?", str(message))
    for pattern in SENSITIVE_TEXT_PATTERNS.values():
        sanitized = pattern.sub("<redacted-secret>", sanitized)
    sanitized = EMAIL_RE.sub(
        lambda match: (
            match.group(0)
            if is_allowed_public_email(match.group(0))
            else "<redacted-email>"
        ),
        sanitized,
    )
    sanitized = PERSONAL_PATH_CANDIDATE_RE.sub(
        lambda match: (
            match.group(0) if is_generic_home_match(match) else "<redacted-personal-path>"
        ),
        sanitized,
    )
    return sanitized


def first_text_violation(
    text: str,
    *,
    allow_all_emails: bool,
    check_unfinished: bool,
) -> str | None:
    if check_unfinished and "[" + "TODO:" in text:
        return "unfinished placeholder"
    if has_personal_absolute_path(text):
        return "personal absolute path"
    if not allow_all_emails:
        for match in EMAIL_RE.finditer(text):
            if not is_allowed_public_email(match.group(0)):
                return "email address"
    for label, pattern in SENSITIVE_TEXT_PATTERNS.items():
        if pattern.search(text) is not None:
            return f"{label} pattern"
    return None


def utf16_text_windows(raw: bytes) -> Iterator[str]:
    """Yield bounded-memory UTF-16 views at both byte alignments."""

    if b"\x00" not in raw:
        return
    step = UTF16_SCAN_CHUNK_BYTES - UTF16_SCAN_OVERLAP_BYTES
    for encoding in ("utf-16-le", "utf-16-be"):
        for alignment in (0, 1):
            start = alignment
            while start < len(raw):
                piece = raw[start : start + UTF16_SCAN_CHUNK_BYTES]
                if len(piece) % 2:
                    piece = piece[:-1]
                if piece:
                    yield piece.decode(encoding, errors="ignore")
                if start + UTF16_SCAN_CHUNK_BYTES >= len(raw):
                    break
                start += step


def first_public_content_violation(
    raw: bytes,
    *,
    allow_all_emails: bool = False,
    check_unfinished: bool = True,
) -> str | None:
    """Inspect arbitrary bytes without dropping non-UTF-8 or NUL-bearing data."""

    violation = first_text_violation(
        raw.decode("latin-1"),
        allow_all_emails=allow_all_emails,
        check_unfinished=check_unfinished,
    )
    if violation is not None:
        return violation
    for text in utf16_text_windows(raw):
        violation = first_text_violation(
            text,
            allow_all_emails=allow_all_emails,
            check_unfinished=check_unfinished,
        )
        if violation is not None:
            return violation
    return None


def safe_path_label(raw_path: bytes) -> str:
    """Return a useful path label without echoing a sensitive filename."""

    violation = first_public_content_violation(raw_path, check_unfinished=False)
    has_control_byte = any(byte < 0x20 or byte == 0x7F for byte in raw_path)
    if violation is not None or has_control_byte:
        digest = hashlib.sha256(raw_path).hexdigest()[:12]
        return f"<redacted-path:{digest}>"
    try:
        return raw_path.decode("utf-8")
    except UnicodeDecodeError:
        digest = hashlib.sha256(raw_path).hexdigest()[:12]
        return f"<redacted-path:{digest}>"


def inspect_public_bytes(
    raw: bytes,
    label: str,
    *,
    allow_all_emails: bool = False,
    check_unfinished: bool = True,
) -> None:
    violation = first_public_content_violation(
        raw,
        allow_all_emails=allow_all_emails,
        check_unfinished=check_unfinished,
    )
    require(violation is None, f"{violation} found in {label}")


def git_bytes(
    root: Path,
    *args: str,
    input_bytes: bytes | None = None,
    allow_failure: bool = False,
) -> bytes:
    result = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(root), *args],
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        if allow_failure:
            return b""
        operation = args[0] if args else "inspection"
        raise ValidationError(f"Git {operation} failed during public-content validation")
    return result.stdout


def validated_unpublished_merge_commit(root: Path) -> str | None:
    """Return the exact CI merge commit whose metadata may be unpublished.

    The exception is available only when all three trusted workflow values are
    present, identify the checked-out two-parent merge, and are anchored in the
    separately fetched public-ref namespace. The merge itself must not be
    reachable from that namespace.
    """

    merge_sha = os.environ.get(SYNTHETIC_MERGE_ENV)
    base_sha = os.environ.get(CONTRIBUTION_BASE_ENV)
    head_sha = os.environ.get(CONTRIBUTION_HEAD_ENV)
    supplied = (merge_sha, base_sha, head_sha)
    if not any(value is not None for value in supplied):
        return None
    require(
        all(
            isinstance(value, str)
            and COMMIT_SHA_RE.fullmatch(value) is not None
            for value in supplied
        ),
        "pull-request merge validation requires three full Git object IDs",
    )
    assert merge_sha is not None and base_sha is not None and head_sha is not None
    require(base_sha != head_sha, "pull-request base and head commits must differ")

    for label, commit_sha in (
        ("merge", merge_sha),
        ("base", base_sha),
        ("head", head_sha),
    ):
        resolved = git_bytes(
            root,
            "rev-parse",
            "--verify",
            f"{commit_sha}^{{commit}}",
            allow_failure=True,
        ).strip()
        require(
            resolved == commit_sha.encode("ascii"),
            f"pull-request {label} object does not resolve to the declared commit",
        )

    checked_out = git_bytes(root, "rev-parse", "--verify", "HEAD^{commit}").strip()
    require(
        checked_out == merge_sha.encode("ascii"),
        "declared pull-request merge is not the checked-out commit",
    )
    parents = git_bytes(root, "show", "-s", "--format=%P", merge_sha).split()
    require(
        len(parents) == 2
        and set(parents) == {base_sha.encode("ascii"), head_sha.encode("ascii")},
        "declared pull-request merge parents do not match the contribution",
    )

    published_refs = git_bytes(
        root,
        "for-each-ref",
        "--format=%(refname)",
        PUBLISHED_REF_NAMESPACE,
    ).splitlines()
    require(
        bool(published_refs),
        "pull-request merge validation requires the fetched public-ref namespace",
    )
    containing_base_refs = git_bytes(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "--contains",
        base_sha,
        PUBLISHED_REF_NAMESPACE,
    ).splitlines()
    require(
        bool(containing_base_refs),
        "pull-request base commit is not anchored in fetched public refs",
    )
    merge_refs = git_bytes(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "--contains",
        merge_sha,
        PUBLISHED_REF_NAMESPACE,
    ).splitlines()
    require(
        not merge_refs,
        "declared pull-request merge is reachable from a fetched public ref",
    )
    return merge_sha


def split_git_object(raw: bytes) -> tuple[bytes, bytes]:
    headers, separator, body = raw.partition(b"\n\n")
    if not separator:
        return raw, b""
    return headers, body


def inspect_tree_entries(
    root: Path,
    treeish: bytes,
    source_label: str,
    scanned_blobs: set[bytes],
    scanned_paths: set[bytes],
) -> None:
    tree = git_bytes(root, "ls-tree", "-rz", "--full-tree", treeish.decode("ascii"))
    for record in tree.split(b"\x00"):
        if not record:
            continue
        metadata, separator, raw_path = record.partition(b"\t")
        require(bool(separator), f"malformed tree record in {source_label}")
        fields = metadata.split()
        require(len(fields) == 3, f"malformed tree metadata in {source_label}")
        mode, object_type, object_id = fields
        path_label = safe_path_label(raw_path)
        if raw_path not in scanned_paths:
            inspect_public_bytes(
                raw_path,
                f"Git history filename in {source_label}: {path_label}",
                check_unfinished=False,
            )
            scanned_paths.add(raw_path)
        require(
            mode != b"120000",
            f"symbolic link is not allowed in Git history at {source_label}: {path_label}",
        )
        if object_type != b"blob" or object_id in scanned_blobs:
            continue
        blob = git_bytes(root, "cat-file", "blob", object_id.decode("ascii"))
        inspect_public_bytes(
            blob,
            f"Git history blob {object_id[:12].decode('ascii')} ({path_label})",
        )
        scanned_blobs.add(object_id)


def inspect_reachable_git_object(
    root: Path,
    object_id: bytes,
    object_type: bytes,
    commit_tips: set[bytes],
    scanned_blobs: set[bytes],
    scanned_paths: set[bytes],
    scanned_tags: set[bytes],
) -> None:
    """Inspect a ref target, including tags that point directly to trees or blobs."""

    require(
        OBJECT_ID_BYTES_RE.fullmatch(object_id) is not None,
        "malformed reachable Git object ID",
    )
    object_label = object_id[:12].decode("ascii")
    if object_type == b"commit":
        commit_tips.add(object_id)
        return
    if object_type == b"blob":
        if object_id not in scanned_blobs:
            blob = git_bytes(root, "cat-file", "blob", object_id.decode("ascii"))
            inspect_public_bytes(blob, f"Git ref blob {object_label}")
            scanned_blobs.add(object_id)
        return
    if object_type == b"tree":
        inspect_tree_entries(
            root,
            object_id,
            f"Git ref tree {object_label}",
            scanned_blobs,
            scanned_paths,
        )
        return
    require(object_type == b"tag", f"unsupported Git ref object type at {object_label}")
    if object_id in scanned_tags:
        return
    scanned_tags.add(object_id)

    raw_tag = git_bytes(root, "cat-file", "tag", object_id.decode("ascii"))
    headers, message = split_git_object(raw_tag)
    inspect_public_bytes(
        headers,
        f"annotated tag metadata {object_label}",
        allow_all_emails=object_id.decode("ascii") in LEGACY_TAG_OBJECT_EXEMPTIONS,
        check_unfinished=False,
    )
    inspect_public_bytes(message, f"annotated tag message {object_label}")

    target_id: bytes | None = None
    declared_type: bytes | None = None
    for line in headers.splitlines():
        if line.startswith(b"object "):
            target_id = line.removeprefix(b"object ")
        elif line.startswith(b"type "):
            declared_type = line.removeprefix(b"type ")
    require(
        target_id is not None
        and OBJECT_ID_BYTES_RE.fullmatch(target_id) is not None
        and declared_type in {b"blob", b"commit", b"tag", b"tree"},
        f"malformed annotated tag {object_label}",
    )
    actual_type = git_bytes(root, "cat-file", "-t", target_id.decode("ascii")).strip()
    require(actual_type == declared_type, f"annotated tag target type mismatch at {object_label}")
    inspect_reachable_git_object(
        root,
        target_id,
        actual_type,
        commit_tips,
        scanned_blobs,
        scanned_paths,
        scanned_tags,
    )


def inspect_index(
    root: Path,
    scanned_blobs: set[bytes],
    scanned_paths: set[bytes],
) -> None:
    index = git_bytes(root, "ls-files", "--stage", "-z")
    for record in index.split(b"\x00"):
        if not record:
            continue
        metadata, separator, raw_path = record.partition(b"\t")
        require(bool(separator), "malformed Git index record")
        fields = metadata.split()
        require(len(fields) == 3, "malformed Git index metadata")
        mode, object_id, _stage = fields
        path_label = safe_path_label(raw_path)
        if raw_path not in scanned_paths:
            inspect_public_bytes(
                raw_path,
                f"Git index filename: {path_label}",
                check_unfinished=False,
            )
            scanned_paths.add(raw_path)
        require(mode != b"120000", f"symbolic link is not allowed in Git index: {path_label}")
        if object_id in scanned_blobs or set(object_id) == {ord("0")}:
            continue
        blob = git_bytes(root, "cat-file", "blob", object_id.decode("ascii"))
        inspect_public_bytes(blob, f"Git index blob {object_id[:12].decode('ascii')} ({path_label})")
        scanned_blobs.add(object_id)


def validate_public_git_history(root: Path) -> None:
    """Scan content reachable from every locally available Git ref and HEAD."""

    require(
        bool(git_bytes(root, "rev-parse", "--git-dir", allow_failure=True)),
        "public-content validation requires a Git repository",
    )
    shallow = git_bytes(root, "rev-parse", "--is-shallow-repository").strip()
    require(
        shallow == b"false",
        "Git history is shallow; fetch full history and tags before public-content validation",
    )
    unpublished_merge = validated_unpublished_merge_commit(root)
    refs_raw = git_bytes(
        root,
        "for-each-ref",
        "--format=%(refname)%00%(objectname)%00%(objecttype)",
        "refs",
    )
    commit_tips: set[bytes] = set()
    scanned_blobs: set[bytes] = set()
    scanned_paths: set[bytes] = set()
    scanned_tags: set[bytes] = set()
    for line in refs_raw.splitlines():
        if not line:
            continue
        fields = line.split(b"\x00")
        require(len(fields) == 3, "malformed Git ref metadata")
        raw_ref, object_id, object_type = fields
        ref_label = safe_path_label(raw_ref)
        inspect_public_bytes(raw_ref, f"Git ref name: {ref_label}", check_unfinished=False)
        inspect_reachable_git_object(
            root,
            object_id,
            object_type,
            commit_tips,
            scanned_blobs,
            scanned_paths,
            scanned_tags,
        )

    head = git_bytes(root, "rev-parse", "-q", "--verify", "HEAD^{commit}", allow_failure=True).strip()
    if head:
        commit_tips.add(head)

    commits: list[bytes] = []
    if commit_tips:
        commits = [
            line
            for line in git_bytes(
                root,
                "rev-list",
                "--topo-order",
                "--stdin",
                input_bytes=b"\n".join(sorted(commit_tips)) + b"\n",
            ).splitlines()
            if line
        ]

    for commit in commits:
        commit_id = commit.decode("ascii")
        raw_commit = git_bytes(root, "cat-file", "commit", commit_id)
        headers, message = split_git_object(raw_commit)
        inspect_public_bytes(
            headers,
            f"commit metadata {commit_id[:12]}",
            allow_all_emails=(
                commit_id in LEGACY_COMMIT_EXEMPTIONS
                or commit_id == unpublished_merge
            ),
            check_unfinished=False,
        )
        inspect_public_bytes(message, f"commit message {commit_id[:12]}")
        inspect_tree_entries(
            root,
            commit,
            f"commit {commit_id[:12]}",
            scanned_blobs,
            scanned_paths,
        )

    inspect_index(root, scanned_blobs, scanned_paths)


def validate_public_worktree(root: Path) -> None:
    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        raw_relative = os.fsencode(path.relative_to(root))
        path_label = safe_path_label(raw_relative)
        inspect_public_bytes(
            raw_relative,
            f"working-tree path: {path_label}",
            check_unfinished=False,
        )
        require(not path.is_symlink(), f"symbolic link is not allowed: {path_label}")
        if path.is_file():
            inspect_public_bytes(path.read_bytes(), f"working-tree file: {path_label}")


def validate_public_content(root: Path = ROOT) -> None:
    validate_public_git_history(root)
    validate_public_worktree(root)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"missing file: {relative(path)}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON in {relative(path)}: {exc}") from exc
    require(isinstance(value, dict), f"expected JSON object: {relative(path)}")
    return value


def frontmatter(skill_md: Path) -> dict[str, str]:
    lines = skill_md.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0].strip() == "---", f"missing frontmatter: {relative(skill_md)}")
    try:
        closing = next(
            i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"
        )
    except StopIteration as exc:
        raise ValidationError(f"unterminated frontmatter: {relative(skill_md)}") from exc

    values: dict[str, str] = {}
    for line in lines[1:closing]:
        key_match = re.match(r"^([A-Za-z0-9_-]+):", line)
        if key_match:
            require(
                key_match.group(1) in ALLOWED_SKILL_FRONTMATTER_FIELDS,
                f"{relative(skill_md)}: unsupported frontmatter field {key_match.group(1)!r}",
            )
        match = re.match(r"^(name|description):\s*(.+?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip("\"'")
    return values


def validate_agent_metadata(skill_root: Path) -> None:
    metadata_path = skill_root / "agents" / "openai.yaml"
    require(metadata_path.is_file(), f"missing OpenAI metadata: {relative(metadata_path)}")
    text = metadata_path.read_text(encoding="utf-8")
    for field in REQUIRED_AGENT_FIELDS:
        require(
            re.search(rf"^\s*{re.escape(field)}:\s*\S", text, re.MULTILINE) is not None,
            f"{relative(metadata_path)}: missing {field}",
        )
    require(
        re.search(r"^\s*allow_implicit_invocation:\s*(?:true|false)\s*$", text, re.MULTILINE)
        is not None,
        f"{relative(metadata_path)}: missing allow_implicit_invocation policy",
    )


def require_exact_keys(payload: dict, expected: set[str], label: str) -> None:
    actual = set(payload)
    missing = expected - actual
    unknown = actual - expected
    require(
        not missing and not unknown,
        f"{label}: keys differ; missing={sorted(missing)}, unknown={sorted(unknown)}",
    )


def validate_nonempty_string(value: object, label: str) -> str:
    require(isinstance(value, str) and value.strip(), f"{label}: must be a non-empty string")
    return value.strip()


def validate_unique_string_list(value: object, label: str) -> list[str]:
    require(
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item.strip() for item in value),
        f"{label}: must be a non-empty string array",
    )
    normalized = [item.strip() for item in value]
    require(len(normalized) == len(set(normalized)), f"{label}: entries must be unique")
    return normalized


def validate_public_ref(value: object, label: str) -> str:
    ref = validate_nonempty_string(value, label)
    require(
        PUBLIC_REF_RE.fullmatch(ref) is not None
        and ".." not in ref
        and not ref.endswith("/")
        and "//" not in ref,
        f"{label}: must be a safe public ref name",
    )
    return ref


def validate_release_artifact(
    artifact: object,
    result_path: Path,
    result_version: str,
    result_kind: str,
) -> dict:
    label = f"{relative(result_path)} tested_artifact"
    require(isinstance(artifact, dict), f"{label}: must be an object")
    expected_keys = (
        RELEASE_SMOKE_ARTIFACT_KEYS
        if result_kind == "release-smoke"
        else RELEASE_ARTIFACT_KEYS
    )
    require_exact_keys(artifact, expected_keys, label)

    expected_state = "published" if result_kind == "release-smoke" else "public-release-candidate"
    require(
        artifact["release_state"] == expected_state,
        f"{label}: release_state must be {expected_state!r}",
    )
    artifact_version = artifact["plugin_version"]
    require(
        isinstance(artifact_version, str) and SEMVER_RE.fullmatch(artifact_version) is not None,
        f"{label}: plugin_version must be strict semver",
    )
    if result_kind == "release-structural":
        require(
            artifact_version == result_version,
            f"{label}: plugin_version must match the result version",
        )
    validate_public_ref(artifact["candidate_ref"], f"{label}.candidate_ref")
    require(
        isinstance(artifact["commit_sha"], str)
        and COMMIT_SHA_RE.fullmatch(artifact["commit_sha"]) is not None,
        f"{label}.commit_sha: must be a full lowercase Git object id",
    )
    require_https_url(artifact["repository_url"], f"{label}.repository_url")
    validate_nonempty_string(artifact["note"], f"{label}.note")
    if result_kind == "release-smoke":
        cli_version = artifact["codex_cli_version"]
        require(
            cli_version is None
            or (isinstance(cli_version, str) and SEMVER_RE.fullmatch(cli_version) is not None),
            f"{label}.codex_cli_version: must be null or strict semver",
        )
    return artifact


def validate_public_candidate(
    verification: object,
    result_path: Path,
    result_version: str,
    result_kind: str,
    artifact: dict,
) -> None:
    label = f"{relative(result_path)} public_candidate_verification"
    require(isinstance(verification, dict), f"{label}: must be an object")
    expected_keys = (
        RELEASE_SMOKE_CANDIDATE_KEYS
        if result_kind == "release-smoke"
        else RELEASE_CANDIDATE_KEYS
    )
    require_exact_keys(verification, expected_keys, label)
    require(verification["status"] == "passed", f"{label}: status must be passed")
    if result_kind == "release-smoke":
        require(
            verification["plugin_version"] == result_version,
            f"{label}: plugin_version must match the result version",
        )
        validate_unique_string_list(verification["passed_checks"], f"{label}.passed_checks")
    candidate_ref = validate_public_ref(
        verification["candidate_ref"], f"{label}.candidate_ref"
    )
    commit_sha = verification["commit_sha"]
    require(
        isinstance(commit_sha, str) and COMMIT_SHA_RE.fullmatch(commit_sha) is not None,
        f"{label}.commit_sha: must be a full lowercase Git object id",
    )
    require_https_url(verification["repository_url"], f"{label}.repository_url")
    cli_version = verification["codex_cli_version"]
    require(
        isinstance(cli_version, str) and SEMVER_RE.fullmatch(cli_version) is not None,
        f"{label}.codex_cli_version: must be strict semver",
    )
    require_https_url(
        verification["github_actions_run_url"],
        f"{label}.github_actions_run_url",
    )
    validate_nonempty_string(verification["note"], f"{label}.note")

    if artifact["release_state"] == "public-release-candidate":
        require(
            candidate_ref == artifact["candidate_ref"]
            and commit_sha == artifact["commit_sha"]
            and verification["repository_url"] == artifact["repository_url"],
            f"{label}: candidate identity must match tested_artifact",
        )


def trusted_candidate_tag_namespace(root: Path) -> str:
    """Prefer the CI-fetched origin tag namespace when it is available."""

    fetched_namespace = f"{PUBLISHED_REF_NAMESPACE}/tags"
    fetched_tags = git_bytes(
        root,
        "for-each-ref",
        "--format=%(refname)",
        fetched_namespace,
    ).splitlines()
    return fetched_namespace if fetched_tags else "refs/tags"


def validate_candidate_tag(
    root: Path,
    candidate_ref: str,
    commit_sha: str,
    label: str,
) -> None:
    namespace = trusted_candidate_tag_namespace(root)
    full_ref = f"{namespace}/{candidate_ref}"
    resolved = git_bytes(
        root,
        "rev-parse",
        "--verify",
        f"{full_ref}^{{commit}}",
        allow_failure=True,
    ).strip()
    require(
        resolved == commit_sha.encode("ascii"),
        f"{label}: candidate tag is missing or resolves to a different commit",
    )


def validate_release_evidence_pairs(
    plugin_dir: Path,
    result_files: list[Path],
) -> None:
    pairs: dict[tuple[str, str], dict[str, tuple[Path, dict]]] = {}
    for result_path in result_files:
        result = load_json(result_path)
        result_keys = set(result)
        if result_keys == RELEASE_STRUCTURAL_RESULT_KEYS:
            result_kind = "structural"
        elif result_keys == RELEASE_SMOKE_RESULT_KEYS:
            result_kind = "smoke"
        else:
            continue
        key = (str(result["date"]), str(result["plugin_version"]))
        pair = pairs.setdefault(key, {})
        require(
            result_kind not in pair,
            f"{relative(plugin_dir / 'evals')}: duplicate {result_kind} release evidence",
        )
        pair[result_kind] = (result_path, result)

    for (result_date, result_version), pair in pairs.items():
        require(
            set(pair) == {"structural", "smoke"},
            f"{relative(plugin_dir / 'evals')}: release evidence for "
            f"{result_date} v{result_version} must include structural and smoke results",
        )
        structural_path, structural = pair["structural"]
        smoke_path, smoke = pair["smoke"]
        structural_candidate = structural["public_candidate_verification"]
        smoke_candidate = smoke["public_candidate_verification"]
        identity_fields = ("candidate_ref", "commit_sha", "repository_url")
        require(
            all(
                structural_candidate[field] == smoke_candidate[field]
                for field in identity_fields
            ),
            f"{relative(structural_path)} and {relative(smoke_path)}: "
            "paired release evidence identifies different public candidates",
        )
        validate_candidate_tag(
            ROOT,
            str(structural_candidate["candidate_ref"]),
            str(structural_candidate["commit_sha"]),
            f"{relative(structural_path)} public_candidate_verification",
        )


def validate_eval_result(
    result_path: Path,
    skill_name: str,
    golden_case_ids: set[str],
    current_plugin_version: str | None = None,
) -> str:
    result = load_json(result_path)
    result_keys = set(result)
    if result_keys == EVAL_RESULT_KEYS:
        result_kind = "canonical"
    elif result_keys == RELEASE_STRUCTURAL_RESULT_KEYS:
        result_kind = "release-structural"
    elif result_keys == RELEASE_SMOKE_RESULT_KEYS:
        result_kind = "release-smoke"
    else:
        expected_shapes = (
            EVAL_RESULT_KEYS,
            RELEASE_STRUCTURAL_RESULT_KEYS,
            RELEASE_SMOKE_RESULT_KEYS,
        )
        closest = min(expected_shapes, key=lambda shape: len(shape ^ result_keys))
        missing_keys = closest - result_keys
        unknown_keys = result_keys - closest
        raise ValidationError(
            f"{relative(result_path)}: evaluation result keys differ; "
            f"missing={sorted(missing_keys)}, unknown={sorted(unknown_keys)}"
        )
    require(
        EVAL_RESULT_KEYS <= result_keys,
        f"{relative(result_path)}: evaluation result is missing core keys",
    )

    require(
        type(result["schema_version"]) is int and result["schema_version"] == 1,
        f"{relative(result_path)}: unsupported schema",
    )
    require(
        result["skill"] == skill_name,
        f"{relative(result_path)}: skill mismatch",
    )

    result_version = result["plugin_version"]
    require(
        isinstance(result_version, str)
        and SEMVER_RE.fullmatch(result_version) is not None,
        f"{relative(result_path)}: plugin_version must be strict semver",
    )

    result_date = result["date"]
    require(
        isinstance(result_date, str)
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", result_date) is not None,
        f"{relative(result_path)}: date must use YYYY-MM-DD",
    )
    try:
        date.fromisoformat(result_date)
    except ValueError as exc:
        raise ValidationError(
            f"{relative(result_path)}: date must be a valid calendar date"
        ) from exc
    result_scope = result["scope"]
    if result_kind == "canonical":
        require(
            isinstance(result_scope, str) and result_scope in EVAL_RESULT_SCOPES,
            f"{relative(result_path)}: invalid scope",
        )
        filename_prefix = f"{result_date}-{result_scope}"
        require(
            result_path.stem == filename_prefix
            or result_path.stem.startswith(f"{filename_prefix}-"),
            f"{relative(result_path)}: filename must begin with date and scope",
        )
    else:
        require(
            isinstance(result_scope, str)
            and RELEASE_SCOPE_RE.fullmatch(result_scope) is not None,
            f"{relative(result_path)}: release evidence scope must be lower-case kebab-case",
        )
        required_scope_terms = (
            {"candidate", "smoke"}
            if result_kind == "release-smoke"
            else {"structural", "regression"}
        )
        require(
            required_scope_terms <= set(result_scope.split("-")),
            f"{relative(result_path)}: release evidence scope does not match its result kind",
        )
        filename_kind = "codex-cli" if result_kind == "release-smoke" else "structural"
        require(
            result_path.stem == f"{result_date}-v{result_version}-{filename_kind}",
            f"{relative(result_path)}: filename must bind date, plugin version, and result kind",
        )

    result_status = result["status"]
    require(
        isinstance(result_status, str) and result_status in EVAL_RESULT_STATUSES,
        f"{relative(result_path)}: invalid status",
    )

    validate_unique_string_list(result["checks"], f"{relative(result_path)} checks")

    if result_kind != "canonical":
        if result_kind == "release-smoke":
            validate_nonempty_string(
                result["result_context"], f"{relative(result_path)} result_context"
            )
        artifact = validate_release_artifact(
            result["tested_artifact"], result_path, result_version, result_kind
        )
        validate_public_candidate(
            result["public_candidate_verification"],
            result_path,
            result_version,
            result_kind,
            artifact,
        )

    replay = result["behavioral_replay"]
    require(
        isinstance(replay, dict),
        f"{relative(result_path)}: behavioral_replay must be an object",
    )
    replay_keys = set(replay)

    if result_kind == "release-smoke":
        require_exact_keys(replay, RELEASE_SMOKE_REPLAY_KEYS, f"{relative(result_path)} replay")
        require(
            result_status == "partial" and replay["status"] == "partial",
            f"{relative(result_path)}: release smoke without golden case IDs must remain partial",
        )
        passed = validate_unique_string_list(
            replay["passed"], f"{relative(result_path)} replay.passed"
        )
        pending = validate_unique_string_list(
            replay["pending"], f"{relative(result_path)} replay.pending"
        )
        require(
            not set(passed) & set(pending),
            f"{relative(result_path)}: replay passed and pending claims must be disjoint",
        )
        validate_nonempty_string(replay["note"], f"{relative(result_path)} replay.note")
        return result_version

    if result_kind == "release-structural":
        require_exact_keys(
            replay,
            RELEASE_STRUCTURAL_REPLAY_KEYS,
            f"{relative(result_path)} replay",
        )
        require(
            result_status == "passed" and replay["status"] == "partial",
            f"{relative(result_path)}: structural release evidence must pass while "
            "delegated behavioral replay remains partial",
        )
        expected_result = f"{result_date}-v{result_version}-codex-cli.json"
        require(
            replay["result"] == expected_result
            and (result_path.parent / expected_result).is_file(),
            f"{relative(result_path)}: replay must reference the matching smoke result",
        )
        return result_version

    if result_scope == "structural":
        require(
            replay_keys == STRUCTURAL_REPLAY_KEYS,
            f"{relative(result_path)}: structural replay metadata must contain "
            "exactly status and reason",
        )
        require(
            replay["status"] == "pending",
            f"{relative(result_path)}: structural replay status must be pending",
        )
        require(
            isinstance(replay["reason"], str) and replay["reason"].strip(),
            f"{relative(result_path)}: structural replay reason must be non-empty",
        )
        return result_version

    require(
        "status" in replay_keys,
        f"{relative(result_path)}: behavioral replay status is missing",
    )
    replay_status = replay["status"]
    require(
        isinstance(replay_status, str) and replay_status in EVAL_RESULT_STATUSES,
        f"{relative(result_path)}: behavioral replay status must be non-pending",
    )
    expected_replay_keys = (
        BEHAVIORAL_REPLAY_BASE_KEYS
        if replay_status == "passed"
        else BEHAVIORAL_REPLAY_REASON_KEYS
    )
    require(
        replay_keys == expected_replay_keys,
        f"{relative(result_path)}: behavioral replay metadata has an invalid shape",
    )
    require(
        isinstance(replay["host"], str) and replay["host"].strip(),
        f"{relative(result_path)}: behavioral replay host must be non-empty",
    )
    replay_case_ids = replay["case_ids"]
    require(
        isinstance(replay_case_ids, list)
        and replay_case_ids
        and all(
            isinstance(case_id, str) and NAME_RE.fullmatch(case_id) is not None
            for case_id in replay_case_ids
        ),
        f"{relative(result_path)}: behavioral replay case_ids must be valid golden case IDs",
    )
    require(
        len(replay_case_ids) == len(set(replay_case_ids)),
        f"{relative(result_path)}: behavioral replay case_ids must be unique",
    )
    validates_current_cases = (
        current_plugin_version is None or result_version == current_plugin_version
    )
    if validates_current_cases:
        require(
            set(replay_case_ids) <= golden_case_ids,
            f"{relative(result_path)}: behavioral replay contains an unknown case id",
        )
        if replay_status == "passed":
            require(
                set(replay_case_ids) == golden_case_ids,
                f"{relative(result_path)}: passed replay must cover every golden case",
            )
    if replay_status != "passed":
        require(
            isinstance(replay["reason"], str) and replay["reason"].strip(),
            f"{relative(result_path)}: partial or failed replay requires a reason",
        )
    require(
        result_status == replay_status,
        f"{relative(result_path)}: behavioral result and replay statuses differ",
    )
    return result_version


def validate_eval_results(
    plugin_dir: Path,
    skill_name: str,
    plugin_version: str,
    golden_case_ids: set[str],
) -> None:
    result_files = sorted((plugin_dir / "evals" / "results").glob("*.json"))
    require(
        result_files,
        f"{relative(plugin_dir / 'evals')}: missing dated validation result",
    )
    current_version_results = 0
    for result_path in result_files:
        result_version = validate_eval_result(
            result_path,
            skill_name,
            golden_case_ids,
            plugin_version,
        )
        if result_version == plugin_version:
            current_version_results += 1
    validate_release_evidence_pairs(plugin_dir, result_files)
    require(
        current_version_results > 0,
        f"{relative(plugin_dir / 'evals')}: "
        f"no validation result for plugin version {plugin_version}",
    )


def validate_eval(plugin_dir: Path, skill_name: str, plugin_version: str) -> None:
    eval_path = plugin_dir / "evals" / f"{skill_name}.json"
    payload = load_json(eval_path)
    require(payload.get("schema_version") == 1, f"{relative(eval_path)}: unsupported schema")
    require(payload.get("skill") == skill_name, f"{relative(eval_path)}: skill mismatch")
    cases = payload.get("cases")
    require(isinstance(cases, list) and cases, f"{relative(eval_path)}: cases must be non-empty")

    ids: set[str] = set()
    kinds: set[str] = set()
    for case in cases:
        require(isinstance(case, dict), f"{relative(eval_path)}: each case must be an object")
        case_id = case.get("id")
        require(
            isinstance(case_id, str) and NAME_RE.fullmatch(case_id),
            f"{relative(eval_path)}: invalid case id {case_id!r}",
        )
        require(case_id not in ids, f"{relative(eval_path)}: duplicate case id {case_id}")
        ids.add(case_id)

        kind = case.get("kind")
        require(kind in REQUIRED_EVAL_KINDS, f"{relative(eval_path)}: invalid kind {kind!r}")
        kinds.add(kind)
        require(
            isinstance(case.get("prompt"), str) and case["prompt"].strip(),
            f"{relative(eval_path)}: {case_id} has no prompt",
        )
        require(
            case.get("expected_activation") in EXPECTED_ACTIVATIONS,
            f"{relative(eval_path)}: {case_id} has invalid expected activation",
        )
        behavior = case.get("expected_behavior")
        require(
            isinstance(behavior, list)
            and behavior
            and all(isinstance(item, str) and item.strip() for item in behavior),
            f"{relative(eval_path)}: {case_id} needs observable expected behavior",
        )

    missing = REQUIRED_EVAL_KINDS - kinds
    require(not missing, f"{relative(eval_path)}: missing case kinds {sorted(missing)}")
    validate_eval_results(plugin_dir, skill_name, plugin_version, ids)


def validate_plugin_interface(manifest_path: Path, manifest: dict, category: str) -> None:
    interface = manifest.get("interface")
    require(isinstance(interface, dict), f"{relative(manifest_path)}: missing interface")
    reject_unknown_fields(
        interface,
        ALLOWED_PLUGIN_INTERFACE_FIELDS,
        f"{relative(manifest_path)} interface",
    )
    for field in REQUIRED_PLUGIN_INTERFACE_STRINGS:
        require(
            isinstance(interface.get(field), str) and interface[field].strip(),
            f"{relative(manifest_path)}: missing interface.{field}",
        )
    require(
        interface.get("category") == category,
        f"{relative(manifest_path)}: interface category differs from marketplace",
    )
    for field in ("websiteURL", "privacyPolicyURL", "termsOfServiceURL"):
        if field in interface:
            require_https_url(interface[field], f"{relative(manifest_path)} interface.{field}")
    capabilities = interface.get("capabilities")
    require(
        isinstance(capabilities, list)
        and capabilities
        and all(isinstance(value, str) and value.strip() for value in capabilities),
        f"{relative(manifest_path)}: capabilities must be a non-empty string array",
    )
    prompts = interface.get("defaultPrompt")
    require(
        isinstance(prompts, list)
        and 1 <= len(prompts) <= 3
        and all(isinstance(value, str) and value.strip() and len(value) <= 128 for value in prompts),
        f"{relative(manifest_path)}: defaultPrompt must contain one to three prompts",
    )
    require(
        HEX_COLOR_RE.fullmatch(str(interface.get("brandColor", ""))) is not None,
        f"{relative(manifest_path)}: brandColor must use #RRGGBB",
    )
    plugin_dir = manifest_path.parent.parent
    for field in ("composerIcon", "logo", "logoDark"):
        if field in interface:
            validate_plugin_asset(
                plugin_dir,
                interface[field],
                f"{relative(manifest_path)} interface.{field}",
            )
    screenshots = interface.get("screenshots", [])
    require(isinstance(screenshots, list), f"{relative(manifest_path)}: screenshots must be an array")
    for index, screenshot in enumerate(screenshots):
        validate_plugin_asset(
            plugin_dir,
            screenshot,
            f"{relative(manifest_path)} interface.screenshots[{index}]",
            png=True,
        )


def validate_skill(
    plugin_dir: Path,
    skill_md: Path,
    skill_names: set[str],
    plugin_version: str,
) -> str:
    metadata = frontmatter(skill_md)
    skill_name = validate_canonical_name(metadata.get("name"), relative(skill_md))
    description = metadata.get("description", "").strip()
    require(skill_name == skill_md.parent.name, f"{relative(skill_md)}: name must match folder")
    require(skill_name not in skill_names, f"duplicate skill name: {skill_name}")
    require(80 <= len(description) <= 500, f"{relative(skill_md)}: description must be 80-500 characters")
    require("Do not use" in description, f"{relative(skill_md)}: description needs a Do not use boundary")
    require(
        f"${skill_name}" not in description,
        f"{relative(skill_md)}: keep invocation syntax out of the activation description",
    )

    text = skill_md.read_text(encoding="utf-8")
    validate_core_skill_language(text, relative(skill_md))
    require(
        not has_personal_absolute_path(text),
        f"{relative(skill_md)}: contains a personal absolute path",
    )

    for reference in re.findall(r"`(references/[^`]+)`", text):
        target = skill_md.parent / reference
        require(target.is_file(), f"{relative(skill_md)}: missing referenced file {reference}")

    validate_agent_metadata(skill_md.parent)
    validate_eval(plugin_dir, skill_name or "", plugin_version)
    skill_names.add(skill_name or "")
    return skill_name


def validate() -> tuple[int, int, int]:
    # Inspect raw bytes and history before parsing attacker-controlled schema data.
    validate_public_content(ROOT)
    marketplace = load_json(MARKETPLACE_PATH)
    reject_unknown_fields(marketplace, ALLOWED_MARKETPLACE_FIELDS, relative(MARKETPLACE_PATH))
    marketplace_name = marketplace.get("name")
    require(
        isinstance(marketplace_name, str) and NAME_RE.fullmatch(marketplace_name),
        "marketplace name must be lower-case kebab-case",
    )
    marketplace_interface = marketplace.get("interface", {})
    require(isinstance(marketplace_interface, dict), "marketplace interface must be an object")
    reject_unknown_fields(
        marketplace_interface,
        ALLOWED_MARKETPLACE_INTERFACE_FIELDS,
        f"{relative(MARKETPLACE_PATH)} interface",
    )
    display_name = marketplace_interface.get("displayName")
    require(isinstance(display_name, str) and display_name.strip(), "missing marketplace displayName")

    entries = marketplace.get("plugins")
    require(isinstance(entries, list) and entries, "marketplace must list at least one plugin")

    entry_names: set[str] = set()
    skill_names: set[str] = set()
    eval_count = 0

    for entry in entries:
        require(isinstance(entry, dict), "each marketplace plugin entry must be an object")
        reject_unknown_fields(
            entry,
            ALLOWED_MARKETPLACE_ENTRY_FIELDS,
            "marketplace plugin entry",
        )
        name = validate_canonical_name(entry.get("name"), "marketplace plugin")
        require(name not in entry_names, f"duplicate marketplace plugin: {name}")
        entry_names.add(name)

        source = entry.get("source")
        require(isinstance(source, dict), f"{name}: source must be an object")
        reject_unknown_fields(source, ALLOWED_MARKETPLACE_SOURCE_FIELDS, f"{name} source")
        expected_path = f"./plugins/{name}"
        require(
            source == {"source": "local", "path": expected_path},
            f"{name}: source must be local path {expected_path}",
        )
        policy = entry.get("policy", {})
        require(isinstance(policy, dict), f"{name}: policy must be an object")
        reject_unknown_fields(policy, ALLOWED_MARKETPLACE_POLICY_FIELDS, f"{name} policy")
        require(policy.get("installation") in INSTALL_POLICIES, f"{name}: invalid installation policy")
        require(policy.get("authentication") in AUTH_POLICIES, f"{name}: invalid authentication policy")
        category = entry.get("category")
        require(category in MARKETPLACE_CATEGORIES, f"{name}: unsupported marketplace category {category!r}")

        plugin_dir = ROOT / "plugins" / name
        manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
        manifest = load_json(manifest_path)
        reject_unknown_fields(manifest, ALLOWED_PLUGIN_FIELDS, relative(manifest_path))
        require(manifest.get("name") == name, f"{name}: manifest name mismatch")
        version = str(manifest.get("version", ""))
        require(SEMVER_RE.fullmatch(version) is not None, f"{name}: invalid semver")
        require(
            isinstance(manifest.get("description"), str) and manifest["description"].strip(),
            f"{name}: missing description",
        )
        require(
            isinstance(manifest.get("author"), dict)
            and isinstance(manifest["author"].get("name"), str)
            and manifest["author"]["name"].strip(),
            f"{name}: missing author.name",
        )
        reject_unknown_fields(
            manifest["author"],
            ALLOWED_AUTHOR_FIELDS,
            f"{relative(manifest_path)} author",
        )
        if "url" in manifest["author"]:
            require_https_url(manifest["author"]["url"], f"{relative(manifest_path)} author.url")
        if "email" in manifest["author"]:
            author_email = manifest["author"]["email"]
            require(
                isinstance(author_email, str)
                and EMAIL_RE.fullmatch(author_email) is not None
                and is_allowed_public_email(author_email),
                f"{relative(manifest_path)} author.email must be a public-safe address",
            )
        for field in ("homepage", "repository"):
            if field in manifest:
                require_https_url(manifest[field], f"{relative(manifest_path)} {field}")
        keywords = manifest.get("keywords", [])
        require(
            isinstance(keywords, list)
            and all(isinstance(keyword, str) and keyword.strip() for keyword in keywords),
            f"{relative(manifest_path)}: keywords must be an array of strings",
        )
        require(manifest.get("skills") == "./skills/", f"{name}: skills path must be ./skills/")
        if "apps" in manifest:
            require(
                manifest["apps"] == "./.app.json" and (plugin_dir / ".app.json").is_file(),
                f"{name}: apps must point to an existing ./.app.json",
            )
        if isinstance(manifest.get("mcpServers"), str):
            require(
                manifest["mcpServers"] == "./.mcp.json" and (plugin_dir / ".mcp.json").is_file(),
                f"{name}: mcpServers must point to an existing ./.mcp.json",
            )
        elif "mcpServers" in manifest:
            require(
                isinstance(manifest["mcpServers"], dict),
                f"{name}: mcpServers must be an object or ./.mcp.json path",
            )
        require(manifest.get("license") == "MIT", f"{name}: license is not allowed by repository policy")
        validate_plugin_interface(manifest_path, manifest, category)

        skill_files = sorted((plugin_dir / "skills").glob("*/SKILL.md"))
        require(skill_files, f"{name}: plugin contains no skills")
        for skill_md in skill_files:
            skill_name = validate_skill(plugin_dir, skill_md, skill_names, version)
            if len(skill_files) == 1:
                require(skill_name == name, f"{name}: one-skill plugin must share the canonical skill name")
            eval_count += 1

        plugin_readme = plugin_dir / "README.md"
        require(plugin_readme.is_file(), f"{name}: missing plugin README")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        require(
            f"## {name} {version}" in changelog,
            f"{name}: changelog has no {version} release entry",
        )

    plugin_dirs = {
        path.name
        for path in (ROOT / "plugins").iterdir()
        if path.is_dir() and (path / ".codex-plugin" / "plugin.json").is_file()
    }
    require(plugin_dirs == entry_names, "stable plugin directories and marketplace entries differ")

    catalog_text = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted((ROOT / "catalog").glob("*.md"))
    )
    for name in entry_names:
        require(f"../plugins/{name}/" in catalog_text, f"{name}: missing category catalog link")

    return len(entry_names), len(skill_names), eval_count


def main() -> int:
    try:
        plugins, skills, evals = validate()
    except (OSError, ValidationError) as exc:
        print(f"validation failed: {sanitize_diagnostic(str(exc))}", file=sys.stderr)
        return 1
    print(f"Validated {plugins} plugin(s), {skills} skill(s), and {evals} golden request set(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
