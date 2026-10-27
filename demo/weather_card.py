#!/usr/bin/env python3
"""Render a Weather Advisor response as a self-contained HTML card.

The card is a read-only view of a response that already conforms to
``schemas/recommendation.schema.json``, optionally annotated with the windowed
evidence from ``demo/weather_brief.py``. It adds no weather facts of its own: it
prints what the response and the brief contain, and nothing else.

Only the card's own interface labels are translated. The response's prose
(summary, claims, actions, reasons, risks) is printed exactly as the response
supplied it, in whatever language that is; the renderer never rewrites it.

Usage:
    python demo/weather_card.py response.json --output card.html
    python demo/weather_card.py response.json --brief brief.json --open
    python demo/weather_card.py response.json --lang zh --open
    python demo/weather_card.py response.json --print --output card.html
    python demo/weather_card.py --check card.html
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
import unicodedata
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from weather_demo import DemoError, INTENTS
except ModuleNotFoundError:  # imported as demo.weather_card
    from demo.weather_demo import DemoError, INTENTS  # type: ignore[no-redef]

# Interface strings. Keys are stable identifiers; values are per-language.
# Adding a language means adding one column, not touching the markup.
STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "title": "Weather Advisor Card",
        "html_lang": "en",
        "answered": "answered",
        "needs_clarification": "needs clarification",
        "insufficient_evidence": "insufficient evidence",
        "low": "low",
        "medium": "medium",
        "high": "high",
        "unknown": "unknown",
        "severe_weather_alert": "official alerts",
        "uv_index": "UV index",
        "humidity": "humidity",
        "visibility": "visibility",
        "thunderstorm": "thunderstorm",
        "temperature": "Temperature",
        "apparent_temperature": "Feels like",
        "precipitation_probability": "Rain chance",
        "precipitation_amount": "Precipitation",
        "wind_speed": "Wind",
        "wind_gust": "Wind gusts",
        "particulate_matter_2_5": "PM2.5",
        "particulate_matter_10": "PM10",
        "us_aqi": "US AQI",
        "european_aqi": "European AQI",
        "weather_lookup": "weather lookup",
        "clothing_advice": "clothing advice",
        "commute_advice": "commute advice",
        "outdoor_activity": "outdoor activity",
        "travel_planning": "travel planning",
        "general_weather_advice": "general weather advice",
        "detail_hourly": "hourly",
        "detail_sparse": "sparse",
        "detail_summary": "summary",
        "mode_live": "live",
        "mode_offline": "offline",
        "window_evidence": "Window evidence",
        "window_evidence_hint": (
            "Hourly figures behind the advice. Every number here traces back to "
            "an evidence entry listed under Evidence."
        ),
        "no_summary_values": "The brief carries no summary values.",
        "no_curves": "The brief has no hourly rows, so no curves are shown.",
        "not_covered": "Not covered by this demo",
        "not_covered_intro": (
            "This demo has no data source for these, so their absence here says "
            "nothing about the location:"
        ),
        "not_covered_body": (
            "Absence of an alert here is not evidence that no alert is in effect."
        ),
        "air_quality": "Air quality",
        "air_quality_body": (
            "PM2.5 peak {pm25}, US AQI {us}, European AQI {eu}. Modelled "
            "forecast (CAMS), not a ground-station measurement; the two AQI "
            "scales are not directly comparable."
        ),
        "evidence": "Evidence",
        "evidence_count": "Evidence ({count})",
        "evidence_note": (
            "Why IDs are shown: each recommendation and risk cites these "
            "evidence IDs, so any figure on the card can be traced back to the "
            "entry it came from."
        ),
        "recommendations": "Recommendations",
        "recommendations_hint": "What to do, and why.",
        "risks": "Risks",
        "missing_information": "Missing information",
        "uncertainty": "Uncertainty",
        "clarification_needed": "Clarification needed",
        "no_evidence": "No evidence entries in this response.",
        "no_recommendations": "No recommendations in this response.",
        "no_risks": "No risks listed in this response.",
        "show_details": "Show",
        "hide_details": "Hide",
        "weather_advice": "Weather advice",
        "hours_shown": "{included}/{total} hours shown",
        "every_hours": "every {step}h",
        "mode": "{mode} mode",
        "total_peak": "{total} total / {peak} peak",
        "curve_label": "{label} over {window}",
        "footer_meta": "schema_version {version} · intent {intent} · status {status}",
        "footer_disclaimer": (
            "This card is a rendering of a Weather Advisor response and its "
            "windowed evidence. It contains no weather data of its own, and it "
            "is not an official warning or an official air-quality bulletin."
        ),
        "source_prefix": "Source: {provider}",
        "licensed_under": "Licensed under {license}",
        "print_hint": "Print or save as PDF to export this card as an image.",
    },
    "zh": {
        "title": "天气建议卡片",
        "html_lang": "zh-CN",
        "answered": "已回答",
        "needs_clarification": "需要澄清",
        "insufficient_evidence": "证据不足",
        "low": "低",
        "medium": "中",
        "high": "高",
        "unknown": "未知",
        "severe_weather_alert": "官方预警",
        "uv_index": "紫外线指数",
        "humidity": "湿度",
        "visibility": "能见度",
        "thunderstorm": "雷暴",
        "temperature": "气温",
        "apparent_temperature": "体感温度",
        "precipitation_probability": "降水概率",
        "precipitation_amount": "降水量",
        "wind_speed": "风速",
        "wind_gust": "阵风",
        "particulate_matter_2_5": "PM2.5",
        "particulate_matter_10": "PM10",
        "us_aqi": "US AQI",
        "european_aqi": "European AQI",
        "weather_lookup": "天气查询",
        "clothing_advice": "穿衣建议",
        "commute_advice": "通勤建议",
        "outdoor_activity": "户外活动",
        "travel_planning": "出行规划",
        "general_weather_advice": "通用天气建议",
        "detail_hourly": "逐小时",
        "detail_sparse": "稀疏采样",
        "detail_summary": "仅统计值",
        "mode_live": "实时",
        "mode_offline": "离线",
        "window_evidence": "时段证据",
        "window_evidence_hint": (
            "建议背后的逐小时数据。这里的每个数字都能在下方「证据」中找到对应条目。"
        ),
        "no_summary_values": "该摘要不含统计值。",
        "no_curves": "该摘要没有逐小时数据，因此不绘制曲线。",
        "not_covered": "本 demo 未覆盖",
        "not_covered_intro": "本 demo 没有接入以下数据源，因此此处不显示它们并不代表当地没有：",
        "not_covered_body": "此处没有预警信息，不等于没有预警生效。",
        "air_quality": "空气质量",
        "air_quality_body": (
            "PM2.5 峰值 {pm25}，US AQI {us}，European AQI {eu}。"
            "CAMS 预报模型输出，非地面监测站实测值；两套 AQI 标度不可直接比较。"
        ),
        "evidence": "证据",
        "evidence_count": "证据（{count} 条）",
        "evidence_note": (
            "为什么显示 ID：每条建议和风险都引用了这些证据 ID，"
            "卡片上的每个数字都能据此追溯到来源条目。"
        ),
        "recommendations": "建议",
        "recommendations_hint": "该做什么，以及为什么。",
        "risks": "风险",
        "missing_information": "缺失信息",
        "uncertainty": "不确定性",
        "clarification_needed": "需要澄清",
        "no_evidence": "该响应中没有证据条目。",
        "no_recommendations": "该响应中没有建议。",
        "no_risks": "该响应中没有列出风险。",
        "show_details": "展开",
        "hide_details": "收起",
        "weather_advice": "天气建议",
        "hours_shown": "显示 {included}/{total} 小时",
        "every_hours": "每 {step} 小时",
        "mode": "{mode} 模式",
        "total_peak": "合计 {total} / 峰值 {peak}",
        "curve_label": "{window} 内的{label}",
        "footer_meta": "schema_version {version} · 意图 {intent} · 状态 {status}",
        "footer_disclaimer": (
            "本卡片是 Weather Advisor 响应及其时段证据的渲染结果，本身不含任何"
            "天气数据，也不构成官方预警或官方空气质量公报。"
        ),
        "source_prefix": "数据来源：{provider}",
        "licensed_under": "许可协议 {license}",
        "print_hint": "打印或另存为 PDF，即可将本卡片导出为图片。",
    },
}
DEFAULT_LANG = "en"
LANGS = tuple(STRINGS)

# Interface label keys for the tiles and curves. Kept separate from the
# evidence-type keys so a metric's row key and its label can differ.
TILE_ROWS = (
    ("temperature", "temperature", "°C", "min/max"),
    ("precipitation_probability", "precipitation_probability", "%", "max"),
    ("precipitation_amount", "precipitation_amount", "mm", "total"),
    ("wind_speed", "wind_speed", "km/h", "max"),
    ("particulate_matter_2_5", "particulate_matter_2_5", "μg/m³", "max"),
    ("us_aqi", "us_aqi", "USAQI", "min/max"),
)
# Tiles that only exist when the brief carries air quality. A tile with no
# value behind it is dropped rather than drawn as a dash, so a weather-only
# brief cannot look like a brief whose air quality failed to load.
AIR_TILES = ("particulate_matter_2_5", "us_aqi")

# Metrics plotted as a curve over the brief's hours: label key, key in
# ``hours[].values``, unit, and the summary key the headline figure comes from.
CURVE_METRICS = (
    ("temperature", "temperature", "temperature", "°C", "min/max"),
    (
        "apparent_temperature",
        "apparent_temperature",
        "apparent_temperature",
        "°C",
        "min/max",
    ),
    (
        "precipitation_probability",
        "precipitation_probability",
        "precipitation_probability",
        "%",
        "max",
    ),
    (
        "precipitation_amount",
        "precipitation_amount",
        "precipitation_amount",
        "mm",
        "max",
    ),
    ("wind_speed", "wind_speed", "wind_speed", "km/h", "max"),
    ("wind_gust", "wind_gust", "wind_gust", "km/h", "max"),
    (
        "particulate_matter_2_5",
        "particulate_matter_2_5",
        "particulate_matter_2_5",
        "μg/m³",
        "max",
    ),
    (
        "particulate_matter_10",
        "particulate_matter_10",
        "particulate_matter_10",
        "μg/m³",
        "max",
    ),
)
CURVE_WIDTH = 480
CURVE_HEIGHT = 120

# A question is treated as Chinese when it contains Han characters. Anything
# else falls back to English, which is the card's default interface language.
HAN_RANGES = (
    (0x3400, 0x4DBF),    # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),    # CJK Unified Ideographs
    (0xF900, 0xFAFF),    # CJK Compatibility Ideographs
    (0x20000, 0x2FA1F),  # CJK Unified Ideographs Extension B and beyond
)


def has_han(text: str) -> bool:
    """True when the text contains at least one Han character."""
    for character in text:
        point = ord(character)
        if any(low <= point <= high for low, high in HAN_RANGES):
            return True
    return False


def detect_lang(*texts: Any) -> str:
    """Pick an interface language from user-supplied text.

    Only the question decides the language. The response's own prose is never
    inspected, because it is printed verbatim and may legitimately be in a
    different language from the question.
    """
    for text in texts:
        if isinstance(text, str) and has_han(text):
            return "zh"
    return DEFAULT_LANG


def normalise_lang(value: str) -> str:
    """Map a user-supplied language tag onto a supported language."""
    if not isinstance(value, str):
        raise DemoError(f"unsupported language: {value!r}")
    tag = value.strip().lower().replace("_", "-")
    if not tag:
        raise DemoError("--lang cannot be empty")
    if tag in STRINGS:
        return tag
    # Accept zh-CN, zh-Hans, zh-TW, en-US, and similar regional variants.
    primary = tag.split("-", 1)[0]
    if primary in STRINGS:
        return primary
    raise DemoError(
        f"unsupported language: {value!r} (supported: {', '.join(LANGS)})"
    )


class Translator:
    """Look up interface strings for one language."""

    def __init__(self, lang: str) -> None:
        self.lang = lang
        self._table = STRINGS[lang]

    def __call__(self, key: str, **fields: Any) -> str:
        try:
            template = self._table[key]
        except KeyError as exc:  # pragma: no cover - internal misuse
            raise DemoError(f"missing string {key!r} for language {self.lang!r}") from exc
        if not fields:
            return template
        try:
            return template.format(**fields)
        except KeyError as exc:  # pragma: no cover - internal misuse
            raise DemoError(
                f"string {key!r} for {self.lang!r} has no field {exc.args[0]!r}"
            ) from exc


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


# Brief enums whose string keys are namespaced to avoid colliding with the
# response enums: `detail` and `mode` both carry short common words.
NAMESPACED_KEYS = {
    ("detail", "hourly"): "detail_hourly",
    ("detail", "sparse"): "detail_sparse",
    ("detail", "summary"): "detail_summary",
    ("mode", "live"): "mode_live",
    ("mode", "offline"): "mode_offline",
}


def label_for(
    t: Translator, value: Any, *, namespace: str = "", fallback: str = ""
) -> str:
    """Translate a schema or brief enum value, falling back to the raw value.

    Enum values come from the response and the brief, so an unrecognised one is
    shown as-is rather than as an empty label: a value the card does not know
    is still better than a blank where the reader expects one.
    """
    if not isinstance(value, str) or not value:
        return fallback
    key = NAMESPACED_KEYS.get((namespace, value), value)
    if key in STRINGS[t.lang]:
        return t(key)
    return value.replace("_", " ") if "_" in value else value


def metric_values(label: str, values: dict[str, Any]) -> list[float]:
    """Return the numeric series for one row label across the brief's hours."""
    series: list[float] = []
    for hour in values.get("hours", []):
        value = (hour.get("values") or {}).get(label)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            series.append(float(value))
    return series


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
    if status not in STRINGS[DEFAULT_LANG]:
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


def window_html(brief: dict[str, Any], t: Translator) -> str:
    coverage = brief.get("coverage") or {}
    location = brief.get("location") or {}
    metrics = brief.get("summary") or {}

    window = esc(coverage.get("window", "—"))
    date = esc(coverage.get("date", "—"))
    # detail and mode are brief enums, so they are translated by value; a
    # value the card does not know falls through unchanged rather than blank.
    detail = esc(
        label_for(t, coverage.get("detail"), namespace="detail", fallback="—")
    )
    step = coverage.get("step_hours")
    included = coverage.get("hours_included")
    in_window = coverage.get("hours_in_window")
    mode = esc(
        label_for(t, (brief.get("source") or {}).get("mode"), namespace="mode", fallback="—")
    )
    name = esc(location.get("name", "—"))
    timezone = esc(location.get("timezone", "—"))

    air = brief.get("air_quality")
    has_air = isinstance(air, dict)

    cards = []
    for label_key, key, unit, tile_mode in TILE_ROWS:
        if label_key in AIR_TILES and not has_air:
            continue
        if tile_mode == "total":
            # The brief reports the window total and the wettest hour; showing
            # only one would misstate a summed quantity as a peak.
            total = extreme(metrics, key, "total")
            peak = extreme(metrics, key, "max_hour")
            if total is None and peak is None:
                continue
            value = t(
                "total_peak",
                total=fmt_number(total.get("value") if total else None),
                peak=fmt_number(peak.get("value") if peak else None),
            )
        else:
            entry = extreme(metrics, key, tile_mode)
            if entry is None and tile_mode == "min/max":
                # Some summaries carry only one extreme; show whichever exists.
                entry = extreme(metrics, key, "max") or extreme(metrics, key, "min")
            if entry is None:
                continue
            value = format_extreme(entry, unit)
        # A total/peak tile carries a phrase rather than a number, so it takes
        # a full row of the grid. Left in a column it wraps, and a grid row is
        # as tall as its tallest tile, which stretches the numbers beside it
        # into half-empty boxes.
        css = "metric metric-wide" if tile_mode == "total" else "metric"
        cards.append(
            f'<div class="{css}">'
            f'<div class="metric-label">{esc(t(label_key))}</div>'
            f'<div class="metric-value">{esc(value)}</div>'
            f'<div class="metric-unit">{esc(unit)}</div>'
            "</div>"
        )

    tiles_html = (
        '<div class="metrics">' + "".join(cards) + "</div>"
        if cards
        else f'<p class="muted">{esc(t("no_summary_values"))}</p>'
    )

    curves = []
    for label_key, values_key, summary_key, unit, curve_mode in CURVE_METRICS:
        series = metric_values(values_key, brief)
        if len(series) < 2:
            continue
        label = t(label_key)
        peak = extreme(metrics, summary_key, curve_mode)
        if peak is None and series:
            peak = {"value": max(series), "unit": unit}
        title = t(
            "curve_label",
            label=label,
            window=coverage.get("window") or "",
        ).strip()
        # The chart does not print its own evidence IDs. Eight charts each
        # carrying six chips put 59 of them on one card and buried the curve
        # they belong to; the IDs are shown once, in the evidence section.
        #
        # The peak figure already ends with its unit ("18.4 °C"), so the caption
        # does not print the unit a second time beside it.
        curves.append(
            '<figure class="curve-card">'
            f'<figcaption><span>{esc(label)}</span>'
            f"<strong>{esc(format_extreme(peak, unit))}</strong>"
            f"</figcaption>"
            f"{sparkline(series, title)}"
            "</figure>"
        )

    curves_html = (
        '<div class="curves">' + "".join(curves) + "</div>"
        if curves
        else f'<p class="muted">{esc(t("no_curves"))}</p>'
    )

    gaps = brief.get("demo_gaps") or []
    gap_labels = [t(gap) if gap in STRINGS[t.lang] else str(gap) for gap in gaps]
    gaps_html = ""
    if gap_labels:
        # One gap per line rather than a comma run: the reader is meant to
        # check each one off, and a wrapped list of five hides that.
        items = "".join(f"<li>{esc(gap)}</li>" for gap in gap_labels)
        gaps_html = (
            f'<div class="notice notice-gap"><strong>{esc(t("not_covered"))}</strong>'
            f'<p>{esc(t("not_covered_intro"))}</p>'
            f'<ul class="gap-list">{items}</ul>'
            f'<p class="gap-caveat">{esc(t("not_covered_body"))}</p></div>'
        )

    air_html = ""
    if has_air:
        us = extreme(air, "us_aqi", "min/max")
        eu = extreme(air, "european_aqi", "min/max")
        air_html = (
            f'<div class="notice notice-air"><strong>{esc(t("air_quality"))}</strong>'
            f'<p>{esc(t("air_quality_body", pm25=format_extreme(extreme(metrics, "particulate_matter_2_5", "max"), "μg/m³"), us=format_extreme(us, "USAQI"), eu=format_extreme(eu, "EAQI")))}</p></div>'
        )

    meta = " · ".join(
        [f"{name}", f"{date}", f"{window}", f"{detail}"]
        + ([t("every_hours", step=esc(step))] if isinstance(step, int) and step > 1 else [])
        + (
            [t("hours_shown", included=esc(included), total=esc(in_window))]
            if isinstance(included, int) and isinstance(in_window, int)
            else []
        )
        + [f"{timezone}", t("mode", mode=mode)]
    )

    return (
        '<section class="section window">'
        f'<div class="section-head"><h2>{esc(t("window_evidence"))}</h2>'
        f'<span class="chip">{window}</span></div>'
        f'<div class="window-meta">{meta}</div>'
        f'<p class="section-hint">{esc(t("window_evidence_hint"))}</p>'
        f"{tiles_html}"
        f"{curves_html}{air_html}{gaps_html}"
        "</section>"
    )


def body_html(
    response: dict[str, Any], brief: dict[str, Any] | None, t: Translator
) -> str:
    summary = esc(response.get("summary", ""))
    evidence = response.get("evidence") or []
    recommendations = response.get("recommendations") or []
    risks = response.get("risks") or []
    missing = response.get("missing_information") or []
    uncertainty = response.get("uncertainty") or []
    question = response.get("clarification_question")

    status = esc(t(response["status"]))
    intent = esc(label_for(t, response["intent"]))
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
    ) or f'<li class="muted">{esc(t("no_evidence"))}</li>'

    # Recommendations and risks print their action and their reason, not the
    # evidence IDs they rest on. At phone width a chip row under every item is
    # a third of the card's height spent on strings the reader cannot act on;
    # the IDs live in the evidence section, and the section hint says so.
    recommendations_html = "".join(
        '<li class="rec">'
        f'<p class="rec-action">{esc(item.get("action", ""))}</p>'
        f'<p class="rec-reason">{esc(item.get("reason", ""))}</p></li>'
        for item in recommendations
    ) or f'<li class="muted">{esc(t("no_recommendations"))}</li>'

    risks_html = "".join(
        '<li class="risk">'
        f'<span class="severity severity-{esc(item.get("severity", "unknown"))}">'
        f'{esc(t(item.get("severity") or "unknown"))}</span>'
        f'<div><p>{esc(item.get("description", ""))}</p></div></li>'
        for item in risks
    ) or f'<li class="muted">{esc(t("no_risks"))}</li>'

    clarification_html = ""
    if isinstance(question, str) and question.strip():
        clarification_html = (
            '<div class="notice notice-question">'
            f'<strong>{esc(t("clarification_needed"))}</strong>'
            f"<p>{esc(question)}</p></div>"
        )

    def list_block(title_key: str, items: list[Any], css: str) -> str:
        if not items:
            return ""
        entries = "".join(f"<li>{esc(item)}</li>" for item in items)
        return (
            f'<section class="section {css}"><h2>{esc(t(title_key))}</h2>'
            f"<ul>{entries}</ul></section>"
        )

    # The evidence list is the longest block on the card and the least useful to
    # a reader who is not auditing a citation: it is a list of IDs and one-line
    # claims. It collapses behind a <details> so it stays one click away without
    # pushing the advice off the first screen. <details> is markup, not script,
    # so the card stays script-free; a browser without it shows the list open.
    if evidence:
        evidence_count = t("evidence_count", count=len(evidence))
        evidence_block = (
            '<section class="section evidence-section">'
            '<details class="collapsible">'
            f'<summary><h2>{esc(evidence_count)}</h2>'
            f'<span class="toggle" data-show="{esc(t("show_details"))}" '
            f'data-hide="{esc(t("hide_details"))}"></span></summary>'
            f'<p class="section-hint">{esc(t("evidence_note"))}</p>'
            f'<ul class="evidence">{evidence_html}</ul></details></section>'
        )
    else:
        evidence_block = (
            f'<section class="section"><h2>{esc(t("evidence"))}</h2>'
            f'<ul class="evidence">{evidence_html}</ul></section>'
        )

    brief_window = window_html(brief, t) if brief else ""
    footer_meta = t(
        "footer_meta", version=version, intent=intent, status=status
    )

    # The accent edge and the hint describe real advice, so an empty
    # recommendations list gets neither: highlighting the placeholder would
    # dress up a card that has nothing to recommend.
    if recommendations:
        recommendations_block = (
            '<section class="section recommendations-section">'
            f'<h2>{esc(t("recommendations"))}</h2>'
            f'<p class="section-hint">{esc(t("recommendations_hint"))}</p>'
            f'<ul class="recommendations">{recommendations_html}</ul></section>'
        )
    else:
        recommendations_block = (
            f'<section class="section"><h2>{esc(t("recommendations"))}</h2>'
            f'<ul class="recommendations">{recommendations_html}</ul></section>'
        )

    # The whole card is one sheet rather than a stack of framed cards: on a
    # phone a dozen separate boxes read as clutter and spend height on padding
    # and gaps that the advice needs.
    #
    # The recommendation is what the reader came for, so it sits directly under
    # the summary; the window evidence that justifies it, the risks, and the raw
    # evidence list follow in descending order of how much the reader needs them.
    return (
        '<main class="sheet">'
        '<header class="section header">'
        f'<div class="header-top"><span class="badge badge-{esc(response["status"])}">{status}</span>'
        f'<span class="intent">{intent}</span></div>'
        f'<h1>{esc(location or t("weather_advice"))}</h1>'
        + (f'<p class="context">{esc(context_line)}</p>' if context_line else "")
        + f'<p class="summary">{summary}</p>'
        f"{clarification_html}"
        "</header>"
        f"{recommendations_block}"
        f"{brief_window}"
        f'<section class="section"><h2>{esc(t("risks"))}</h2>'
        f'<ul class="risks">{risks_html}</ul></section>'
        f"{evidence_block}"
        f"{list_block('missing_information', missing, 'missing')}"
        f"{list_block('uncertainty', uncertainty, 'uncertainty')}"
        f'<footer class="section footer"><p>{esc(footer_meta)}</p>'
        f'<p>{esc(t("footer_disclaimer"))}</p>'
        f'<p class="print-hint">{esc(t("print_hint"))}</p>'
        "</footer>"
        "</main>"
    )


def source_html(brief: dict[str, Any], t: Translator) -> str:
    source = brief.get("source") or {}
    parts = [
        source.get("attribution"),
        source.get("air_quality_attribution"),
    ]
    license_name = source.get("license")
    if license_name:
        parts.append(t("licensed_under", license=license_name))
    if source.get("provider"):
        parts.insert(0, t("source_prefix", provider=source["provider"]))
    text = " · ".join(str(part) for part in parts if part)
    return f'<p class="source">{esc(text)}</p>' if text else ""


def render_card(
    response: dict[str, Any],
    brief: dict[str, Any] | None,
    lang: str = DEFAULT_LANG,
) -> str:
    check_response(response)
    if brief is not None and not isinstance(brief.get("coverage"), dict):
        raise DemoError("brief is missing its coverage block")

    t = Translator(lang)
    style = (Path(__file__).resolve().parent / "card.css").read_text(
        encoding="utf-8"
    )
    source = source_html(brief, t) if brief else ""
    return (
        "<!doctype html>\n"
        f'<html lang="{esc(t("html_lang"))}">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(t('title'))}</title>\n"
        f"<style>\n{style}\n</style>\n</head>\n<body>\n"
        f"{body_html(response, brief, t)}\n"
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
        "--lang",
        choices=LANGS,
        help="interface language; defaults to the language of --query, "
        "or English when no Chinese text is found",
    )
    parser.add_argument(
        "--query",
        default="",
        help="the user's question; its language selects the interface "
        "language when --lang is not given",
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
        "--print",
        dest="print_hint",
        action="store_true",
        help="open the card and trigger the browser's print dialog, which is "
        "how the card is exported as an image or PDF",
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
        # The question decides the language, not the response's prose: the
        # response is printed verbatim and may be in another language.
        lang = (
            normalise_lang(args.lang)
            if args.lang
            else detect_lang(args.query)
        )
        card = render_card(response, brief, lang)
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

    if args.open or args.print_hint:
        webbrowser.open(target.resolve().as_uri())
    if args.print_hint:
        print(
            "Opened in the browser. Use the browser's print dialog "
            "(Ctrl/Cmd+P) and choose 'Save as PDF' to export the card.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
