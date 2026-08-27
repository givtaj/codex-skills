from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = (
    ROOT
    / "plugins"
    / "github-repository-guardrails"
    / "skills"
    / "github-repository-guardrails"
)
WORKFLOW = (
    SKILL_ROOT
    / "assets"
    / "guardrails"
    / "ci"
    / ".github"
    / "workflows"
    / "guardrails-audit.yml"
)
AGENTS_TEMPLATE = SKILL_ROOT / "assets" / "guardrails" / "core" / "AGENTS.md"

LOCAL_SURFACE_PATHS = {
    "intent": "docs/prompts.md",
    "tasks": "TASKS.md",
    "outcomes": "CHANGELOG.md",
    "planning": "PLAN.md",
    "status": "PROJECT_STATUS.md",
    "issues": ".github/ISSUE_TEMPLATE/work-item.yml",
    "review": ".github/pull_request_template.md",
    "ci": ".github/workflows/guardrails-audit.yml",
}


def workflow_script() -> str:
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    marker = "        run: |"
    start = lines.index(marker) + 1
    body: list[str] = []
    for line in lines[start:]:
        if not line:
            body.append("")
        elif line.startswith("          "):
            body.append(line[10:])
        else:
            break
    return "\n".join(body) + "\n"


def run_audit(
    surfaces: str,
    *,
    present_paths: tuple[str, ...] = (),
    project_authority: str = "discover",
) -> subprocess.CompletedProcess[str]:
    with TemporaryDirectory() as temporary_directory:
        repository = Path(temporary_directory)
        (repository / "AGENTS.md").write_text(
            AGENTS_TEMPLATE.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        config = repository / ".github" / "repository-guardrails.conf"
        config.parent.mkdir(parents=True)
        config.write_text(
            "\n".join(
                (
                    "schema_version=1",
                    "repository=self",
                    f"project_authority={project_authority}",
                    f"surfaces={surfaces}",
                    "strictness=advisory",
                    "",
                )
            ),
            encoding="utf-8",
        )
        for relative_path in present_paths:
            target = repository / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("guardrail fixture\n", encoding="utf-8")

        return subprocess.run(
            ["bash", "-s"],
            cwd=repository,
            input=workflow_script(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )


class GuardrailAuditWorkflowTests(unittest.TestCase):
    def test_unselected_local_surfaces_remain_optional(self) -> None:
        result = run_audit("core")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_each_selected_local_surface_requires_its_authority_file(self) -> None:
        for surface, relative_path in LOCAL_SURFACE_PATHS.items():
            with self.subTest(surface=surface):
                missing = run_audit(f"core,{surface}")
                present = run_audit(
                    f"core,{surface}",
                    present_paths=(relative_path,),
                )

                self.assertNotEqual(missing.returncode, 0)
                self.assertIn(relative_path, missing.stderr)
                self.assertEqual(present.returncode, 0, present.stderr)

    def test_tasks_and_review_require_both_selected_files(self) -> None:
        tasks_only = run_audit(
            "core,tasks,review",
            present_paths=(LOCAL_SURFACE_PATHS["tasks"],),
        )
        complete = run_audit(
            "core,tasks,review",
            present_paths=(
                LOCAL_SURFACE_PATHS["tasks"],
                LOCAL_SURFACE_PATHS["review"],
            ),
        )

        self.assertNotEqual(tasks_only.returncode, 0)
        self.assertIn(LOCAL_SURFACE_PATHS["review"], tasks_only.stderr)
        self.assertEqual(complete.returncode, 0, complete.stderr)

    def test_projects_is_external_but_cannot_be_selected_when_disabled(self) -> None:
        discover = run_audit("core,projects")
        disabled = run_audit("core,projects", project_authority="disabled")

        self.assertEqual(discover.returncode, 0, discover.stderr)
        self.assertNotEqual(disabled.returncode, 0)
        self.assertIn("cannot be selected", disabled.stderr)


if __name__ == "__main__":
    unittest.main()
