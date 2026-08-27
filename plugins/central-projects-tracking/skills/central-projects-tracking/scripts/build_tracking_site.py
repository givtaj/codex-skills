#!/usr/bin/env python3
"""Build a complete deterministic local tracking website from a validated snapshot."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any

import collect_portfolio_facts as collector
import validate_portfolio_snapshot as snapshot_validator
import validate_tracking_site as site_validator


TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "assets" / "site"
TEMPLATE_FILES = {
    "index.html": TEMPLATE_ROOT / "index.html",
    "assets/app.css": TEMPLATE_ROOT / "app.css",
    "assets/app.js": TEMPLATE_ROOT / "app.js",
}


class BuildError(RuntimeError):
    pass


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=True))
        return True
    except (OSError, ValueError):
        return False


def validate_input_file(path: Path, maximum: int) -> Path:
    if path.is_symlink():
        raise BuildError("symlink_snapshot")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise BuildError("snapshot_missing") from exc
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise BuildError("snapshot_file_required")
    if stat.S_IMODE(metadata.st_mode) != 0o600:
        raise BuildError("snapshot_permissions")
    if metadata.st_size > maximum:
        raise BuildError("snapshot_too_large")
    return resolved


def validate_output(output: Path, projects_root: Path) -> Path:
    if output.is_symlink():
        raise BuildError("symlink_output")
    if output.exists():
        raise BuildError("output_exists")
    parent = output.parent.resolve(strict=True)
    if not parent.is_dir():
        raise BuildError("output_parent_required")
    candidate = parent / output.name
    if within(candidate, projects_root):
        raise BuildError("output_inside_projects")
    if candidate == parent or candidate.name in {"", ".", ".."}:
        raise BuildError("invalid_output")
    return candidate


def read_snapshot(path: Path) -> dict[str, Any]:
    try:
        value = snapshot_validator.load_json(
            path,
            snapshot_validator.MAX_SNAPSHOT_BYTES,
            require_private_mode=True,
        )
    except (OSError, RuntimeError) as exc:
        raise BuildError("invalid_snapshot_json") from exc
    validate_document = getattr(snapshot_validator, "validate_snapshot_document", None)
    if validate_document is None:
        raise BuildError("snapshot_validator_unavailable")
    errors = validate_document(value)
    if errors:
        raise BuildError("invalid_snapshot:" + errors[0])
    return value


def enforce_private_directory(
    path: Path,
    expected: os.stat_result | None = None,
) -> os.stat_result:
    """Require one stable real directory and force its mode independent of umask."""
    try:
        before = path.lstat()
    except OSError as exc:
        raise BuildError("site_directory_unavailable") from exc
    if stat.S_ISLNK(before.st_mode) or not stat.S_ISDIR(before.st_mode):
        raise BuildError("invalid_site_directory")
    if expected is not None and (
        before.st_dev != expected.st_dev or before.st_ino != expected.st_ino
    ):
        raise BuildError("site_directory_changed")
    try:
        os.chmod(path, 0o700, follow_symlinks=False)
        after = path.lstat()
    except (NotImplementedError, OSError) as exc:
        raise BuildError("site_directory_permissions") from exc
    if (
        stat.S_ISLNK(after.st_mode)
        or not stat.S_ISDIR(after.st_mode)
        or after.st_dev != before.st_dev
        or after.st_ino != before.st_ino
    ):
        raise BuildError("site_directory_changed")
    if stat.S_IMODE(after.st_mode) != 0o700:
        raise BuildError("site_directory_permissions")
    return after


def create_private_directory(path: Path) -> os.stat_result:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise BuildError("site_directory_exists") from exc
    created = path.lstat()
    return enforce_private_directory(path, created)


def private_write(path: Path, payload: bytes) -> None:
    enforce_private_directory(path.parent)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        handle = os.fdopen(descriptor, "wb")
        descriptor = -1
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        if path.exists():
            path.unlink()
        raise


def copy_template(destination: Path) -> None:
    for relative, source in TEMPLATE_FILES.items():
        if source.is_symlink() or not source.is_file():
            raise BuildError("invalid_site_template")
        payload = source.read_bytes()
        if len(payload) > site_validator.MAX_FILE_BYTES:
            raise BuildError("site_template_too_large")
        private_write(destination / relative, payload)


def build_site(snapshot_path: Path, projects_root: Path, output: Path) -> Path:
    approved_root = collector.validate_projects_root(projects_root)
    snapshot_input = validate_input_file(snapshot_path, snapshot_validator.MAX_SNAPSHOT_BYTES)
    if within(snapshot_input, approved_root):
        raise BuildError("snapshot_inside_projects")
    snapshot = read_snapshot(snapshot_input)
    final_output = validate_output(output, approved_root)
    try:
        final_output.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise BuildError("output_exists") from exc
    created = final_output.lstat()
    try:
        enforce_private_directory(final_output, created)
        create_private_directory(final_output / "assets")
        create_private_directory(final_output / "data")
        copy_template(final_output)
        private_write(
            final_output / "data" / "snapshot.js",
            site_validator.snapshot_javascript(snapshot),
        )
        records = site_validator.site_file_records(final_output)
        manifest = site_validator.expected_manifest(snapshot, records)
        private_write(
            final_output / "site-manifest.json",
            (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
        )
        errors = site_validator.validate_site(final_output, snapshot, approved_root)
        if errors:
            raise BuildError("site_validation:" + errors[0])
        return final_output
    except BaseException:
        try:
            current = final_output.lstat()
        except OSError:
            current = None
        if (
            current is not None
            and not stat.S_ISLNK(current.st_mode)
            and current.st_dev == created.st_dev
            and current.st_ino == created.st_ino
        ):
            try:
                os.chmod(final_output, 0o700, follow_symlinks=False)
            except (NotImplementedError, OSError):
                pass
            shutil.rmtree(final_output)
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--projects-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        output = build_site(args.snapshot, args.projects_root, args.output_dir)
    except (BuildError, collector.CollectionError, OSError) as exc:
        reason = exc.code if isinstance(exc, collector.CollectionError) else str(exc)
        print(json.dumps({"status": "failed", "reason": reason}, separators=(",", ":")), file=sys.stderr)
        return 2
    mode = stat.S_IMODE(output.stat(follow_symlinks=False).st_mode)
    print(json.dumps({"status": "built", "output": str(output), "mode": oct(mode)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
