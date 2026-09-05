from __future__ import annotations

import unittest

from scripts import validate_repo


class CanonicalSkillNameTests(unittest.TestCase):
    def test_accepts_durable_domain_and_standard_names(self) -> None:
        names = [
            "github-repository-guardrails",
            "codex-skill-portability-audit",
            "wcag-2-2-accessibility-audit",
            "iso-8601-date-normalization",
            "oauth2-token-review",
            "python-3-12-migration",
            "world-cup-2026-analysis",
            "gemini-2-mission-archive",
            "latest-game-publisher",
            "o3-air-quality-monitor",
        ]
        for name in names:
            with self.subTest(name=name):
                self.assertEqual(validate_repo.validate_canonical_name(name, "skill"), name)

    def test_rejects_objectively_nonportable_names(self) -> None:
        names = [
            "Status-Review",
            "status--review",
            "a" * 65,
            "example-skill",
            "weekly-review-2026-08-29",
            "weekly-review-2026",
            "august-2026-dashboard",
            "q3-2026-release-helper",
            "issue-72-world-cup-publisher",
            "thread-01a043b0-monitor",
            "01a043b0-34cd-79a2-a1b6-6c8d055cf4d9-review",
            "gpt-5-code-review",
            "claude-sonnet-4-research",
            "gemini-2-5-pro-dashboard",
            "llama-4-evaluator",
            "codex-spark-coordinator",
            "openai-o3-reviewer",
            "o3-mini-reviewer",
            "o3-debug-agent",
            "sol-ultra-project-manager",
        ]
        for name in names:
            with self.subTest(name=name):
                with self.assertRaises(validate_repo.ValidationError):
                    validate_repo.validate_canonical_name(name, "skill")


class CoreSkillLanguageTests(unittest.TestCase):
    def test_accepts_capability_domain_and_runtime_language(self) -> None:
        texts = [
            "Use the available repository capability to inspect GitHub issues.",
            "In Codex, inspect task history when the host exposes it; otherwise ask for the source.",
            "Apply WCAG 2.2 criteria and normalize ISO 8601 timestamps.",
            "Use Python 3.12 or a later compatible runtime.",
            "Select the latest completed World Cup 2026 match.",
            "Archive evidence for the Gemini 2 mission.",
            "Measure O3 concentrations for the air-quality report.",
            "Inspect the control whose accessible name matches the requested action.",
            "Read `references/compatibility.md` when host compatibility matters.",
        ]
        for text in texts:
            with self.subTest(text=text):
                validate_repo.validate_core_skill_language(text, "SKILL.md")

    def test_rejects_model_release_and_host_surface_bindings(self) -> None:
        texts = [
            "Run this only with GPT-5.6 Sol Ultra.",
            "Delegate the review to Claude Sonnet 4.",
            "Use Gemini 2.5 Pro for analysis.",
            "Use Llama 3.1 for the summary.",
            "This workflow requires Codex 0.148.",
            "Ask OpenAI o3 to review the result.",
            "Use o3-mini for the task.",
            "Use o3 for the task.",
            "Use Sol Ultra with maximum reasoning.",
            "Use Luna with max reasoning.",
            "Call window.openai.sendFollowUpMessage().",
            "Call WINDOW.OPENAI.sendFollowUpMessage().",
            "Open codex://threads/THREAD_ID.",
            "Open Codex://threads/THREAD_ID.",
        ]
        for text in texts:
            with self.subTest(text=text):
                with self.assertRaises(validate_repo.ValidationError):
                    validate_repo.validate_core_skill_language(text, "SKILL.md")

    def test_normalizes_unicode_dashes_before_checking_model_releases(self) -> None:
        texts = [
            "Use GPT\N{NON-BREAKING HYPHEN}5.6 for this workflow.",
            "Use GPT\N{MINUS SIGN}5.6 for this workflow.",
            "Use \N{FULLWIDTH LATIN CAPITAL LETTER G}\N{FULLWIDTH LATIN CAPITAL LETTER P}\N{FULLWIDTH LATIN CAPITAL LETTER T}\N{FULLWIDTH HYPHEN-MINUS}\N{FULLWIDTH DIGIT FIVE}.6 for this workflow.",
            "Use G\N{ZERO WIDTH SPACE}PT-5.6 for this workflow.",
        ]
        for text in texts:
            with self.subTest(text=text):
                with self.assertRaises(validate_repo.ValidationError):
                    validate_repo.validate_core_skill_language(text, "SKILL.md")


if __name__ == "__main__":
    unittest.main()
