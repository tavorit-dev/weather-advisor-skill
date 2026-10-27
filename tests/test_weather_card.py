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

    def test_advice_is_shown_before_the_evidence_behind_it(self) -> None:
        """The recommendation is the point of the card, so it comes first."""
        body = self.render().split("<body>", 1)[1]
        order = [
            body.index('class="summary"'),
            body.index("recommendations-section"),
            body.index('class="section window"'),
            body.index('class="risks"'),
            body.index("evidence-section"),
        ]
        self.assertEqual(order, sorted(order))

    def test_evidence_list_collapses_without_scripting(self) -> None:
        """The raw evidence list folds away, and the fold stays script-free."""
        card = self.render()
        self.assertIn("<details>", card)
        self.assertIn("<summary>", card)
        # Collapsing is markup, not behaviour: the card keeps zero scripts.
        self.assertNotIn("<script", card)
        self.assertNotIn("onclick", card)
        # The count tells the reader what is folded away.
        count = len(
            json.loads(
                (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
            )["evidence"]
        )
        self.assertIn(f"Evidence ({count})", visible_text(card))
        # The evidence itself is still present, just folded.
        self.assertIn('class="evidence"', card)

    def test_evidence_id_explanation_is_shown(self) -> None:
        """A reader who sees ev-rain-001 is told why the ID is on the card."""
        text = visible_text(self.render())
        self.assertIn("Why IDs are shown", text)
        self.assertIn("evidence IDs", text)

    def test_empty_recommendations_are_not_highlighted(self) -> None:
        """An accent edge would dress up a card that has nothing to advise."""
        card = self.render("missing-location-output.json", with_brief=False)
        body = card.split("<body>", 1)[1]
        text = visible_text(card)
        self.assertIn("No recommendations in this response.", text)
        self.assertNotIn("recommendations-section", body)
        self.assertNotIn("What to do, and why.", text)

    def test_uncovered_metrics_are_listed_one_per_line(self) -> None:
        """A wrapped comma run hides which metrics are missing."""
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        card = self.render()
        gaps = json.loads(self.brief.stdout)["demo_gaps"]
        self.assertGreater(len(gaps), 1)
        self.assertIn('class="gap-list"', card)
        for gap in gaps:
            with self.subTest(gap=gap):
                # Gaps are translated like any other interface label.
                label = weather_card.STRINGS["en"].get(gap, gap)
                self.assertIn(f"<li>{label}</li>", card)
        # The caveat is a separate sentence, not glued onto the list.
        self.assertIn(
            "Absence of an alert here is not evidence", visible_text(card)
        )
        self.assertIn("official alerts", visible_text(card))

    def test_print_always_reveals_the_collapsed_evidence(self) -> None:
        """A collapsed <details> would silently drop evidence from a PDF.

        Setting `display` on the children does not do it: a closed <details>
        hides its whole content slot, so the slot itself must be revealed via
        ``::details-content``. Verified against a headless Chrome print.
        """
        card = self.render()
        print_block = card.split("@media print", 1)[1]
        self.assertIn("::details-content", print_block)
        self.assertIn("content-visibility: visible", print_block)
        # The marker and the toggle label are screen affordances only.
        self.assertIn(".toggle", print_block)
        self.assertIn("display: none", print_block)

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

        # The response's own evidence IDs are what the card cites, and they are
        # shown in the evidence list rather than under each item. The brief's
        # per-hour IDs are a separate namespace and are not evidence entries, so
        # the card does not print them: an ID on the card must resolve to an
        # entry in the evidence list, or it is a dangling reference.
        response = json.loads(
            (EXAMPLES / "commute-rain-output.json").read_text(encoding="utf-8")
        )
        for item in response["evidence"]:
            with self.subTest(evidence_id=item["evidence_id"]):
                self.assertIn(
                    f'<span class="ref">{item["evidence_id"]}</span>', card
                )
        # Every ID the card does print resolves to an evidence entry.
        printed = set(re.findall(r'<span class="ref">([^<]+)</span>', card))
        listed = {item["evidence_id"] for item in response["evidence"]}
        self.assertTrue(printed <= listed, printed - listed)

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

    def test_card_is_one_sheet_rather_than_a_stack_of_cards(self) -> None:
        """A dozen framed cards read as box-in-box clutter at phone width."""
        card = self.render()
        body = card.split("<body>", 1)[1]
        self.assertEqual(body.count('class="sheet"'), 1)
        # Sections divide the sheet; none of them is a framed card of its own.
        self.assertGreaterEqual(body.count('class="section'), 6)
        self.assertNotIn("card-stack", body)

    def test_curves_are_tiled_rather_than_scrolled(self) -> None:
        """Every series is visible at once; none is hidden behind a swipe."""
        card = self.render()
        curves_rule = card.split(".curves {", 1)[1].split("}", 1)[0]
        self.assertIn("display: grid", curves_rule)
        self.assertIn("grid-template-columns", curves_rule)
        self.assertNotIn("overflow-x", curves_rule)
        # Nothing scrolls sideways: a tile the reader has to swipe to reach is
        # a series they may never see.
        self.assertNotIn("scroll-snap", card)
        # Print keeps the grid at a fixed column count.
        print_block = card.split("@media print", 1)[1]
        self.assertIn("grid-template-columns", print_block)

    def test_curve_caption_does_not_repeat_the_unit(self) -> None:
        """The peak figure already ends with its unit: "18.4 °C", not "18.4 °C °C"."""
        card = self.render()
        captions = re.findall(r"<figcaption>.*?</figcaption>", card, re.DOTALL)
        self.assertTrue(captions)
        for caption in captions:
            # Stripping tags leaves a space where each tag was, and the unit
            # would be separated from itself by two of them; collapse the run
            # so the check does not pass on a formatting accident.
            detail = re.sub(r"\s+", " ", TAG.sub(" ", caption)).strip()
            with self.subTest(caption=detail):
                for duplicated in ("°C °C", "mm mm", "km/h km/h", "% %"):
                    self.assertNotIn(duplicated, detail)

    def test_evidence_ids_are_not_printed_under_every_item(self) -> None:
        """Dozens of chips drowned the data they were meant to support."""
        card = self.render()
        # Markup only: the embedded stylesheet also names the .ref class.
        body = STYLE.sub(" ", card).split("<body>", 1)[1]
        before, _, after = body.partition('<section class="section evidence-section"')
        self.assertTrue(after, "the evidence section is missing")
        # Chips appear only inside the evidence list, not under the advice,
        # the risks, or the charts.
        self.assertNotIn('class="ref"', before)
        self.assertIn('class="ref"', after)

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

    def test_every_interface_enum_is_translated(self) -> None:
        """Enums the card renders must not leak through as English.

        The intent, the brief's detail mode, and its live/offline mode are all
        card chrome, so a Chinese card must not show them untranslated.
        """
        card = self.render("--query", "今日天津天气")
        text = visible_text(card)
        # commute-rain-output.json uses commute_advice; the brief is --every 3
        # offline, so detail=sparse and mode=offline.
        self.assertIn("通勤建议", text)
        self.assertIn("稀疏采样", text)
        self.assertIn("离线", text)
        for leaked in (
            "commute advice",
            "sparse",
            "offline",
            "answered",
        ):
            with self.subTest(leaked=leaked):
                self.assertNotIn(leaked, text)

    def test_every_schema_intent_has_a_translation(self) -> None:
        """A new intent in the schema must not silently fall back to English."""
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        schema = json.loads(
            (ROOT / "schemas" / "recommendation.schema.json").read_text(
                encoding="utf-8"
            )
        )
        intents = schema["properties"]["intent"]["enum"]
        statuses = schema["properties"]["status"]["enum"]
        severities = schema["properties"]["risks"]["items"]["properties"][
            "severity"
        ]["enum"]
        for lang, table in weather_card.STRINGS.items():
            for name, values in (
                ("intent", intents),
                ("status", statuses),
                ("severity", severities),
            ):
                for value in values:
                    with self.subTest(lang=lang, field=name, value=value):
                        self.assertIn(value, table)

    def test_unknown_enum_value_falls_back_rather_than_blanking(self) -> None:
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        t = weather_card.Translator("zh")
        # A value the card does not know is shown as-is, not dropped.
        self.assertEqual(
            weather_card.label_for(t, "some_new_intent"), "some new intent"
        )
        self.assertEqual(
            weather_card.label_for(t, "bogus", namespace="detail"), "bogus"
        )
        self.assertEqual(weather_card.label_for(t, "", fallback="—"), "—")

    def test_brief_detail_and_mode_enums_are_namespaced(self) -> None:
        """detail and mode are short words that could collide with other keys."""
        sys.path.insert(0, str(ROOT / "demo"))
        import weather_card  # noqa: PLC0415

        t = weather_card.Translator("zh")
        self.assertEqual(
            weather_card.label_for(t, "summary", namespace="detail"), "仅统计值"
        )
        self.assertEqual(
            weather_card.label_for(t, "offline", namespace="mode"), "离线"
        )
        # The same words without a namespace are not the brief's enums.
        self.assertEqual(weather_card.label_for(t, "summary"), "summary")

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


STATS = {
    "source": "claude-code-transcript",
    "input_tokens": 12345,
    "output_tokens": 678,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
    "elapsed_seconds": 83,
    "requests": 3,
    "started_at": "2026-10-27T10:00:00Z",
    "generated_at": "2026-10-27T10:01:23Z",
    "model": "claude-sonnet-5-5",
}


class GenerationStatsTests(unittest.TestCase):
    """Optional session stats, supplied by scripts/claude_session_stats.py."""

    def render(
        self, stats: object | None = None, *extra: object
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            args: list[object] = [CARD, EXAMPLES / "commute-rain-output.json"]
            if stats is not None:
                stats_path = directory / "stats.json"
                stats_path.write_text(json.dumps(stats), encoding="utf-8")
                args += ["--stats", stats_path]
            out = directory / "card.html"
            args += ["--output", out, *extra]
            result = run(*args)
            card = out.read_text(encoding="utf-8") if out.exists() else ""
        return result, card

    def test_stats_block_is_omitted_without_stats(self) -> None:
        result, card = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Generation stats", visible_text(card))
        self.assertNotIn('class="stats-block"', card)

    def test_stats_are_rendered_at_the_end(self) -> None:
        result, card = self.render(STATS)
        self.assertEqual(result.returncode, 0, result.stderr)
        body = card.split("<body>", 1)[1]
        stats_at = body.index('class="stats-block"')
        self.assertGreater(stats_at, body.index('class="section footer"'))
        self.assertGreater(stats_at, body.index("This card is a rendering"))

    def test_stats_show_tokens_elapsed_and_model(self) -> None:
        result, card = self.render(STATS)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = visible_text(card)
        self.assertIn("Generation stats", text)
        self.assertIn("Input tokens", text)
        self.assertIn("Output tokens", text)
        self.assertIn("Total tokens", text)
        self.assertIn("12,345", text)
        self.assertIn("678", text)
        self.assertIn("13,023", text)
        self.assertIn("Elapsed", text)
        self.assertIn("1m 23s", text)
        self.assertIn("Model", text)
        self.assertIn("claude-sonnet-5-5", text)

    def test_stats_are_translated_with_the_interface(self) -> None:
        result, card = self.render(STATS, "--query", "今日天津天气")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = visible_text(card)
        for label in ("生成统计", "输入 tokens", "输出 tokens", "合计 tokens", "耗时", "模型"):
            self.assertIn(label, text)
        self.assertIn("1 分 23 秒", text)
        self.assertIn("12,345", text)

    def test_stats_without_model_omit_the_model_row(self) -> None:
        stats = dict(STATS)
        del stats["model"]
        result, card = self.render(stats)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = visible_text(card)
        self.assertIn("Generation stats", text)
        self.assertNotIn("Model", text)

    def test_stats_note_states_where_the_numbers_come_from(self) -> None:
        result, card = self.render(STATS)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = visible_text(card)
        self.assertIn("session transcript", text)
        self.assertIn("not counted yet", text)
        self.assertIn("not an estimate", text)

        result, card = self.render(STATS, "--query", "今日天津天气")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("会话记录", visible_text(card))
        self.assertIn("尚未计入", visible_text(card))

    def test_zero_tokens_survive_rather_than_being_hidden(self) -> None:
        """Zero is a measurement; a missing block would be a different thing."""
        stats = dict(
            STATS, input_tokens=0, output_tokens=0, elapsed_seconds=0
        )
        result, card = self.render(stats)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = visible_text(card)
        self.assertIn("Generation stats", text)
        self.assertIn("0s", text)
        self.assertIn("Total tokens", text)

    def test_elapsed_over_an_hour_uses_hours(self) -> None:
        stats = dict(STATS, elapsed_seconds=3725)
        result, card = self.render(stats)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1h 2m", visible_text(card))

        result, card = self.render(stats, "--query", "今日天津天气")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 小时 2 分", visible_text(card))

    def test_stats_values_are_escaped(self) -> None:
        stats = dict(STATS, model='<script>alert("x")</script>')
        result, card = self.render(stats)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("<script", card)
        self.assertIn("&lt;script&gt;", card)

    def test_stats_do_not_add_scripts(self) -> None:
        result, card = self.render(STATS)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("<script", card)
        self.assertNotIn("onclick", card)

    def test_invalid_stats_are_rejected(self) -> None:
        cases = (
            (dict(STATS, input_tokens=-1), "non-negative"),
            (dict(STATS, elapsed_seconds="83"), "non-negative"),
            (dict(STATS, source="handwritten"), "stats source"),
            (dict(STATS, model=""), "model"),
        )
        for stats, message in cases:
            with self.subTest(message=message, stats=stats.get("source")):
                result, card = self.render(stats)
                self.assertEqual(result.returncode, 1)
                self.assertIn("stats", result.stderr)
                self.assertIn(message, result.stderr)
                self.assertEqual(card, "")

    def test_non_finite_stats_are_rejected(self) -> None:
        """NaN is valid JSON for Python but not a number the card can print."""
        for value in (float("nan"), float("inf")):
            with self.subTest(value=value):
                result, card = self.render(dict(STATS, elapsed_seconds=value))
                self.assertEqual(result.returncode, 1)
                self.assertIn("finite", result.stderr)
                self.assertEqual(card, "")

    def test_stats_missing_source_is_rejected(self) -> None:
        stats = dict(STATS)
        del stats["source"]
        result, card = self.render(stats)
        self.assertEqual(result.returncode, 1)
        self.assertIn("stats source", result.stderr)
        self.assertEqual(card, "")

    def test_stats_must_be_a_json_object(self) -> None:
        result, card = self.render([1, 2, 3])
        self.assertEqual(result.returncode, 1)
        self.assertIn("stats must be a JSON object", result.stderr)
        self.assertEqual(card, "")

    def test_malformed_stats_json_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stats_path = Path(directory) / "stats.json"
            stats_path.write_text("{oops", encoding="utf-8")
            result = run(
                CARD,
                EXAMPLES / "commute-rain-output.json",
                "--stats",
                stats_path,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("not valid JSON", result.stderr)


if __name__ == "__main__":
    unittest.main()
