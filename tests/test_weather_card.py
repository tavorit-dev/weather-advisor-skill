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


class CardLanguageTests(unittest.TestCase):
    """The interface language follows the question, not the response prose."""

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

    def render(self, *extra: object) -> str:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            args: list[object] = [
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--brief",
                self.brief_path,
                "--output",
                out,
                *extra,
            ]
            result = run(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            return out.read_text(encoding="utf-8")

    def test_default_language_is_english(self) -> None:
        card = self.render()
        self.assertIn('<html lang="en"', card)
        self.assertIn("Window evidence", visible_text(card))

    def test_chinese_question_selects_the_chinese_interface(self) -> None:
        card = self.render("--query", "今日天津天气")
        self.assertIn('<html lang="zh-CN"', card)
        text = visible_text(card)
        # Sections the example response actually carries.
        for label in ("时段证据", "建议", "风险", "证据", "不确定性"):
            self.assertIn(label, text)
        for label in ("Window evidence", "Recommendations", "Risks"):
            self.assertNotIn(label, text)

    def test_chinese_interface_translates_every_section(self) -> None:
        """Including sections only some responses carry."""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "response.json"
            base = json.loads(
                (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
            )
            base["missing_information"] = ["官方预警未提供。"]
            base["status"] = "needs_clarification"
            base["clarification_question"] = "你打算几点出门？"
            source.write_text(json.dumps(base, ensure_ascii=False), encoding="utf-8")
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                source,
                "--query",
                "今日天津天气",
                "--output",
                out,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            text = visible_text(out.read_text(encoding="utf-8"))
        for label in ("缺失信息", "需要澄清", "官方预警未提供。", "你打算几点出门？"):
            self.assertIn(label, text)

    def test_english_question_keeps_the_english_interface(self) -> None:
        card = self.render("--query", "Tianjin weather today")
        self.assertIn('<html lang="en"', card)
        self.assertIn("Window evidence", visible_text(card))

    def test_lang_flag_overrides_the_question(self) -> None:
        card = self.render("--query", "今日天津天气", "--lang", "en")
        self.assertIn('<html lang="en"', card)
        self.assertIn("Window evidence", visible_text(card))

        card = self.render("--query", "Tianjin weather", "--lang", "zh")
        self.assertIn('<html lang="zh-CN"', card)
        self.assertIn("时段证据", visible_text(card))

    def test_response_prose_is_never_translated(self) -> None:
        """The card labels its own chrome; it does not touch the response."""
        response = json.loads(
            (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
        )
        for extra in ((), ("--query", "今日天津天气")):
            with self.subTest(lang=extra or ("default",)):
                text = visible_text(self.render(*extra))
                self.assertIn(response["summary"], text)
                for item in response["evidence"]:
                    self.assertIn(item["claim"], text)
                for item in response["recommendations"]:
                    self.assertIn(item["action"], text)
                    self.assertIn(item["reason"], text)
                for item in response["risks"]:
                    self.assertIn(item["description"], text)
                for item in response.get("uncertainty", []):
                    self.assertIn(item, text)

    def test_chinese_card_keeps_attribution_and_limits(self) -> None:
        text = visible_text(self.render("--query", "今日天津天气"))
        # Attribution is a proper name and stays verbatim in both languages.
        self.assertIn("Weather data by Open-Meteo.com", text)
        self.assertIn("CC BY 4.0", text)
        self.assertIn("官方预警", text)

    def test_unknown_language_is_rejected(self) -> None:
        result = run(
            CARD,
            EXAMPLES / "commute-rain-output.json",
            "--lang",
            "fr",
        )
        # argparse rejects it before the renderer runs.
        self.assertEqual(result.returncode, 2)
        self.assertIn("--lang", result.stderr)

    def test_both_languages_define_every_key(self) -> None:
        """A missing key would surface as a raw identifier in the markup."""
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        english = set(weather_card.STRINGS["en"])
        chinese = set(weather_card.STRINGS["zh"])
        self.assertEqual(english, chinese)
        for lang, table in weather_card.STRINGS.items():
            for key, value in table.items():
                with self.subTest(lang=lang, key=key):
                    self.assertTrue(value.strip(), f"{lang}.{key} is empty")

    def test_tile_and_curve_label_keys_all_exist(self) -> None:
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        for lang, table in weather_card.STRINGS.items():
            for label_key, *_ in weather_card.TILE_ROWS:
                with self.subTest(lang=lang, key=label_key):
                    self.assertIn(label_key, table)
            for label_key, *_ in weather_card.CURVE_METRICS:
                with self.subTest(lang=lang, key=label_key):
                    self.assertIn(label_key, table)

    def test_language_detection_reads_han_only(self) -> None:
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        for text in ("今日天津天气", "上海 通勤 明天", "Tokyo 东京"):
            with self.subTest(text=text):
                self.assertEqual(weather_card.detect_lang(text), "zh")
        for text in ("", "   ", "Tianjin weather", "12345", "café ☔"):
            with self.subTest(text=text):
                self.assertEqual(weather_card.detect_lang(text), "en")


class CardPrintExportTests(unittest.TestCase):
    """Export is print-to-PDF, so the print rules must be present and complete."""

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--output",
                out,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr)
            cls.card = out.read_text(encoding="utf-8")

    def test_print_stylesheet_is_embedded(self) -> None:
        self.assertIn("@media print", self.card)
        self.assertIn("@page", self.card)
        # Cards must not be split across pages when printed.
        self.assertIn("break-inside: avoid", self.card)

    def test_print_rules_force_light_ink_on_white(self) -> None:
        print_block = self.card.split("@media print", 1)[1]
        self.assertIn("--bg: #ffffff", print_block)
        self.assertIn("--ink: #111111", print_block)

    def test_print_hint_is_hidden_on_screen_and_on_paper(self) -> None:
        # The hint is guidance for a screen reader of the card, not printed
        # content, and it must not appear in an exported image.
        text = visible_text(self.card)
        self.assertNotIn("Print or save as PDF", text.split("Uncertainty")[0])
        self.assertIn(".print-hint", self.card)
        self.assertIn("display: none", self.card)

    def test_print_export_needs_no_script(self) -> None:
        """Export must stay a browser print, so the card keeps zero scripts."""
        self.assertNotIn("<script", self.card)
        self.assertNotIn("onclick", self.card)
        self.assertNotIn("javascript:", self.card)

    def test_print_hint_lists_a_language_appropriate_instruction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--query",
                "今日天津天气",
                "--output",
                out,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            card = out.read_text(encoding="utf-8")
        self.assertIn("打印或另存为 PDF", card)

    def test_print_flag_reports_the_export_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "card.html"
            result = run(
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--output",
                out,
                "--print",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("print dialog", result.stderr)


if __name__ == "__main__":
    unittest.main()
