from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class ValidationWorkflowTests(unittest.TestCase):
    def test_fetches_all_published_refs_without_platform_pull_refs(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("git fetch --quiet --force --prune origin", workflow)
        self.assertIn("'+refs/*:refs/validation/origin/*'", workflow)
        self.assertIn("'^refs/pull/*'", workflow)


if __name__ == "__main__":
    unittest.main()
