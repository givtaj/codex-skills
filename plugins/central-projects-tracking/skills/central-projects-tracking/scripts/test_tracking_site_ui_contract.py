#!/usr/bin/env python3
"""Static contract tests for the bundled tracking-site interface."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent.parent
APP = (SKILL_ROOT / "assets" / "site" / "app.js").read_text(encoding="utf-8")
CSS = (SKILL_ROOT / "assets" / "site" / "app.css").read_text(encoding="utf-8")


def relative_luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(left: str, right: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(left), relative_luminance(right)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


class TrackingSiteUiContractTests(unittest.TestCase):
    def test_brief_renders_decisions_gaps_and_empty_states(self) -> None:
        for token in (
            "snapshot.brief.decisions",
            "snapshot.brief.evidenceGaps",
            "Decisions to make",
            "Evidence gaps",
            "No explicit decisions are waiting in this snapshot.",
            "No consequential evidence gaps were recorded for this snapshot.",
            'aria-label", "Portfolio decisions and evidence gaps',
        ):
            self.assertIn(token, APP)

    def test_faint_text_meets_normal_text_contrast_on_site_surfaces(self) -> None:
        faint_match = re.search(r"--faint:\s*(#[0-9a-fA-F]{6})", CSS)
        self.assertIsNotNone(faint_match)
        faint = faint_match.group(1)
        for background in ("#11171b", "#171f24", "#1d272d"):
            self.assertGreaterEqual(contrast(faint, background), 4.5)

    def test_navigation_honors_motion_and_compact_layout_preferences(self) -> None:
        self.assertIn('window.matchMedia("(prefers-reduced-motion: reduce)").matches', APP)
        self.assertIn('behavior: reduceMotion ? "auto" : "smooth"', APP)
        self.assertIn(
            ".primary-nav { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); overflow: visible; }",
            CSS,
        )
        self.assertIn(
            ".primary-nav button { min-width: 0; min-height: 60px;",
            CSS,
        )

    def test_ready_actions_use_button_valid_phrasing_content(self) -> None:
        ready_actions = APP.split("const horizon =", 1)[1].split(
            "function renderPortfolio", 1
        )[0]
        self.assertIn('element("span", "move-title", project.name)', ready_actions)
        self.assertIn('element("span", "move-copy", project.next)', ready_actions)
        self.assertNotIn('element("h3", "", project.name)', ready_actions)
        self.assertNotIn('element("p", "", project.next)', ready_actions)
        self.assertIn(".move-title { display: block;", CSS)
        self.assertIn(".move-copy { display: block;", CSS)

    def test_brief_table_scroll_is_contained_on_narrow_viewports(self) -> None:
        self.assertIn(
            ".control-grid > *, .brief-rail > *, .focus-panel { min-width: 0; }",
            CSS,
        )
        self.assertIn(
            ".project-table { min-width: 0; max-width: 100%; overflow-x: auto; }",
            CSS,
        )

    def test_maximum_project_label_can_wrap_inside_the_mobile_drawer(self) -> None:
        self.assertIn(
            ".copy-path > span { min-width: 0; overflow-wrap: anywhere; }",
            CSS,
        )
        self.assertIn(".copy-path b { flex: 0 0 auto;", CSS)
        self.assertIn('"projects/" + project.id', APP)


if __name__ == "__main__":
    unittest.main()
