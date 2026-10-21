#!/usr/bin/env python3
"""Build a compact weather brief from the demo's evidence.

The brief keeps only the requested date and window, summary statistics, and the
evidence IDs needed for citations. It is a token-efficient view of
``demo/weather_demo.py``, not a new data source and not a recommendation engine.

Usage:
    python demo/weather_brief.py Tianjin --date today --window 13:00-18:00
    python demo/weather_brief.py Tianjin --date tomorrow
    python demo/weather_brief.py Tokyo --offline --date 2026-10-22 --window 08:00-12:00
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    from weather_demo import (
        INTENTS,
        DemoError,
        build_evidence,
        fetch_forecast,
        geocode,
    )
except ModuleNotFoundError:  # imported as demo.weather_brief
    from demo.weather_demo import (  # type: ignore[no-redef]
        INTENTS,
        DemoError,
        build_evidence,
        fetch_forecast,
        geocode,
    )

WINDOW_RE = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})$")
VALUE_TYPES = [
    "temperature",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation_amount",
    "wind_speed",
    "wind_gust",
]
DEMO_GAPS = [
    "severe_weather_alert",
    "air_quality",
    "uv_index",
    "humidity",
    "visibility",
    "thunderstorm",
]


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def resolve_date(
    value: str, timezone: ZoneInfo, *, offline: bool = False
) -> tuple[date, int]:
    today = datetime.now(timezone).date()
    if value == "today":
        target = today
    elif value == "tomorrow":
        target = today + timedelta(days=1)
    else:
        try:
            target = date.fromisoformat(value)
        except ValueError as exc:
            raise DemoError(
                "--date must be today, tomorrow, or YYYY-MM-DD"
            ) from exc

    days = (target - today).days + 1
    # The offline fixture is synthetic and fixed in time, so its date can be in
    # the past relative to the wall clock. Live forecasts cannot.
    if not offline and days < 1:
        raise DemoError("--date cannot be in the past for a forecast")
    if not offline and days > 7:
        raise DemoError("--date is beyond the demo's 7-day forecast range")
    return target, max(1, days)


def resolve_window(
    value: str | None,
    target: date,
    timezone: ZoneInfo,
    *,
    full_day: bool,
) -> tuple[datetime, datetime, str]:
    if value:
        match = WINDOW_RE.fullmatch(value.strip())
        if not match:
            raise DemoError("--window must look like HH:MM-HH:MM")
        start_hour, start_minute, end_hour, end_minute = map(int, match.groups())
        if start_hour > 23 or start_minute > 59:
            raise DemoError("--window start is not a valid time")
        start = datetime.combine(
            target, time(start_hour, start_minute), tzinfo=timezone
        )
        if end_hour == 24 and end_minute == 0:
            end = datetime.combine(
                target + timedelta(days=1), time(0, 0), tzinfo=timezone
            )
        elif end_hour > 23 or end_minute > 59:
            raise DemoError("--window end is not a valid time")
        else:
            end = datetime.combine(
                target, time(end_hour, end_minute), tzinfo=timezone
            )
        if end <= start:
            raise DemoError("--window end must be after its start")
        return start, end, value.strip()

    start = datetime.combine(target, time(0, 0), tzinfo=timezone)
    end = start + timedelta(days=1)
    if not full_day and target == datetime.now(timezone).date():
        now = datetime.now(timezone)
        start = now.replace(minute=0, second=0, microsecond=0)
    end_label = "24:00" if end.date() > start.date() else f"{end:%H:%M}"
    return start, end, f"{start:%H:%M}-{end_label}"


def stat(
    rows: dict[datetime, dict[str, dict[str, Any]]],
    evidence_type: str,
    mode: str,
) -> dict[str, Any] | None:
    pairs = [
        (row[evidence_type]["value"], row[evidence_type]["id"], row[evidence_type]["unit"])
        for row in rows.values()
        if evidence_type in row
    ]
    if not pairs:
        return None
    if mode == "min":
        value, evidence_id, unit = min(pairs, key=lambda item: item[0])
    elif mode == "max":
        value, evidence_id, unit = max(pairs, key=lambda item: item[0])
    elif mode == "sum":
        value = sum(item[0] for item in pairs)
        evidence_id = ""
        unit = pairs[0][2]
    else:  # pragma: no cover - internal misuse
        raise ValueError(f"Unknown stat mode: {mode}")
    result: dict[str, Any] = {"value": value, "unit": unit}
    if evidence_id:
        result["evidence_id"] = evidence_id
    return result


def build_brief(
    *,
    location: dict[str, Any],
    timezone: ZoneInfo,
    target: date,
    days: int,
    start: datetime,
    end: datetime,
    window_label: str,
    query: str,
    intent: str,
    offline: bool,
) -> dict[str, Any]:
    forecast = fetch_forecast(location, days=days, offline=offline)
    retrieved_at = datetime.now(timezone).isoformat(timespec="seconds")
    evidence = build_evidence(location, forecast, retrieved_at)

    rows: dict[datetime, dict[str, dict[str, Any]]] = {}
    available_types: set[str] = set()
    for item in evidence:
        available_types.add(item["type"])
        hour = datetime.fromisoformat(item["valid_from"])
        if start <= hour < end:
            rows.setdefault(hour, {})[item["type"]] = item

    if not rows:
        raise DemoError("No evidence covers the requested date and window")

    hours = []
    for hour in sorted(rows):
        values: dict[str, Any] = {}
        ids: dict[str, str] = {}
        ordered_types = [
            evidence_type
            for evidence_type in VALUE_TYPES
            if evidence_type in rows[hour]
        ]
        ordered_types += sorted(set(rows[hour]) - set(VALUE_TYPES))
        for evidence_type in ordered_types:
            item = rows[hour][evidence_type]
            values[evidence_type] = item["value"]
            ids[evidence_type] = item["id"]
        hours.append(
            {
                "time": hour.strftime("%H:%M"),
                "values": values,
                "evidence_ids": ids,
            }
        )

    return {
        "user_query": query,
        "intent": intent,
        "location": location,
        "coverage": {
            "date": target.isoformat(),
            "window": window_label,
            "hours_included": len(hours),
            "source_start": min(item["valid_from"] for item in evidence),
            "source_end": max(item["valid_to"] for item in evidence),
        },
        "summary": {
            "temperature": {
                "min": stat(rows, "temperature", "min"),
                "max": stat(rows, "temperature", "max"),
            },
            "apparent_temperature": {
                "min": stat(rows, "apparent_temperature", "min"),
                "max": stat(rows, "apparent_temperature", "max"),
            },
            "precipitation_probability": {
                "max": stat(rows, "precipitation_probability", "max"),
            },
            "precipitation_amount": {
                "total": stat(rows, "precipitation_amount", "sum"),
                "max_hour": stat(rows, "precipitation_amount", "max"),
            },
            "wind_speed": {"max": stat(rows, "wind_speed", "max")},
            "wind_gust": {"max": stat(rows, "wind_gust", "max")},
        },
        "hours": hours,
        "source": {
            "provider": "Open-Meteo",
            "mode": "offline" if offline else "live",
            "retrieved_at": retrieved_at,
            "attribution": "Weather data by Open-Meteo.com",
            "license": "CC BY 4.0",
        },
        "available_evidence_types": sorted(available_types),
        "demo_gaps": DEMO_GAPS,
        "note": (
            "Compact brief derived from demo evidence; only the requested window "
            "is included. It is not a recommendation and not a substitute for "
            "official warnings or air-quality data."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a compact weather brief from Open-Meteo demo evidence."
    )
    parser.add_argument("city", help="city name, for example Tianjin")
    parser.add_argument(
        "--date",
        default="today",
        help="today, tomorrow, or YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--window",
        default=None,
        help="HH:MM-HH:MM in the location timezone; defaults to the remaining day "
        "for today, or the full day for later dates",
    )
    parser.add_argument(
        "--full-day",
        action="store_true",
        help="include the whole requested date even when it is today",
    )
    parser.add_argument("--query", default="", help="user query to echo in the brief")
    parser.add_argument(
        "--intent",
        default="general_weather_advice",
        choices=sorted(INTENTS),
        help="intent to echo in the brief",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="use the bundled Tokyo fixture and make no network call",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the brief to this file instead of stdout",
    )
    args = parser.parse_args(argv)

    try:
        location = geocode(args.city, offline=args.offline)
        timezone = _zone(location["timezone"])
        target, days = resolve_date(args.date, timezone, offline=args.offline)
        start, end, window_label = resolve_window(
            args.window, target, timezone, full_day=args.full_day
        )
        brief = build_brief(
            location=location,
            timezone=timezone,
            target=target,
            days=days,
            start=start,
            end=end,
            window_label=window_label,
            query=args.query,
            intent=args.intent,
            offline=args.offline,
        )
    except DemoError as exc:
        print(f"Weather brief failed: {exc}", file=sys.stderr)
        return 1

    payload = json.dumps(brief, ensure_ascii=False, indent=2)
    if args.output:
        try:
            args.output.write_text(payload + "\n", encoding="utf-8")
        except OSError as exc:
            print(f"Weather brief failed: {exc}", file=sys.stderr)
            return 1
        print(f"Wrote compact brief to {args.output}", file=sys.stderr)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
