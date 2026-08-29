from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidationWorkflowTests(unittest.TestCase):
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
