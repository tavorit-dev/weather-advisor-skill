#!/usr/bin/env python3
"""Render a Weather Advisor response as a self-contained HTML card.

The card is a read-only view of a response that already conforms to
``schemas/recommendation.schema.json``, optionally annotated with the windowed
evidence from ``demo/weather_brief.py``. It adds no weather facts of its own: it
prints what the response and the brief contain, and nothing else.

Usage:
    python demo/weather_card.py response.json --output card.html
    python demo/weather_card.py response.json --brief brief.json --open
    python demo/weather_card.py --check card.html
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from weather_demo import DemoError, INTENTS
except ModuleNotFoundError:  # imported as demo.weather_card
    from demo.weather_demo import DemoError, INTENTS  # type: ignore[no-redef]

STATUS_LABELS = {
    "answered": "answered",
    "needs_clarification": "needs clarification",
    "insufficient_evidence": "insufficient evidence",
}
SEVERITY_LABELS = {
    "low": "low",
    "medium": "medium",
    "high": "high",
    "unknown": "unknown",
}
DEMO_GAP_LABELS = {
    "severe_weather_alert": "official alerts",
    "uv_index": "UV index",
    "humidity": "humidity",
    "visibility": "visibility",
    "thunderstorm": "thunderstorm",
}

# Rows in the summary tiles, and the mode used to read each one. Precipitation
# is summed over the window while the others are single hours, so it is read
# from both the window total and the wettest hour.
TILE_ROWS = (
    ("Temperature", "temperature", "°C", "min/max"),
    ("Rain chance", "precipitation_probability", "%", "max"),
    ("Precipitation", "precipitation_amount", "mm", "total"),
    ("Wind", "wind_speed", "km/h", "max"),
    ("PM2.5", "particulate_matter_2_5", "μg/m³", "max"),
    ("US AQI", "us_aqi", "USAQI", "min/max"),
)
# Tiles that only exist when the brief carries air quality. A tile with no
# value behind it is dropped rather than drawn as a dash, so a weather-only
# brief cannot look like a brief whose air quality failed to load.
AIR_TILES = ("PM2.5", "US AQI")

# Metrics plotted as a curve over the brief's hours: label, key in
# ``hours[].values``, unit, and the summary key the headline figure comes from.
CURVE_METRICS = (
    ("Temperature", "temperature", "temperature", "°C", "min/max"),
    ("Feels like", "apparent_temperature", "apparent_temperature", "°C", "min/max"),
    (
        "Rain chance",
        "precipitation_probability",
        "precipitation_probability",
        "%",
        "max",
    ),
    ("Precipitation", "precipitation_amount", "precipitation_amount", "mm", "max"),
    ("Wind", "wind_speed", "wind_speed", "km/h", "max"),
    ("Wind gusts", "wind_gust", "wind_gust", "km/h", "max"),
    ("PM2.5", "particulate_matter_2_5", "particulate_matter_2_5", "μg/m³", "max"),
    ("PM10", "particulate_matter_10", "particulate_matter_10", "μg/m³", "max"),
)
CURVE_WIDTH = 480
CURVE_HEIGHT = 120


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def fmt_number(value: Any, unit: str = "") -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "—"
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    text = f"{value:,.1f}" if isinstance(value, float) else f"{value:,}"
    if text.endswith(".0"):
        text = text[:-2]
    return f"{text} {unit}".strip() if unit else text


def fmt_clock(value: Any) -> str:
    """Render an ISO timestamp as its local wall-clock time."""
    if not isinstance(value, str):
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%H:%M")
    except ValueError:
        return "—"


def metric_values(label: str, values: dict[str, Any]) -> list[float]:
    """Return the numeric series for one row label across the brief's hours."""
    series: list[float] = []
    for hour in values.get("hours", []):
        value = (hour.get("values") or {}).get(label)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            series.append(float(value))
    return series


def metric_ids(label: str, values: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for hour in values.get("hours", []):
        evidence_id = (hour.get("evidence_ids") or {}).get(label)
        if isinstance(evidence_id, str) and evidence_id and evidence_id not in ids:
            ids.append(evidence_id)
    return ids


def extreme(
    summary: dict[str, Any], key: str, mode: str
) -> dict[str, Any] | None:
    """Return the extreme entry for one summary key, or None when absent."""
    group = (summary or {}).get(key)
    if not isinstance(group, dict):
        return None
    candidates = ["min", "max"] if mode == "min/max" else [mode]
    for name in candidates:
        entry = group.get(name)
        if isinstance(entry, dict) and isinstance(entry.get("value"), (int, float)):
            return entry
    return None


def format_extreme(entry: dict[str, Any] | None, unit: str) -> str:
    if not entry:
        return "—"
    return fmt_number(entry.get("value"), entry.get("unit") or unit)


def curve_points(
    series: list[float],
) -> tuple[list[tuple[float, float]], float, float]:
    """Map a series onto SVG coordinates with a little vertical padding."""
    low = min(series)
    high = max(series)
    span = high - low
    top = high + (span * 0.12 if span else 1.0)
    bottom = low - (span * 0.12 if span else 1.0)
    width = top - bottom
    step = CURVE_WIDTH / max(1, len(series) - 1)
    points = [
        (
            round(index * step, 2),
            round(CURVE_HEIGHT - ((value - bottom) / width) * CURVE_HEIGHT, 2),
        )
        for index, value in enumerate(series)
    ]
    return points, low, high


def sparkline(series: list[float], title: str) -> str:
    points, low, high = curve_points(series)
    if len(points) == 1:
        points = [(points[0][0], points[0][1]), (CURVE_WIDTH, points[0][1])]
    path = " ".join(f"{x},{y}" for x, y in points)
    first_x, first_y = points[0]
    last_x, last_y = points[-1]
    area = (
        f"{first_x},{CURVE_HEIGHT} {path} {last_x},{CURVE_HEIGHT}"
    )
    return (
        f'<svg class="curve" viewBox="0 0 {CURVE_WIDTH} {CURVE_HEIGHT}" '
        f'preserveAspectRatio="none" role="img" aria-label="{esc(title)}">'
        f'<polygon class="curve-area" points="{esc(area)}"/>'
        f'<polyline class="curve-line" points="{esc(path)}"/>'
        f'<circle class="curve-dot" cx="{last_x}" cy="{last_y}" r="4"/>'
        f"</svg>"
        f'<div class="curve-range"><span>{fmt_number(low)}</span>'
        f"<span>{fmt_number(high)}</span></div>"
    )


def read_json(path: Path, what: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DemoError(f"cannot read {what}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DemoError(f"{what} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DemoError(f"{what} must be a JSON object")
    return value


def check_response(response: dict[str, Any]) -> None:
    """Fail loudly on a response that is not a Weather Advisor response.

    The card only reads defined fields, so an unexpected key cannot leak into
    the markup; an unknown ``status`` or ``intent`` is reported instead of
    being rendered as an invented label.
    """
    for field in ("schema_version", "status", "intent", "summary"):
        if field not in response:
            raise DemoError(f"response is missing required field: {field}")
    status = response["status"]
    if status not in STATUS_LABELS:
        raise DemoError(f"unknown status: {status!r}")
    intent = response["intent"]
    if intent not in INTENTS:
        raise DemoError(f"unknown intent: {intent!r}")
    for field in ("evidence", "recommendations", "risks", "missing_information"):
        if not isinstance(response.get(field), list):
            raise DemoError(f"response field must be an array: {field}")
    question = response.get("clarification_question")
    if status == "needs_clarification" and not (
        isinstance(question, str) and question.strip()
    ):
        raise DemoError("needs_clarification requires a clarification_question")


def reference_html(ids: Any) -> str:
    if not isinstance(ids, list) or not ids:
        return ""
    chips = "".join(
        f'<span class="ref">{esc(item)}</span>' for item in ids if item
    )
    return f'<div class="refs">{chips}</div>' if chips else ""


def window_html(brief: dict[str, Any]) -> str:
    coverage = brief.get("coverage") or {}
    location = brief.get("location") or {}
    metrics = brief.get("summary") or {}

    window = esc(coverage.get("window", "—"))
    date = esc(coverage.get("date", "—"))
    detail = esc(coverage.get("detail", "—"))
    step = coverage.get("step_hours")
    included = coverage.get("hours_included")
    in_window = coverage.get("hours_in_window")
    mode = esc((brief.get("source") or {}).get("mode", "—"))
    name = esc(location.get("name", "—"))
    timezone = esc(location.get("timezone", "—"))

    air = brief.get("air_quality")
    has_air = isinstance(air, dict)

    cards = []
    for label, key, unit, mode in TILE_ROWS:
        if label in AIR_TILES and not has_air:
            continue
        if mode == "total":
            # The brief reports the window total and the wettest hour; showing
            # only one would misstate a summed quantity as a peak.
            total = extreme(metrics, key, "total")
            peak = extreme(metrics, key, "max_hour")
            if total is None and peak is None:
                continue
            value = (
                f'{fmt_number(total.get("value") if total else None)} total / '
                f'{fmt_number(peak.get("value") if peak else None)} peak'
            )
        else:
            entry = extreme(metrics, key, mode)
            if entry is None and mode == "min/max":
                # Some summaries carry only one extreme; show whichever exists.
                entry = extreme(metrics, key, "max") or extreme(metrics, key, "min")
            if entry is None:
                continue
            value = format_extreme(entry, unit)
        cards.append(
            '<div class="metric">'
            f'<div class="metric-label">{esc(label)}</div>'
            f'<div class="metric-value">{esc(value)}</div>'
            f'<div class="metric-unit">{esc(unit)}</div>'
            "</div>"
        )

    tiles_html = (
        '<div class="metrics">' + "".join(cards) + "</div>"
        if cards
        else '<p class="muted">The brief carries no summary values.</p>'
    )

    curves = []
    for label, values_key, summary_key, unit, mode_ in CURVE_METRICS:
        series = metric_values(values_key, brief)
        if len(series) < 2:
            continue
        ids = metric_ids(values_key, brief)
        peak = extreme(metrics, summary_key, mode_)
        if peak is None and series:
            peak = {"value": max(series), "unit": unit}
        curves.append(
            '<figure class="curve-card">'
            f'<figcaption><span>{esc(label)}</span>'
            f'<strong>{esc(format_extreme(peak, unit))} <small>{esc(unit)}</small></strong>'
            f"</figcaption>"
            f"{sparkline(series, f'{label} over {coverage.get('window', 'the window')}')}"
            f"{reference_html(ids)}"
            "</figure>"
        )

    curves_html = (
        '<div class="curves">' + "".join(curves) + "</div>"
        if curves
        else '<p class="muted">The brief has no hourly rows, so no curves are shown.</p>'
    )

    gaps = brief.get("demo_gaps") or []
    gap_labels = [DEMO_GAP_LABELS.get(gap, str(gap)) for gap in gaps]
    gaps_html = ""
    if gap_labels:
        gaps_html = (
            '<div class="notice notice-gap"><strong>Not covered by this demo</strong>'
            f"<p>{esc(', '.join(gap_labels))}. Absence of an alert here is not "
            "evidence that no alert is in effect.</p></div>"
        )

    air = brief.get("air_quality")
    air_html = ""
    if has_air:
        us = extreme(air, "us_aqi", "min/max")
        eu = extreme(air, "european_aqi", "min/max")
        air_html = (
            '<div class="notice notice-air"><strong>Air quality</strong>'
            f"<p>PM2.5 peak {esc(format_extreme(extreme(metrics, 'particulate_matter_2_5', 'max'), 'μg/m³'))}, "
            f"US AQI {esc(format_extreme(us, 'USAQI'))}, European AQI {esc(format_extreme(eu, 'EAQI'))}. "
            "Modelled forecast (CAMS), not a ground-station measurement; the two "
            "AQI scales are not directly comparable.</p></div>"
        )

    return (
        '<section class="card window">'
        '<div class="section-head"><h2>Window evidence</h2>'
        f'<span class="chip">{window}</span></div>'
        f'<div class="window-meta">{name} · {date} · {window} · '
        f"{esc(detail)}"
        + (
            f" · every {esc(step)}h"
            if isinstance(step, int) and step > 1
            else ""
        )
        + (
            f" · {esc(included)}/{esc(in_window)} hours shown"
            if isinstance(included, int) and isinstance(in_window, int)
            else ""
        )
        + f" · {timezone} · {mode} mode</div>"
        f"{tiles_html}"
        f"{curves_html}{air_html}{gaps_html}"
        "</section>"
    )


def body_html(response: dict[str, Any], brief: dict[str, Any] | None) -> str:
    summary = esc(response.get("summary", ""))
    evidence = response.get("evidence") or []
    recommendations = response.get("recommendations") or []
    risks = response.get("risks") or []
    missing = response.get("missing_information") or []
    uncertainty = response.get("uncertainty") or []
    question = response.get("clarification_question")

    status = esc(STATUS_LABELS[response["status"]])
    intent = esc(str(response["intent"]).replace("_", " "))
    version = esc(response.get("schema_version", ""))

    location = ""
    if brief:
        location = str((brief.get("location") or {}).get("name", ""))
    date = str((brief or {}).get("coverage", {}).get("date", ""))
    context_line = " · ".join(part for part in (location, date) if part)

    evidence_html = "".join(
        '<li class="evidence-item">'
        f'<span class="ref">{esc(item.get("evidence_id", ""))}</span>'
        f'<p>{esc(item.get("claim", ""))}</p></li>'
        for item in evidence
    ) or '<li class="muted">No evidence entries in this response.</li>'

    recommendations_html = "".join(
        '<li class="rec">'
        f'<p class="rec-action">{esc(item.get("action", ""))}</p>'
        f'<p class="rec-reason">{esc(item.get("reason", ""))}</p>'
        f"{reference_html(item.get('evidence_ids'))}</li>"
        for item in recommendations
    ) or '<li class="muted">No recommendations in this response.</li>'

    risks_html = "".join(
        '<li class="risk">'
        f'<span class="severity severity-{esc(item.get("severity", "unknown"))}">'
        f'{esc(SEVERITY_LABELS.get(item.get("severity"), "unknown"))}</span>'
        f'<div><p>{esc(item.get("description", ""))}</p>'
        f"{reference_html(item.get('evidence_ids'))}</div></li>"
        for item in risks
    ) or '<li class="muted">No risks listed in this response.</li>'

    clarification_html = ""
    if isinstance(question, str) and question.strip():
        clarification_html = (
            '<div class="notice notice-question"><strong>Clarification needed</strong>'
            f"<p>{esc(question)}</p></div>"
        )

    def list_block(title: str, items: list[Any], css: str) -> str:
        if not items:
            return ""
        entries = "".join(f"<li>{esc(item)}</li>" for item in items)
        return (
            f'<section class="card {css}"><h2>{esc(title)}</h2>'
            f"<ul>{entries}</ul></section>"
        )

    brief_window = window_html(brief) if brief else ""

    return (
        '<main class="card-stack">'
        '<header class="card header">'
        f'<div class="header-top"><span class="badge badge-{esc(response["status"])}">{status}</span>'
        f'<span class="intent">{intent}</span></div>'
        f'<h1>{esc(location or "Weather advice")}</h1>'
        + (f'<p class="context">{esc(context_line)}</p>' if context_line else "")
        + f'<p class="summary">{summary}</p>'
        f"{clarification_html}"
        "</header>"
        f"{brief_window}"
        '<section class="card"><h2>Evidence</h2>'
        f'<ul class="evidence">{evidence_html}</ul></section>'
        '<section class="card"><h2>Recommendations</h2>'
        f'<ul class="recommendations">{recommendations_html}</ul></section>'
        '<section class="card"><h2>Risks</h2>'
        f'<ul class="risks">{risks_html}</ul></section>'
        f"{list_block('Missing information', missing, 'missing')}"
        f"{list_block('Uncertainty', uncertainty, 'uncertainty')}"
        f'<footer class="card footer"><p>schema_version {version} · '
        f"intent {intent} · status {status}</p>"
        "<p>This card is a rendering of a Weather Advisor response and its "
        "windowed evidence. It contains no weather data of its own, and it is "
        "not an official warning or an official air-quality bulletin.</p>"
        "</footer>"
        "</main>"
    )


def source_html(brief: dict[str, Any]) -> str:
    source = brief.get("source") or {}
    parts = [
        source.get("attribution"),
        source.get("air_quality_attribution"),
    ]
    license_name = source.get("license")
    if license_name:
        parts.append(f"Licensed under {license_name}")
    if source.get("provider"):
        parts.insert(0, f"Source: {source['provider']}")
    text = " · ".join(str(part) for part in parts if part)
    return f'<p class="source">{esc(text)}</p>' if text else ""


def render_card(response: dict[str, Any], brief: dict[str, Any] | None) -> str:
    check_response(response)
    if brief is not None and not isinstance(brief.get("coverage"), dict):
        raise DemoError("brief is missing its coverage block")

    style = (Path(__file__).resolve().parent / "card.css").read_text(
        encoding="utf-8"
    )
    source = source_html(brief) if brief else ""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Weather Advisor Card</title>\n"
        f"<style>\n{style}\n</style>\n</head>\n<body>\n"
        f"{body_html(response, brief)}\n"
        f"{source}\n"
        "</body>\n</html>\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render a Weather Advisor response as an HTML card."
    )
    parser.add_argument(
        "response",
        nargs="?",
        type=Path,
        help="response JSON matching schemas/recommendation.schema.json",
    )
    parser.add_argument(
        "--brief",
        type=Path,
        help="optional compact brief from demo/weather_brief.py",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="write the card here (default: a temporary file)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="open the card in the default browser",
    )
    parser.add_argument(
        "--check",
        type=Path,
        metavar="CARD",
        help="validate an existing card file without writing a new one",
    )
    args = parser.parse_args(argv)

    try:
        if args.check is not None:
            text = args.check.read_text(encoding="utf-8")
            for required in ("<!doctype html>", "<style>", "</html>"):
                if required not in text:
                    raise DemoError(f"card is missing {required}")
            if "<script" in text:
                raise DemoError("card must not contain scripts")
            print(f"Card is well-formed: {args.check}")
            return 0

        if args.response is None:
            raise DemoError("a response file is required")
        response = read_json(args.response, "response")
        brief = read_json(args.brief, "brief") if args.brief else None
        card = render_card(response, brief)
    except (DemoError, OSError) as exc:
        print(f"Weather card failed: {exc}", file=sys.stderr)
        return 1

    if args.output:
        try:
            args.output.write_text(card, encoding="utf-8")
        except OSError as exc:
            print(f"Weather card failed: {exc}", file=sys.stderr)
            return 1
        target = args.output
        print(f"Wrote card to {target}", file=sys.stderr)
    else:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".html", prefix="weather-card-", delete=False,
            encoding="utf-8",
        )
        with handle:
            handle.write(card)
        target = Path(handle.name)
        print(target)

    if args.open:
        webbrowser.open(target.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
