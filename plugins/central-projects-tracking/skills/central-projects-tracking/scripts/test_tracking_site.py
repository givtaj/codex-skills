#!/usr/bin/env python3
"""Synthetic tests for the complete local tracking website."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIRECTORY))

import build_tracking_site as builder
import collect_portfolio_facts as collector
import validate_portfolio_snapshot as snapshot_validator
import validate_tracking_site as site_validator


class TrackingSiteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.temporary_directory.name)
        self.projects_root = self.sandbox / "projects"
        self.projects_root.mkdir()
        self.snapshot_path = self.sandbox / "snapshot.json"
        self.output = self.sandbox / "tracking-site"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def snapshot(self) -> dict:
        repository = {
            "state": "dirty",
            "branch": "main",
            "branchRedacted": False,
            "hasUpstream": True,
            "ahead": 1,
            "behind": 0,
            "changeCount": 2,
            "modifiedCount": 1,
            "deletedCount": 0,
            "untrackedCount": 1,
            "conflictedCount": 0,
            "stagedCount": 1,
            "unstagedCount": 1,
            "lastCommit": {"at": "2026-08-26T12:00:00Z", "subject": "Refine portfolio view"},
            "outgoing": {
                "status": "known",
                "count": 1,
                "truncated": False,
                "commits": [{"at": "2026-08-26T12:00:00Z", "subject": "Refine portfolio view"}],
            },
            "commitSuggestionKinds": ["commit-staged", "stage-tracked", "review-untracked"],
        }
        snapshot = {
            "schemaVersion": 2,
            "generatedAt": "2026-08-27T09:30:00Z",
            "sourceDigest": "a" * 64,
            "contentDigest": None,
            "scopeLabel": "Product development portfolio",
            "coverage": {
                "currentProjectCount": 1,
                "completeProjectCount": 1,
                "partialProjectCount": 0,
                "missingProjectCount": 0,
            },
            "brief": {
                "focusProjectIds": ["project-one"],
                "readyProjectIds": ["project-one"],
                "decisions": ["Choose the reviewed release boundary."],
                "evidenceGaps": [],
            },
            "projects": [{
                "id": "project-one",
                "name": "Project One",
                "present": True,
                "stage": "Build",
                "health": "Active",
                "tone": "info",
                "attention": True,
                "summary": "The first bounded implementation slice is under review.",
                "risk": "The release boundary still requires an explicit decision.",
                "next": "Review the current slice and record the accepted release boundary.",
                "stack": "Local application",
                "evidence": "Approved project status and local Git facts",
                "observedAt": "2026-08-26",
                "repository": repository,
                "lastActivity": {"on": "2026-08-26", "kind": "commit"},
            }],
            "activity": [{
                "id": "project-one:2026-08-26:commit:refine",
                "on": "2026-08-26",
                "type": "COMMIT",
                "projectId": "project-one",
                "note": "A bounded portfolio view refinement was recorded.",
            }],
        }
        snapshot["contentDigest"] = snapshot_validator.content_digest(snapshot)
        return snapshot

    def write_snapshot(self, value: dict | None = None) -> dict:
        snapshot = value or self.snapshot()
        collector.atomic_json_write(self.snapshot_path, snapshot)
        return snapshot

    def test_builds_and_validates_complete_offline_site(self) -> None:
        snapshot = self.write_snapshot()
        output = builder.build_site(self.snapshot_path, self.projects_root, self.output)

        self.assertEqual(output, self.output)
        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        for relative in site_validator.REQUIRED_DIRECTORIES:
            self.assertEqual((output / relative).stat().st_mode & 0o777, 0o700)
        for relative in site_validator.REQUIRED_FILES:
            self.assertEqual((output / relative).stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            sorted(path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()),
            sorted(site_validator.REQUIRED_FILES),
        )
        self.assertEqual(site_validator.validate_site(output, snapshot, self.projects_root), [])

        app = (output / "assets" / "app.js").read_text(encoding="utf-8")
        for phrase in (
            "Today’s architect brief",
            "Portfolio ledger",
            "Evidence trail",
            "System / evidence boundary",
            "Git change plan",
            "Copy prompt",
        ):
            self.assertIn(phrase, app)
        for forbidden in ("fetch(", "XMLHttpRequest", ".innerHTML"):
            self.assertNotIn(forbidden, app)
        self.assertIn("trapDrawerFocus", app)
        self.assertIn("node.inert = active", app)
        self.assertIn("dataset.filterId", app)
        index = (output / "index.html").read_text(encoding="utf-8")
        self.assertIn("Content-Security-Policy", index)
        self.assertIn("connect-src 'none'", index)

    def test_builder_enforces_private_modes_independent_of_umask(self) -> None:
        self.write_snapshot()
        previous_umask = os.umask(0o777)
        try:
            output = builder.build_site(
                self.snapshot_path,
                self.projects_root,
                self.output,
            )
        finally:
            os.umask(previous_umask)

        self.assertEqual(output.stat().st_mode & 0o777, 0o700)
        for relative in site_validator.REQUIRED_DIRECTORIES:
            self.assertEqual((output / relative).stat().st_mode & 0o777, 0o700)
        for relative in site_validator.REQUIRED_FILES:
            self.assertEqual((output / relative).stat().st_mode & 0o777, 0o600)

    def test_validator_rejects_nonprivate_artifact_modes(self) -> None:
        snapshot = self.write_snapshot()
        output = builder.build_site(self.snapshot_path, self.projects_root, self.output)
        output.chmod(0o755)
        for relative in site_validator.REQUIRED_DIRECTORIES:
            (output / relative).chmod(0o755)
        for relative in site_validator.REQUIRED_FILES:
            (output / relative).chmod(0o644)

        errors = site_validator.validate_site(output, snapshot, self.projects_root)

        self.assertIn("site:root-permissions", errors)
        self.assertIn("site:directory-permissions", errors)
        self.assertIn("site:file-permissions", errors)

    @unittest.skipUnless(shutil.which("node"), "Node is optional and used only for syntax checking")
    def test_browser_javascript_has_valid_syntax(self) -> None:
        self.write_snapshot()
        output = builder.build_site(self.snapshot_path, self.projects_root, self.output)
        subprocess.run(
            [shutil.which("node") or "node", "--check", str(output / "assets" / "app.js")],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=10,
        )

    def test_manifest_detects_tampering(self) -> None:
        snapshot = self.write_snapshot()
        output = builder.build_site(self.snapshot_path, self.projects_root, self.output)
        with (output / "assets" / "app.css").open("ab") as handle:
            handle.write(b"\n/* changed */\n")
        self.assertIn(
            "site:template_mismatch",
            site_validator.validate_site(output, snapshot, self.projects_root),
        )

    def test_rejects_extra_directory_even_when_file_set_is_unchanged(self) -> None:
        snapshot = self.write_snapshot()
        output = builder.build_site(
            self.snapshot_path,
            self.projects_root,
            self.output,
        )
        (output / "unexpected").mkdir()
        self.assertIn(
            "site:directory-set",
            site_validator.validate_site(output, snapshot, self.projects_root),
        )

    def test_rejects_output_or_snapshot_inside_projects_root(self) -> None:
        self.write_snapshot()
        with self.assertRaises(builder.BuildError):
            builder.build_site(self.snapshot_path, self.projects_root, self.projects_root / "site")
        inside = self.projects_root / "snapshot.json"
        collector.atomic_json_write(inside, self.snapshot())
        with self.assertRaises(builder.BuildError):
            builder.build_site(inside, self.projects_root, self.output)

    def test_standalone_validator_rejects_snapshot_inside_projects(self) -> None:
        inside = self.projects_root / "snapshot.json"
        collector.atomic_json_write(inside, self.snapshot())
        site_root = self.sandbox / "site"
        self.write_snapshot()
        builder.build_site(self.snapshot_path, self.projects_root, site_root)
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "validate_tracking_site.py"),
                str(site_root),
                "--snapshot",
                str(inside),
                "--projects-root",
                str(self.projects_root),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("input_inside_projects", process.stderr)

    def test_refuses_to_overwrite_an_existing_output(self) -> None:
        self.write_snapshot()
        self.output.mkdir()
        with self.assertRaises(builder.BuildError):
            builder.build_site(self.snapshot_path, self.projects_root, self.output)

    def test_builder_rejects_nonprivate_snapshot_permissions(self) -> None:
        self.write_snapshot()
        self.snapshot_path.chmod(0o644)
        with self.assertRaisesRegex(builder.BuildError, "snapshot_permissions"):
            builder.build_site(
                self.snapshot_path,
                self.projects_root,
                self.output,
            )

    def test_failed_build_removes_only_its_reserved_output(self) -> None:
        self.write_snapshot()
        original = builder.TEMPLATE_FILES
        builder.TEMPLATE_FILES = {
            "index.html": self.sandbox / "missing-template.html"
        }
        try:
            with self.assertRaises(builder.BuildError):
                builder.build_site(
                    self.snapshot_path,
                    self.projects_root,
                    self.output,
                )
        finally:
            builder.TEMPLATE_FILES = original
        self.assertFalse(self.output.exists())

    def test_snapshot_script_escapes_script_breakout_characters(self) -> None:
        payload = site_validator.snapshot_javascript({"value": "</script>&\u2028"}).decode("utf-8")
        self.assertNotIn("</script>", payload)
        self.assertNotIn("&", payload)
        self.assertIn("\\u003c", payload)
        self.assertIn("\\u2028", payload)

    def test_invalid_snapshot_never_creates_output(self) -> None:
        invalid = self.snapshot()
        invalid["projects"][0]["summary"] = "Contact private" + chr(64) + "example.test"
        invalid["contentDigest"] = snapshot_validator.content_digest(invalid)
        self.write_snapshot(invalid)
        with self.assertRaises(builder.BuildError):
            builder.build_site(self.snapshot_path, self.projects_root, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
