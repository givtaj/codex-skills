#!/usr/bin/env python3
"""Synthetic tests for the Central Projects Tracking helpers."""

from __future__ import annotations

import copy
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIRECTORY))

import collect_portfolio_facts as collector
import runtime_support
import validate_portfolio_snapshot as snapshot_validator


class PortfolioWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.sandbox = Path(self.temporary_directory.name)
        self.projects_root = self.sandbox / "projects"
        self.private_root = self.sandbox / "private"
        self.projects_root.mkdir()
        self.private_root.mkdir(mode=0o700)
        self.generated_at = (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_git(self, repository: Path, *arguments: str) -> None:
        subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def create_repository(self, name: str = "project-one") -> Path:
        repository = self.projects_root / name
        repository.mkdir()
        self.run_git(repository, "init", "-q")
        self.run_git(repository, "config", "user.name", "Fixture Author")
        fixture_address = "fixture" + chr(64) + "invalid"
        self.run_git(repository, "config", "user.email", fixture_address)
        (repository / "README.md").write_text("Fixture project\n", encoding="utf-8")
        self.run_git(repository, "add", "README.md")
        self.run_git(repository, "commit", "-q", "-m", "Initial fixture")
        return repository

    def evidence_map(
        self,
        *,
        required: bool = False,
        evidence_path: str = "PROJECT_STATUS.md",
    ) -> dict:
        return {
            "schemaVersion": 1,
            "limits": {
                "maxFileBytes": 4096,
                "maxProjectBytes": 8192,
            },
            "default": [
                {
                    "id": "project-status",
                    "path": evidence_path,
                    "required": required,
                }
            ],
            "projects": {},
        }

    def write_evidence_map(self, value: dict) -> Path:
        path = self.private_root / "evidence-map.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def collect(self, mapping: dict | None = None) -> tuple[dict, bool]:
        self.generated_at = collector.utc_timestamp()
        return collector.collect(
            collector.validate_projects_root(self.projects_root),
            mapping or self.evidence_map(),
            self.generated_at,
        )

    def candidate_for(self, facts: dict) -> dict:
        project = facts["projects"][0]
        candidate = {
            "schemaVersion": 2,
            "generatedAt": facts["generatedAt"],
            "sourceDigest": facts["sourceDigest"],
            "contentDigest": None,
            "scopeLabel": "Approved project portfolio",
            "coverage": {
                "currentProjectCount": len(facts["projects"]),
                "completeProjectCount": sum(
                    project["collectionStatus"] == "ok"
                    for project in facts["projects"]
                ),
                "partialProjectCount": sum(
                    project["collectionStatus"] == "partial"
                    for project in facts["projects"]
                ),
                "missingProjectCount": 0,
            },
            "brief": {
                "focusProjectIds": [project["id"]],
                "readyProjectIds": [],
                "decisions": ["Confirm the next evidence-backed milestone."],
                "evidenceGaps": ["Delivery evidence has not been provided."],
            },
            "projects": [
                {
                    "id": project["id"],
                    "name": "Project One",
                    "present": True,
                    "stage": "Unknown",
                    "health": "Unknown",
                    "tone": "neutral",
                    "attention": True,
                    "summary": "Repository facts are available; delivery state is unknown.",
                    "risk": "Missing delivery evidence may hide a release blocker.",
                    "next": "Review the approved status document and record its observation date.",
                    "stack": "Unclassified local repository",
                    "evidence": "Bounded repository facts; delivery evidence missing.",
                    "observedAt": None,
                    "repository": copy.deepcopy(project["repository"]),
                    "lastActivity": {
                        "on": (
                            project["repository"]["lastCommit"]["at"][:10]
                            if project["repository"]["lastCommit"]
                            else None
                        ),
                        "kind": (
                            "commit"
                            if project["repository"]["lastCommit"]
                            else "none"
                        ),
                    },
                }
            ],
            "activity": (
                [
                    {
                        "id": project["id"] + ":" + project["repository"]["lastCommit"]["at"][:10] + ":commit:fixture",
                        "on": project["repository"]["lastCommit"]["at"][:10],
                        "type": "COMMIT",
                        "projectId": project["id"],
                        "note": "A local fixture commit was recorded for validation.",
                    }
                ]
                if project["repository"]["lastCommit"]
                else []
            ),
        }
        candidate["contentDigest"] = snapshot_validator.content_digest(candidate)
        return candidate

    def run_validator(
        self,
        candidate_path: Path,
        facts_path: Path,
        *,
        previous_path: Path | None = None,
        finalize: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPT_DIRECTORY / "validate_portfolio_snapshot.py"),
            str(candidate_path),
            "--projects-root",
            str(self.projects_root),
            "--facts",
            str(facts_path),
        ]
        if previous_path:
            command.extend(["--previous", str(previous_path)])
        if finalize:
            command.append("--finalize")
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_collects_path_free_counts_and_local_upstream_state(self) -> None:
        repository = self.create_repository()
        sensitive_filename = "private-customer-record.txt"
        (repository / sensitive_filename).write_text("changed\n", encoding="utf-8")

        facts, partial = self.collect()

        self.assertFalse(partial)
        repository_facts = facts["projects"][0]["repository"]
        self.assertEqual(repository_facts["state"], "dirty")
        self.assertEqual(repository_facts["untrackedCount"], 1)
        self.assertFalse(repository_facts["hasUpstream"])
        self.assertEqual(repository_facts["ahead"], 0)
        self.assertEqual(repository_facts["behind"], 0)
        self.assertIsInstance(repository_facts["branch"], str)
        self.assertFalse(repository_facts["branchRedacted"])
        self.assertEqual(
            repository_facts["lastCommit"]["subject"],
            "Initial fixture",
        )
        self.assertEqual(repository_facts["outgoing"]["status"], "no-upstream")
        self.assertEqual(
            repository_facts["commitSuggestionKinds"],
            ["review-untracked"],
        )
        self.assertNotIn(sensitive_filename, json.dumps(facts))
        self.assertEqual(snapshot_validator.validate_facts(facts), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_collects_sanitized_locally_recorded_outgoing_commits(self) -> None:
        repository = self.create_repository()
        remote = self.sandbox / "remote.git"
        self.run_git(self.sandbox, "init", "--bare", str(remote))
        self.run_git(repository, "remote", "add", "origin", str(remote))
        self.run_git(repository, "push", "-u", "origin", "HEAD")
        (repository / "status.txt").write_text("ready\n", encoding="utf-8")
        self.run_git(repository, "add", "status.txt")
        self.run_git(repository, "commit", "-q", "-m", "Record reviewed status")

        facts, partial = self.collect()

        self.assertFalse(partial)
        observed = facts["projects"][0]["repository"]
        self.assertTrue(observed["hasUpstream"])
        self.assertEqual(observed["ahead"], 1)
        self.assertEqual(observed["behind"], 0)
        self.assertEqual(observed["outgoing"]["status"], "known")
        self.assertEqual(observed["outgoing"]["count"], 1)
        self.assertFalse(observed["outgoing"]["truncated"])
        self.assertEqual(
            observed["outgoing"]["commits"],
            [
                {
                    "at": observed["lastCommit"]["at"],
                    "subject": "Record reviewed status",
                }
            ],
        )
        self.assertNotIn(str(remote), json.dumps(facts))
        self.assertEqual(snapshot_validator.validate_facts(facts), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_unsafe_commit_subject_is_withheld_from_public_facts(self) -> None:
        unsafe_subjects = (
            "Review internal.example/path before release",
            "Review 192.168." + "001.001 before release",
            "Review 2001:" + "db8::1 before release",
            "Review user" + "@" + "workstation before release",
            "Review db" + ":9 before release",
            "Review \\\\" + "server\\share before release",
            "Review PROD_" + "MODE=release before release",
            "Review refs/" + "heads/private before release",
            "diff --" + "git a/x b/x",
            "Review private" + ".txt before release",
            "Review np" + "m_" + ("a" * 24) + " before release",
        )
        for index, subject in enumerate(unsafe_subjects):
            repository = self.create_repository(f"project-{index:02d}")
            (repository / "status.txt").write_text("review\n", encoding="utf-8")
            self.run_git(repository, "add", "status.txt")
            self.run_git(repository, "commit", "-q", "-m", subject)

        facts, partial = self.collect()

        self.assertFalse(partial)
        for project in facts["projects"]:
            self.assertIsNone(project["repository"]["lastCommit"]["subject"])
        self.assertEqual(snapshot_validator.validate_facts(facts), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_shared_clone_alternates_fail_before_evidence_git_calls(self) -> None:
        source = self.sandbox / "shared-source"
        source.mkdir()
        self.run_git(source, "init", "-q")
        self.run_git(source, "config", "user.name", "Fixture Author")
        fixture_address = "fixture" + chr(64) + "invalid"
        self.run_git(source, "config", "user.email", fixture_address)
        (source / "README.md").write_text("Shared source\n", encoding="utf-8")
        self.run_git(source, "add", "README.md")
        self.run_git(source, "commit", "-q", "-m", "Initial shared source")

        shared = self.projects_root / "shared-project"
        subprocess.run(
            ["git", "clone", "--shared", "-q", str(source), str(shared)],
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with mock.patch.object(
            collector,
            "evidence_facts",
            side_effect=AssertionError("evidence Git calls must not run"),
        ):
            facts, partial = self.collect()

        self.assertTrue(partial)
        project = facts["projects"][0]
        self.assertEqual(project["repository"]["state"], "unavailable")
        self.assertIn("git_alternates_forbidden", project["issues"])
        self.assertIn("evidence_not_checked", project["issues"])
        self.assertEqual(snapshot_validator.validate_facts(facts), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_external_common_dir_and_object_symlink_are_rejected(self) -> None:
        common_repo = self.create_repository("common-dir-project")
        external_common = self.sandbox / "external-common"
        external_common.mkdir()
        relative_common = os.path.relpath(external_common, common_repo / ".git")
        (common_repo / ".git" / "commondir").write_text(
            relative_common + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(collector.CollectionError) as common_error:
            collector.validate_git_metadata(common_repo, self.projects_root)
        self.assertEqual(
            common_error.exception.code,
            "git_common_dir_outside_project",
        )

        symlink_repo = self.create_repository("object-symlink-project")
        objects = symlink_repo / ".git" / "objects"
        external_objects = self.sandbox / "external-objects"
        objects.rename(external_objects)
        objects.symlink_to(external_objects, target_is_directory=True)
        with self.assertRaises(collector.CollectionError) as symlink_error:
            collector.validate_git_metadata(symlink_repo, self.projects_root)
        self.assertEqual(symlink_error.exception.code, "git_metadata_symlink")

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_executable_git_filter_is_rejected_before_any_collection_git_call(self) -> None:
        repository = self.create_repository()
        attributes = repository / ".gitattributes"
        payload = repository / "payload.txt"
        attributes.write_text("payload.txt filter=sentinel\n", encoding="utf-8")
        payload.write_text("initial payload\n", encoding="utf-8")
        self.run_git(repository, "add", ".gitattributes", "payload.txt")
        self.run_git(repository, "commit", "-q", "-m", "Add filtered fixture")

        marker = self.sandbox / "filter-command-ran"
        filter_command = f"touch {marker} && cat"
        self.run_git(
            repository,
            "config",
            "filter.sentinel.clean",
            filter_command,
        )
        payload.write_text("changed payload\n", encoding="utf-8")
        self.run_git(repository, "status", "--porcelain")
        self.assertTrue(marker.exists(), "fixture filter must be executable")
        marker.unlink()

        with mock.patch.object(
            collector,
            "git_call",
            side_effect=AssertionError("collector Git must not run"),
        ):
            facts, partial = self.collect()

        self.assertTrue(partial)
        self.assertFalse(marker.exists())
        project = facts["projects"][0]
        self.assertEqual(project["repository"]["state"], "unavailable")
        self.assertIn("git_filter_config_forbidden", project["issues"])
        self.assertLessEqual(len("git_filter_config_forbidden"), 80)
        self.assertIn("evidence_not_checked", project["issues"])
        self.assertEqual(snapshot_validator.validate_facts(facts), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_source_digest_ignores_generation_time(self) -> None:
        self.create_repository()
        facts_one, _ = self.collect()
        facts_two, _ = collector.collect(
            self.projects_root,
            self.evidence_map(),
            "2000-01-01T00:00:00Z",
        )
        self.assertEqual(facts_one["sourceDigest"], facts_two["sourceDigest"])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_required_evidence_gap_is_partial_and_private(self) -> None:
        self.create_repository()
        evidence_map_path = self.write_evidence_map(self.evidence_map(required=True))
        facts_path = self.private_root / "facts.json"
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "collect_portfolio_facts.py"),
                "--projects-root",
                str(self.projects_root),
                "--evidence-map",
                str(evidence_map_path),
                "--facts-output",
                str(facts_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 3)
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        self.assertEqual(facts["collectionStatus"], "partial")
        self.assertIn("required_evidence_missing", facts["projects"][0]["issues"])
        self.assertEqual(stat.S_IMODE(facts_path.stat().st_mode), 0o600)
        self.assertEqual(list(self.private_root.glob(".facts.*")), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_symlinked_project_and_forbidden_evidence_fail_closed(self) -> None:
        self.create_repository()
        outside = self.sandbox / "outside-project"
        outside.mkdir()
        (self.projects_root / "linked-project").symlink_to(outside, target_is_directory=True)

        facts, partial = self.collect()

        self.assertTrue(partial)
        self.assertEqual(facts["skipped"]["symlinkEntryCount"], 1)
        self.assertTrue(collector.forbidden_evidence_path(".env.local"))
        self.assertTrue(collector.forbidden_evidence_path("logs/output.txt"))
        with self.assertRaises(collector.CollectionError):
            collector.load_evidence_map(
                self.write_evidence_map(
                    self.evidence_map(evidence_path="logs/output.txt")
                )
            )

    def test_rejects_broad_roots_and_outputs_inside_projects(self) -> None:
        with self.assertRaises(collector.CollectionError):
            collector.validate_projects_root(Path(self.projects_root.anchor))
        with self.assertRaises(collector.CollectionError):
            collector.validate_output_path(
                self.projects_root / "facts.json",
                self.projects_root,
            )
        for broad_root in ("/usr", "/usr/local", "/var", "/var/lib", "/opt"):
            with self.subTest(broad_root=broad_root):
                with self.assertRaises(collector.CollectionError):
                    collector.validate_projects_root(Path(broad_root))

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_facts_output_is_new_only_and_cannot_alias_evidence_input(self) -> None:
        self.create_repository()
        existing = self.private_root / "existing-facts.json"
        existing.write_text("preserve me\n", encoding="utf-8")
        with self.assertRaises(collector.CollectionError) as existing_error:
            collector.validate_output_path(existing, self.projects_root)
        self.assertEqual(existing_error.exception.code, "facts_output_exists")

        raced = self.private_root / "raced-facts.json"
        validated = collector.validate_output_path(raced, self.projects_root)
        raced.write_text("preserve race winner\n", encoding="utf-8")
        with self.assertRaises(collector.CollectionError) as race_error:
            collector.atomic_json_write(validated, {"value": "new facts"})
        self.assertEqual(race_error.exception.code, "facts_output_exists")
        self.assertEqual(raced.read_text(encoding="utf-8"), "preserve race winner\n")
        self.assertEqual(list(self.private_root.glob(".facts.*")), [])

        linked = self.private_root / "linked-facts.json"
        linked.symlink_to(existing)
        dangling = self.private_root / "dangling-facts.json"
        dangling.symlink_to(self.private_root / "missing-target.json")
        for path in (linked, dangling):
            with self.subTest(path=path.name):
                with self.assertRaises(collector.CollectionError) as symlink_error:
                    collector.validate_output_path(path, self.projects_root)
                self.assertEqual(symlink_error.exception.code, "facts_output_invalid")
                self.assertTrue(path.is_symlink())
        self.assertEqual(existing.read_text(encoding="utf-8"), "preserve me\n")

        evidence_map_path = self.write_evidence_map(self.evidence_map())
        original_map = evidence_map_path.read_bytes()
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "collect_portfolio_facts.py"),
                "--projects-root",
                str(self.projects_root),
                "--evidence-map",
                str(evidence_map_path),
                "--facts-output",
                str(evidence_map_path),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("facts_output_conflict", process.stderr)
        self.assertEqual(evidence_map_path.read_bytes(), original_map)

        evidence_alias = self.private_root / "evidence-map-alias.json"
        os.link(evidence_map_path, evidence_alias)
        alias_output = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "collect_portfolio_facts.py"),
                "--projects-root",
                str(self.projects_root),
                "--evidence-map",
                str(evidence_map_path),
                "--facts-output",
                str(evidence_alias),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(alias_output.returncode, 2)
        self.assertIn("facts_output_exists", alias_output.stderr)
        self.assertEqual(evidence_map_path.read_bytes(), original_map)

        verification_alias = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "collect_portfolio_facts.py"),
                "--projects-root",
                str(self.projects_root),
                "--evidence-map",
                str(evidence_map_path),
                "--verify-evidence",
                str(evidence_alias),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(verification_alias.returncode, 2)
        self.assertIn("verification_input_conflict", verification_alias.stderr)

        pinned_parent = self.private_root / "pinned-output"
        pinned_parent.mkdir(mode=0o700)
        pinned_output = collector.validate_output_path(
            pinned_parent / "facts.json",
            self.projects_root,
        )
        directory_descriptor = collector.pin_output_parent(pinned_output)
        moved_parent = self.sandbox / "moved-pinned-output"
        pinned_parent.rename(moved_parent)
        pinned_parent.mkdir(mode=0o700)
        try:
            with self.assertRaises(collector.CollectionError) as parent_error:
                collector.atomic_json_write(
                    pinned_output,
                    {"value": "new facts"},
                    directory_descriptor=directory_descriptor,
                )
            self.assertEqual(
                parent_error.exception.code,
                "facts_output_parent_changed",
            )
        finally:
            os.close(directory_descriptor)
        self.assertFalse((pinned_parent / "facts.json").exists())
        self.assertFalse((moved_parent / "facts.json").exists())
        self.assertEqual(list(moved_parent.glob(".facts.*")), [])

        late_parent = self.private_root / "late-pinned-output"
        late_parent.mkdir(mode=0o700)
        late_output = collector.validate_output_path(
            late_parent / "facts.json",
            self.projects_root,
        )
        late_descriptor = collector.pin_output_parent(late_output)
        moved_late_parent = self.sandbox / "moved-late-pinned-output"
        real_link = os.link

        def link_then_swap_parent(*args, **kwargs):
            result = real_link(*args, **kwargs)
            late_parent.rename(moved_late_parent)
            late_parent.mkdir(mode=0o700)
            return result

        try:
            with mock.patch.object(
                collector.os,
                "link",
                side_effect=link_then_swap_parent,
            ):
                with self.assertRaises(collector.CollectionError) as late_error:
                    collector.atomic_json_write(
                        late_output,
                        {"value": "new facts"},
                        directory_descriptor=late_descriptor,
                    )
            self.assertEqual(
                late_error.exception.code,
                "facts_output_parent_changed",
            )
        finally:
            os.close(late_descriptor)
        self.assertFalse((late_parent / "facts.json").exists())
        self.assertFalse((moved_late_parent / "facts.json").exists())
        self.assertEqual(list(moved_late_parent.glob(".facts.*")), [])

    def test_rejects_sensitive_evidence_filename_tokens_and_stems(self) -> None:
        for path in (
            "credentials.json",
            "notes/private-key.md",
            "archive.csv",
            ".npmrc",
            "status-session-backup.txt",
        ):
            with self.subTest(path=path):
                self.assertTrue(collector.forbidden_evidence_path(path))

    def test_evidence_map_lists_are_bounded_before_collection(self) -> None:
        def entries(prefix: str, count: int) -> list[dict]:
            return [
                {
                    "id": f"{prefix}-{index:02d}",
                    "path": f"docs/{prefix}-{index:02d}.md",
                    "required": False,
                }
                for index in range(count)
            ]

        oversized_default = self.evidence_map()
        oversized_default["default"] = entries("default", 65)

        oversized_project = self.evidence_map()
        oversized_project["projects"]["project-one"] = entries("project", 65)

        oversized_merge = self.evidence_map()
        oversized_merge["default"] = entries("default", 33)
        oversized_merge["projects"]["project-one"] = entries("project", 32)

        for name, mapping in (
            ("default", oversized_default),
            ("project", oversized_project),
            ("merged", oversized_merge),
        ):
            with self.subTest(name=name):
                with self.assertRaises(collector.CollectionError) as raised:
                    collector.load_evidence_map(self.write_evidence_map(mapping))
                self.assertEqual(raised.exception.code, "evidence_map_invalid")

        with mock.patch.object(
            collector,
            "git_call",
            side_effect=AssertionError("Git must not run before map bounds pass"),
        ):
            with self.assertRaises(collector.CollectionError) as direct_error:
                collector.collect(
                    self.projects_root,
                    oversized_merge,
                    self.generated_at,
                )
        self.assertEqual(direct_error.exception.code, "evidence_map_invalid")

    def test_git_environment_disables_lazy_fetch(self) -> None:
        self.assertEqual(collector.git_environment()["GIT_NO_LAZY_FETCH"], "1")

    def test_runtime_preflight_is_bounded_and_precedes_argument_parsing(self) -> None:
        error = io.StringIO()
        self.assertFalse(
            runtime_support.require_supported_python((3, 9, 99), error)
        )
        self.assertEqual(
            error.getvalue(),
            '{"status":"failed","reason":"unsupported_python","required":"3.10+"}\n',
        )
        self.assertTrue(runtime_support.require_supported_python((3, 10, 0), error))

        for module in (collector, snapshot_validator):
            with self.subTest(module=module.__name__), mock.patch.object(
                module,
                "require_supported_python",
                return_value=False,
            ), mock.patch.object(
                module,
                "parse_args",
                side_effect=AssertionError("argument parsing must not run"),
            ):
                self.assertEqual(module.main(), 2)

    def test_network_location_shaped_project_ids_are_rejected(self) -> None:
        for value in (
            "api.internal.example.com",
            "api.internal.example.com.",
            "api.internal.example.com-project",
            "x_api.example_backup",
            "192.0.2.1",
            "192.168.001.001",
            "x_192.168.001.001_backup",
            "project.local:8443",
        ):
            with self.subTest(value=value):
                self.assertFalse(collector.valid_project_id(value))
                self.assertTrue(collector.public_text_violation_kinds(value))
        self.assertTrue(collector.valid_project_id("project-one"))

        mapping = self.evidence_map()
        mapping["projects"]["api.internal.example.com"] = []
        with self.assertRaises(collector.CollectionError) as raised:
            collector.load_evidence_map(self.write_evidence_map(mapping))
        self.assertEqual(raised.exception.code, "evidence_map_project")

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_collector_skips_network_location_shaped_repository_names(self) -> None:
        self.create_repository("api.internal.example.com")
        self.create_repository("api.internal.example.com.")
        self.create_repository("api.internal.example.com-project")
        self.create_repository("x_api.example_backup")
        self.create_repository("192.0.2.1")
        self.create_repository("192.168.001.001")
        self.create_repository("x_192.168.001.001_backup")

        facts, partial = self.collect()

        self.assertTrue(partial)
        self.assertEqual(facts["projects"], [])
        self.assertEqual(facts["skipped"]["unsafeNameEntryCount"], 7)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_decorated_network_identifiers_cannot_reach_a_snapshot(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        baseline = self.candidate_for(facts)

        for project_id in (
            "x_api.example_backup",
            "x_192.168.001.001_backup",
        ):
            with self.subTest(project_id=project_id):
                unsafe_facts = copy.deepcopy(facts)
                unsafe_facts["projects"][0]["id"] = project_id
                unsafe_facts["sourceDigest"] = collector.compute_source_digest(
                    unsafe_facts
                )
                facts_errors = snapshot_validator.validate_facts(unsafe_facts)
                self.assertIn("facts:project:0:id", facts_errors)

                unsafe_snapshot = copy.deepcopy(baseline)
                unsafe_snapshot["projects"][0]["id"] = project_id
                unsafe_snapshot["contentDigest"] = snapshot_validator.content_digest(
                    unsafe_snapshot
                )
                snapshot_errors = snapshot_validator.validate_snapshot(
                    unsafe_snapshot,
                    facts,
                )
                self.assertIn("snapshot:project:id", snapshot_errors)
                self.assertIn(
                    "root.projects[0].id:unsafe-string",
                    snapshot_errors,
                )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_activity_ids_must_be_structured_safe_and_record_bound(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        baseline = self.candidate_for(facts)
        activity = baseline["activity"][0]

        unsafe = copy.deepcopy(baseline)
        unsafe["activity"][0]["id"] = "localhost:8443"
        unsafe["contentDigest"] = snapshot_validator.content_digest(unsafe)
        errors = snapshot_validator.validate_snapshot(unsafe, facts)
        self.assertIn("snapshot:activity:0:id", errors)
        self.assertIn("root.activity[0].id:unsafe-string", errors)

        mismatches = (
            (
                "project-other:"
                + activity["on"]
                + ":commit:fixture",
                "snapshot:activity:0:id-project",
            ),
            (
                activity["projectId"] + ":2001-01-01:commit:fixture",
                "snapshot:activity:0:id-date",
            ),
            (
                activity["projectId"]
                + ":"
                + activity["on"]
                + ":evidence:fixture",
                "snapshot:activity:0:id-type",
            ),
        )
        for identifier, expected_error in mismatches:
            with self.subTest(identifier=identifier):
                candidate = copy.deepcopy(baseline)
                candidate["activity"][0]["id"] = identifier
                candidate["contentDigest"] = snapshot_validator.content_digest(
                    candidate
                )
                self.assertIn(
                    expected_error,
                    snapshot_validator.validate_snapshot(candidate, facts),
                )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_current_commit_claims_require_captured_repository_dates(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        candidate = self.candidate_for(facts)
        unsupported_date = "2001-01-01"

        stale_last_activity = copy.deepcopy(candidate)
        stale_last_activity["projects"][0]["lastActivity"] = {
            "on": unsupported_date,
            "kind": "commit",
        }
        stale_last_activity["contentDigest"] = snapshot_validator.content_digest(
            stale_last_activity
        )
        self.assertIn(
            "snapshot:project:project-one:last-activity:commit-evidence",
            snapshot_validator.validate_snapshot(stale_last_activity, facts),
        )

        fabricated_activity = copy.deepcopy(candidate)
        fabricated_activity["activity"][0]["on"] = unsupported_date
        fabricated_activity["activity"][0]["id"] = (
            "project-one:2001-01-01:commit:fixture"
        )
        fabricated_activity["contentDigest"] = snapshot_validator.content_digest(
            fabricated_activity
        )
        self.assertIn(
            "snapshot:activity:0:commit-evidence",
            snapshot_validator.validate_snapshot(fabricated_activity, facts),
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_current_editorial_and_noncommit_claims_require_present_evidence(
        self,
    ) -> None:
        self.create_repository()
        facts, _ = self.collect()
        baseline = self.candidate_for(facts)
        claim_date = facts["generatedAt"][:10]

        editorial_claims = (
            ("stage", "Live", "snapshot:project:project-one:stage-without-evidence"),
            (
                "health",
                "Healthy",
                "snapshot:project:project-one:health-without-evidence",
            ),
            ("tone", "good", "snapshot:project:project-one:tone-without-evidence"),
            (
                "observedAt",
                claim_date,
                "snapshot:project:project-one:observed-at-without-evidence",
            ),
        )
        for field, value, expected_error in editorial_claims:
            with self.subTest(field=field):
                candidate = copy.deepcopy(baseline)
                candidate["projects"][0][field] = value
                candidate["contentDigest"] = snapshot_validator.content_digest(
                    candidate
                )
                self.assertIn(
                    expected_error,
                    snapshot_validator.validate_snapshot(candidate, facts),
                )

        for kind, activity_type in (
            ("evidence", "EVIDENCE"),
            ("build", "BUILD"),
            ("study", "STUDY"),
        ):
            with self.subTest(kind=kind):
                candidate = copy.deepcopy(baseline)
                candidate["projects"][0]["lastActivity"] = {
                    "on": claim_date,
                    "kind": kind,
                }
                candidate["activity"] = [
                    {
                        "id": f"project-one:{claim_date}:{kind}:fixture",
                        "on": claim_date,
                        "type": activity_type,
                        "projectId": "project-one",
                        "note": "An unsupported editorial activity claim was recorded.",
                    }
                ]
                candidate["contentDigest"] = snapshot_validator.content_digest(
                    candidate
                )
                errors = snapshot_validator.validate_snapshot(candidate, facts)
                self.assertIn(
                    "snapshot:project:project-one:last-activity:allowlisted-evidence",
                    errors,
                )
                self.assertIn(
                    "snapshot:activity:0:allowlisted-evidence",
                    errors,
                )

        no_activity = copy.deepcopy(baseline)
        no_activity["projects"][0]["lastActivity"] = {"on": None, "kind": "none"}
        no_activity["activity"] = []
        no_activity["contentDigest"] = snapshot_validator.content_digest(no_activity)
        self.assertEqual(
            snapshot_validator.validate_snapshot(no_activity, facts),
            [],
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_attention_rows_reject_no_risk_and_no_action_sentinels(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        baseline = self.candidate_for(facts)

        for field, value, expected_error in (
            (
                "risk",
                snapshot_validator.NO_RISK_SENTINEL,
                "snapshot:project:project-one:attention-risk",
            ),
            (
                "next",
                snapshot_validator.NO_ACTION_SENTINEL,
                "snapshot:project:project-one:attention-next",
            ),
        ):
            with self.subTest(field=field):
                candidate = copy.deepcopy(baseline)
                candidate["projects"][0][field] = value
                candidate["contentDigest"] = snapshot_validator.content_digest(
                    candidate
                )
                self.assertIn(
                    expected_error,
                    snapshot_validator.validate_snapshot(candidate, facts),
                )

        non_attention = copy.deepcopy(baseline)
        non_attention["projects"][0]["attention"] = False
        non_attention["projects"][0]["risk"] = snapshot_validator.NO_RISK_SENTINEL
        non_attention["projects"][0]["next"] = snapshot_validator.NO_ACTION_SENTINEL
        non_attention["contentDigest"] = snapshot_validator.content_digest(
            non_attention
        )
        self.assertEqual(
            snapshot_validator.validate_snapshot(non_attention, facts),
            [],
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_present_evidence_can_support_reviewed_editorial_activity(self) -> None:
        repository = self.create_repository()
        (repository / "PROJECT_STATUS.md").write_text(
            "Reviewed delivery evidence.\n",
            encoding="utf-8",
        )
        facts, _ = self.collect()
        candidate = self.candidate_for(facts)
        claim_date = facts["generatedAt"][:10]
        project = candidate["projects"][0]
        project["stage"] = "Live"
        project["health"] = "Healthy"
        project["tone"] = "good"
        project["observedAt"] = claim_date
        project["lastActivity"] = {"on": claim_date, "kind": "build"}
        candidate["activity"] = [
            {
                "id": f"project-one:{claim_date}:build:fixture",
                "on": claim_date,
                "type": "BUILD",
                "projectId": "project-one",
                "note": "The allowlisted delivery evidence supports this build record.",
            }
        ]
        candidate["contentDigest"] = snapshot_validator.content_digest(candidate)

        self.assertTrue(snapshot_validator.project_has_present_evidence(facts["projects"][0]))
        self.assertEqual(snapshot_validator.validate_snapshot(candidate, facts), [])

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_unborn_repository_cannot_support_current_commit_claims(self) -> None:
        repository = self.projects_root / "project-one"
        repository.mkdir()
        self.run_git(repository, "init", "-q")
        facts, partial = self.collect()
        self.assertFalse(partial)
        candidate = self.candidate_for(facts)
        claim_date = facts["generatedAt"][:10]
        candidate["projects"][0]["lastActivity"] = {
            "on": claim_date,
            "kind": "commit",
        }
        candidate["activity"] = [
            {
                "id": "project-one:" + claim_date + ":commit:invented",
                "on": claim_date,
                "type": "COMMIT",
                "projectId": "project-one",
                "note": "An unsupported local commit claim was recorded here.",
            }
        ]
        candidate["contentDigest"] = snapshot_validator.content_digest(candidate)

        errors = snapshot_validator.validate_snapshot(candidate, facts)
        self.assertIn(
            "snapshot:project:project-one:last-activity:commit-evidence",
            errors,
        )
        self.assertIn("snapshot:activity:0:commit-evidence", errors)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_previous_snapshot_commit_dates_remain_shape_only(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        previous = self.candidate_for(facts)
        previous["projects"][0]["lastActivity"]["on"] = "2001-01-01"
        previous["activity"][0]["on"] = "2001-01-01"
        previous["activity"][0]["id"] = (
            "project-one:2001-01-01:commit:historical"
        )
        previous["contentDigest"] = snapshot_validator.content_digest(previous)

        self.assertEqual(snapshot_validator.validate_previous_snapshot(previous), [])

    def test_collection_and_final_sanitizers_reject_the_same_sensitive_forms(
        self,
    ) -> None:
        slash = chr(47)
        unsafe_values = (
            f"Path:{slash}{'ho' + 'me'}{slash}account",
            f"file:{slash}{'et' + 'c'}{slash}settings",
            f"value=({slash}{'va' + 'r'}{slash}records)",
            "192.168." + "001.001",
            "2001:" + "db8::1",
            "user" + "@" + "workstation",
            "localhost" + ":8",
            "db" + ":9",
            "\\\\" + "server\\share",
            "PROD_" + "MODE=release",
            "refs/" + "heads/private",
            "diff --" + "git a/x b/x",
            "private" + ".txt",
            "np" + "m_" + ("a" * 24),
        )
        for value in unsafe_values:
            with self.subTest(value=value):
                self.assertIsNone(collector.safe_public_text(value, 180))
                validator = snapshot_validator.Validator()
                snapshot_validator.append_sanitization_errors(
                    validator,
                    {"value": value},
                    "root",
                )
                self.assertIn("root.value:unsafe-string", validator.errors)

        safe = "Review the approved release boundary"
        self.assertEqual(collector.safe_public_text(safe, 180), safe)
        validator = snapshot_validator.Validator()
        snapshot_validator.append_sanitization_errors(
            validator,
            {"value": safe},
            "root",
        )
        self.assertEqual(validator.errors, [])

    def test_rejects_evidence_map_inside_projects_root(self) -> None:
        evidence_map_path = self.projects_root / "evidence-map.json"
        evidence_map_path.write_text(
            json.dumps(self.evidence_map()),
            encoding="utf-8",
        )
        process = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "collect_portfolio_facts.py"),
                "--projects-root",
                str(self.projects_root),
                "--evidence-map",
                str(evidence_map_path),
                "--facts-output",
                str(self.private_root / "facts.json"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("evidence_map_inside_projects", process.stderr)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_evidence_size_limit_is_partial(self) -> None:
        repository = self.create_repository()
        (repository / "PROJECT_STATUS.md").write_text(
            "This evidence is larger than the configured bound.\n",
            encoding="utf-8",
        )
        mapping = self.evidence_map(required=True)
        mapping["limits"] = {
            "maxFileBytes": 8,
            "maxProjectBytes": 16,
        }

        facts, partial = self.collect(mapping)

        self.assertTrue(partial)
        self.assertIn("evidence_too_large", facts["projects"][0]["issues"])
        self.assertIn(
            "required_evidence_missing",
            facts["projects"][0]["issues"],
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_unmatched_evidence_map_project_is_bounded_partial(self) -> None:
        self.create_repository()
        mapping = self.evidence_map()
        mapping["projects"]["not-discovered"] = []

        facts, partial = self.collect(mapping)

        self.assertTrue(partial)
        self.assertEqual(facts["collectionStatus"], "partial")
        self.assertEqual(facts["skipped"]["unmatchedProjectEntryCount"], 1)
        self.assertEqual(snapshot_validator.validate_facts(facts), [])

    def test_git_output_is_killed_at_hard_streaming_limit(self) -> None:
        script = (
            "import os\n"
            "chunk = b'x' * 65536\n"
            "for index in range(18):\n"
            "    os.write(1 if index % 2 == 0 else 2, chunk)\n"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )

        with self.assertRaises(collector.CollectionError) as raised:
            collector.bounded_process_output(process)

        self.assertEqual(raised.exception.code, "git_output_limit")
        self.assertIsNotNone(process.returncode)

    def test_git_timeout_kills_process_group(self) -> None:
        process = subprocess.Popen(
            [sys.executable, "-c", "import time; time.sleep(30)"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        original_timeout = collector.GIT_TIMEOUT_SECONDS
        collector.GIT_TIMEOUT_SECONDS = 0.05
        try:
            with self.assertRaises(collector.CollectionError) as raised:
                collector.bounded_process_output(process)
        finally:
            collector.GIT_TIMEOUT_SECONDS = original_timeout

        self.assertEqual(raised.exception.code, "git_timeout")
        self.assertIsNotNone(process.returncode)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_verified_evidence_detects_mutation_and_symlink_swap(self) -> None:
        repository = self.create_repository()
        evidence = repository / "PROJECT_STATUS.md"
        original = "Approved status evidence.\n"
        evidence.write_text(original, encoding="utf-8")
        mapping = self.evidence_map(required=True)
        mapping_path = self.write_evidence_map(mapping)
        facts, partial = self.collect(mapping)
        self.assertFalse(partial)
        facts_path = self.private_root / "facts.json"
        collector.atomic_json_write(facts_path, facts)

        command = [
            sys.executable,
            str(SCRIPT_DIRECTORY / "collect_portfolio_facts.py"),
            "--projects-root",
            str(self.projects_root),
            "--evidence-map",
            str(mapping_path),
            "--verify-evidence",
            str(facts_path),
        ]
        verified = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)

        facts_path.chmod(0o644)
        public_facts = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(public_facts.returncode, 2)
        self.assertIn("facts_permissions", public_facts.stderr)
        facts_path.chmod(0o600)

        evidence.write_text("Mutated status evidence.\n", encoding="utf-8")
        mutated = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(mutated.returncode, 3)
        self.assertIn("evidence_changed", mutated.stderr)

        evidence.write_text(original, encoding="utf-8")
        outside = self.sandbox / "outside-status.md"
        outside.write_text(original, encoding="utf-8")
        evidence.unlink()
        evidence.symlink_to(outside)
        swapped = subprocess.run(command, check=False, capture_output=True, text=True)
        self.assertEqual(swapped.returncode, 3)
        self.assertIn("evidence_changed", swapped.stderr)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_validates_and_finalizes_exact_snapshot(self) -> None:
        self.create_repository()
        facts, partial = self.collect()
        self.assertFalse(partial)
        candidate = self.candidate_for(facts)
        self.assertEqual(
            snapshot_validator.validate_snapshot(candidate, facts),
            [],
        )

        facts_path = self.private_root / "facts.json"
        candidate_path = self.private_root / "candidate.json"
        collector.atomic_json_write(facts_path, facts)
        unfinalized = copy.deepcopy(candidate)
        unfinalized["contentDigest"] = None
        collector.atomic_json_write(candidate_path, unfinalized)
        process = self.run_validator(
            candidate_path,
            facts_path,
            finalize=True,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        finalized = json.loads(candidate_path.read_text(encoding="utf-8"))
        self.assertEqual(
            finalized["contentDigest"],
            snapshot_validator.content_digest(finalized),
        )
        self.assertEqual(stat.S_IMODE(candidate_path.stat().st_mode), 0o600)
        repeated = self.run_validator(
            candidate_path,
            facts_path,
            finalize=True,
        )
        self.assertEqual(repeated.returncode, 3)
        self.assertIn("content-digest-unfinalized", repeated.stdout)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_snapshot_rejects_sensitive_text_and_tampering(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        candidate = self.candidate_for(facts)
        unsafe = copy.deepcopy(candidate)
        unsafe_value = "sk-" + ("A" * 24)
        unsafe["projects"][0]["summary"] = "Leaked value " + unsafe_value
        unsafe["contentDigest"] = snapshot_validator.content_digest(unsafe)
        errors = snapshot_validator.validate_snapshot(unsafe, facts)
        self.assertTrue(any(error.endswith(":unsafe-string") for error in errors))

        tampered = copy.deepcopy(candidate)
        tampered["projects"][0]["repository"]["changeCount"] += 1
        tampered["contentDigest"] = snapshot_validator.content_digest(tampered)
        errors = snapshot_validator.validate_snapshot(tampered, facts)
        self.assertIn(
            "snapshot:project:project-one:repository-facts",
            errors,
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_snapshot_rejects_markup_network_and_credential_forms(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        candidate = self.candidate_for(facts)
        slash = chr(47)
        unsafe_values = (
            "**Private** release status has not been approved.",
            "Review internal.example/path before making the release decision.",
            r"Review \\server\share before making the release decision.",
            "Review 2001:db8::1 before making the release decision.",
            "Review PROD_TOKEN=value before making the release decision.",
            "Review AKIA" + ("A" * 16) + " before making the release decision.",
            "Review PROJECT_STATUS.md before making the release decision.",
            f"Review {slash}{'tm' + 'p'} before making the release decision.",
            f"Review ~{slash}private before making the release decision.",
            f"Review C:{slash}{'Users'}{slash}private before making the release decision.",
            f"Review Path:{slash}{'ho' + 'me'}{slash}account before making the release decision.",
            f"Review file:{slash}{'et' + 'c'}{slash}settings before making the release decision.",
        )

        for value in unsafe_values:
            with self.subTest(value=value):
                unsafe = copy.deepcopy(candidate)
                unsafe["projects"][0]["summary"] = value
                unsafe["contentDigest"] = snapshot_validator.content_digest(unsafe)
                errors = snapshot_validator.validate_snapshot(unsafe, facts)
                self.assertTrue(
                    any(error.endswith(":unsafe-string") for error in errors),
                    errors,
                )

    def test_snapshot_final_serialization_enforces_exact_byte_limit(self) -> None:
        draft = {"contentDigest": None, "padding": ""}
        base_size = len(snapshot_validator.snapshot_json_bytes(draft))
        draft["padding"] = "x" * (
            snapshot_validator.MAX_SNAPSHOT_BYTES - base_size
        )
        self.assertEqual(
            len(snapshot_validator.snapshot_json_bytes(draft)),
            snapshot_validator.MAX_SNAPSHOT_BYTES,
        )

        finalized = snapshot_validator.prospective_final_snapshot(draft)
        self.assertGreater(
            len(snapshot_validator.snapshot_json_bytes(finalized)),
            snapshot_validator.MAX_SNAPSHOT_BYTES,
        )
        output = self.private_root / "oversized-snapshot.json"
        with self.assertRaisesRegex(ValueError, "snapshot_output_too_large"):
            snapshot_validator.atomic_snapshot_write(output, finalized)
        self.assertFalse(output.exists())

        errors = snapshot_validator.validate_snapshot(
            draft,
            {"generatedAt": self.generated_at, "projects": []},
            allow_unfinalized=True,
        )
        self.assertIn("snapshot:serialized-size", errors)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_previous_snapshot_is_fully_validated_and_supports_no_change(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        previous = self.candidate_for(facts)
        self.assertEqual(snapshot_validator.validate_previous_snapshot(previous), [])
        self.assertEqual(
            snapshot_validator.validate_snapshot(previous, facts, previous),
            [],
        )

        invalid_variants: list[tuple[str, dict, str]] = []
        bad_digest = copy.deepcopy(previous)
        bad_digest["contentDigest"] = "0" * 64
        invalid_variants.append(("digest", bad_digest, "previous:content-digest-mismatch"))

        bad_coverage = copy.deepcopy(previous)
        bad_coverage["coverage"]["currentProjectCount"] = 2
        bad_coverage["contentDigest"] = snapshot_validator.content_digest(bad_coverage)
        invalid_variants.append(("coverage", bad_coverage, "previous:coverage:current"))

        duplicate = copy.deepcopy(previous)
        duplicate["projects"].append(copy.deepcopy(duplicate["projects"][0]))
        duplicate["coverage"]["currentProjectCount"] = 2
        duplicate["coverage"]["completeProjectCount"] = 2
        duplicate["contentDigest"] = snapshot_validator.content_digest(duplicate)
        invalid_variants.append(("unique", duplicate, "previous:project-ids-unique"))

        unsafe = copy.deepcopy(previous)
        unsafe["projects"][0]["summary"] = "**Private** state is not publication safe."
        unsafe["contentDigest"] = snapshot_validator.content_digest(unsafe)
        invalid_variants.append(
            ("sanitize", unsafe, "previous.projects[0].summary:unsafe-string")
        )

        for name, value, expected in invalid_variants:
            with self.subTest(name=name):
                self.assertIn(
                    expected,
                    snapshot_validator.validate_previous_snapshot(value),
                )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_standalone_mode_validates_previous_before_reuse(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        previous_path = self.private_root / "previous.json"
        collector.atomic_json_write(previous_path, self.candidate_for(facts))

        valid = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "validate_portfolio_snapshot.py"),
                str(previous_path),
                "--projects-root",
                str(self.projects_root),
                "--standalone",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)

        tampered = json.loads(previous_path.read_text(encoding="utf-8"))
        tampered["projects"][0]["summary"] = "Tampered after finalization."
        previous_path.write_text(
            json.dumps(tampered, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        invalid = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIRECTORY / "validate_portfolio_snapshot.py"),
                str(previous_path),
                "--projects-root",
                str(self.projects_root),
                "--standalone",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(invalid.returncode, 3)
        self.assertIn("content-digest-mismatch", invalid.stdout)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_previous_missing_project_is_retained(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        previous = self.candidate_for(facts)
        missing = copy.deepcopy(previous["projects"][0])
        missing["id"] = "previous-project"
        missing["name"] = "Previous Project"
        previous["projects"].append(missing)
        previous["coverage"]["currentProjectCount"] = 2
        previous["coverage"]["completeProjectCount"] = 2
        previous["contentDigest"] = snapshot_validator.content_digest(previous)

        candidate = self.candidate_for(facts)
        candidate_missing = copy.deepcopy(missing)
        candidate_missing["present"] = False
        candidate_missing["stage"] = "Unknown"
        candidate_missing["health"] = "Unknown"
        candidate_missing["summary"] = "The previously tracked project was not discovered."
        candidate_missing["risk"] = "Its current location and state are unknown."
        candidate_missing["next"] = "Confirm whether the project moved or left the approved scope."
        candidate_missing["evidence"] = "Not present in the current bounded collection."
        candidate_missing["observedAt"] = None
        candidate_missing["repository"] = snapshot_validator.unavailable_repository()
        candidate["projects"].append(candidate_missing)
        candidate["coverage"]["missingProjectCount"] = 1
        candidate["contentDigest"] = snapshot_validator.content_digest(candidate)

        self.assertEqual(
            snapshot_validator.validate_snapshot(candidate, facts, previous),
            [],
        )

        changed_activity = copy.deepcopy(candidate)
        changed_activity["projects"][1]["lastActivity"] = {
            "on": "2001-01-01",
            "kind": "study",
        }
        changed_activity["contentDigest"] = snapshot_validator.content_digest(
            changed_activity
        )
        self.assertIn(
            "snapshot:project:previous-project:missing-last-activity",
            snapshot_validator.validate_snapshot(changed_activity, facts, previous),
        )

        fresh_observation = copy.deepcopy(candidate)
        fresh_observation["projects"][1]["observedAt"] = facts["generatedAt"][:10]
        fresh_observation["contentDigest"] = snapshot_validator.content_digest(
            fresh_observation
        )
        self.assertIn(
            "snapshot:project:previous-project:missing-observed-at",
            snapshot_validator.validate_snapshot(fresh_observation, facts, previous),
        )
        self.assertIn(
            "previous:project:previous-project:missing-observed-at",
            snapshot_validator.validate_previous_snapshot(fresh_observation),
        )

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_validator_rejects_inputs_inside_projects_and_nonprivate_draft(self) -> None:
        repository = self.create_repository()
        facts, _ = self.collect()
        candidate = self.candidate_for(facts)
        facts_path = self.private_root / "facts.json"
        candidate_path = self.private_root / "candidate.json"
        previous_path = self.private_root / "previous.json"
        collector.atomic_json_write(facts_path, facts)
        collector.atomic_json_write(candidate_path, candidate)
        collector.atomic_json_write(previous_path, candidate)

        bad_mode = self.private_root / "bad-mode.json"
        collector.atomic_json_write(bad_mode, candidate)
        bad_mode.chmod(0o640)
        result = self.run_validator(bad_mode, facts_path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("snapshot_permissions", result.stderr)

        facts_path.chmod(0o644)
        result = self.run_validator(candidate_path, facts_path)
        self.assertEqual(result.returncode, 2)
        self.assertIn("snapshot_permissions", result.stderr)
        facts_path.chmod(0o600)

        inside_candidate = repository / "candidate.json"
        inside_facts = repository / "facts.json"
        inside_previous = repository / "previous.json"
        collector.atomic_json_write(inside_candidate, candidate)
        collector.atomic_json_write(inside_facts, facts)
        collector.atomic_json_write(inside_previous, candidate)

        cases = (
            ("candidate", inside_candidate, facts_path, None),
            ("facts", candidate_path, inside_facts, None),
            ("previous", candidate_path, facts_path, inside_previous),
        )
        for name, selected_candidate, selected_facts, selected_previous in cases:
            with self.subTest(name=name):
                result = self.run_validator(
                    selected_candidate,
                    selected_facts,
                    previous_path=selected_previous,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("input_inside_projects", result.stderr)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_validator_rejects_symlinked_facts_and_previous(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        candidate = self.candidate_for(facts)
        facts_path = self.private_root / "facts.json"
        candidate_path = self.private_root / "candidate.json"
        previous_path = self.private_root / "previous.json"
        collector.atomic_json_write(facts_path, facts)
        collector.atomic_json_write(candidate_path, candidate)
        collector.atomic_json_write(previous_path, candidate)

        linked_facts = self.private_root / "linked-facts.json"
        linked_previous = self.private_root / "linked-previous.json"
        linked_facts.symlink_to(facts_path)
        linked_previous.symlink_to(previous_path)

        cases = (
            ("facts", linked_facts, None),
            ("previous", facts_path, linked_previous),
        )
        for name, selected_facts, selected_previous in cases:
            with self.subTest(name=name):
                result = self.run_validator(
                    candidate_path,
                    selected_facts,
                    previous_path=selected_previous,
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("symlink_input", result.stderr)

    @unittest.skipUnless(shutil.which("git"), "Git is required")
    def test_snapshot_input_symlink_is_rejected(self) -> None:
        self.create_repository()
        facts, _ = self.collect()
        facts_path = self.private_root / "facts.json"
        real_candidate = self.private_root / "real-candidate.json"
        linked_candidate = self.private_root / "linked-candidate.json"
        collector.atomic_json_write(facts_path, facts)
        collector.atomic_json_write(real_candidate, self.candidate_for(facts))
        linked_candidate.symlink_to(real_candidate)

        process = self.run_validator(linked_candidate, facts_path)
        self.assertEqual(process.returncode, 2)
        self.assertIn("symlink_input", process.stderr)


if __name__ == "__main__":
    unittest.main()
