#!/usr/bin/env python3
"""Validate a Weather Advisor JSON response against the repository schema.

Two modes:

* Manual: ``python3 .claude/hooks/validate-weather-output.py response.json``
* Stop hook: read the hook payload from stdin, find the last weather JSON block
  in the final assistant turn, and validate it. A missing dependency or no
  weather JSON is treated as a no-op.

Exit codes: 0 = valid or nothing to validate, 2 = validation failed or the
hook payload could not be used (Stop hooks treat 2 as blocking).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "tests" / "validate_schema.py"
FENCE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.IGNORECASE | re.DOTALL)


def looks_like_weather_response(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "schema_version" in value
        and "status" in value
        and "recommendations" in value
    )


def weather_blocks(text: str) -> list[dict[str, Any]]:
    """Return JSON objects in fenced blocks that look like skill responses."""
    found: list[dict[str, Any]] = []
    for match in FENCE.finditer(text):
        try:
            value = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        if looks_like_weather_response(value):
            found.append(value)
    return found


def is_human_turn(entry: dict[str, Any]) -> bool:
    if entry.get("type") != "user":
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        return any(
            isinstance(part, dict) and part.get("type") == "text"
            for part in content
        )
    return False


def assistant_texts(entry: dict[str, Any]) -> Iterable[str]:
    if entry.get("type") != "assistant":
        return []
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
    return []


def final_turn_text(transcript_path: Path) -> str:
    entries: list[dict[str, Any]] = []
    with transcript_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                entries.append(entry)

    start = 0
    for index, entry in enumerate(entries):
        if is_human_turn(entry):
            start = index + 1

    texts: list[str] = []
    for entry in entries[start:]:
        texts.extend(assistant_texts(entry))
    return "\n\n".join(texts)


def validate_payload(payload: dict[str, Any]) -> tuple[int, str]:
    text = payload.get("last_assistant_message")
    if not isinstance(text, str) or not text.strip():
        transcript_path = payload.get("transcript_path")
        if not isinstance(transcript_path, str):
            return 0, ""
        path = Path(transcript_path).expanduser()
        if not path.is_file():
            return 0, ""
        text = final_turn_text(path)

    blocks = weather_blocks(text)
    if not blocks:
        return 0, ""
    return validate_object(blocks[-1], hook_mode=True)


def validator_python() -> str:
    """Prefer the repository virtualenv when it exists."""
    candidates = [
        ROOT / ".venv" / "bin" / "python",
        ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def validate_object(value: Any, hook_mode: bool) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="weather-advisor-") as directory:
        target = Path(directory) / "response.json"
        target.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [validator_python(), str(VALIDATOR), str(target)],
            capture_output=True,
            text=True,
            check=False,
        )

    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        return 0, ""
    if "Missing dependency" in output:
        print(
            "weather-advisor hook: skipped schema validation because jsonschema "
            "is not installed; run `python -m pip install -r tests/requirements.txt`.",
            file=sys.stderr,
        )
        return (0, "") if hook_mode else (2, output)
    if hook_mode:
        return 2, f"Weather Advisor output failed schema validation:\n{output}"
    return 2, output


def validate_file(path: Path) -> tuple[int, str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return 2, f"Cannot read weather response: {exc}"
    return validate_object(value, hook_mode=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a Weather Advisor JSON response against the schema."
    )
    parser.add_argument(
        "file",
        nargs="?",
        type=Path,
        help="response JSON file; omit when used as a Stop hook",
    )
    args = parser.parse_args()

    if args.file is not None:
        code, message = validate_file(args.file)
    else:
        try:
            payload = json.load(sys.stdin)
        except (json.JSONDecodeError, OSError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        code, message = validate_payload(payload)

    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
