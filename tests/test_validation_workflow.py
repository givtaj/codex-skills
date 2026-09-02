from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
SKILL_CONTRACT_WORKFLOW = ROOT / ".github" / "workflows" / "skill-contract.yml"
WORKFLOW_DIRECTORY = ROOT / ".github" / "workflows"


class ValidationWorkflowTests(unittest.TestCase):
    def test_pull_requests_run_repository_validator(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("python3 scripts/validate_repo.py", workflow)

    def test_skill_contract_uses_trusted_main_policy_and_rechecks_body_edits(self) -> None:
        workflow = SKILL_CONTRACT_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("pull_request_target:", workflow)
        for event_type in ("opened", "synchronize", "reopened", "edited"):
            self.assertIn(f"      - {event_type}\n", workflow)
        self.assertIn("    branches:\n      - main", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("statuses: write", workflow)
        self.assertIn(
            "permissions:\n  contents: read\n  pull-requests: read\n  statuses: write\n\nconcurrency:",
            workflow,
        )
        self.assertIn("group: skill-contract-${{ github.event.pull_request.number }}", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("/pulls/${CONTRIBUTION_PR_NUMBER}", workflow)
        self.assertIn("test \"${current_base_sha}\" = \"${CONTRIBUTION_BASE_SHA}\"", workflow)
        self.assertIn("test \"${current_head_sha}\" = \"${CONTRIBUTION_HEAD_SHA}\"", workflow)
        self.assertNotIn('--event "${GITHUB_EVENT_PATH}"', workflow)
        self.assertIn("refs/pull/${CONTRIBUTION_PR_NUMBER}/head", workflow)
        self.assertIn("python3 scripts/validate_skill_pr.py", workflow)
        self.assertEqual(workflow.count("uses: actions/checkout@"), 1)
        self.assertEqual(workflow.count("python3 scripts/validate_skill_pr.py"), 1)
        self.assertEqual(workflow.count('"context":"skill-contribution-contract"'), 3)
        for state in ("pending", "success", "failure"):
            self.assertIn(f'"state":"{state}"', workflow)
        self.assertNotIn("continue-on-error", workflow)
        self.assertNotIn("github.event.pull_request.head.repo", workflow)
        self.assertNotIn("ref: ${{ github.event.pull_request.head", workflow)
        for forbidden_command in (
            "git checkout",
            "git switch",
            "git reset",
            "git worktree",
        ):
            self.assertNotIn(forbidden_command, workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)

    def test_only_trusted_contract_workflow_can_publish_contract_status(self) -> None:
        workflow_paths = list(WORKFLOW_DIRECTORY.glob("*.yml")) + list(
            WORKFLOW_DIRECTORY.glob("*.yaml")
        )
        for path in workflow_paths:
            if path == SKILL_CONTRACT_WORKFLOW:
                continue
            workflow = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("statuses: write", workflow)
                self.assertNotIn('"context":"skill-contribution-contract"', workflow)

    def test_validates_the_default_pull_request_merge_checkout(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("github.event.pull_request.head.sha || github.sha", workflow)
        self.assertIn("VALIDATION_SYNTHETIC_MERGE_SHA: ${{ github.sha }}", workflow)
        self.assertIn(
            "VALIDATION_CONTRIBUTION_BASE_SHA: ${{ github.event.pull_request.base.sha }}",
            workflow,
        )
        self.assertIn(
            "VALIDATION_CONTRIBUTION_HEAD_SHA: ${{ github.event.pull_request.head.sha }}",
            workflow,
        )

    def test_fetches_all_published_refs_without_platform_pull_refs(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("git fetch --quiet --force --prune origin", workflow)
        self.assertIn("'+refs/*:refs/validation/origin/*'", workflow)
        self.assertIn("'^refs/pull/*'", workflow)


if __name__ == "__main__":
    unittest.main()
