#!/usr/bin/env python3
"""L1 data-layer tests for demo/weather_demo.py.

These tests use the bundled Tokyo fixtures and never touch the network.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "demo"
sys.path.insert(0, str(DEMO_DIR))

import weather_demo  # noqa: E402


class OfflineDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.location = weather_demo.geocode("Tokyo", offline=True)
        cls.forecast = weather_demo.fetch_forecast(cls.location, offline=True)
        cls.retrieved_at = "2026-10-21T21:00:00+09:00"
        cls.evidence = weather_demo.build_evidence(
            cls.location, cls.forecast, cls.retrieved_at
        )
        cls.document = weather_demo.build_document("Tokyo", offline=True)

    def test_geocoding_normalizes_location(self) -> None:
        self.assertEqual(self.location["name"], "Tokyo")
        self.assertEqual(self.location["country"], "Japan")
        self.assertEqual(self.location["timezone"], "Asia/Tokyo")
        self.assertAlmostEqual(self.location["latitude"], 35.6895)
        self.assertAlmostEqual(self.location["longitude"], 139.69171)

    def test_forecast_contains_all_hourly_fields(self) -> None:
        hourly = self.forecast["hourly"]
        self.assertEqual(len(hourly["time"]), 12)
        for api_field, _, _ in weather_demo.HOURLY_FIELDS:
            self.assertIn(api_field, hourly)
            self.assertEqual(len(hourly[api_field]), 12)

    def test_evidence_types_and_units(self) -> None:
        expected_units = {
            "temperature": "°C",
            "apparent_temperature": "°C",
            "precipitation_probability": "%",
            "precipitation_amount": "mm",
            "wind_speed": "km/h",
            "wind_gust": "km/h",
        }
        self.assertEqual(len(self.evidence), 12 * len(expected_units))
        for item in self.evidence:
            self.assertIn(item["type"], expected_units)
            self.assertEqual(item["unit"], expected_units[item["type"]])
            self.assertEqual(item["source"], "Open-Meteo")
            self.assertEqual(item["observed_at"], self.retrieved_at)
            self.assertIsNotNone(item["value"])

    def test_evidence_ids_are_unique(self) -> None:
        ids = [item["id"] for item in self.evidence]
        self.assertEqual(len(ids), len(set(ids)))

    def test_validity_windows_are_one_hour_with_offset(self) -> None:
        first = min(self.evidence, key=lambda item: item["valid_from"])
        start = datetime.fromisoformat(first["valid_from"])
        end = datetime.fromisoformat(first["valid_to"])
        self.assertEqual(end - start, timedelta(hours=1))
        self.assertEqual(start.utcoffset(), timedelta(hours=9))

    def test_document_is_a_skill_ready_envelope(self) -> None:
        self.assertEqual(
            set(self.document),
            {
                "user_query",
                "intent",
                "context",
                "weather_evidence",
                "attribution",
                "metadata",
            },
        )
        self.assertEqual(self.document["intent"], "weather_lookup")
        self.assertIn("Tokyo", self.document["user_query"])

        context = self.document["context"]
        self.assertEqual(context["start"], "2026-10-22T08:00:00+09:00")
        self.assertEqual(context["end"], "2026-10-22T20:00:00+09:00")
        self.assertEqual(context["location"]["timezone"], "Asia/Tokyo")

        metadata = self.document["metadata"]
        self.assertEqual(metadata["mode"], "offline")
        self.assertEqual(metadata["data_license"], "CC BY 4.0")
        self.assertIn("Open-Meteo.com", self.document["attribution"])
        self.assertIn("synthetic", metadata["data_note"])

    def test_offline_mode_does_not_call_network(self) -> None:
        with mock.patch.object(
            weather_demo,
            "_request_json",
            side_effect=AssertionError("network call attempted"),
        ):
            document = weather_demo.build_document("Tokyo", offline=True)
        self.assertEqual(document["metadata"]["mode"], "offline")
        self.assertEqual(len(document["weather_evidence"]), 72)

    def test_offline_mode_rejects_other_cities(self) -> None:
        with self.assertRaises(weather_demo.DemoError):
            weather_demo.geocode("Osaka", offline=True)

    def test_unknown_intent_is_rejected(self) -> None:
        with self.assertRaises(weather_demo.DemoError):
            weather_demo.build_document(
                "Tokyo", intent="not_an_intent", offline=True
            )

    def test_cli_offline_outputs_json(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(DEMO_DIR / "weather_demo.py"),
                "Tokyo",
                "--offline",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["context"]["location"]["name"], "Tokyo")
        self.assertEqual(len(payload["weather_evidence"]), 72)

    def test_cli_accepts_query_and_intent(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(DEMO_DIR / "weather_demo.py"),
                "Tokyo",
                "--offline",
                "--query",
                "明天东京适合户外跑步吗？",
                "--intent",
                "outdoor_activity",
            ],
            capture_output=True,
            text=True,
            cwd=ROOT,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["user_query"], "明天东京适合户外跑步吗？")
        self.assertEqual(payload["intent"], "outdoor_activity")


if __name__ == "__main__":
    unittest.main(verbosity=2)
