#!/usr/bin/env python3
"""Collect bounded, path-free Git and allowlisted evidence facts."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime_support import require_supported_python


SCHEMA_VERSION = 2
EVIDENCE_MAP_SCHEMA_VERSION = 1
COLLECTOR_VERSION = "0.1.0"
GIT_TIMEOUT_SECONDS = 8
MAX_GIT_OUTPUT_BYTES = 1024 * 1024
MAX_FACTS_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_MAP_BYTES = 512 * 1024
MAX_PROJECTS = 500
MAX_EVIDENCE_ENTRIES = 64
MAX_GIT_CONFIG_BYTES = 1024 * 1024
MAX_GIT_METADATA_ENTRIES = 200000
PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
EVIDENCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
SAFE_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,159}$")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://", re.IGNORECASE)
FILE_URI_RE = re.compile(
    r"(?i)\bfile:(?://)?(?:/|[A-Za-z]:[\\/])[^\s]*"
)
HOSTNAME_RE = re.compile(
    r"(?i)\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}"
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
GIT_OBJECT_RE = re.compile(r"\b[a-f0-9]{40,64}\b", re.IGNORECASE)
MARKUP_RE = re.compile(
    r"(?m)(?:<[^>]+>|^#{1,6}\s|^>\s|^(?:[-*+]|\d+\.)\s|`{1,3}|\*\*|__|!\[|\[[^\]\r\n]+\]\([^)]+\))"
)
ABSOLUTE_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9._~-])(?:~[/\\][^\s]*|/(?:[^/\s]+(?:/[^/\s]*)*)?|[A-Za-z]:[\\/][^\s]+)"
)
SECRET_TEXT_RE = re.compile(
    r"(?i)(?:api[_-]?key|authorization|password|secret|token)\s*[:=]\s*\S+"
)
PROVIDER_TOKEN_RE = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{20,}\b|\bgh[pousr]_[A-Za-z0-9_]{20,}\b|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bdop_v1_[A-Za-z0-9]{20,}\b|"
    r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b|\beyJ[A-Za-z0-9_-]{10,}\."
    r"[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b)"
)


def valid_project_id(value: Any) -> bool:
    """Accept path-safe ids while excluding network-location-shaped values."""
    if not isinstance(value, str) or not PROJECT_ID_RE.fullmatch(value):
        return False
    if HOSTNAME_RE.search(value) or IPV4_RE.search(value):
        return False
    return True


GIT_CONFIG_INCLUDE_RE = re.compile(
    r"(?im)^\s*\[\s*include(?:if\b[^\]]*)?\s*\]"
)
GIT_CONFIG_FILTER_RE = re.compile(
    r"(?im)^\s*(?:\ufeff)?\[\s*filter(?:\s+[^\]]+|\.[^\]]+)?\s*\]"
)
GIT_CONFIG_WORKTREE_RE = re.compile(r"(?im)^\s*worktree\s*=")
OUTGOING_COMMIT_LIMIT = 8
ROOT_MAP_KEYS = {"schemaVersion", "limits", "default", "projects"}
LIMIT_KEYS = {"maxFileBytes", "maxProjectBytes"}
EVIDENCE_KEYS = {"id", "path", "required"}
FORBIDDEN_PARTS = {
    ".git",
    ".next",
    ".vinext",
    ".wrangler",
    "auth",
    "build",
    "cache",
    "caches",
    "coverage",
    "credentials",
    "data",
    "database",
    "databases",
    "dist",
    "logs",
    "node_modules",
    "out",
    "outputs",
    "profiles",
    "raw",
    "secrets",
    "sessions",
    "target",
    "temp",
    "tmp",
    "traces",
    "users",
    "work",
}
FORBIDDEN_SUFFIXES = {
    ".bak",
    ".backup",
    ".csv",
    ".db",
    ".der",
    ".dump",
    ".jsonl",
    ".kdbx",
    ".key",
    ".log",
    ".lock",
    ".ndjson",
    ".ovpn",
    ".p12",
    ".pem",
    ".pfx",
    ".sqlite",
    ".sqlite3",
    ".tsv",
    ".trace",
}
FORBIDDEN_FILENAME_STEMS = {
    ".netrc",
    ".npmrc",
    ".pypirc",
    "authorized_keys",
    "credential",
    "credentials",
    "cookies",
    "customer",
    "customers",
    "database",
    "dump",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
    "passwd",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "secrets",
    "session",
    "shadow",
    "token",
}
FORBIDDEN_FILENAME_TOKENS = {
    "auth",
    "backup",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "customer",
    "customers",
    "database",
    "dump",
    "env",
    "export",
    "exports",
    "key",
    "keys",
    "log",
    "logs",
    "password",
    "private",
    "raw",
    "secret",
    "secrets",
    "session",
    "sessions",
    "token",
    "tokens",
    "trace",
    "traces",
}
BROAD_SYSTEM_ROOTS = {
    "/bin",
    "/boot",
    "/dev",
    "/etc",
    "/home",
    "/lib",
    "/lib64",
    "/media",
    "/mnt",
    "/opt",
    "/proc",
    "/root",
    "/run",
    "/sbin",
    "/srv",
    "/sys",
    "/tmp",
    "/usr",
    "/usr/local",
    "/var",
    "/var/lib",
}


class CollectionError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class EvidenceChanged(CollectionError):
    pass


def exact_keys(value: dict[str, Any], expected: set[str], code: str) -> None:
    if set(value) != expected:
        raise CollectionError(code)


def utc_timestamp(value: str | None = None) -> str:
    try:
        parsed = (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            if value
            else datetime.now(timezone.utc)
        )
    except ValueError as exc:
        raise CollectionError("generated_time_invalid") from exc
    if parsed.tzinfo is None:
        raise CollectionError("generated_time_invalid")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (OSError, ValueError):
        return False


def validate_projects_root(path: Path) -> Path:
    if path.is_symlink():
        raise CollectionError("projects_root_symlink")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise CollectionError("projects_root_missing") from exc
    if not resolved.is_dir():
        raise CollectionError("projects_root_invalid")
    anchor = Path(resolved.anchor).resolve()
    try:
        user_root = Path.home().resolve()
    except RuntimeError:
        user_root = None
    broad_roots = {Path(item).resolve() for item in BROAD_SYSTEM_ROOTS}
    probable_home_parent = resolved.parent in {Path("/home"), Path("/Users")}
    if (
        resolved == anchor
        or len(resolved.parts) < 3
        or resolved in broad_roots
        or probable_home_parent
        or (user_root is not None and resolved == user_root)
    ):
        raise CollectionError("projects_root_too_broad")
    return resolved


def validate_output_path(path: Path, projects_root: Path) -> Path:
    if path.is_symlink() or not path.name:
        raise CollectionError("facts_output_invalid")
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise CollectionError("facts_output_invalid") from exc
    output = parent / path.name
    if within(output, projects_root):
        raise CollectionError("facts_output_inside_projects")
    return output


def read_regular_file_no_follow(
    path: Path,
    maximum: int,
    *,
    unreadable_code: str,
    too_large_code: str,
) -> bytes:
    """Read one regular file without following its final symlink."""
    if not hasattr(os, "O_NOFOLLOW"):
        raise CollectionError("no_follow_unsupported")
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
        )
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CollectionError(unreadable_code)
        if metadata.st_size > maximum:
            raise CollectionError(too_large_code)
        chunks: list[bytes] = []
        consumed = 0
        while True:
            chunk = os.read(descriptor, min(65536, maximum + 1 - consumed))
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > maximum:
                raise CollectionError(too_large_code)
            chunks.append(chunk)
        return b"".join(chunks)
    except CollectionError:
        raise
    except OSError as exc:
        raise CollectionError(unreadable_code) from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)


def forbidden_evidence_path(path_text: str) -> bool:
    path = Path(path_text)
    if not path_text or path.is_absolute() or ".." in path.parts:
        return True
    if any(part in {"", "."} for part in path.parts):
        return True
    lowered = [part.casefold() for part in path.parts]
    if any(part.startswith(".env") for part in lowered):
        return True
    if any(part in FORBIDDEN_PARTS for part in lowered):
        return True
    filename = lowered[-1]
    if Path(filename).suffix in FORBIDDEN_SUFFIXES:
        return True
    stems: set[str] = {filename}
    stem = filename
    while "." in stem:
        next_stem = Path(stem).stem
        if next_stem == stem:
            break
        stem = next_stem
        stems.add(stem)
    if stems & FORBIDDEN_FILENAME_STEMS:
        return True
    filename_tokens = {
        token for token in re.split(r"[^a-z0-9]+", filename) if token
    }
    return bool(filename_tokens & FORBIDDEN_FILENAME_TOKENS)


def validate_evidence_entry(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CollectionError("evidence_map_invalid")
    exact_keys(value, EVIDENCE_KEYS, "evidence_map_invalid")
    evidence_id = value.get("id")
    path_text = value.get("path")
    required = value.get("required")
    if not isinstance(evidence_id, str) or not EVIDENCE_ID_RE.fullmatch(evidence_id):
        raise CollectionError("evidence_map_invalid")
    if not isinstance(path_text, str) or forbidden_evidence_path(path_text):
        raise CollectionError("evidence_path_forbidden")
    if not isinstance(required, bool):
        raise CollectionError("evidence_map_invalid")
    return {"id": evidence_id, "path": path_text, "required": required}


def validate_evidence_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > MAX_EVIDENCE_ENTRIES:
        raise CollectionError("evidence_map_invalid")
    entries = [validate_evidence_entry(item) for item in value]
    ids = [item["id"] for item in entries]
    paths = [item["path"] for item in entries]
    if len(ids) != len(set(ids)) or len(paths) != len(set(paths)):
        raise CollectionError("evidence_map_duplicate")
    return entries


def load_evidence_map(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise CollectionError("evidence_map_symlink")
    try:
        raw = read_regular_file_no_follow(
            path,
            MAX_EVIDENCE_MAP_BYTES,
            unreadable_code="evidence_map_unreadable",
            too_large_code="evidence_map_too_large",
        ).decode("utf-8")
        value = json.loads(raw)
    except CollectionError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CollectionError("evidence_map_unreadable") from exc
    if not isinstance(value, dict):
        raise CollectionError("evidence_map_invalid")
    exact_keys(value, ROOT_MAP_KEYS, "evidence_map_invalid")
    if value.get("schemaVersion") != EVIDENCE_MAP_SCHEMA_VERSION:
        raise CollectionError("evidence_map_version")

    limits = value.get("limits")
    if not isinstance(limits, dict):
        raise CollectionError("evidence_map_invalid")
    exact_keys(limits, LIMIT_KEYS, "evidence_map_invalid")
    max_file = limits.get("maxFileBytes")
    max_project = limits.get("maxProjectBytes")
    if (
        not isinstance(max_file, int)
        or isinstance(max_file, bool)
        or not 1 <= max_file <= 2 * 1024 * 1024
        or not isinstance(max_project, int)
        or isinstance(max_project, bool)
        or not max_file <= max_project <= 8 * 1024 * 1024
    ):
        raise CollectionError("evidence_map_limits")

    defaults = validate_evidence_list(value.get("default"))
    projects = value.get("projects")
    if not isinstance(projects, dict) or len(projects) > MAX_PROJECTS:
        raise CollectionError("evidence_map_invalid")
    normalized_projects: dict[str, list[dict[str, Any]]] = {}
    for project_id, entries in projects.items():
        if not valid_project_id(project_id):
            raise CollectionError("evidence_map_project")
        normalized_projects[project_id] = validate_evidence_list(entries)

    for project_id, entries in normalized_projects.items():
        merged_entries = {entry["id"]: entry for entry in defaults}
        merged_entries.update({entry["id"]: entry for entry in entries})
        merged_paths = [entry["path"] for entry in merged_entries.values()]
        if (
            len(merged_entries) > MAX_EVIDENCE_ENTRIES
            or len(merged_paths) != len(set(merged_paths))
        ):
            raise CollectionError("evidence_map_invalid")

    return {
        "schemaVersion": EVIDENCE_MAP_SCHEMA_VERSION,
        "limits": {"maxFileBytes": max_file, "maxProjectBytes": max_project},
        "default": defaults,
        "projects": normalized_projects,
    }


def project_evidence_entries(mapping: dict[str, Any], project_id: str) -> list[dict[str, Any]]:
    merged = {entry["id"]: entry for entry in mapping["default"]}
    merged.update({entry["id"]: entry for entry in mapping["projects"].get(project_id, [])})
    values = list(merged.values())
    if len(values) > MAX_EVIDENCE_ENTRIES:
        raise CollectionError("evidence_map_invalid")
    paths = [entry["path"] for entry in values]
    if len(paths) != len(set(paths)):
        raise CollectionError("evidence_map_duplicate")
    return values


def validate_evidence_map_cardinality(mapping: dict[str, Any]) -> None:
    try:
        defaults = mapping["default"]
        projects = mapping["projects"]
        if (
            not isinstance(defaults, list)
            or len(defaults) > MAX_EVIDENCE_ENTRIES
            or not isinstance(projects, dict)
        ):
            raise CollectionError("evidence_map_invalid")
        for project_id, entries in projects.items():
            if (
                not isinstance(project_id, str)
                or not isinstance(entries, list)
                or len(entries) > MAX_EVIDENCE_ENTRIES
            ):
                raise CollectionError("evidence_map_invalid")
            project_evidence_entries(mapping, project_id)
    except CollectionError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise CollectionError("evidence_map_invalid") from exc


def git_environment() -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", os.defpath),
        "LC_ALL": "C",
        "TZ": "UTC",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_PAGER": "cat",
        "PAGER": "cat",
        "NO_COLOR": "1",
    }


def terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except OSError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        process.wait()


def bounded_process_output(process: subprocess.Popen[bytes]) -> bytes:
    """Drain both pipes incrementally and kill the process group at hard bounds."""
    if process.stdout is None or process.stderr is None:
        terminate_process_group(process)
        raise CollectionError("git_command_failed")
    selector = selectors.DefaultSelector()
    streams = {
        process.stdout.fileno(): ("stdout", process.stdout),
        process.stderr.fileno(): ("stderr", process.stderr),
    }
    for descriptor, (_, stream) in streams.items():
        os.set_blocking(descriptor, False)
        selector.register(stream, selectors.EVENT_READ, descriptor)

    deadline = time.monotonic() + GIT_TIMEOUT_SECONDS
    stdout = bytearray()
    total = 0
    try:
        while streams:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise CollectionError("git_timeout")
            events = selector.select(remaining)
            if not events:
                raise CollectionError("git_timeout")
            for key, _ in events:
                descriptor = key.data
                try:
                    chunk = os.read(descriptor, 65536)
                except BlockingIOError:
                    continue
                if not chunk:
                    _, stream = streams.pop(descriptor)
                    selector.unregister(stream)
                    stream.close()
                    continue
                total += len(chunk)
                if total > MAX_GIT_OUTPUT_BYTES:
                    raise CollectionError("git_output_limit")
                if streams[descriptor][0] == "stdout":
                    stdout.extend(chunk)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise CollectionError("git_timeout")
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired as exc:
            raise CollectionError("git_timeout") from exc
        return bytes(stdout)
    except CollectionError:
        terminate_process_group(process)
        raise
    except (OSError, ValueError) as exc:
        terminate_process_group(process)
        raise CollectionError("git_command_failed") from exc
    finally:
        selector.close()
        for _, stream in streams.values():
            stream.close()


def git_call(
    git_binary: str,
    repo: Path,
    args: list[str],
    allowed: tuple[int, ...] = (0,),
) -> tuple[bytes, int]:
    command = [
        git_binary,
        "-c",
        "core.fsmonitor=false",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        "core.untrackedCache=false",
        "-c",
        "core.excludesFile=",
        "-c",
        "submodule.recurse=false",
        "-c",
        "maintenance.auto=false",
        "-c",
        "credential.helper=",
        "-c",
        "color.ui=false",
        *args,
    ]
    try:
        process = subprocess.Popen(
            command,
            cwd=repo,
            env=git_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        stdout = bounded_process_output(process)
    except (OSError, PermissionError) as exc:
        raise CollectionError("git_command_failed") from exc
    if process.returncode not in allowed:
        raise CollectionError("git_command_failed")
    return stdout, process.returncode


def optional_lstat(path: Path) -> os.stat_result | None:
    try:
        return path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CollectionError("git_metadata_unreadable") from exc


def git_control_text(path: Path, maximum: int = 4096) -> str:
    try:
        return read_regular_file_no_follow(
            path,
            maximum,
            unreadable_code="git_metadata_unreadable",
            too_large_code="git_metadata_unreadable",
        ).decode("utf-8")
    except CollectionError:
        raise
    except UnicodeError as exc:
        raise CollectionError("git_metadata_unreadable") from exc


def one_line_git_path(value: str) -> str:
    lines = value.splitlines()
    if len(lines) != 1 or not lines[0].strip() or "\x00" in lines[0]:
        raise CollectionError("git_metadata_unreadable")
    return lines[0].strip()


def resolve_metadata_directory(
    candidate: Path,
    repo: Path,
    outside_code: str,
) -> Path:
    lexical = Path(os.path.abspath(candidate))
    try:
        relative = lexical.relative_to(repo)
    except ValueError as exc:
        raise CollectionError(outside_code) from exc
    current = repo
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise CollectionError("git_metadata_symlink")
    try:
        resolved = lexical.resolve(strict=True)
    except OSError as exc:
        raise CollectionError("git_metadata_unreadable") from exc
    if not resolved.is_dir() or not within(resolved, repo):
        raise CollectionError(outside_code)
    return resolved


def scan_git_metadata_no_symlinks(roots: list[Path], repo: Path) -> None:
    stack = list(roots)
    visited: set[tuple[int, int]] = set()
    entry_count = 0
    while stack:
        directory = stack.pop()
        try:
            metadata = directory.stat(follow_symlinks=False)
        except OSError as exc:
            raise CollectionError("git_metadata_unreadable") from exc
        identity = (metadata.st_dev, metadata.st_ino)
        if identity in visited:
            continue
        visited.add(identity)
        if not stat.S_ISDIR(metadata.st_mode) or not within(directory, repo):
            raise CollectionError("git_metadata_outside_project")
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    entry_count += 1
                    if entry_count > MAX_GIT_METADATA_ENTRIES:
                        raise CollectionError("git_metadata_limit")
                    try:
                        item_metadata = entry.stat(follow_symlinks=False)
                    except OSError as exc:
                        raise CollectionError("git_metadata_unreadable") from exc
                    if stat.S_ISLNK(item_metadata.st_mode):
                        raise CollectionError("git_metadata_symlink")
                    item = Path(entry.path)
                    if not within(item, repo):
                        raise CollectionError("git_metadata_outside_project")
                    if stat.S_ISDIR(item_metadata.st_mode):
                        stack.append(item)
                    elif not stat.S_ISREG(item_metadata.st_mode):
                        raise CollectionError("git_metadata_special_file")
        except CollectionError:
            raise
        except OSError as exc:
            raise CollectionError("git_metadata_unreadable") from exc


def validate_git_config(path: Path) -> None:
    metadata = optional_lstat(path)
    if metadata is None:
        return
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise CollectionError("git_metadata_symlink")
    text = git_control_text(path, MAX_GIT_CONFIG_BYTES)
    if GIT_CONFIG_INCLUDE_RE.search(text):
        raise CollectionError("git_config_include_forbidden")
    if GIT_CONFIG_FILTER_RE.search(text):
        raise CollectionError("git_filter_config_forbidden")
    if GIT_CONFIG_WORKTREE_RE.search(text):
        raise CollectionError("git_worktree_config_forbidden")


def validate_git_metadata(repo: Path, projects_root: Path) -> None:
    try:
        resolved_repo = repo.resolve(strict=True)
    except OSError as exc:
        raise CollectionError("git_metadata_unreadable") from exc
    if repo.is_symlink() or not resolved_repo.is_dir() or not within(resolved_repo, projects_root):
        raise CollectionError("git_metadata_outside_project")

    marker = resolved_repo / ".git"
    marker_metadata = optional_lstat(marker)
    if marker_metadata is None or stat.S_ISLNK(marker_metadata.st_mode):
        raise CollectionError("git_metadata_symlink")
    if stat.S_ISDIR(marker_metadata.st_mode):
        git_directory = resolve_metadata_directory(
            marker,
            resolved_repo,
            "git_metadata_outside_project",
        )
    elif stat.S_ISREG(marker_metadata.st_mode):
        marker_text = one_line_git_path(git_control_text(marker))
        if not marker_text.startswith("gitdir: "):
            raise CollectionError("git_metadata_unreadable")
        target_text = marker_text[8:].strip()
        if not target_text:
            raise CollectionError("git_metadata_unreadable")
        git_directory = resolve_metadata_directory(
            resolved_repo / target_text,
            resolved_repo,
            "git_metadata_outside_project",
        )
    else:
        raise CollectionError("git_metadata_unreadable")
    if not git_directory.is_dir() or not within(git_directory, resolved_repo):
        raise CollectionError("git_metadata_outside_project")

    common_file = git_directory / "commondir"
    common_metadata = optional_lstat(common_file)
    if common_metadata is None:
        common_directory = git_directory
    else:
        if stat.S_ISLNK(common_metadata.st_mode) or not stat.S_ISREG(
            common_metadata.st_mode
        ):
            raise CollectionError("git_metadata_symlink")
        common_text = one_line_git_path(git_control_text(common_file))
        common_directory = resolve_metadata_directory(
            git_directory / common_text,
            resolved_repo,
            "git_common_dir_outside_project",
        )
    if not common_directory.is_dir() or not within(common_directory, resolved_repo):
        raise CollectionError("git_common_dir_outside_project")

    metadata_roots = [git_directory]
    if common_directory != git_directory:
        metadata_roots.append(common_directory)
    scan_git_metadata_no_symlinks(metadata_roots, resolved_repo)

    objects_directory = common_directory / "objects"
    if not objects_directory.is_dir() or not within(objects_directory, resolved_repo):
        raise CollectionError("git_objects_outside_project")
    for alternate_name in ("alternates", "http-alternates"):
        alternate = objects_directory / "info" / alternate_name
        if optional_lstat(alternate) is not None:
            raise CollectionError("git_alternates_forbidden")

    for config in (
        git_directory / "config",
        common_directory / "config",
        common_directory / "config.worktree",
    ):
        validate_git_config(config)


def status_counts(payload: bytes) -> dict[str, int | bool]:
    tokens = payload.split(b"\0")
    index = 0
    changed = modified = deleted = untracked = conflicted = staged = unstaged = 0
    conflicts = {b"DD", b"AU", b"UD", b"UA", b"DU", b"AA", b"UU"}
    while index < len(tokens) and tokens[index]:
        token = tokens[index]
        if len(token) < 3:
            raise CollectionError("git_status_malformed")
        code = token[:2]
        changed += 1
        is_conflicted = code in conflicts or b"U" in code
        if code == b"??":
            untracked += 1
        elif is_conflicted:
            conflicted += 1
        else:
            if code[:1] not in (b" ", b"?"):
                staged += 1
            if code[1:2] not in (b" ", b"?"):
                unstaged += 1
            if b"D" in code:
                deleted += 1
            else:
                modified += 1
        index += 2 if any(flag in code for flag in (b"R", b"C")) else 1
    return {
        "clean": changed == 0,
        "changeCount": changed,
        "modifiedCount": modified,
        "deletedCount": deleted,
        "untrackedCount": untracked,
        "conflictedCount": conflicted,
        "stagedCount": staged,
        "unstagedCount": unstaged,
    }


def safe_public_text(value: str, maximum: int) -> str | None:
    value = value.strip()
    if not value or len(value) > maximum:
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return None
    if (
        EMAIL_RE.search(value)
        or URL_RE.search(value)
        or FILE_URI_RE.search(value)
        or HOSTNAME_RE.search(value)
        or GIT_OBJECT_RE.search(value)
        or MARKUP_RE.search(value)
        or ABSOLUTE_PATH_RE.search(value)
        or SECRET_TEXT_RE.search(value)
        or PROVIDER_TOKEN_RE.search(value)
    ):
        return None
    return value


def normalized_commit_time(value: str) -> str | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return (
        parsed.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def parse_commit_records(payload: bytes) -> list[dict[str, str | None]]:
    commits: list[dict[str, str | None]] = []
    for record in payload.split(b"\x1e"):
        parts = record.strip(b"\n\r\x00").split(b"\x00", 1)
        if not parts or parts == [b""]:
            continue
        if len(parts) != 2:
            raise CollectionError("git_log_malformed")
        timestamp = normalized_commit_time(parts[0].decode("utf-8", "replace"))
        if not timestamp:
            raise CollectionError("git_log_malformed")
        commits.append(
            {
                "at": timestamp,
                "subject": safe_public_text(
                    parts[1].decode("utf-8", "replace"),
                    180,
                ),
            }
        )
    return commits


def empty_outgoing(status: str) -> dict[str, Any]:
    return {"status": status, "count": None, "truncated": False, "commits": []}


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
        "outgoing": empty_outgoing("unavailable"),
        "commitSuggestionKinds": [],
    }


def commit_suggestion_kinds(
    state: str,
    counts: dict[str, int | bool],
) -> list[str]:
    if state == "unavailable" or not counts["changeCount"]:
        return []
    if counts["conflictedCount"]:
        return ["resolve-conflicts"]
    if state == "unborn":
        return ["review-initial-commit"]
    suggestions: list[str] = []
    if counts["stagedCount"]:
        suggestions.append("commit-staged")
    if counts["unstagedCount"]:
        suggestions.append("stage-tracked")
    if counts["untrackedCount"]:
        suggestions.append("review-untracked")
    return suggestions


def last_commit(
    git_binary: str,
    repo: Path,
) -> dict[str, str | None] | None:
    output, _ = git_call(
        git_binary,
        repo,
        ["log", "--max-count=1", "--format=%cI%x00%s%x00%x1e"],
    )
    commits = parse_commit_records(output)
    if len(commits) > 1:
        raise CollectionError("git_log_malformed")
    return commits[0] if commits else None


def outgoing_facts(
    git_binary: str,
    repo: Path,
    count: int,
) -> dict[str, Any]:
    output, _ = git_call(
        git_binary,
        repo,
        [
            "log",
            f"--max-count={OUTGOING_COMMIT_LIMIT}",
            "--format=%cI%x00%s%x00%x1e",
            "@{upstream}..HEAD",
        ],
    )
    commits = parse_commit_records(output)
    if len(commits) != min(count, OUTGOING_COMMIT_LIMIT):
        raise CollectionError("git_log_malformed")
    return {
        "status": "known",
        "count": count,
        "truncated": count > OUTGOING_COMMIT_LIMIT,
        "commits": commits,
    }


def repository_facts(
    git_binary: str, repo: Path, projects_root: Path
) -> tuple[dict[str, Any], list[str]]:
    try:
        validate_git_metadata(repo, projects_root)
        status_raw, _ = git_call(
            git_binary,
            repo,
            ["status", "--porcelain=v1", "-z", "--untracked-files=normal", "--ignore-submodules=all"],
        )
        counts = status_counts(status_raw)
        head_raw, head_code = git_call(
            git_binary, repo, ["rev-parse", "--verify", "HEAD"], allowed=(0, 128)
        )
        has_commits = head_code == 0 and bool(head_raw.strip())
        branch_raw, _ = git_call(
            git_binary,
            repo,
            ["symbolic-ref", "--quiet", "--short", "HEAD"],
            allowed=(0, 1),
        )
        branch_candidate = branch_raw.decode("utf-8", "replace").strip()
        branch = (
            branch_candidate
            if SAFE_BRANCH_RE.fullmatch(branch_candidate)
            and ".." not in branch_candidate
            and safe_public_text(branch_candidate, 160)
            else None
        )
        branch_redacted = bool(branch_candidate) and branch is None

        has_upstream = False
        ahead = behind = 0
        outgoing = empty_outgoing("unborn" if not has_commits else "no-upstream")
        if has_commits:
            _, upstream_code = git_call(
                git_binary,
                repo,
                [
                    "rev-parse",
                    "--abbrev-ref",
                    "--symbolic-full-name",
                    "@{upstream}",
                ],
                allowed=(0, 128),
            )
            has_upstream = upstream_code == 0
            if has_upstream:
                divergence_raw, _ = git_call(
                    git_binary,
                    repo,
                    ["rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                )
                try:
                    ahead_text, behind_text = divergence_raw.decode("ascii").strip().split()
                    ahead, behind = int(ahead_text), int(behind_text)
                except (ValueError, UnicodeError) as exc:
                    raise CollectionError("git_divergence_malformed") from exc
                if ahead < 0 or behind < 0:
                    raise CollectionError("git_divergence_malformed")
                outgoing = outgoing_facts(git_binary, repo, ahead)

        state = "unborn" if not has_commits else ("clean" if counts["clean"] else "dirty")
        return {
            "state": state,
            "branch": branch,
            "branchRedacted": branch_redacted,
            "hasUpstream": has_upstream,
            "ahead": ahead,
            "behind": behind,
            "changeCount": counts["changeCount"],
            "modifiedCount": counts["modifiedCount"],
            "deletedCount": counts["deletedCount"],
            "untrackedCount": counts["untrackedCount"],
            "conflictedCount": counts["conflictedCount"],
            "stagedCount": counts["stagedCount"],
            "unstagedCount": counts["unstagedCount"],
            "lastCommit": last_commit(git_binary, repo) if has_commits else None,
            "outgoing": outgoing,
            "commitSuggestionKinds": commit_suggestion_kinds(state, counts),
        }, []
    except CollectionError as exc:
        return unavailable_repository(), [exc.code]


def evidence_is_ignored(git_binary: str, repo: Path, relative_path: str) -> bool:
    _, code = git_call(
        git_binary,
        repo,
        ["check-ignore", "--quiet", "--", relative_path],
        allowed=(0, 1),
    )
    return code == 0


def hash_evidence_file_no_follow(
    project: Path,
    relative_path: str,
    max_bytes: int,
) -> tuple[str, int]:
    """Hash a regular evidence file without following any symlink component."""
    if not all(hasattr(os, name) for name in ("O_NOFOLLOW", "O_DIRECTORY")):
        raise CollectionError("no_follow_unsupported")
    descriptors: list[int] = []
    try:
        directory_flags = (
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY
        )
        current = os.open(project, directory_flags)
        descriptors.append(current)
        parts = Path(relative_path).parts
        for part in parts[:-1]:
            current = os.open(part, directory_flags, dir_fd=current)
            descriptors.append(current)
        file_descriptor = os.open(
            parts[-1],
            os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW,
            dir_fd=current,
        )
        descriptors.append(file_descriptor)
        metadata = os.fstat(file_descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise CollectionError("evidence_not_regular")
        if metadata.st_size > max_bytes:
            raise CollectionError("evidence_too_large")
        digest = hashlib.sha256()
        consumed = 0
        while True:
            chunk = os.read(
                file_descriptor,
                min(65536, max_bytes + 1 - consumed),
            )
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > max_bytes:
                raise CollectionError("evidence_too_large")
            digest.update(chunk)
        return digest.hexdigest(), consumed
    except FileNotFoundError as exc:
        raise CollectionError("evidence_missing") from exc
    except CollectionError:
        raise
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise CollectionError("evidence_symlink") from exc
        raise CollectionError("evidence_unreadable") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def evidence_facts(
    git_binary: str,
    project: Path,
    project_id: str,
    mapping: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    entries = project_evidence_entries(mapping, project_id)
    max_file = mapping["limits"]["maxFileBytes"]
    max_project = mapping["limits"]["maxProjectBytes"]
    total = 0
    results: list[dict[str, Any]] = []
    issues: list[str] = []

    for entry in entries:
        status = "missing"
        digest: str | None = None
        size: int | None = None
        try:
            if evidence_is_ignored(git_binary, project, entry["path"]):
                status = "rejected"
                issues.append("evidence_ignored")
            else:
                digest, size = hash_evidence_file_no_follow(
                    project,
                    entry["path"],
                    max_file,
                )
                total += size
                if total > max_project:
                    status = "rejected"
                    digest = None
                    size = None
                    issues.append("project_evidence_too_large")
                else:
                    status = "present"
        except CollectionError as exc:
            if exc.code == "evidence_missing":
                status = "missing"
            else:
                status = "rejected"
                issues.append(exc.code)
        if entry["required"] and status != "present":
            issues.append("required_evidence_missing")
        results.append(
            {
                "id": entry["id"],
                "required": entry["required"],
                "status": status,
                "sha256": digest,
                "bytes": size,
            }
        )
    return results, sorted(set(issues))


def unavailable_evidence_facts(
    project_id: str,
    mapping: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    entries = project_evidence_entries(mapping, project_id)
    issues = ["evidence_not_checked"]
    if any(entry["required"] for entry in entries):
        issues.append("required_evidence_missing")
    return [
        {
            "id": entry["id"],
            "required": entry["required"],
            "status": "rejected",
            "sha256": None,
            "bytes": None,
        }
        for entry in entries
    ], issues


def source_digest_payload(facts: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": facts["schemaVersion"],
        "collectorVersion": facts["collectorVersion"],
        "collectionStatus": facts["collectionStatus"],
        "projects": facts["projects"],
        "skipped": facts["skipped"],
    }


def compute_source_digest(facts: dict[str, Any]) -> str:
    payload = json.dumps(
        source_digest_payload(facts),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def collect(
    projects_root: Path,
    mapping: dict[str, Any],
    generated_at: str,
) -> tuple[dict[str, Any], bool]:
    validate_evidence_map_cardinality(mapping)
    git_binary = shutil.which("git")
    if not git_binary:
        raise CollectionError("git_not_available")

    projects: list[dict[str, Any]] = []
    collected_project_ids: set[str] = set()
    hidden = symlinks = unsafe_names = non_repositories = 0
    partial = False
    try:
        entries = sorted(projects_root.iterdir(), key=lambda item: os.fsencode(item.name))
    except OSError as exc:
        raise CollectionError("projects_root_unreadable") from exc
    if len(entries) > MAX_PROJECTS:
        raise CollectionError("project_limit")

    for project in entries:
        if project.name.startswith("."):
            hidden += 1
            continue
        if project.is_symlink():
            symlinks += 1
            partial = True
            continue
        if not project.is_dir():
            continue
        if not valid_project_id(project.name):
            unsafe_names += 1
            partial = True
            continue
        marker = project / ".git"
        if optional_lstat(marker) is None:
            non_repositories += 1
            continue

        repository, repository_issues = repository_facts(
            git_binary, project, projects_root
        )
        if repository_issues:
            evidence, evidence_issues = unavailable_evidence_facts(
                project.name,
                mapping,
            )
        else:
            evidence, evidence_issues = evidence_facts(
                git_binary, project, project.name, mapping
            )
        issues = sorted(set(repository_issues + evidence_issues))
        partial = partial or bool(issues)
        projects.append(
            {
                "id": project.name,
                "collectionStatus": "partial" if issues else "ok",
                "repository": repository,
                "evidence": evidence,
                "issues": issues,
            }
        )
        collected_project_ids.add(project.name)

    unmatched_project_entries = len(
        set(mapping["projects"]) - collected_project_ids
    )
    partial = partial or unmatched_project_entries > 0

    facts = {
        "schemaVersion": SCHEMA_VERSION,
        "collectorVersion": COLLECTOR_VERSION,
        "generatedAt": generated_at,
        "collectionStatus": "partial" if partial else "complete",
        "sourceDigest": "",
        "projects": projects,
        "skipped": {
            "hiddenEntryCount": hidden,
            "symlinkEntryCount": symlinks,
            "unsafeNameEntryCount": unsafe_names,
            "nonRepositoryEntryCount": non_repositories,
            "unmatchedProjectEntryCount": unmatched_project_entries,
        },
    }
    facts["sourceDigest"] = compute_source_digest(facts)
    return facts, partial


def load_facts_for_verification(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            read_regular_file_no_follow(
                path,
                MAX_FACTS_BYTES,
                unreadable_code="facts_unreadable",
                too_large_code="facts_too_large",
            ).decode("utf-8")
        )
    except CollectionError:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CollectionError("facts_unreadable") from exc
    if not isinstance(value, dict):
        raise CollectionError("facts_invalid")
    required = {
        "schemaVersion",
        "collectorVersion",
        "generatedAt",
        "collectionStatus",
        "sourceDigest",
        "projects",
        "skipped",
    }
    if set(value) != required:
        raise CollectionError("facts_invalid")
    digest = value.get("sourceDigest")
    if (
        value.get("schemaVersion") != SCHEMA_VERSION
        or value.get("collectorVersion") != COLLECTOR_VERSION
        or not isinstance(digest, str)
        or not re.fullmatch(r"[a-f0-9]{64}", digest)
    ):
        raise CollectionError("facts_invalid")
    try:
        if compute_source_digest(value) != digest:
            raise CollectionError("facts_digest_mismatch")
    except (KeyError, TypeError, ValueError) as exc:
        raise CollectionError("facts_invalid") from exc
    return value


def verify_evidence_reads(
    projects_root: Path,
    mapping: dict[str, Any],
    facts: dict[str, Any],
) -> None:
    """Re-read every mapped evidence item and compare it with private facts."""
    validate_evidence_map_cardinality(mapping)
    git_binary = shutil.which("git")
    if not git_binary:
        raise CollectionError("git_not_available")
    projects = facts.get("projects")
    if not isinstance(projects, list) or len(projects) > MAX_PROJECTS:
        raise CollectionError("facts_invalid")
    project_ids: set[str] = set()
    for fact_project in projects:
        if not isinstance(fact_project, dict):
            raise CollectionError("facts_invalid")
        project_id = fact_project.get("id")
        if (
            not isinstance(project_id, str)
            or not valid_project_id(project_id)
            or project_id in project_ids
            or not isinstance(fact_project.get("evidence"), list)
        ):
            raise CollectionError("facts_invalid")
        project_ids.add(project_id)
        project = projects_root / project_id
        if project.is_symlink() or not project.is_dir():
            raise EvidenceChanged("evidence_changed")
        try:
            validate_git_metadata(project, projects_root)
        except CollectionError as exc:
            raise EvidenceChanged("evidence_changed") from exc
        observed, _ = evidence_facts(
            git_binary,
            project,
            project_id,
            mapping,
        )
        if observed != fact_project["evidence"]:
            raise EvidenceChanged("evidence_changed")

    skipped = facts.get("skipped")
    if not isinstance(skipped, dict):
        raise CollectionError("facts_invalid")
    unmatched = len(set(mapping["projects"]) - project_ids)
    if skipped.get("unmatchedProjectEntryCount") != unmatched:
        raise EvidenceChanged("evidence_map_changed")


def atomic_json_write(path: Path, value: dict[str, Any], mode: int = 0o600) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if len(payload) > MAX_FACTS_BYTES:
        raise CollectionError("facts_output_too_large")
    descriptor, temporary_name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects-root", required=True, type=Path)
    parser.add_argument("--evidence-map", required=True, type=Path)
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--facts-output", type=Path)
    output.add_argument(
        "--verify-evidence",
        metavar="FACTS_FILE",
        type=Path,
        help="Re-read mapped evidence without following symlinks and compare it to facts",
    )
    parser.add_argument("--generated-at", help="Fixed timezone-aware time for testing")
    return parser.parse_args()


def main() -> int:
    if not require_supported_python():
        return 2
    args = parse_args()
    try:
        projects_root = validate_projects_root(args.projects_root)
        try:
            evidence_map_path = args.evidence_map.resolve(strict=True)
        except OSError as exc:
            raise CollectionError("evidence_map_unreadable") from exc
        if within(evidence_map_path, projects_root):
            raise CollectionError("evidence_map_inside_projects")
        evidence_map = load_evidence_map(args.evidence_map)
        if args.verify_evidence:
            if args.generated_at:
                raise CollectionError("verification_options_invalid")
            try:
                verification_path = args.verify_evidence.resolve(strict=True)
            except OSError as exc:
                raise CollectionError("facts_unreadable") from exc
            if args.verify_evidence.is_symlink():
                raise CollectionError("facts_symlink")
            if within(verification_path, projects_root):
                raise CollectionError("facts_inside_projects")
            facts = load_facts_for_verification(args.verify_evidence)
            verify_evidence_reads(projects_root, evidence_map, facts)
            print(
                json.dumps(
                    {
                        "status": "verified",
                        "projects": len(facts["projects"]),
                        "sourceDigest": facts["sourceDigest"],
                    },
                    separators=(",", ":"),
                )
            )
            return 0
        if args.facts_output is None:
            raise CollectionError("facts_output_invalid")
        generated_at = utc_timestamp(args.generated_at)
        facts_output = validate_output_path(args.facts_output, projects_root)
        facts, partial = collect(projects_root, evidence_map, generated_at)
        atomic_json_write(facts_output, facts)
        print(
            json.dumps(
                {
                    "status": facts["collectionStatus"],
                    "projects": len(facts["projects"]),
                    "sourceDigest": facts["sourceDigest"],
                },
                separators=(",", ":"),
            )
        )
        return 3 if partial else 0
    except EvidenceChanged as exc:
        print(
            json.dumps({"status": "changed", "reason": exc.code}, separators=(",", ":")),
            file=sys.stderr,
        )
        return 3
    except CollectionError as exc:
        print(
            json.dumps({"status": "failed", "reason": exc.code}, separators=(",", ":")),
            file=sys.stderr,
        )
        return 2
    except (OSError, ValueError, TypeError):
        print(
            json.dumps({"status": "failed", "reason": "unexpected_input"}, separators=(",", ":")),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
