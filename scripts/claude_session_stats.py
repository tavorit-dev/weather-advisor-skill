#!/usr/bin/env python3
"""Summarise the current Claude Code session's token usage and elapsed time.

The card must never invent its own cost figures, so this helper reads them
from Claude Code's session transcript: it sums the ``usage`` block of each
assistant response since the last prompt and measures the time from that
prompt to now. The output is what ``weather_card.py --stats`` renders.

The transcript is JSONL. The same assistant message is written once per
content block with an identical id and usage, so entries are deduplicated by
``message.id``; without that the token count would be several times too high.

Usage:
    python scripts/claude_session_stats.py --output stats.json
    python scripts/claude_session_stats.py --transcript t.jsonl --until ISO8601

This script is Claude Code-specific and stays outside the canonical skill.
It uses only the standard library and never accesses the network.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SOURCE = "claude-code-transcript"
INTERRUPT_MARKER = "[Request interrupted"


class StatsError(Exception):
    """A transcript could not be read or summarised."""


def parse_time(value: Any, what: str) -> datetime:
    """Parse an ISO 8601 timestamp; naive values are treated as UTC."""
    if not isinstance(value, str) or not value:
        raise StatsError(f"missing {what} timestamp")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise StatsError(f"invalid {what} timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def iso(value: datetime) -> str:
    """Render a timestamp the way Claude Code writes them."""
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def message_text(entry: dict[str, Any]) -> str:
    """Return the text a user entry carries, whether string or blocks."""
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def is_prompt(entry: dict[str, Any]) -> bool:
    """True for a real user prompt, not a tool result or injected context.

    Claude Code records tool results, skill content, and command caveats as
    ``user`` entries too. Only a typed prompt (including a slash command)
    starts a consultation, so everything else is skipped.
    """
    if entry.get("isMeta") or entry.get("isSidechain"):
        return False
    if "toolUseResult" in entry:
        return False
    text = message_text(entry).strip()
    if not text or text.startswith(INTERRUPT_MARKER):
        return False
    return True


def find_transcript(args: argparse.Namespace) -> Path:
    """Locate the transcript explicitly, or by the current session id."""
    if args.transcript is not None:
        path = args.transcript.expanduser()
        if not path.is_file():
            raise StatsError(f"cannot read transcript: {path}")
        return path

    session_id = args.session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session_id:
        raise StatsError(
            "no transcript: pass --transcript or set CLAUDE_CODE_SESSION_ID"
        )
    config_dir = Path(
        args.config_dir
        or os.environ.get("CLAUDE_CONFIG_DIR")
        or Path.home() / ".claude"
    ).expanduser()
    projects = config_dir / "projects"
    matches = sorted(projects.glob(f"*/{session_id}.jsonl"))
    if not matches:
        raise StatsError(
            f"cannot find transcript for session {session_id} under {projects}"
        )
    if len(matches) == 1:
        return matches[0]
    # The session id is unique, but a copied project directory could contain
    # an older duplicate; the most recently written one is the live session.
    return max(matches, key=lambda path: path.stat().st_mtime)


def load_entries(path: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    # A partially written final line is normal while a session
                    # is live; it is skipped rather than failing the report.
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except OSError as exc:
        raise StatsError(f"cannot read transcript: {exc}") from exc
    return entries


def usage_value(usage: dict[str, Any], name: str) -> int:
    value = usage.get(name, 0)
    if value is None:
        return 0
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise StatsError(f"invalid usage value: {name}={value!r}")
    return int(value)


def summarise(entries: list[dict[str, Any]], until: datetime) -> dict[str, Any]:
    """Sum assistant usage since the last prompt and measure elapsed time."""
    starts: list[datetime] = []
    for entry in entries:
        if entry.get("type") != "user" or not is_prompt(entry):
            continue
        try:
            stamp = parse_time(entry.get("timestamp"), "entry")
        except StatsError:
            continue
        if stamp <= until:
            starts.append(stamp)
    if not starts:
        raise StatsError("no user prompt found in transcript")
    start = max(starts)

    seen: set[str] = set()
    requests = 0
    input_tokens = output_tokens = 0
    cache_read = cache_creation = 0
    model: str | None = None
    for index, entry in enumerate(entries):
        if entry.get("type") != "assistant":
            continue
        try:
            stamp = parse_time(entry.get("timestamp"), "entry")
        except StatsError:
            continue
        if stamp < start or stamp > until:
            continue
        message = entry.get("message") or {}
        message_id = message.get("id")
        key = (
            message_id
            if isinstance(message_id, str) and message_id
            else entry.get("uuid") or f"line-{index}"
        )
        if key in seen:
            continue
        seen.add(key)

        usage = message.get("usage") or {}
        fresh = usage_value(usage, "input_tokens")
        cached = usage_value(usage, "cache_read_input_tokens")
        created = usage_value(usage, "cache_creation_input_tokens")
        input_tokens += fresh + cached + created
        output_tokens += usage_value(usage, "output_tokens")
        cache_read += cached
        cache_creation += created
        requests += 1
        if isinstance(message.get("model"), str) and message["model"]:
            model = message["model"]

    if not requests:
        raise StatsError("no assistant usage found after the last prompt")

    elapsed = int(round((until - start).total_seconds()))
    stats: dict[str, Any] = {
        "source": SOURCE,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_input_tokens": cache_read,
        "cache_creation_input_tokens": cache_creation,
        "elapsed_seconds": max(0, elapsed),
        "requests": requests,
        "started_at": iso(start),
        "generated_at": iso(until),
    }
    if model is not None:
        stats["model"] = model
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report the current Claude Code session's token usage "
        "and elapsed time since the last prompt."
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        help="read this transcript instead of locating the current session",
    )
    parser.add_argument(
        "--session-id",
        help="Claude Code session id; defaults to $CLAUDE_CODE_SESSION_ID",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        help="Claude Code config directory; defaults to $CLAUDE_CONFIG_DIR "
        "or ~/.claude",
    )
    parser.add_argument(
        "--until",
        help="measure up to this ISO 8601 time instead of now",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the stats JSON here instead of stdout",
    )
    args = parser.parse_args(argv)

    try:
        until = (
            parse_time(args.until, "--until")
            if args.until
            else datetime.now(timezone.utc)
        )
        transcript = find_transcript(args)
        stats = summarise(load_entries(transcript), until)
    except StatsError as exc:
        print(f"Session stats failed: {exc}", file=sys.stderr)
        return 1

    text = json.dumps(stats, ensure_ascii=False, indent=2) + "\n"
    if args.output is not None:
        try:
            args.output.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"Session stats failed: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote session stats to {args.output}", file=sys.stderr)
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
