from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock

from scripts import validate_repo


class EvaluationResultValidationTests(unittest.TestCase):
    skill_name = "example-skill"
    plugin_version = "1.2.3"
    golden_case_ids = {"direct-case", "edge-case"}

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.plugin_dir = self.root / "plugins" / "example-skill"
        self.results_dir = self.plugin_dir / "evals" / "results"
        self.results_dir.mkdir(parents=True)
        self.root_patch = mock.patch.object(validate_repo, "ROOT", self.root)
        self.root_patch.start()
        self.git("init", "--initial-branch=main")
        (self.root / "README.md").write_text("release fixture\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "--message", "Create release fixture")
        self.candidate_sha = self.git("rev-parse", "HEAD")
        self.git(
            "tag",
            "--annotate",
            "--message",
            "Candidate fixture",
            "example-skill-v1.2.3-rc.1",
        )
        tag_object = self.git(
            "rev-parse",
            "refs/tags/example-skill-v1.2.3-rc.1",
        )
        self.git(
            "update-ref",
            "refs/validation/origin/tags/example-skill-v1.2.3-rc.1",
            tag_object,
        )

    def tearDown(self) -> None:
        self.root_patch.stop()
        self.temporary_directory.cleanup()

    def git(self, *args: str) -> str:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": "Example Validator",
                "GIT_AUTHOR_EMAIL": "12345678+example-validator@users.noreply.github.com",
                "GIT_COMMITTER_NAME": "Example Validator",
                "GIT_COMMITTER_EMAIL": "12345678+example-validator@users.noreply.github.com",
            }
        )
        result = subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "tag.gpgsign=false",
                "-c",
                "core.hooksPath=/dev/null",
                *args,
            ],
            cwd=self.root,
            env=environment,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def valid_result(self) -> dict:
        return {
            "schema_version": 1,
            "skill": self.skill_name,
            "plugin_version": self.plugin_version,
            "date": "2026-08-27",
            "scope": "structural",
            "status": "passed",
            "checks": [
                "repository marketplace validation",
                "skill structure validation",
            ],
            "behavioral_replay": {
                "status": "pending",
                "reason": "Host-level replay remains pending for this preview.",
            },
        }

    def valid_behavioral_result(self) -> dict:
        result = self.valid_result()
        result["scope"] = "behavioral"
        result["behavioral_replay"] = {
            "status": "passed",
            "host": "Codex desktop",
            "case_ids": sorted(self.golden_case_ids),
        }
        return result

    def valid_release_smoke_result(self) -> dict:
        result = self.valid_result()
        result.update(
            {
                "scope": "published-v1.2.2-baseline-and-v1.2.3-candidate-smoke",
                "status": "partial",
                "result_context": "Records the published baseline and candidate smoke separately.",
                "tested_artifact": {
                    "release_state": "published",
                    "plugin_version": "1.2.2",
                    "candidate_ref": "example-skill-v1.2.2",
                    "commit_sha": "a" * 40,
                    "repository_url": "https://example.com/example/repository",
                    "codex_cli_version": None,
                    "note": "The baseline host version was not recorded.",
                },
                "behavioral_replay": {
                    "status": "partial",
                    "passed": ["the skill loaded from the candidate package"],
                    "pending": ["complete replay of every golden case"],
                    "note": "The bounded smoke stopped before full behavioral replay.",
                },
                "public_candidate_verification": {
                    "status": "passed",
                    "plugin_version": self.plugin_version,
                    "candidate_ref": "example-skill-v1.2.3-rc.1",
                    "commit_sha": self.candidate_sha,
                    "repository_url": "https://example.com/example/repository",
                    "codex_cli_version": "0.150.0-alpha.8",
                    "github_actions_run_url": "https://example.com/actions/runs/123",
                    "passed_checks": ["anonymous clone", "candidate validation"],
                    "note": "The immutable public candidate passed its release gate.",
                },
            }
        )
        return result

    def valid_release_structural_result(self) -> dict:
        result = self.valid_result()
        result.update(
            {
                "scope": "public-release-candidate-structural-and-regression",
                "tested_artifact": {
                    "release_state": "public-release-candidate",
                    "plugin_version": self.plugin_version,
                    "candidate_ref": "example-skill-v1.2.3-rc.1",
                    "commit_sha": self.candidate_sha,
                    "repository_url": "https://example.com/example/repository",
                    "note": "Checks passed against an immutable public candidate.",
                },
                "behavioral_replay": {
                    "status": "partial",
                    "result": "2026-08-27-v1.2.3-codex-cli.json",
                },
                "public_candidate_verification": {
                    "status": "passed",
                    "candidate_ref": "example-skill-v1.2.3-rc.1",
                    "commit_sha": self.candidate_sha,
                    "repository_url": "https://example.com/example/repository",
                    "codex_cli_version": "0.150.0-alpha.8",
                    "github_actions_run_url": "https://example.com/actions/runs/123",
                    "note": "The candidate passed its release gate.",
                },
            }
        )
        return result

    def write_result(
        self,
        result: dict,
        filename: str = "2026-08-27-structural.json",
    ) -> Path:
        result_path = self.results_dir / filename
        result_path.write_text(json.dumps(result), encoding="utf-8")
        return result_path

    def validate(
        self,
        result: dict,
        filename: str = "2026-08-27-structural.json",
    ) -> str:
        result_path = self.write_result(result, filename)
        return validate_repo.validate_eval_result(
            result_path,
            self.skill_name,
            self.golden_case_ids,
        )

    def assert_invalid(self, result: dict, filename: str = "2026-08-27-structural.json") -> None:
        with self.assertRaises(validate_repo.ValidationError):
            self.validate(result, filename)

    def write_release_pair(
        self,
        smoke: dict | None = None,
        structural: dict | None = None,
    ) -> None:
        self.write_result(
            smoke or self.valid_release_smoke_result(),
            "2026-08-27-v1.2.3-codex-cli.json",
        )
        self.write_result(
            structural or self.valid_release_structural_result(),
            "2026-08-27-v1.2.3-structural.json",
        )

    def validate_result_set(self) -> None:
        validate_repo.validate_eval_results(
            self.plugin_dir,
            self.skill_name,
            self.plugin_version,
            self.golden_case_ids,
        )

    def test_accepts_current_result_shape(self) -> None:
        self.assertEqual(self.validate(self.valid_result()), self.plugin_version)

    def test_accepts_passed_behavioral_replay_with_full_coverage(self) -> None:
        self.assertEqual(
            self.validate(
                self.valid_behavioral_result(),
                "2026-08-27-behavioral.json",
            ),
            self.plugin_version,
        )

    def test_accepts_partial_behavioral_replay_with_reason(self) -> None:
        result = self.valid_behavioral_result()
        result["status"] = "partial"
        result["behavioral_replay"] = {
            "status": "partial",
            "host": "Codex desktop",
            "case_ids": ["direct-case"],
            "reason": "The edge case could not be replayed.",
        }
        self.assertEqual(
            self.validate(result, "2026-08-27-behavioral.json"),
            self.plugin_version,
        )

    def test_accepts_exact_release_evidence_variants(self) -> None:
        smoke_filename = "2026-08-27-v1.2.3-codex-cli.json"
        self.assertEqual(
            self.validate(self.valid_release_smoke_result(), smoke_filename),
            self.plugin_version,
        )
        self.assertEqual(
            self.validate(
                self.valid_release_structural_result(),
                "2026-08-27-v1.2.3-structural.json",
            ),
            self.plugin_version,
        )

    def test_accepts_release_pair_bound_to_trusted_candidate_tag(self) -> None:
        self.write_release_pair()

        self.validate_result_set()

    def test_rejects_release_pair_with_inconsistent_candidate_identity(self) -> None:
        structural = self.valid_release_structural_result()
        structural["tested_artifact"]["repository_url"] = (
            "https://example.org/another/repository"
        )
        structural["public_candidate_verification"]["repository_url"] = (
            "https://example.org/another/repository"
        )
        self.write_release_pair(structural=structural)

        with self.assertRaises(validate_repo.ValidationError):
            self.validate_result_set()

    def test_rejects_release_pair_with_missing_or_mismatched_tag(self) -> None:
        fixtures = ("missing-ref", "wrong-commit")
        for fixture in fixtures:
            with self.subTest(fixture=fixture):
                for result_path in self.results_dir.glob("*.json"):
                    result_path.unlink()
                smoke = self.valid_release_smoke_result()
                structural = self.valid_release_structural_result()
                if fixture == "missing-ref":
                    for candidate in (
                        smoke["public_candidate_verification"],
                        structural["tested_artifact"],
                        structural["public_candidate_verification"],
                    ):
                        candidate["candidate_ref"] = "example-skill-v1.2.3-rc.404"
                else:
                    for candidate in (
                        smoke["public_candidate_verification"],
                        structural["tested_artifact"],
                        structural["public_candidate_verification"],
                    ):
                        candidate["commit_sha"] = "c" * 40
                self.write_release_pair(smoke=smoke, structural=structural)

                with self.assertRaises(validate_repo.ValidationError):
                    self.validate_result_set()
    def test_rejects_unknown_or_inconsistent_release_evidence(self) -> None:
        unknown_nested_key = self.valid_release_smoke_result()
        unknown_nested_key["tested_artifact"]["unexpected"] = True
        self.assert_invalid(
            unknown_nested_key,
            "2026-08-27-v1.2.3-codex-cli.json",
        )

        mismatched_candidate = self.valid_release_structural_result()
        mismatched_candidate["public_candidate_verification"]["commit_sha"] = "c" * 40
        self.write_result(
            self.valid_release_smoke_result(),
            "2026-08-27-v1.2.3-codex-cli.json",
        )
        self.assert_invalid(
            mismatched_candidate,
            "2026-08-27-v1.2.3-structural.json",
        )

        nonpassing_structural = self.valid_release_structural_result()
        nonpassing_structural["status"] = "partial"
        self.assert_invalid(
            nonpassing_structural,
            "2026-08-27-v1.2.3-structural.json",
        )

    def test_release_smoke_cannot_claim_complete_behavioral_replay(self) -> None:
        result = self.valid_release_smoke_result()
        result["status"] = "passed"
        result["behavioral_replay"]["status"] = "passed"
        self.assert_invalid(result, "2026-08-27-v1.2.3-codex-cli.json")

    def test_accepts_historical_result_alongside_current_result(self) -> None:
        historical = self.valid_behavioral_result()
        historical["plugin_version"] = "1.2.2"
        historical["date"] = "2026-08-26"
        historical["behavioral_replay"]["case_ids"] = [
            "retired-direct-case",
            "retired-edge-case",
        ]
        self.write_result(historical, "2026-08-26-behavioral.json")
        self.write_result(self.valid_result())

        validate_repo.validate_eval_results(
            self.plugin_dir,
            self.skill_name,
            self.plugin_version,
            self.golden_case_ids,
        )

    def test_current_behavioral_result_still_uses_current_golden_cases(self) -> None:
        current = self.valid_behavioral_result()
        current["behavioral_replay"]["case_ids"] = ["retired-direct-case"]
        self.write_result(current, "2026-08-27-behavioral.json")

        with self.assertRaises(validate_repo.ValidationError):
            validate_repo.validate_eval_results(
                self.plugin_dir,
                self.skill_name,
                self.plugin_version,
                self.golden_case_ids,
            )

    def test_rejects_result_set_without_current_plugin_version(self) -> None:
        historical = self.valid_result()
        historical["plugin_version"] = "1.2.2"
        self.write_result(historical)

        with self.assertRaises(validate_repo.ValidationError):
            validate_repo.validate_eval_results(
                self.plugin_dir,
                self.skill_name,
                self.plugin_version,
                self.golden_case_ids,
            )

    def test_rejects_malformed_plugin_version(self) -> None:
        fixtures = [
            "01.2.3",
            "1.2.3-01",
            "\N{FULLWIDTH DIGIT ONE}.2.3",
        ]
        for plugin_version in fixtures:
            with self.subTest(plugin_version=plugin_version):
                result = self.valid_result()
                result["plugin_version"] = plugin_version
                self.assert_invalid(result)

    def test_rejects_filename_date_mismatch_or_invalid_calendar_date(self) -> None:
        mismatched = self.valid_result()
        mismatched["date"] = "2026-08-26"
        self.assert_invalid(mismatched)

        invalid_date = self.valid_result()
        invalid_date["date"] = "2026-02-30"
        self.assert_invalid(invalid_date, "2026-02-30-structural.json")

        self.assert_invalid(
            self.valid_result(),
            "2026-08-27-behavioral.json",
        )

    def test_accepts_filename_suffix_after_date_and_scope(self) -> None:
        self.assertEqual(
            self.validate(
                self.valid_result(),
                "2026-08-27-structural-v1.2.3.json",
            ),
            self.plugin_version,
        )

    def test_rejects_unknown_and_missing_top_level_keys(self) -> None:
        unknown = self.valid_result()
        unknown["unexpected"] = True
        self.assert_invalid(unknown)

        missing = self.valid_result()
        del missing["scope"]
        self.assert_invalid(missing)

    def test_rejects_malformed_checks(self) -> None:
        fixtures = [
            [],
            [" "],
            ["duplicate", " duplicate "],
            ["valid", 3],
        ]
        for checks in fixtures:
            with self.subTest(checks=checks):
                result = self.valid_result()
                result["checks"] = checks
                self.assert_invalid(result)

    def test_rejects_invalid_structural_replay_metadata(self) -> None:
        fixtures = [
            None,
            {},
            {"status": "unsupported"},
            {"status": "pending"},
            {"status": "pending", "reason": " "},
            {"status": "passed", "reason": "Replay was completed."},
            {
                "status": "pending",
                "reason": "Replay remains pending.",
                "host": "Codex desktop",
            },
        ]
        for replay in fixtures:
            with self.subTest(replay=replay):
                result = deepcopy(self.valid_result())
                result["behavioral_replay"] = replay
                self.assert_invalid(result)

    def test_rejects_invalid_behavioral_replay_metadata(self) -> None:
        full_case_ids = sorted(self.golden_case_ids)
        fixtures = [
            {"status": "pending", "host": "Codex desktop", "case_ids": full_case_ids},
            {"status": "passed", "case_ids": full_case_ids},
            {"status": "passed", "host": " ", "case_ids": full_case_ids},
            {"status": "passed", "host": "Codex desktop"},
            {"status": "passed", "host": "Codex desktop", "case_ids": []},
            {
                "status": "passed",
                "host": "Codex desktop",
                "case_ids": ["direct-case", "direct-case"],
            },
            {
                "status": "passed",
                "host": "Codex desktop",
                "case_ids": ["direct-case", "unknown-case"],
            },
            {
                "status": "passed",
                "host": "Codex desktop",
                "case_ids": ["direct-case"],
            },
            {
                "status": "passed",
                "host": "Codex desktop",
                "case_ids": full_case_ids,
                "reason": "Unexpected metadata for a passed replay.",
            },
            {
                "status": "passed",
                "host": "Codex desktop",
                "case_ids": full_case_ids,
                "unknown": "metadata",
            },
        ]
        for replay in fixtures:
            with self.subTest(replay=replay):
                result = self.valid_behavioral_result()
                result["behavioral_replay"] = replay
                self.assert_invalid(result, "2026-08-27-behavioral.json")

    def test_rejects_behavioral_status_mismatch_or_missing_reason(self) -> None:
        status_mismatch = self.valid_behavioral_result()
        status_mismatch["status"] = "partial"
        self.assert_invalid(status_mismatch, "2026-08-27-behavioral.json")

        for replay_status, reason in [("partial", None), ("failed", " ")]:
            with self.subTest(replay_status=replay_status):
                result = self.valid_behavioral_result()
                result["status"] = replay_status
                result["behavioral_replay"] = {
                    "status": replay_status,
                    "host": "Codex desktop",
                    "case_ids": ["direct-case"],
                }
                if reason is not None:
                    result["behavioral_replay"]["reason"] = reason
                self.assert_invalid(result, "2026-08-27-behavioral.json")


if __name__ == "__main__":
    unittest.main()
