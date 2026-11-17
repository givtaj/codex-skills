import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
SCRIPT = BASE / "skills/skill-sync/scripts/skill_manifest.py"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


manifest = load("current_manifest", SCRIPT)


class GitManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-sync-manifest-")
        self.root = Path(self.temp.name)
        self.a = self.root / "a"
        self.a.mkdir()
        (self.a / "SKILL.md").write_text("---\nname: sample\ndescription: Test sample.\n---\n")
        (self.a / "references").mkdir()
        (self.a / "references/guide.md").write_text("Original\n")
        (self.a / "run.sh").write_text("#!/bin/sh\nexit 0\n")
        (self.a / "run.sh").chmod(0o755)
        self.b = self.root / "b"
        shutil.copytree(self.a, self.b)

    def tearDown(self):
        self.temp.cleanup()

    def digest(self, path, git=True):
        result = manifest.fingerprint(path, git_compatible=git)
        self.assertTrue(result["complete"], result["errors"])
        return result["sha256"]

    def test_inspected_folders_are_unchanged(self):
        def state():
            return {str(p.relative_to(self.a)): (p.stat().st_mode, p.read_bytes())
                    for p in self.a.rglob("*") if p.is_file()}
        before = state()
        self.digest(self.a)
        self.digest(self.a, False)
        self.assertEqual(before, state())

    def test_renamed_file_changes_manifest(self):
        (self.b / "references/guide.md").rename(self.b / "references/renamed.md")
        self.assertNotEqual(self.digest(self.a), self.digest(self.b))

    def test_documented_exclusions_are_reported(self):
        (self.b / ".git").mkdir()
        (self.b / ".git/config").write_text("fixture")
        (self.b / "__pycache__").mkdir()
        (self.b / "__pycache__/cache.pyc").write_bytes(b"fixture")
        (self.b / ".DS_Store").write_bytes(b"fixture")
        (self.b / "cache.pyo").write_bytes(b"fixture")
        self.assertEqual(self.digest(self.a), self.digest(self.b))
        self.assertEqual(manifest.fingerprint(self.b)["excluded"],
                         [".DS_Store", ".git", "__pycache__/", "cache.pyo"])

    def test_invalid_root_and_symlink_skill_are_incomplete(self):
        linked = self.root / "linked"
        linked.symlink_to(self.a, target_is_directory=True)
        (self.b / "SKILL.md").unlink()
        (self.b / "SKILL.md").symlink_to(self.a / "SKILL.md")
        for invalid in (linked, self.b):
            result = manifest.fingerprint(invalid, git_compatible=True)
            self.assertFalse(result["complete"])
            self.assertIsNone(result["sha256"])

    def test_bytecode_suffix_directories_keep_their_payload(self):
        for suffix in (".pyc", ".pyo"):
            with self.subTest(suffix=suffix):
                relative = "assets" + suffix
                for root in (self.a, self.b):
                    (root / relative).mkdir()
                    (root / relative / "required.txt").write_text("same\n")
                for git_mode in (False, True):
                    self.assertEqual(self.digest(self.a, git_mode), self.digest(self.b, git_mode))
                (self.b / relative / "required.txt").write_text("changed\n")
                for git_mode in (False, True):
                    self.assertNotEqual(self.digest(self.a, git_mode), self.digest(self.b, git_mode))
                    result = manifest.fingerprint(self.b, git_compatible=git_mode)
                    self.assertNotIn(relative, result["excluded"])
                    self.assertTrue(any(row["path"] == relative + "/required.txt"
                                        and row["kind"] == "file" for row in result["entries"]))
                (self.b / relative / "required.txt").write_text("same\n")

    def test_bytecode_suffix_symlinks_keep_their_targets(self):
        for suffix in (".pyc", ".pyo"):
            with self.subTest(suffix=suffix):
                relative = "linked" + suffix
                for root in (self.a, self.b):
                    (root / relative).symlink_to("../first-missing-target")
                for git_mode in (False, True):
                    self.assertEqual(self.digest(self.a, git_mode), self.digest(self.b, git_mode))
                (self.b / relative).unlink()
                (self.b / relative).symlink_to("../second-missing-target")
                for git_mode in (False, True):
                    self.assertNotEqual(self.digest(self.a, git_mode), self.digest(self.b, git_mode))
                    result = manifest.fingerprint(self.b, git_compatible=git_mode)
                    self.assertTrue(result["has_symlinks"])
                    self.assertNotIn(relative, result["excluded"])
                    self.assertIn({"path": relative, "kind": "symlink",
                                   "target": "../second-missing-target"}, result["entries"])
                (self.b / relative).unlink()
                (self.b / relative).symlink_to("../first-missing-target")

    def test_regular_bytecode_files_remain_excluded(self):
        for suffix in (".pyc", ".pyo"):
            (self.a / ("cache" + suffix)).write_bytes(b"original-bytecode")
            (self.b / ("cache" + suffix)).write_bytes(b"different-bytecode")
        for git_mode in (False, True):
            with self.subTest(git_mode=git_mode):
                self.assertEqual(self.digest(self.a, git_mode), self.digest(self.b, git_mode))
                result = manifest.fingerprint(self.a, git_compatible=git_mode)
                self.assertEqual(result["excluded"], ["cache.pyc", "cache.pyo"])
                self.assertFalse(any(row["path"] in result["excluded"] for row in result["entries"]))

    def test_unsupported_special_file_is_incomplete(self):
        os.mkfifo(self.b / "pipe")
        result = manifest.fingerprint(self.b)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["sha256"])
        self.assertTrue(any(row["path"] == "pipe" for row in result["errors"]))

    def test_identical_payloads_ignore_folder_location(self):
        self.assertEqual(self.digest(self.a), self.digest(self.b))

    def test_stable_fixture_preserves_v1_hashes(self):
        # Recorded from the original v1 helper using this unchanged fixture.
        self.assertEqual(self.digest(self.a, False),
                         "7d5c7904b993e1ce720a759356683303cabd58026b53eff5d5c9182d8e8e0d03")
        self.assertEqual(self.digest(self.a, True),
                         "fa23c3c83cfe089af7c181ba7abe855bf9afbb6fa9ec8a47805550d8518802c4")

    def test_supporting_file_change_detected(self):
        (self.b / "references/guide.md").write_text("Changed\n")
        self.assertNotEqual(self.digest(self.a), self.digest(self.b))

    def test_execution_status_is_preserved(self):
        (self.b / "run.sh").chmod(0o644)
        self.assertNotEqual(self.digest(self.a), self.digest(self.b))

    def test_permission_normalization_only_in_git_mode(self):
        (self.b / "run.sh").chmod(0o700)
        self.assertEqual(self.digest(self.a), self.digest(self.b))
        self.assertNotEqual(self.digest(self.a, False), self.digest(self.b, False))
        result = manifest.fingerprint(self.b, git_compatible=True)
        self.assertEqual(result["normalized_executable_modes"], [
            {"path": "run.sh", "source_executable_bits": 0o100, "git_executable": True}
        ])

    def test_empty_directories_omitted_only_in_git_mode(self):
        (self.b / "empty/nested").mkdir(parents=True)
        self.assertEqual(self.digest(self.a), self.digest(self.b))
        self.assertNotEqual(self.digest(self.a, False), self.digest(self.b, False))
        result = manifest.fingerprint(self.b, git_compatible=True)
        self.assertEqual(result["omitted_empty_directories"], ["empty", "empty/nested"])
        self.assertFalse(any(entry["kind"] == "directory" for entry in result["entries"]))

    def test_symlink_target_is_preserved_and_not_followed(self):
        (self.a / "outside").symlink_to("/nonexistent/example-a")
        (self.b / "outside").symlink_to("/nonexistent/example-a")
        self.assertEqual(self.digest(self.a), self.digest(self.b))
        result = manifest.fingerprint(self.a, git_compatible=True)
        self.assertTrue(result["has_symlinks"])
        self.assertIn({"path": "outside", "kind": "symlink", "target": "/nonexistent/example-a"}, result["entries"])
        (self.b / "outside").unlink()
        (self.b / "outside").symlink_to("/nonexistent/example-b")
        self.assertNotEqual(self.digest(self.a), self.digest(self.b))

    def test_errors_stay_incomplete_and_cli_signals_failure(self):
        missing = self.root / "missing"
        result = manifest.fingerprint(missing, git_compatible=True)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["sha256"])
        run = subprocess.run([sys.executable, str(SCRIPT), "--git-compatible", str(self.a), str(missing)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        output = json.loads(run.stdout)
        self.assertEqual(output["method"], "sha256-git-payload-v1")
        self.assertTrue(output["skills"][0]["complete"])
        self.assertFalse(output["skills"][1]["complete"])

    def assert_swap_stays_private(self, entry, *, symlink=True, swap_on=1):
        marker = b"outside-fixture-content-must-not-be-read"
        outside = self.root / "outside-fixture"
        is_directory = entry in ("root", "references")
        if is_directory:
            outside.mkdir()
            (outside / "SKILL.md").write_bytes(marker)
            (outside / "outside.txt").write_bytes(marker)
        else:
            outside.write_bytes(marker)
        target = self.a if entry == "root" else self.a / entry
        retained = self.root / "retained-entry"
        original_lstat, original_read = manifest._lstat, os.read
        original_sha256 = manifest.hashlib.sha256
        observed_reads, observed_hashes = [], []
        calls = 0

        def racing_lstat(name, dir_fd=None):
            nonlocal calls
            result = original_lstat(name, dir_fd)
            matches = Path(name) == self.a if entry == "root" else name == entry
            if matches:
                calls += 1
                if calls == swap_on:
                    target.rename(retained)
                    if symlink:
                        target.symlink_to(outside, target_is_directory=is_directory)
                    else:
                        outside.rename(target)
            return result

        def tracked_read(fd, size):
            data = original_read(fd, size)
            observed_reads.append(data)
            return data

        class TrackedHash:
            def __init__(self, data=b""):
                observed_hashes.append(data)
                self.digest = original_sha256(data)

            def update(self, data):
                observed_hashes.append(data)
                self.digest.update(data)

            def hexdigest(self):
                return self.digest.hexdigest()

        with mock.patch.object(manifest, "_lstat", side_effect=racing_lstat), \
                mock.patch.object(manifest.os, "read", side_effect=tracked_read), \
                mock.patch.object(manifest.hashlib, "sha256", TrackedHash):
            result = manifest.fingerprint(self.a)
        self.assertGreaterEqual(calls, swap_on, "Race fixture must actually trigger")
        self.assertFalse(result["complete"], result)
        self.assertIsNone(result["sha256"])
        self.assertNotIn(marker, b"".join(observed_reads))
        self.assertNotIn(marker, b"".join(observed_hashes))
        self.assertFalse(any(row["path"].endswith("outside.txt") for row in result["entries"]))

    def test_root_symlink_swap_before_open_does_not_read_outside(self):
        self.assert_swap_stays_private("root")

    def test_root_directory_replacement_before_open_is_rejected(self):
        self.assert_swap_stays_private("root", symlink=False)

    def test_child_directory_symlink_swap_does_not_read_outside(self):
        self.assert_swap_stays_private("references")

    def test_child_directory_replacement_is_rejected_before_listing(self):
        self.assert_swap_stays_private("references", symlink=False)

    def test_file_symlink_swap_does_not_read_outside(self):
        self.assert_swap_stays_private("run.sh")

    def test_file_replacement_is_rejected_before_payload_read(self):
        self.assert_swap_stays_private("run.sh", symlink=False)

    def test_root_rebound_after_open_stays_anchored(self):
        self.assert_swap_stays_private("root", swap_on=2)

    def test_child_directory_rebound_after_open_stays_anchored(self):
        self.assert_swap_stays_private("references", swap_on=2)

    def test_symlink_replacement_during_readlink_is_incomplete(self):
        link = self.a / "outside-link"
        link.symlink_to("../first-target")
        original_lstat = manifest._lstat
        calls = 0

        def racing_lstat(name, dir_fd=None):
            nonlocal calls
            result = original_lstat(name, dir_fd)
            if name == "outside-link":
                calls += 1
                if calls == 2:
                    link.unlink()
                    link.symlink_to("../second-target")
            return result

        with mock.patch.object(manifest, "_lstat", side_effect=racing_lstat):
            result = manifest.fingerprint(self.a)
        self.assertEqual(calls, 2)
        self.assertFalse(result["complete"])
        self.assertIsNone(result["sha256"])
        self.assertTrue(any("Symlink changed" in row["error"] for row in result["errors"]))

    def test_missing_safe_scan_capability_fails_without_reading(self):
        with mock.patch.object(manifest, "_safe_scan_supported", return_value=False), \
                mock.patch.object(manifest.os, "read") as read:
            result = manifest.fingerprint(self.a)
        read.assert_not_called()
        self.assertFalse(result["complete"])
        self.assertIsNone(result["sha256"])
        self.assertIn("unsupported", result["errors"][0]["error"])

    def test_git_executable_semantics_match_fixture_index(self):
        # The index lives entirely in this temporary test folder; no user repository is changed.
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull)
        subprocess.run(["git", "init", "-q", str(self.root / "index-fixture")], env=env, check=True)
        repo = self.root / "index-fixture"
        path = repo / "probe"
        path.write_text("probe")
        for mode, expected in [(0o700, "100755"), (0o755, "100755"), (0o644, "100644"), (0o610, "100644")]:
            path.chmod(mode)
            subprocess.run(["git", "-c", "core.filemode=true", "-C", str(repo), "add", "probe"], env=env, check=True)
            observed = subprocess.check_output(["git", "-C", str(repo), "ls-files", "--stage", "probe"], env=env, text=True).split()[0]
            self.assertEqual(observed, expected)
            (self.a / "run.sh").chmod(mode)
            entry = next(row for row in manifest.fingerprint(self.a, git_compatible=True)["entries"] if row["path"] == "run.sh")
            self.assertEqual(entry["executable"], expected == "100755")


if __name__ == "__main__":
    unittest.main(verbosity=2)
