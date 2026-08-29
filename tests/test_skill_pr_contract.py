from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import validate_skill_pr


ROOT = Path(__file__).resolve().parents[1]
PULL_REQUEST_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
CONTRIBUTING = ROOT / "CONTRIBUTING.md"
CODEOWNERS = ROOT / ".github" / "CODEOWNERS"


def valid_review_body() -> str:
    return """
<!-- skill-contract:global-name:start -->
The name describes the public user goal in standard domain language and has no private context.
<!-- skill-contract:global-name:end -->
- [x] <!-- skill-contract:global-name-attested --> reviewed

<!-- skill-contract:six-month:start -->
The core workflow uses capability terms and routes volatile compatibility details to references.
<!-- skill-contract:six-month:end -->
- [X] <!-- skill-contract:six-month-attested --> reviewed
"""


class SkillPullRequestContractTests(unittest.TestCase):
    def test_requires_review_only_for_skill_contract_changes(self) -> None:
        self.assertTrue(
            validate_skill_pr.changed_paths_require_skill_review(
                ["plugins/example/skills/example/SKILL.md"]
            )
        )
        self.assertTrue(
            validate_skill_pr.changed_paths_require_skill_review(
                ["incubator/example/SKILL.md"]
            )
        )
        self.assertTrue(
            validate_skill_pr.changed_paths_require_skill_review(
                ["plugins/example/skills/example/references/runtime.md"]
            )
        )
        self.assertTrue(
            validate_skill_pr.changed_paths_require_skill_review(["SKILL.md"])
        )
        self.assertTrue(
            validate_skill_pr.changed_paths_require_skill_review(
                ["custom/example/reference.md"], {"custom/example"}
            )
        )
        self.assertFalse(
            validate_skill_pr.changed_paths_require_skill_review(
                ["README.md", "plugins/example/README.md"]
            )
        )

    def test_accepts_complete_rationales_and_attestations(self) -> None:
        validate_skill_pr.validate_skill_review_body(valid_review_body())

    def test_reads_current_pull_request_api_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            payload = Path(temporary_directory) / "pull-request.json"
            payload.write_text(
                json.dumps({"body": valid_review_body(), "head": {}, "base": {}}),
                encoding="utf-8",
            )
            self.assertEqual(
                validate_skill_pr.load_pull_request_body(payload),
                valid_review_body(),
            )

    def test_rejects_missing_or_placeholder_rationales(self) -> None:
        fixtures = [
            "",
            valid_review_body().replace(
                "The name describes the public user goal in standard domain language and has no private context.",
                "<!-- still a placeholder -->",
            ),
            valid_review_body().replace(
                "The core workflow uses capability terms and routes volatile compatibility details to references.",
                "Too short.",
            ),
            valid_review_body().replace(
                "The name describes the public user goal in standard domain language and has no private context.",
                "x" * 80,
            ),
            valid_review_body().replace(
                "The name describes the public user goal in standard domain language and has no private context.",
                "\N{ZERO WIDTH SPACE}" * 80,
            ),
        ]
        for body in fixtures:
            with self.subTest(body=body):
                with self.assertRaises(validate_skill_pr.PullRequestContractError):
                    validate_skill_pr.validate_skill_review_body(body)

    def test_rejects_contract_markers_inside_a_fenced_example(self) -> None:
        body = f"```markdown\n{valid_review_body()}\n```\n"
        with self.assertRaises(validate_skill_pr.PullRequestContractError):
            validate_skill_pr.validate_skill_review_body(body)

    def test_rejects_duplicate_contract_markers(self) -> None:
        body = valid_review_body().replace(
            "<!-- skill-contract:global-name:start -->",
            "<!-- skill-contract:global-name:start -->\n<!-- skill-contract:global-name:start -->",
        )
        with self.assertRaises(validate_skill_pr.PullRequestContractError):
            validate_skill_pr.validate_skill_review_body(body)

    def test_rejects_unchecked_attestations(self) -> None:
        for marker in ("[x]", "[X]"):
            with self.subTest(marker=marker):
                body = valid_review_body().replace(marker, "[ ]", 1)
                with self.assertRaises(validate_skill_pr.PullRequestContractError):
                    validate_skill_pr.validate_skill_review_body(body)

    def test_policy_authorities_retain_semantic_acceptance_markers(self) -> None:
        template = PULL_REQUEST_TEMPLATE.read_text(encoding="utf-8")
        policy = CONTRIBUTING.read_text(encoding="utf-8")
        codeowners = CODEOWNERS.read_text(encoding="utf-8")
        for marker in (
            "skill-contract:global-name:start",
            "skill-contract:global-name-attested",
            "skill-contract:six-month:start",
            "skill-contract:six-month-attested",
            "Maintainer semantic acceptance",
        ):
            self.assertIn(marker, template)
        self.assertIn("Global-name review", policy)
        self.assertIn("Six-month durability review", policy)
        self.assertIn("automation does not prove", policy)
        self.assertIn("separate policy pull request", policy)
        self.assertIn("skill-contribution-contract", policy)
        self.assertIn("**/SKILL.md @givtaj", codeowners)
        self.assertIn("**/skills/** @givtaj", codeowners)
        self.assertIn("/.github/workflows/ @givtaj", codeowners)

    def test_rename_away_from_skill_file_still_requires_review(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            self._git(repository, "init", "-q")
            self._git(repository, "config", "user.name", "GitHub Actions")
            self._git(
                repository,
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )
            skill = repository / "incubator" / "example" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("original\n", encoding="utf-8")
            self._git(repository, "add", ".")
            self._git(repository, "commit", "-q", "-m", "base")
            base = self._git(repository, "rev-parse", "HEAD").stdout.strip()

            skill.rename(skill.with_name("GUIDE.md"))
            self._git(repository, "add", "-A")
            self._git(repository, "commit", "-q", "-m", "rename")
            head = self._git(repository, "rev-parse", "HEAD").stdout.strip()

            paths = self._changed_paths_from(repository, base, head)
            self.assertIn("incubator/example/SKILL.md", paths)
            self.assertTrue(validate_skill_pr.changed_paths_require_skill_review(paths))

            event = repository / "event.json"
            event.write_text(
                json.dumps({"pull_request": {"body": ""}}),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_skill_pr.py"),
                    "--event",
                    str(event),
                    "--base",
                    base,
                    "--head",
                    head,
                ],
                cwd=repository,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("skill contribution contract failed", result.stderr)

    def test_cli_accepts_a_complete_contract_for_a_skill_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            self._git(repository, "init", "-q")
            self._git(repository, "config", "user.name", "GitHub Actions")
            self._git(
                repository,
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )
            skill = repository / "skills" / "example" / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text("original\n", encoding="utf-8")
            self._git(repository, "add", ".")
            self._git(repository, "commit", "-q", "-m", "base")
            base = self._git(repository, "rev-parse", "HEAD").stdout.strip()

            skill.write_text("changed\n", encoding="utf-8")
            self._git(repository, "add", ".")
            self._git(repository, "commit", "-q", "-m", "change")
            head = self._git(repository, "rev-parse", "HEAD").stdout.strip()
            event = repository / "event.json"
            event.write_text(
                json.dumps({"pull_request": {"body": valid_review_body()}}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_skill_pr.py"),
                    "--event",
                    str(event),
                    "--base",
                    base,
                    "--head",
                    head,
                ],
                cwd=repository,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_discovers_support_files_beside_a_standalone_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repository = Path(temporary_directory)
            self._git(repository, "init", "-q")
            self._git(repository, "config", "user.name", "GitHub Actions")
            self._git(
                repository,
                "config",
                "user.email",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )
            skill_root = repository / "custom" / "example"
            skill_root.mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("contract\n", encoding="utf-8")
            reference = skill_root / "reference.md"
            reference.write_text("original\n", encoding="utf-8")
            self._git(repository, "add", ".")
            self._git(repository, "commit", "-q", "-m", "base")
            base = self._git(repository, "rev-parse", "HEAD").stdout.strip()

            reference.write_text("changed\n", encoding="utf-8")
            self._git(repository, "add", ".")
            self._git(repository, "commit", "-q", "-m", "support")
            head = self._git(repository, "rev-parse", "HEAD").stdout.strip()
            event = repository / "event.json"
            event.write_text(
                json.dumps({"pull_request": {"body": ""}}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "validate_skill_pr.py"),
                    "--event",
                    str(event),
                    "--base",
                    base,
                    "--head",
                    head,
                ],
                cwd=repository,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("skill contribution contract failed", result.stderr)

    @staticmethod
    def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    @staticmethod
    def _changed_paths_from(repository: Path, base: str, head: str) -> list[str]:
        result = subprocess.run(
            [
                "git",
                "diff",
                "--no-renames",
                "--name-only",
                "-z",
                f"{base}...{head}",
                "--",
            ],
            cwd=repository,
            check=True,
            stdout=subprocess.PIPE,
        )
        return [part.decode("utf-8") for part in result.stdout.split(b"\0") if part]


if __name__ == "__main__":
    unittest.main()
