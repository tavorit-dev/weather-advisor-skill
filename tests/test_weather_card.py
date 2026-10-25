#!/usr/bin/env python3
"""Tests for the HTML card renderer used by /weather-advisor-card."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "demo" / "weather_card.py"
BRIEF = ROOT / "demo" / "weather_brief.py"
EXAMPLES = ROOT / "examples"
FIXTURE_DATE = "2026-10-22"
TAG = re.compile(r"<[^>]+>")
STYLE = re.compile(r"<style>.*?</style>", re.DOTALL)
HEAD = re.compile(r"<head>.*?</head>", re.DOTALL)


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def visible_text(markup: str) -> str:
    """Return only the text a reader sees, with markup and CSS removed."""
    return TAG.sub(" ", STYLE.sub(" ", HEAD.sub(" ", markup)))


class WeatherCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.brief = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--every",
            "3",
            "--compact",
        )
        if cls.brief.returncode != 0:
            raise RuntimeError(cls.brief.stderr)
        cls.brief_path = Path(tempfile.mkdtemp()) / "brief.json"
        cls.brief_path.write_text(cls.brief.stdout, encoding="utf-8")

    def render(
        self,
        response_name: str = "commute-rain-output.json",
        *,
        with_brief: bool = True,
    ) -> str:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            args: list[object] = [CARD, EXAMPLES / response_name]
            if with_brief:
                args += ["--brief", self.brief_path]
            args += ["--output", out]
            result = run(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            return out.read_text(encoding="utf-8")

    def test_card_is_a_self_contained_document(self) -> None:
        card = self.render()
        self.assertTrue(card.startswith("<!doctype html>"))
        self.assertIn('<meta name="viewport"', card)
        self.assertIn("<style>", card)
        self.assertTrue(card.rstrip().endswith("</html>"))
        # Self-contained: no external stylesheet, script, or image.
        for marker in ("<link", "<script", "<img", "http://", "https://"):
            self.assertNotIn(marker, card)

    def test_card_carries_the_response_verbatim(self) -> None:
        response = json.loads(
            (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
        )
        text = visible_text(self.render())
        self.assertIn(response["summary"], text)
        for item in response["evidence"]:
            self.assertIn(item["evidence_id"], text)
            self.assertIn(item["claim"], text)
        for item in response["recommendations"]:
            self.assertIn(item["action"], text)
            self.assertIn(item["reason"], text)
        for item in response["risks"]:
            self.assertIn(item["description"], text)
            self.assertIn(item["severity"], text)
        for item in response.get("uncertainty", []):
            self.assertIn(item, text)

    def test_card_shows_window_evidence_and_curves(self) -> None:
        brief = json.loads(self.brief.stdout)
        card = self.render()
        text = visible_text(card)
        coverage = brief["coverage"]
        self.assertIn(coverage["date"], text)
        self.assertIn(coverage["window"], text)
        self.assertIn(brief["location"]["name"], text)

        curves = card.count('class="curve-card"')
        self.assertGreaterEqual(curves, 4)
        self.assertEqual(card.count("<svg"), curves)
        self.assertIn("<polyline", card)

        # Every evidence ID the brief exposes for a plotted hour is on the card.
        plotted = set()
        for label in ("temperature", "wind_speed"):
            for hour in brief["hours"]:
                plotted.add(hour["evidence_ids"][label])
        for evidence_id in plotted:
            self.assertIn(evidence_id, card)

    def test_card_carries_attribution_and_limits(self) -> None:
        card = self.render()
        text = visible_text(card)
        self.assertIn("Weather data by Open-Meteo.com", text)
        self.assertIn("CC BY 4.0", text)
        self.assertIn("not an official warning", text)
        # The demo's gaps must be stated, not silently omitted.
        self.assertIn("Absence of an alert here is not evidence", text)
        self.assertIn("official alerts", text)

    def test_card_without_brief_renders_the_response_alone(self) -> None:
        card = self.render(with_brief=False)
        text = visible_text(card)
        self.assertNotIn("Window evidence", text)
        self.assertIn("Recommendations", text)
        self.assertNotIn("Open-Meteo", text)
        # With no brief there is no window, so no metrics or curves are drawn.
        self.assertNotIn("<svg", card)
        self.assertNotIn('class="metric"', card)

    def test_all_examples_render(self) -> None:
        for path in sorted(EXAMPLES.glob("*-output.json")):
            with self.subTest(example=path.name):
                card = self.render(path.name)
                self.assertIn("</html>", card)

    def test_status_and_intent_are_shown(self) -> None:
        card = self.render("missing-location-output.json")
        text = visible_text(card)
        self.assertIn("needs clarification", text)
        self.assertIn("outdoor activity", text)
        question = json.loads(
            (EXAMPLES / "missing-location-output.json").read_text(encoding="utf-8")
        )["clarification_question"]
        self.assertIn(question, text)

    def test_summary_only_brief_renders_tiles_without_curves(self) -> None:
        summary = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--summary-only",
            "--compact",
        )
        self.assertEqual(summary.returncode, 0, summary.stderr)
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(summary.stdout, encoding="utf-8")
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                EXAMPLES / "outdoor-wind-output.json",
                "--brief",
                brief_path,
                "--output",
                out,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            card = out.read_text(encoding="utf-8")
        self.assertIn('class="metric"', card)
        self.assertNotIn("<svg", card)
        self.assertIn("no curves are shown", visible_text(card))

    def test_no_air_quality_brief_omits_the_air_notice(self) -> None:
        brief = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--every",
            "3",
            "--compact",
            "--no-air-quality",
        )
        self.assertEqual(brief.returncode, 0, brief.stderr)
        with tempfile.TemporaryDirectory() as directory:
            brief_path = Path(directory) / "brief.json"
            brief_path.write_text(brief.stdout, encoding="utf-8")
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--brief",
                brief_path,
                "--output",
                out,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            card = out.read_text(encoding="utf-8")
        text = visible_text(card)
        self.assertNotIn("Air quality", text)
        # The air-quality tiles and curves drop out with the section.
        self.assertNotIn("PM2.5", text)
        self.assertNotIn("US AQI", text)
        self.assertIn("Temperature", text)

    def test_markup_escapes_response_content(self) -> None:
        response = json.loads(
            (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
        )
        response["summary"] = '<script>alert("x")</script> & "quoted"'
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "response.json"
            source.write_text(json.dumps(response), encoding="utf-8")
            out = Path(directory) / "card.html"
            result = run(CARD, source, "--output", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            card = out.read_text(encoding="utf-8")
        self.assertNotIn("<script", card)
        self.assertIn("&lt;script&gt;", card)
        self.assertIn("&amp;", card)

    def test_unknown_status_or_intent_is_rejected(self) -> None:
        base = json.loads(
            (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
        )
        for field, value, message in (
            ("status", "bogus", "unknown status"),
            ("intent", "bogus", "unknown intent"),
        ):
            with self.subTest(field=field):
                broken = dict(base, **{field: value})
                with tempfile.TemporaryDirectory() as directory:
                    source = Path(directory) / "response.json"
                    source.write_text(json.dumps(broken), encoding="utf-8")
                    result = run(CARD, source)
                self.assertEqual(result.returncode, 1)
                self.assertIn(message, result.stderr)

    def test_missing_required_field_is_rejected(self) -> None:
        base = json.loads(
            (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
        )
        del base["summary"]
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "response.json"
            source.write_text(json.dumps(base), encoding="utf-8")
            result = run(CARD, source)
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing required field: summary", result.stderr)

    def test_malformed_json_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "response.json"
            source.write_text("{not json", encoding="utf-8")
            result = run(CARD, source)
        self.assertEqual(result.returncode, 1)
        self.assertIn("not valid JSON", result.stderr)

    def test_check_accepts_a_rendered_card(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--brief",
                self.brief_path,
                "--output",
                out,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            check = run(CARD, "--check", out)
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("well-formed", check.stdout)

    def test_check_rejects_a_truncated_card(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            out.write_text("<html><body>oops", encoding="utf-8")
            check = run(CARD, "--check", out)
        self.assertEqual(check.returncode, 1)
        self.assertIn("card is missing", check.stderr)

    def test_default_output_is_a_temporary_file(self) -> None:
        result = run(CARD, EXAMPLES / "commute-rain-output.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        path = Path(result.stdout.strip())
        self.addCleanup(path.unlink, missing_ok=True)
        self.assertTrue(path.is_file())
        self.assertTrue(path.read_text(encoding="utf-8").startswith("<!doctype html>"))

    def test_renderer_does_not_need_the_network_or_third_party_packages(self) -> None:
        source = CARD.read_text(encoding="utf-8")
        for marker in ("urllib", "requests", "http.client", "socket"):
            self.assertNotIn(f"import {marker}", source)


if __name__ == "__main__":
    unittest.main()
