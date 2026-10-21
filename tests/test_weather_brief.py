#!/usr/bin/env python3
"""Tests for the compact weather brief used by the Claude Code entry."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF = ROOT / "demo" / "weather_brief.py"
DEMO = ROOT / "demo" / "weather_demo.py"
FIXTURE_DATE = "2026-10-22"


def run(*args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


class WeatherBriefTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.demo = run(DEMO, "Tokyo", "--offline")
        if cls.demo.returncode != 0:
            raise RuntimeError(cls.demo.stderr)
        cls.demo_ids = {
            item["id"]
            for item in json.loads(cls.demo.stdout)["weather_evidence"]
        }

    def test_windowed_brief_is_compact_and_traceable(self) -> None:
        result = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--window",
            "08:00-12:00",
            "--query",
            "Is tomorrow morning good for a run?",
            "--intent",
            "outdoor_activity",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        brief = json.loads(result.stdout)

        self.assertEqual(brief["coverage"]["date"], FIXTURE_DATE)
        self.assertEqual(brief["coverage"]["window"], "08:00-12:00")
        self.assertEqual(brief["coverage"]["hours_included"], 4)
        self.assertEqual([hour["time"] for hour in brief["hours"]], [
            "08:00",
            "09:00",
            "10:00",
            "11:00",
        ])
        self.assertNotIn("weather_evidence", brief)
        self.assertEqual(brief["source"]["attribution"], "Weather data by Open-Meteo.com")

        cited = set()
        for hour in brief["hours"]:
            cited.update(hour["evidence_ids"].values())
        for group in brief["summary"].values():
            for value in group.values():
                if value and "evidence_id" in value:
                    cited.add(value["evidence_id"])
        self.assertTrue(cited)
        self.assertTrue(cited <= self.demo_ids)

        self.assertLess(len(result.stdout.encode()), len(self.demo.stdout.encode()))

    def test_default_window_is_the_full_fixture_day(self) -> None:
        result = run(BRIEF, "Tokyo", "--offline", "--date", FIXTURE_DATE)
        self.assertEqual(result.returncode, 0, result.stderr)
        brief = json.loads(result.stdout)
        self.assertEqual(brief["coverage"]["hours_included"], 12)
        self.assertEqual(brief["coverage"]["window"], "00:00-24:00")

    def test_summary_only_omits_hourly_rows(self) -> None:
        result = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--window",
            "08:00-12:00",
            "--summary-only",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        brief = json.loads(result.stdout)
        self.assertNotIn("hours", brief)
        self.assertEqual(brief["coverage"]["detail"], "summary")
        self.assertEqual(brief["coverage"]["hours_included"], 4)

        cited = {
            value["evidence_id"]
            for group in brief["summary"].values()
            for value in group.values()
            if value and "evidence_id" in value
        }
        self.assertTrue(cited)
        self.assertTrue(cited <= self.demo_ids)

    def test_compact_output_is_smaller_and_valid_json(self) -> None:
        common = (
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--window",
            "08:00-12:00",
        )
        pretty = run(*common)
        compact = run(*common, "--compact")
        self.assertEqual(pretty.returncode, 0, pretty.stderr)
        self.assertEqual(compact.returncode, 0, compact.stderr)
        self.assertEqual(json.loads(pretty.stdout), json.loads(compact.stdout))
        self.assertLess(len(compact.stdout), len(pretty.stdout))
        self.assertEqual(compact.stdout.count("\n"), 1)

    def test_every_three_hours_keeps_a_day_curve(self) -> None:
        result = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--every",
            "3",
            "--compact",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        brief = json.loads(result.stdout)
        self.assertEqual(brief["coverage"]["detail"], "sparse")
        self.assertEqual(brief["coverage"]["step_hours"], 3)
        self.assertEqual(brief["coverage"]["hours_in_window"], 12)
        self.assertEqual(brief["coverage"]["hours_included"], 4)
        self.assertEqual([hour["time"] for hour in brief["hours"]], [
            "09:00",
            "12:00",
            "15:00",
            "18:00",
        ])
        self.assertEqual(
            brief["summary"]["wind_gust"]["max"]["evidence_id"],
            "ev-006-wind_gusts_10m",
        )

    def test_invalid_every_fails(self) -> None:
        result = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--every",
            "0",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("--every", result.stderr)

    def test_output_file_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "brief.json"
            result = run(
                BRIEF,
                "Tokyo",
                "--offline",
                "--date",
                FIXTURE_DATE,
                "--window",
                "08:00-12:00",
                "--output",
                output,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Wrote compact brief", result.stderr)
            self.assertEqual(
                json.loads(output.read_text(encoding="utf-8"))["coverage"][
                    "hours_included"
                ],
                4,
            )

    def test_window_outside_coverage_fails(self) -> None:
        result = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--window",
            "20:00-23:00",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("No evidence covers", result.stderr)

    def test_invalid_window_order_fails(self) -> None:
        result = run(
            BRIEF,
            "Tokyo",
            "--offline",
            "--date",
            FIXTURE_DATE,
            "--window",
            "12:00-10:00",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("end must be after", result.stderr)


if __name__ == "__main__":
    unittest.main()
