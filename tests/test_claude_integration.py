#!/usr/bin/env python3
"""Tests for the Claude Code entry, installer, and optional Stop hook."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude" / "hooks" / "validate-weather-output.py"
INSTALLER = ROOT / "scripts" / "install_claude_skill.py"
ENTRY = ROOT / ".claude" / "skills" / "weather-advisor" / "SKILL.md"
VALID_OUTPUT = ROOT / "examples" / "commute-rain-output.json"
HAS_JSONSCHEMA = importlib.util.find_spec("jsonschema") is not None


def run(*args: object, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


class EntryTests(unittest.TestCase):
    def test_entry_has_claude_code_metadata(self) -> None:
        text = ENTRY.read_text(encoding="utf-8")
        self.assertIn("name: weather-advisor", text)
        self.assertIn("argument-hint:", text)
        self.assertIn("../../../SKILL.md", text)
        self.assertIn("demo/weather_demo.py", text)
        self.assertIn("tests/validate_schema.py", text)

    def test_canonical_skill_stays_portable(self) -> None:
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for field in ("argument-hint:", "disable-model-invocation:", "user-invocable:"):
            self.assertNotIn(field, text)


class InstallerTests(unittest.TestCase):
    def test_installer_creates_a_self_contained_skill(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "weather-advisor"
            result = run(INSTALLER, "--dest", dest)
            self.assertEqual(result.returncode, 0, result.stderr)

            entry = (dest / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("CANONICAL-SKILL.md", entry)
            self.assertNotIn("../../../SKILL.md", entry)
            self.assertTrue((dest / "CANONICAL-SKILL.md").is_file())
            self.assertTrue((dest / "references" / "intent-catalog.md").is_file())
            self.assertTrue((dest / "demo" / "weather_brief.py").is_file())
            self.assertFalse((dest / ".claude").exists())

            demo = run(dest / "demo" / "weather_demo.py", "Tokyo", "--offline")
            self.assertEqual(demo.returncode, 0, demo.stderr)
            envelope = json.loads(demo.stdout)
            self.assertEqual(envelope["metadata"]["mode"], "offline")
            self.assertIn("synthetic", envelope["metadata"]["data_note"])

            brief = run(
                dest / "demo" / "weather_brief.py",
                "Tokyo",
                "--offline",
                "--date",
                "2026-10-22",
                "--window",
                "08:00-12:00",
            )
            self.assertEqual(brief.returncode, 0, brief.stderr)
            self.assertEqual(json.loads(brief.stdout)["coverage"]["hours_included"], 4)

    def test_installer_refuses_to_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "weather-advisor"
            dest.mkdir()
            result = run(INSTALLER, "--dest", dest)
            self.assertEqual(result.returncode, 1)
            self.assertIn("--force", result.stderr)

    def test_installer_force_replaces_an_existing_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "weather-advisor"
            dest.mkdir()
            (dest / "stale.txt").write_text("old", encoding="utf-8")
            result = run(INSTALLER, "--dest", dest, "--force")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse((dest / "stale.txt").exists())
            self.assertTrue((dest / "CANONICAL-SKILL.md").is_file())


@unittest.skipUnless(HAS_JSONSCHEMA, "jsonschema is not installed")
class HookTests(unittest.TestCase):
    def make_transcript(self, directory: Path, text: str) -> Path:
        transcript = directory / "transcript.jsonl"
        entries = [
            {
                "type": "user",
                "message": {"role": "user", "content": "Return the advice as JSON."},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                },
            },
        ]
        transcript.write_text(
            "\n".join(json.dumps(entry) for entry in entries) + "\n",
            encoding="utf-8",
        )
        return transcript

    def test_valid_json_in_final_turn_passes(self) -> None:
        response = VALID_OUTPUT.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            transcript = self.make_transcript(
                Path(directory), f"```json\n{response}\n```"
            )
            payload = json.dumps({"transcript_path": str(transcript)})
            result = run(HOOK, stdin=payload)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_invalid_json_in_final_turn_blocks(self) -> None:
        response = json.loads(VALID_OUTPUT.read_text(encoding="utf-8"))
        response["status"] = "bogus"
        with tempfile.TemporaryDirectory() as directory:
            transcript = self.make_transcript(
                Path(directory),
                "```json\n" + json.dumps(response) + "\n```",
            )
            payload = json.dumps({"transcript_path": str(transcript)})
            result = run(HOOK, stdin=payload)
            self.assertEqual(result.returncode, 2)
            self.assertIn("failed schema validation", result.stderr)

    def test_conversational_answer_is_a_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            transcript = self.make_transcript(
                Path(directory), "Bring an umbrella; rain is likely."
            )
            payload = json.dumps({"transcript_path": str(transcript)})
            result = run(HOOK, stdin=payload)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_manual_validation(self) -> None:
        result = run(HOOK, VALID_OUTPUT)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
