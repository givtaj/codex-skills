from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import validate_repo


SAFE_EMAIL = "12345678+example-validator@users.noreply.github.com"
VALIDATE_REPO_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_repo.py"
IDENTITY_SCRIPT = (
    Path(__file__).resolve().parents[1] / "scripts" / "validate_public_git_identity.py"
)


class GitFixture:
    def __init__(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self._temporary_directory.name)
        self.git("init", "--initial-branch=main")

    def __enter__(self) -> GitFixture:
        return self

    def __exit__(self, *_args: object) -> None:
        self._temporary_directory.cleanup()

    def git_with_environment(
        self,
        environment_updates: dict[str, str],
        *args: str,
    ) -> str:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": "Example Validator",
                "GIT_AUTHOR_EMAIL": SAFE_EMAIL,
                "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
                "GIT_COMMITTER_NAME": "Example Validator",
                "GIT_COMMITTER_EMAIL": SAFE_EMAIL,
                "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
            }
        )
        environment.update(environment_updates)
        result = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", *args],
            cwd=self.path,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def git(self, *args: str) -> str:
        return self.git_with_environment({}, *args)

    def write(self, relative_path: str, content: bytes | str) -> Path:
        path = self.path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            path.write_bytes(content)
        return path

    def commit(self, message: str) -> str:
        self.git("add", "--all")
        self.git("commit", "--message", message)
        return self.git("rev-parse", "HEAD")

    def validate(self) -> None:
        validate_repo.validate_public_content(self.path)


def representative_new_secrets() -> list[tuple[str, str]]:
    return [
        ("GitLab", "gl" + "pat-" + "A" * 20),
        ("npm", "np" + "m_" + "B" * 36),
        ("Stripe", "sk_" + "live_" + "C" * 24),
        (
            "JWT",
            "ey" + "J" + "D" * 8 + "." + "E" * 12 + "." + "F" * 16,
        ),
        ("encrypted PKCS#8", "-----BEGIN " + "ENCRYPTED " + "PRIVATE KEY-----"),
        ("Slack application", "xa" + "pp-1-" + "G" * 24),
    ]


class PublicContentValidationTests(unittest.TestCase):
    def synthetic_merge_fixture(
        self,
        fixture: GitFixture,
        *,
        message: str = "Merge contribution for validation",
    ) -> tuple[str, str, str]:
        fixture.write("README.md", "base\n")
        base_sha = fixture.commit("Create base")
        fixture.git("checkout", "-b", "feature")
        fixture.write("feature.txt", "safe contribution\n")
        head_sha = fixture.commit("Add feature")
        fixture.git("checkout", "main")
        private_email = "merge-bot@" + "platform.internal"
        fixture.git_with_environment(
            {
                "GIT_AUTHOR_EMAIL": private_email,
                "GIT_COMMITTER_EMAIL": private_email,
            },
            "merge",
            "--no-ff",
            "--message",
            message,
            "feature",
        )
        merge_sha = fixture.git("rev-parse", "HEAD")
        fixture.git("checkout", "--detach", merge_sha)
        fixture.git("branch", "--force", "main", base_sha)
        fixture.git(
            "update-ref",
            "refs/validation/origin/heads/main",
            base_sha,
        )
        return merge_sha, base_sha, head_sha

    def synthetic_merge_environment(
        self,
        merge_sha: str,
        base_sha: str,
        head_sha: str,
    ) -> dict[str, str]:
        return {
            validate_repo.SYNTHETIC_MERGE_ENV: merge_sha,
            validate_repo.CONTRIBUTION_BASE_ENV: base_sha,
            validate_repo.CONTRIBUTION_HEAD_ENV: head_sha,
        }

    def assert_rejected_without_echo(self, fixture: GitFixture, secret: str) -> str:
        with self.assertRaises(validate_repo.ValidationError) as caught:
            fixture.validate()
        message = str(caught.exception)
        self.assertNotIn(secret, message)
        return message

    def test_clean_repository_passes(self) -> None:
        with GitFixture() as fixture:
            fixture.write("README.md", "Portable public documentation.\n")
            fixture.commit("Create clean repository")

            fixture.validate()

    def test_verified_unpublished_merge_exempts_only_commit_metadata(self) -> None:
        with GitFixture() as fixture:
            merge_sha, base_sha, head_sha = self.synthetic_merge_fixture(fixture)
            environment = self.synthetic_merge_environment(
                merge_sha,
                base_sha,
                head_sha,
            )

            with mock.patch.dict(os.environ, environment, clear=False):
                fixture.validate()

    def test_unverified_or_published_merge_cannot_claim_the_exception(self) -> None:
        with GitFixture() as fixture:
            merge_sha, base_sha, head_sha = self.synthetic_merge_fixture(fixture)
            environment = self.synthetic_merge_environment(
                merge_sha,
                merge_sha,
                head_sha,
            )
            with mock.patch.dict(os.environ, environment, clear=False):
                with self.assertRaises(validate_repo.ValidationError):
                    fixture.validate()

        with GitFixture() as fixture:
            merge_sha, base_sha, head_sha = self.synthetic_merge_fixture(fixture)
            fixture.git(
                "update-ref",
                "refs/validation/origin/heads/published-merge",
                merge_sha,
            )
            environment = self.synthetic_merge_environment(
                merge_sha,
                base_sha,
                head_sha,
            )
            with mock.patch.dict(os.environ, environment, clear=False):
                with self.assertRaises(validate_repo.ValidationError):
                    fixture.validate()

    def test_merge_exception_does_not_exempt_commit_message(self) -> None:
        secret = "sk_" + "test_" + "Z" * 24
        with GitFixture() as fixture:
            merge_sha, base_sha, head_sha = self.synthetic_merge_fixture(
                fixture,
                message="Accidental " + secret,
            )
            environment = self.synthetic_merge_environment(
                merge_sha,
                base_sha,
                head_sha,
            )
            with mock.patch.dict(os.environ, environment, clear=False):
                message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("commit message", message)

    def test_direct_email_in_ordinary_commit_metadata_is_rejected(self) -> None:
        private_email = "author@" + "privatecorp.dev"
        with GitFixture() as fixture:
            fixture.write("README.md", "safe\n")
            fixture.git("add", "--all")
            fixture.git_with_environment(
                {
                    "GIT_AUTHOR_EMAIL": private_email,
                    "GIT_COMMITTER_EMAIL": private_email,
                },
                "commit",
                "--message",
                "Add safe content",
            )

            with self.assertRaises(validate_repo.ValidationError) as caught:
                fixture.validate()

        self.assertNotIn(private_email, str(caught.exception))
        self.assertIn("commit metadata", str(caught.exception))

    def test_harmless_example_addresses_and_generic_home_paths_pass(self) -> None:
        content = """\
Contact docs@example.com or release-bot@sub.example.org.
Use /home/user/project, /home/example/project, or /home/runner/work.
On Windows, use C:\\Users\\username\\project.
"""
        with GitFixture() as fixture:
            fixture.write("docs/examples.md", content)
            fixture.commit("Add portable examples")

            fixture.validate()

    def test_deleted_from_head_secret_is_rejected_from_history(self) -> None:
        secret = "gl" + "pat-" + "H" * 20
        with GitFixture() as fixture:
            exposed = fixture.write("temporary.txt", secret)
            fixture.commit("Add temporary value")
            exposed.unlink()
            fixture.commit("Remove temporary value")

            message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("Git history blob", message)

    def test_nul_and_non_utf8_blob_does_not_hide_ascii_secret(self) -> None:
        secret = "np" + "m_" + "I" * 36
        payload = b"\xff\x00binary-prefix\x00" + secret.encode("ascii") + b"\x00\xfe"
        with GitFixture() as fixture:
            fixture.write("asset.bin", payload)
            fixture.commit("Add binary fixture")

            message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("npm access token pattern", message)

    def test_utf16_little_and_big_endian_secrets_are_rejected(self) -> None:
        for encoding, prefix in (("utf-16-le", b"\xff"), ("utf-16-be", b"\x01")):
            secret = "gl" + "pat-" + encoding[-2:].upper() * 10
            with self.subTest(encoding=encoding), GitFixture() as fixture:
                fixture.write("credential.bin", prefix + secret.encode(encoding))
                fixture.commit("Add encoded fixture")

                message = self.assert_rejected_without_echo(fixture, secret)

                self.assertIn("GitLab access token pattern", message)

    def test_representative_new_credential_formats_are_rejected(self) -> None:
        for label, secret in representative_new_secrets():
            with self.subTest(label=label), GitFixture() as fixture:
                fixture.write("credential.txt", f"value={secret}\n")
                fixture.commit("Add credential fixture")

                message = self.assert_rejected_without_echo(fixture, secret)

                self.assertIn("pattern", message)

    def test_sensitive_deleted_filename_is_scanned_and_redacted(self) -> None:
        secret = "xa" + "pp-1-" + "J" * 24
        with GitFixture() as fixture:
            exposed = fixture.write(f"archive/{secret}.txt", "safe contents\n")
            fixture.commit("Add temporary filename")
            exposed.unlink()
            fixture.commit("Remove temporary filename")

            message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("Git history filename", message)
        self.assertIn("<redacted-path:", message)

    def test_secret_in_commit_message_is_scanned_without_echo(self) -> None:
        secret = "sk_" + "test_" + "K" * 24
        with GitFixture() as fixture:
            fixture.write("README.md", "safe\n")
            fixture.commit(f"Accidental metadata {secret}")

            message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("commit message", message)

    def test_blob_reachable_only_from_a_tag_is_scanned(self) -> None:
        secret = "wh" + "sec_" + "M" * 24
        with GitFixture() as fixture:
            fixture.write("README.md", "safe\n")
            fixture.commit("Initial commit")
            orphan = fixture.write("orphan.bin", secret)
            blob = fixture.git("hash-object", "-w", str(orphan))
            orphan.unlink()
            fixture.git("update-ref", "refs/tags/orphan-blob", blob)

            message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("Git ref blob", message)

    def test_notes_and_custom_refs_are_scanned(self) -> None:
        cases = ("notes", "custom")
        for ref_kind in cases:
            secret = "wh" + "sec_" + ref_kind.upper() * 8
            with self.subTest(ref_kind=ref_kind), GitFixture() as fixture:
                fixture.write("README.md", "safe\n")
                fixture.commit("Initial commit")
                if ref_kind == "notes":
                    fixture.git(
                        "notes",
                        "--ref=review",
                        "add",
                        "--message",
                        secret,
                        "HEAD",
                    )
                else:
                    orphan = fixture.write("orphan.bin", secret)
                    blob = fixture.git("hash-object", "-w", str(orphan))
                    orphan.unlink()
                    fixture.git("update-ref", "refs/review/orphan", blob)

                message = self.assert_rejected_without_echo(fixture, secret)

                self.assertIn("Git", message)

    def test_malformed_manifest_key_cannot_echo_an_escaped_secret(self) -> None:
        secret = "gl" + "pat-" + "Q" * 20
        escaped_key = "glp" + "\\u0061" + "t-" + "Q" * 20
        marketplace = (
            '{"name":"fixture-marketplace","interface":{"displayName":"Fixture"},'
            f'"plugins":[{{"{escaped_key}":"value"}}]}}'
        )
        with GitFixture() as fixture:
            fixture.write("scripts/validate_repo.py", VALIDATE_REPO_SCRIPT.read_bytes())
            fixture.write("scripts/validate_public_git_identity.py", IDENTITY_SCRIPT.read_bytes())
            fixture.write(".agents/plugins/marketplace.json", marketplace)
            fixture.commit("Add malformed manifest fixture")

            result = subprocess.run(
                [sys.executable, "scripts/validate_repo.py"],
                cwd=fixture.path,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

        combined_output = result.stdout + result.stderr
        self.assertEqual(result.returncode, 1)
        self.assertNotIn(secret, combined_output)
        self.assertIn("<redacted-secret>", result.stderr)
        self.assertIn("unsupported field", result.stderr)

    def test_real_email_and_personal_home_path_are_rejected(self) -> None:
        private_email = "owner@" + "privatecorp.dev"
        private_path = "/home/" + "specific-person/work"
        private_file_uri = "file:///" + "Users/specific-person/work"
        private_windows_path = "C:\\Users\\" + "specific-person\\work"
        cases = [
            ("email", private_email),
            ("path", private_path),
            ("file URI", private_file_uri),
            ("Windows path", private_windows_path),
        ]
        for label, exposure in cases:
            with self.subTest(label=label), GitFixture() as fixture:
                fixture.write("notes.txt", exposure)
                fixture.commit("Add private fixture")

                message = self.assert_rejected_without_echo(fixture, exposure)

                self.assertIn("found", message)

    def test_staged_blob_is_checked_even_if_worktree_was_replaced(self) -> None:
        secret = "gl" + "pat-" + "L" * 20
        with GitFixture() as fixture:
            fixture.write("README.md", "initial\n")
            fixture.commit("Initial commit")
            fixture.write("staged.txt", secret)
            fixture.git("add", "staged.txt")
            fixture.write("staged.txt", "safe worktree replacement\n")

            message = self.assert_rejected_without_echo(fixture, secret)

        self.assertIn("Git index blob", message)

    def test_shallow_clone_requires_full_history(self) -> None:
        with GitFixture() as source:
            source.write("README.md", "first\n")
            source.commit("First commit")
            source.write("README.md", "second\n")
            source.commit("Second commit")
            with tempfile.TemporaryDirectory() as clone_directory:
                shallow_path = Path(clone_directory) / "shallow"
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--quiet",
                        "--depth=1",
                        source.path.as_uri(),
                        str(shallow_path),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )

                with self.assertRaises(validate_repo.ValidationError) as caught:
                    validate_repo.validate_public_content(shallow_path)

        self.assertIn("fetch full history and tags", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
