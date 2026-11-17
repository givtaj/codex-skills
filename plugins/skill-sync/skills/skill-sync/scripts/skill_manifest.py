#!/usr/bin/env python3
"""Read-only skill manifests; safe descriptor filesystem APIs required (stdlib only)."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat


SKIP_DIRS = {".git", "__pycache__"}
SKIP_FILES = {".DS_Store"}


def _safe_scan_supported():
    return (
        all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK"))
        and os.open in os.supports_dir_fd
        and os.stat in os.supports_dir_fd
        and os.stat in os.supports_follow_symlinks
        and os.readlink in os.supports_dir_fd
        and os.listdir in os.supports_fd
    )


def _lstat(name, dir_fd=None):
    return os.stat(name, dir_fd=dir_fd, follow_symlinks=False)


def _fields(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _unchanged(before, *observations):
    if any(_fields(before) != _fields(after) for after in observations):
        raise ValueError("Entry changed while scanning; take a fresh manifest")


@contextmanager
def _open_verified(name, parent_fd, before, *, directory=False):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    if directory:
        flags |= os.O_DIRECTORY
    descriptor = os.open(name, flags, dir_fd=parent_fd)
    try:
        # Verify the opened object BEFORE listing it or reading any payload.
        _unchanged(before, os.fstat(descriptor), _lstat(name, parent_fd))
        yield descriptor
        # The descriptor stays anchored if a path is rebound during traversal.
        _unchanged(before, os.fstat(descriptor), _lstat(name, parent_fd))
    finally:
        os.close(descriptor)


def fingerprint(folder, git_compatible=False):
    root = Path(folder).expanduser().absolute()
    records, excluded, errors = [], [], []

    def visit(directory_fd, prefix=""):
        try:
            children = sorted(os.listdir(directory_fd))
        except (OSError, NotImplementedError) as exc:
            errors.append({"path": prefix or str(root), "error": str(exc)})
            return
        for name in children:
            relative = prefix + name
            try:
                before = _lstat(name, directory_fd)
                bytecode_file = stat.S_ISREG(before.st_mode) and Path(name).suffix in {".pyc", ".pyo"}
                if name == ".git" or name in SKIP_FILES or bytecode_file:
                    excluded.append(relative)
                    continue
                if stat.S_ISLNK(before.st_mode):
                    target = os.readlink(name, dir_fd=directory_fd)
                    _unchanged(before, _lstat(name, directory_fd))
                    if target != os.readlink(name, dir_fd=directory_fd):
                        raise ValueError("Symlink changed while scanning; take a fresh manifest")
                    _unchanged(before, _lstat(name, directory_fd))
                    records.append({"path": relative, "kind": "symlink", "target": target})
                elif stat.S_ISDIR(before.st_mode):
                    if name in SKIP_DIRS:
                        excluded.append(relative + "/")
                        continue
                    with _open_verified(name, directory_fd, before, directory=True) as child_fd:
                        records.append({"path": relative, "kind": "directory"})
                        visit(child_fd, relative + "/")
                elif stat.S_ISREG(before.st_mode):
                    digest = hashlib.sha256()
                    with _open_verified(name, directory_fd, before) as file_fd:
                        for chunk in iter(lambda: os.read(file_fd, 1024 * 1024), b""):
                            digest.update(chunk)
                    records.append({"path": relative, "kind": "file", "size": before.st_size,
                                    "executable_bits": before.st_mode & 0o111,
                                    "sha256": digest.hexdigest()})
                else:
                    raise ValueError("Unsupported special file; inspect before copying")
            except (OSError, ValueError, NotImplementedError) as exc:
                errors.append({"path": relative, "error": str(exc)})
        try:
            if sorted(os.listdir(directory_fd)) != children:
                errors.append({"path": prefix or str(root), "error": "Directory changed while reading; take a fresh manifest"})
        except (OSError, NotImplementedError) as exc:
            errors.append({"path": prefix or str(root), "error": str(exc)})

    try:
        if not _safe_scan_supported():
            raise ValueError("Safe scanning requires no-follow opens and descriptor-relative filesystem APIs; this host is unsupported")
        before = _lstat(root)
        if not stat.S_ISDIR(before.st_mode):
            raise ValueError("Expected a real directory; resolve symlink roots explicitly")
        with _open_verified(root, None, before, directory=True) as root_fd:
            if not stat.S_ISREG(_lstat("SKILL.md", root_fd).st_mode):
                raise ValueError("A regular SKILL.md is required")
            visit(root_fd)
    except (OSError, ValueError, NotImplementedError) as exc:
        errors.append({"path": str(root), "error": str(exc)})
    records.sort(key=lambda row: row["path"])
    representation = {}
    if git_compatible:
        payload = [row for row in records if row["kind"] != "directory"]
        payload_paths = [row["path"] for row in payload]
        representation = {
            "omitted_empty_directories": [
                row["path"] for row in records if row["kind"] == "directory"
                and not any(path.startswith(row["path"] + "/") for path in payload_paths)
            ],
            "mode_normalization": (
                "Git records only owner-executable versus non-executable for regular files; "
                "exact permission bits and directory-only entries are not represented."
            ),
            "normalized_executable_modes": [],
        }
        for row in payload:
            if row["kind"] == "file":
                executable_bits = row.pop("executable_bits")
                row["executable"] = bool(executable_bits & stat.S_IXUSR)
                git_bits = 0o111 if row["executable"] else 0
                if executable_bits != git_bits:
                    representation["normalized_executable_modes"].append({
                        "path": row["path"], "source_executable_bits": executable_bits,
                        "git_executable": row["executable"],
                    })
        records = payload
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return {"folder": str(root), "complete": not errors,
            "sha256": hashlib.sha256(encoded).hexdigest() if not errors else None,
            "has_symlinks": any(r["kind"] == "symlink" for r in records),
            "entries": records, "excluded": sorted(excluded), "errors": errors,
            **representation}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-compatible", action="store_true",
                        help="Compare Git payloads: omit directory entries and normalize executable mode")
    parser.add_argument("folders", nargs="+", help="Explicit skill folders, not broad project roots")
    args = parser.parse_args()
    results = [fingerprint(folder, git_compatible=args.git_compatible) for folder in args.folders]
    method = "sha256-git-payload-v1" if args.git_compatible else "sha256-canonical-entries-v1"
    print(json.dumps({"schema_version": 1, "method": method, "skills": results}, indent=2))
    return 0 if all(row["complete"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
