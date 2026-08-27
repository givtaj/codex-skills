from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_public_git_identity.py"
GOOD_EMAIL = "12345678+example-user@users.noreply.github.com"


class GitFixture:
    def __init__(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self._temporary_directory.name)
        self.git("init", "--initial-branch=main")

    def close(self) -> None:
        self._temporary_directory.cleanup()

    def git(
        self,
        *args: str,
        name: str = "Example User",
        email: str = GOOD_EMAIL,
    ) -> str:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": name,
                "GIT_AUTHOR_EMAIL": email,
                "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
                "GIT_COMMITTER_NAME": name,
                "GIT_COMMITTER_EMAIL": email,
                "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
            }
        )
        result = subprocess.run(
            ["git", *args],
            cwd=self.path,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def commit(self, message: str, email: str = GOOD_EMAIL) -> str:
        self.git("commit", "--allow-empty", "--message", message, email=email)
        return self.git("rev-parse", "HEAD")

    def validate(self, *args: str) -> subprocess.CompletedProcess[str]:
        return validate_at(self.path, *args)


def validate_at(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=path,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


class PublicGitIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = GitFixture()

    def tearDown(self) -> None:
        self.repo.close()

    def test_accepts_github_system_human_and_bot_noreply_addresses(self) -> None:
        accepted = [
            "noreply@github.com",
            GOOD_EMAIL,
            "41898282+github-actions[bot]@users.noreply.github.com",
            "dependabot[bot]@users.noreply.github.com",
        ]
        for index, email in enumerate(accepted):
            self.repo.commit(f"accepted {index}", email=email)

        result = self.repo.validate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 non-legacy commit(s)", result.stdout)

    def test_rejects_a_direct_personal_email(self) -> None:
        self.repo.commit("private identity", email="person@example.com")

        result = self.repo.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn("must use a GitHub-provided noreply address", result.stderr)

    def test_default_walk_reaches_a_non_head_remote_ref(self) -> None:
        self.repo.commit("public main")
        self.repo.git("switch", "--orphan", "topic")
        private_commit = self.repo.commit("private remote", email="person@example.com")
        self.repo.git("switch", "main")
        self.repo.git("update-ref", "refs/remotes/origin/topic", private_commit)
        self.repo.git("branch", "--delete", "--force", "topic")

        result = self.repo.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn(private_commit[:12], result.stderr)

    def test_explicit_range_can_exclude_a_synthetic_merge_commit(self) -> None:
        base = self.repo.commit("base")
        self.repo.git("switch", "--create", "feature")
        feature = self.repo.commit("contribution")
        self.repo.git("switch", "main")
        self.repo.git(
            "merge",
            "--no-ff",
            "feature",
            "--message",
            "synthetic pull request merge",
            email="person@example.com",
        )

        default_result = self.repo.validate()
        contribution_result = self.repo.validate(
            "--commit-range", f"{base}..{feature}", "--skip-tags"
        )

        self.assertEqual(default_result.returncode, 1)
        self.assertEqual(contribution_result.returncode, 0, contribution_result.stderr)
        self.assertIn("1 non-legacy commit(s)", contribution_result.stdout)

    def test_default_mode_rejects_shallow_history_but_a_range_is_allowed(self) -> None:
        self.repo.commit("older")
        self.repo.commit("tip")
        with tempfile.TemporaryDirectory() as clone_directory:
            shallow_path = Path(clone_directory) / "shallow"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--depth=1",
                    self.repo.path.as_uri(),
                    str(shallow_path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            default_result = validate_at(shallow_path)
            range_result = validate_at(
                shallow_path, "--commit-range", "HEAD", "--skip-tags"
            )

        self.assertEqual(default_result.returncode, 1)
        self.assertIn("requires a complete Git history", default_result.stderr)
        self.assertEqual(range_result.returncode, 0, range_result.stderr)
        self.assertIn("1 non-legacy commit(s)", range_result.stdout)

    def test_legacy_tag_name_does_not_exempt_a_new_tag_object(self) -> None:
        self.repo.commit("public commit")
        self.repo.git(
            "tag",
            "--annotate",
            "status-review-dashboard-v0.1.0",
            "--message",
            "new object under legacy name",
            email="person@example.com",
        )

        result = self.repo.validate()

        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "annotated tag status-review-dashboard-v0.1.0 tagger", result.stderr
        )

    def test_non_commit_tag_is_checked_without_becoming_a_revision_root(self) -> None:
        self.repo.commit("public commit")
        blob_path = self.repo.path / "release-note.txt"
        blob_path.write_text("release evidence\n", encoding="utf-8")
        blob = self.repo.git("hash-object", "-w", str(blob_path))
        self.repo.git(
            "tag",
            "--annotate",
            "evidence-v1",
            blob,
            "--message",
            "tag a non-commit object",
        )

        result = self.repo.validate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 non-legacy commit(s)", result.stdout)
        self.assertIn("1 non-legacy annotated tag(s)", result.stdout)

    def test_legacy_exemptions_are_immutable_object_ids(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")

        self.assertIn("85d7b564961bcbbc7f47325f8df18fd5ab49b4fb", source)
        self.assertNotIn("LEGACY_TAG_EXEMPTIONS", source)


if __name__ == "__main__":
    unittest.main()
