#!/usr/bin/env python3
"""Validate a deterministic Central Projects Tracking local website."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any

import collect_portfolio_facts as collector
import validate_portfolio_snapshot as snapshot_validator
from runtime_support import require_supported_python


SITE_SCHEMA_VERSION = 1
SITE_VERSION = "0.1.0"
MAX_SITE_BYTES = 2 * 1024 * 1024
MAX_FILE_BYTES = 1024 * 1024
REQUIRED_FILES = (
    "index.html",
    "assets/app.css",
    "assets/app.js",
    "data/snapshot.js",
    "site-manifest.json",
)
REQUIRED_DIRECTORIES = ("assets", "data")
TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "site"
AUDITED_TEMPLATE_FILES = {
    "index.html": TEMPLATE_ROOT / "index.html",
    "assets/app.css": TEMPLATE_ROOT / "app.css",
    "assets/app.js": TEMPLATE_ROOT / "app.js",
}
MANIFEST_KEYS = {
    "schemaVersion",
    "siteVersion",
    "generatedAt",
    "sourceDigest",
    "contentDigest",
    "files",
}
MANIFEST_FILE_KEYS = {"path", "sha256", "bytes"}
DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")


class SiteValidationError(RuntimeError):
    pass


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def regular_file(path: Path) -> bool:
    return path.exists() and path.is_file() and not path.is_symlink()


def load_json(path: Path, maximum: int) -> dict[str, Any]:
    if not regular_file(path):
        raise SiteValidationError("regular_file_required")
    try:
        size = path.stat(follow_symlinks=False).st_size
    except OSError as exc:
        raise SiteValidationError("input_unreadable") from exc
    if size > maximum:
        raise SiteValidationError("input_too_large")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SiteValidationError("invalid_json") from exc
    if not isinstance(value, dict):
        raise SiteValidationError("object_required")
    return value


def snapshot_javascript(snapshot: dict[str, Any]) -> bytes:
    payload = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    payload = (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    return ("window.CENTRAL_PROJECTS_SNAPSHOT=" + payload + ";\n").encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def site_file_records(site_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    total = 0
    for relative in REQUIRED_FILES[:-1]:
        path = site_root / relative
        if not regular_file(path):
            raise SiteValidationError("missing_site_file")
        payload = path.read_bytes()
        if len(payload) > MAX_FILE_BYTES:
            raise SiteValidationError("site_file_too_large")
        total += len(payload)
        template = AUDITED_TEMPLATE_FILES.get(relative)
        if template is not None:
            if not regular_file(template) or payload != template.read_bytes():
                raise SiteValidationError("template_mismatch")
        records.append({
            "path": relative,
            "sha256": sha256_bytes(payload),
            "bytes": len(payload),
        })
    if total > MAX_SITE_BYTES:
        raise SiteValidationError("site_too_large")
    return records


def expected_manifest(snapshot: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": SITE_SCHEMA_VERSION,
        "siteVersion": SITE_VERSION,
        "generatedAt": snapshot["generatedAt"],
        "sourceDigest": snapshot["sourceDigest"],
        "contentDigest": snapshot["contentDigest"],
        "files": records,
    }


def validate_site(
    site_root: Path,
    snapshot: dict[str, Any],
    projects_root: Path,
) -> list[str]:
    errors: list[str] = []
    try:
        approved_root = collector.validate_projects_root(projects_root)
    except collector.CollectionError as exc:
        return ["site:projects-root:" + exc.code]

    if site_root.is_symlink():
        return ["site:symlink-root"]
    if not site_root.is_dir():
        return ["site:directory-required"]
    try:
        if stat.S_IMODE(site_root.lstat().st_mode) != 0o700:
            errors.append("site:root-permissions")
    except OSError:
        return ["site:unreadable"]
    if within(site_root, approved_root):
        return ["site:inside-projects-root"]

    actual_files: list[str] = []
    actual_directories: list[str] = []
    entry_count = 0
    try:
        for directory, directory_names, filenames in os.walk(site_root, followlinks=False):
            base = Path(directory)
            relative_base = base.relative_to(site_root)
            if len(relative_base.parts) > 2:
                errors.append("site:directory-depth")
                directory_names[:] = []
                continue
            if base.is_symlink():
                errors.append("site:symlink-entry")
                continue
            for name in directory_names:
                path = base / name
                entry_count += 1
                if entry_count > 16:
                    errors.append("site:entry-limit")
                    directory_names[:] = []
                    break
                if path.is_symlink():
                    errors.append("site:symlink-entry")
                actual_directories.append(path.relative_to(site_root).as_posix())
            for name in filenames:
                path = base / name
                entry_count += 1
                if entry_count > 16:
                    errors.append("site:entry-limit")
                    break
                if path.is_symlink():
                    errors.append("site:symlink-entry")
                actual_files.append(path.relative_to(site_root).as_posix())
    except OSError:
        return ["site:unreadable"]
    if sorted(actual_files) != sorted(REQUIRED_FILES):
        errors.append("site:file-set")
    if sorted(actual_directories) != sorted(REQUIRED_DIRECTORIES):
        errors.append("site:directory-set")
    for relative in REQUIRED_DIRECTORIES:
        path = site_root / relative
        try:
            metadata = path.lstat()
        except OSError:
            continue
        if stat.S_ISDIR(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) != 0o700:
            errors.append("site:directory-permissions")
    for relative in REQUIRED_FILES:
        path = site_root / relative
        try:
            metadata = path.lstat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode) and stat.S_IMODE(metadata.st_mode) != 0o600:
            errors.append("site:file-permissions")

    standalone = getattr(snapshot_validator, "validate_snapshot_document", None)
    if standalone is None:
        errors.append("site:snapshot-validator-unavailable")
    else:
        errors.extend("site:snapshot:" + item for item in standalone(snapshot))

    try:
        records = site_file_records(site_root)
        manifest = load_json(site_root / "site-manifest.json", MAX_FILE_BYTES)
    except SiteValidationError as exc:
        errors.append("site:" + str(exc))
        return sorted(set(errors))

    if set(manifest) != MANIFEST_KEYS:
        errors.append("site:manifest-keys")
    files = manifest.get("files")
    if not isinstance(files, list) or any(
        not isinstance(item, dict) or set(item) != MANIFEST_FILE_KEYS
        for item in files
    ):
        errors.append("site:manifest-files")
    if manifest != expected_manifest(snapshot, records):
        errors.append("site:manifest-content")

    snapshot_script = site_root / "data" / "snapshot.js"
    if regular_file(snapshot_script) and snapshot_script.read_bytes() != snapshot_javascript(snapshot):
        errors.append("site:snapshot-script")

    try:
        index = (site_root / "index.html").read_text(encoding="utf-8")
        app = (site_root / "assets" / "app.js").read_text(encoding="utf-8")
        css = (site_root / "assets" / "app.css").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        errors.append("site:text-unreadable")
        return sorted(set(errors))

    required_index = (
        'href="#main-content"',
        'aria-label="Tracking views"',
        'id="drawer-root"',
        'aria-live="polite"',
        'http-equiv="Content-Security-Policy"',
        "connect-src 'none'",
        'src="data/snapshot.js"',
        'src="assets/app.js"',
    )
    if any(token not in index for token in required_index):
        errors.append("site:index-contract")
    if re.search(r"(?:src|href)=[\"']https?://", index, re.IGNORECASE):
        errors.append("site:external-resource")
    if re.search(r"(?:src|href)=[\"']//", index, re.IGNORECASE):
        errors.append("site:external-resource")

    required_functions = (
        "Brief",
        "Portfolio",
        "Activity",
        "System",
        "Copy prompt",
        "Git change plan",
        "Commits not pushed",
        "Potential commits",
        "document.execCommand(\"copy\")",
        "aria-modal",
        "locally recorded upstream",
    )
    if any(token not in app and token not in index for token in required_functions):
        errors.append("site:function-contract")
    forbidden_runtime = (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "sendBeacon",
        "SharedWorker",
        "new Worker",
        "new Image",
        "window.open",
        ".innerHTML",
        ".outerHTML",
        "insertAdjacentHTML",
    )
    if any(token in app for token in forbidden_runtime):
        errors.append("site:unsafe-runtime")
    if re.search(r"(?i)@import|url\(\s*[\"']?(?:https?:)?//", css):
        errors.append("site:external-style-resource")
    if "prefers-reduced-motion" not in css or "@media (max-width:" not in css:
        errors.append("site:responsive-accessibility")

    root_text = approved_root.as_posix()
    for relative in REQUIRED_FILES:
        path = site_root / relative
        if regular_file(path):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError:
                continue
            if root_text and root_text in text:
                errors.append("site:absolute-root-leak")

    return sorted(set(errors))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_root", type=Path)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--projects-root", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    if not require_supported_python():
        return 2
    args = parse_args()
    try:
        projects_root = collector.validate_projects_root(args.projects_root)
        snapshot_path = snapshot_validator.validate_input_path(
            args.snapshot,
            projects_root,
            require_private_mode=True,
        )
        snapshot = load_json(
            snapshot_path,
            snapshot_validator.MAX_SNAPSHOT_BYTES,
        )
        errors = validate_site(args.site_root, snapshot, projects_root)
    except (
        OSError,
        RuntimeError,
        collector.CollectionError,
        SiteValidationError,
    ) as exc:
        print(json.dumps({"status": "failed", "reason": str(exc)}, separators=(",", ":")), file=sys.stderr)
        return 2
    if errors:
        print(json.dumps({"status": "invalid", "errors": errors}, separators=(",", ":")))
        return 3
    print(json.dumps({"status": "valid", "files": len(REQUIRED_FILES)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
