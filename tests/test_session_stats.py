#!/usr/bin/env python3
"""Tests for the Claude Code session-stats helper used by the card.

The helper reads the current session's transcript and reports the token usage
and elapsed time since the last prompt. Tests use synthetic transcripts so
nothing here depends on a real session or the network.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "claude_session_stats.py"


def run(
    *args: object, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def prompt(
    timestamp: str,
    text: str = "明天上海通勤要带伞吗？",
    *,
    is_meta: bool = False,
    sidechain: bool = False,
) -> dict:
    return {
        "type": "user",
        "timestamp": timestamp,
        "isMeta": is_meta,
        "isSidechain": sidechain,
        "message": {"role": "user", "content": text},
    }


def tool_result(timestamp: str) -> dict:
    return {
        "type": "user",
        "timestamp": timestamp,
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "content": "ok"}],
        },
        "toolUseResult": {"ok": True},
    }


def assistant(
    message_id: str,
    timestamp: str,
    *,
    model: str | None = "test-model",
    input_tokens: int = 0,
    output_tokens: int = 0,
    cache_read: int = 0,
    cache_creation: int = 0,
) -> dict:
    message: dict = {
        "id": message_id,
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_input_tokens": cache_read,
            "cache_creation_input_tokens": cache_creation,
        },
    }
    if model is not None:
        message["model"] = model
    return {
        "type": "assistant",
        "timestamp": timestamp,
        "message": message,
    }


class SessionStatsTests(unittest.TestCase):
    def write(self, lines: list[dict] | list[str]) -> Path:
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        path = directory / "transcript.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for line in lines:
                if isinstance(line, str):
                    handle.write(line + "\n")
                else:
                    handle.write(json.dumps(line, ensure_ascii=False) + "\n")
        return path

    def stats(
        self,
        lines: list[dict] | list[str],
        *extra: object,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        path = self.write(lines)
        result = run(HELPER, "--transcript", path, *extra)
        payload = {}
        if result.returncode == 0 and result.stdout.strip():
            payload = json.loads(result.stdout)
        return result, payload

    def test_sums_input_output_and_cache_tokens_after_the_prompt(self) -> None:
        result, stats = self.stats(
            [
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=100,
                    output_tokens=20,
                    cache_read=25,
                    cache_creation=5,
                ),
                assistant(
                    "msg-b",
                    "2026-10-27T10:00:20Z",
                    input_tokens=50,
                    output_tokens=10,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        # Input covers every prompt token: fresh input plus cache creation and
        # cache reads. Reporting only input_tokens would understate the prompt.
        self.assertEqual(stats["input_tokens"], 100 + 25 + 5 + 50)
        self.assertEqual(stats["output_tokens"], 30)
        self.assertEqual(stats["cache_read_input_tokens"], 25)
        self.assertEqual(stats["requests"], 2)
        self.assertEqual(stats["elapsed_seconds"], 30)
        self.assertEqual(stats["model"], "test-model")
        self.assertEqual(stats["source"], "claude-code-transcript")

    def test_repeated_message_ids_are_counted_once(self) -> None:
        """Claude Code writes one line per content block for the same message."""
        result, stats = self.stats(
            [prompt("2026-10-27T10:00:00Z")]
            + [
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=100,
                    output_tokens=20,
                )
            ]
            * 3,
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stats["input_tokens"], 100)
        self.assertEqual(stats["output_tokens"], 20)
        self.assertEqual(stats["requests"], 1)

    def test_usage_before_the_last_prompt_is_not_counted(self) -> None:
        result, stats = self.stats(
            [
                prompt("2026-10-27T09:00:00Z", "先前的提问"),
                assistant(
                    "msg-old",
                    "2026-10-27T09:00:05Z",
                    input_tokens=9999,
                    output_tokens=9999,
                ),
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-new",
                    "2026-10-27T10:00:05Z",
                    input_tokens=10,
                    output_tokens=5,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stats["input_tokens"], 10)
        self.assertEqual(stats["output_tokens"], 5)
        self.assertEqual(stats["elapsed_seconds"], 30)

    def test_tool_results_and_meta_messages_do_not_reset_the_start(self) -> None:
        result, stats = self.stats(
            [
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=10,
                    output_tokens=5,
                ),
                tool_result("2026-10-27T10:00:10Z"),
                prompt(
                    "2026-10-27T10:00:15Z",
                    "Base directory for this skill: /tmp",
                    is_meta=True,
                ),
                assistant(
                    "msg-b",
                    "2026-10-27T10:00:20Z",
                    input_tokens=20,
                    output_tokens=6,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stats["elapsed_seconds"], 30)
        self.assertEqual(stats["input_tokens"], 30)

    def test_a_slash_command_counts_as_the_prompt(self) -> None:
        result, stats = self.stats(
            [
                prompt(
                    "2026-10-27T10:00:00Z",
                    "<command-name>/weather-advisor-card</command-name>\n"
                    "<command-args>上海 通勤</command-args>",
                ),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=10,
                    output_tokens=5,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stats["elapsed_seconds"], 30)
        self.assertEqual(stats["input_tokens"], 10)

    def test_interrupt_markers_do_not_reset_the_start(self) -> None:
        result, stats = self.stats(
            [
                prompt("2026-10-27T10:00:00Z"),
                prompt("2026-10-27T10:00:10Z", "[Request interrupted by user]"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:20Z",
                    input_tokens=10,
                    output_tokens=5,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stats["elapsed_seconds"], 30)

    def test_a_missing_model_is_omitted(self) -> None:
        result, stats = self.stats(
            [
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    model=None,
                    input_tokens=10,
                    output_tokens=5,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("model", stats)

    def test_malformed_lines_are_skipped(self) -> None:
        result, stats = self.stats(
            [
                "{not json",
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=10,
                    output_tokens=5,
                ),
            ],
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(stats["input_tokens"], 10)

    def test_output_file_is_written(self) -> None:
        path = self.write(
            [
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=10,
                    output_tokens=5,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory) / "stats.json"
            result = run(
                HELPER,
                "--transcript",
                path,
                "--until",
                "2026-10-27T10:00:30Z",
                "--output",
                out,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            stats = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(stats["input_tokens"], 10)
        self.assertEqual(stats["source"], "claude-code-transcript")

    def test_session_id_locates_the_transcript(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory)
            project = config / "projects" / "-tmp-project"
            project.mkdir(parents=True)
            transcript = project / "session-123.jsonl"
            transcript.write_text(
                "\n".join(
                    json.dumps(line)
                    for line in (
                        prompt("2026-10-27T10:00:00Z"),
                        assistant(
                            "msg-a",
                            "2026-10-27T10:00:05Z",
                            input_tokens=10,
                            output_tokens=5,
                        ),
                    )
                )
                + "\n",
                encoding="utf-8",
            )
            env = {
                **os.environ,
                "CLAUDE_CONFIG_DIR": str(config),
                "CLAUDE_CODE_SESSION_ID": "session-123",
            }
            result = run(
                HELPER,
                "--until",
                "2026-10-27T10:00:30Z",
                env=env,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["input_tokens"], 10)

    def test_missing_transcript_is_an_error(self) -> None:
        result = run(HELPER, "--transcript", "/nonexistent/transcript.jsonl")
        self.assertEqual(result.returncode, 1)
        self.assertIn("transcript", result.stderr)

    def test_no_usage_after_the_prompt_is_an_error(self) -> None:
        path = self.write([prompt("2026-10-27T10:00:00Z")])
        result = run(
            HELPER,
            "--transcript",
            path,
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("no assistant", result.stderr)

    def test_negative_usage_is_an_error(self) -> None:
        path = self.write(
            [
                prompt("2026-10-27T10:00:00Z"),
                assistant(
                    "msg-a",
                    "2026-10-27T10:00:05Z",
                    input_tokens=-5,
                ),
            ]
        )
        result = run(
            HELPER,
            "--transcript",
            path,
            "--until",
            "2026-10-27T10:00:30Z",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("usage", result.stderr)

    def test_helper_needs_no_network_or_third_party_packages(self) -> None:
        source = HELPER.read_text(encoding="utf-8")
        for marker in ("urllib", "requests", "http.client", "socket"):
            self.assertNotIn(f"import {marker}", source)


if __name__ == "__main__":
    unittest.main()
