#!/usr/bin/env python3
"""Synthetic tests for the Central Projects Tracking helpers."""

from __future__ import annotations

import copy
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
        repository = self.create_repository()
        (repository / "status.txt").write_text("review\n", encoding="utf-8")
        self.run_git(repository, "add", "status.txt")
        self.run_git(
            repository,
            "commit",
            "-q",
            "-m",
            "Review internal.example/path before release",
        )

        facts, partial = self.collect()

        self.assertFalse(partial)
        serialized = json.dumps(facts)
        self.assertNotIn("internal.example", serialized)
        self.assertIsNone(
            facts["projects"][0]["repository"]["lastCommit"]["subject"]
        )
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

    def test_public_text_rejects_punctuated_paths_and_file_uri(self) -> None:
        slash = chr(47)
        unsafe_values = (
            f"Path:{slash}{'ho' + 'me'}{slash}account",
            f"file:{slash}{'et' + 'c'}{slash}settings",
            f"value=({slash}{'va' + 'r'}{slash}records)",
        )
        for value in unsafe_values:
            with self.subTest(value=value):
                self.assertIsNone(collector.safe_public_text(value, 180))

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
        collector.atomic_json_write(previous_path, tampered)
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
