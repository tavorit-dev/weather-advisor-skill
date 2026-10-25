---
name: weather-advisor
description: >
  Analyze weather conditions and give evidence-based advice for commuting,
  clothing, outdoor activities, travel, and daily planning. Use when a user
  asks about weather-related decisions, forecasts, or activity planning,
  including when weather is only implied. The skill uses only supplied weather
  evidence and never invents values.
argument-hint: "[city] [activity] [date]"
---

# Weather Advisor (Claude Code entry)

This file is the Claude Code entry point. Read and follow the canonical skill
at `../../../SKILL.md` before answering. It is the single source of truth for
the workflow, ground rules, status selection, and output contract. The
`references/`, `schemas/`, `examples/`, and `tests/` directories sit at the
repository root next to that canonical file.

## Invocation

The user may invoke the skill explicitly:

- `/weather-advisor Tokyo outdoor running tomorrow`
- `/weather-advisor 上海 通勤 明天`
- `/weather-advisor --live Osaka travel tomorrow`

`$ARGUMENTS` contains the text after the command; treat it as the user query.
Natural-language weather questions should also trigger this skill.

## Live weather

For a live consultation, prefer the compact brief. It returns only the requested
hours, summary statistics, and evidence IDs, so one tool call is usually enough:

```bash
# User named a time range: keep hourly rows
python3 demo/weather_brief.py <city> --date today --window 13:00-18:00 --compact

# Whole day with no time range: keep a 3-hour curve
python3 demo/weather_brief.py <city> --date tomorrow --every 3 --compact

# Only extremes are needed: summary only
python3 demo/weather_brief.py <city> --date tomorrow --summary-only --compact

# Weather only, when context is tight and air quality is not decisive
python3 demo/weather_brief.py <city> --date tomorrow --every 3 --compact --no-air-quality
```

- Always add `--compact` to keep the JSON small.
- Pass `--window` when the user names a time range; include hourly rows for that
  window.
- When the user asks about a whole day without a time range, use `--every 3` so
  the day curve remains visible without 24 rows.
- Use `--summary-only` only when the question needs extremes or a yes/no, not a
  time-of-day recommendation.
- Air quality is included by default and is usually decisive for running,
  cycling, or other strenuous outdoor activity. Drop it with `--no-air-quality`
  only when the question is purely about weather and context is tight.
- When air quality is present, read `air_quality` and the PM2.5 statistics
  alongside the weather. Report the PM2.5 concentration and name the AQI scale
  you are quoting; the US and European scales are not comparable, so prefer
  concentration when describing a trend.
- Air-quality values are modelled forecasts (CAMS), not ground-station
  measurements. Say so when air quality drives the answer, and do not present
  them as an official AQI bulletin.
- If the user gives no date, use `--date today`; for "明天" use
  `--date tomorrow`.
- `--offline` uses the bundled synthetic Tokyo fixture and requires an explicit
  date (`--date 2026-10-22`).
- Use `demo/weather_demo.py` only when the full envelope or complete evidence is
  needed.

If the command fails, explain the failure and do not substitute invented
values. The demo is a replaceable adapter, not part of the skill's rules.

## Response

The canonical contract defines the fields, evidence rules, and statuses. In a
Claude Code conversation, present that result as:

1. Summary
2. Weather evidence
3. Recommendations
4. Risks and uncertainty
5. Missing information, if any

Every weather fact and recommendation must cite the supplied `evidence_id`
values. When the user asks for JSON, return one object conforming to
`schemas/recommendation.schema.json` and validate it with:

```bash
python3 tests/validate_schema.py <file>
```

Keep a simple suitability answer compact: lead with the recommended window,
cite 3–5 key values, give 3–4 recommendations and 2–3 risks. Do not enumerate
every hour; expand only when the user asks for detail.

## Constraints

- Do not claim live data was retrieved unless the command succeeded.
- Distinguish forecasts from observations.
- Absence of alert evidence is not evidence of safety.
- Do not claim a specific official warning exists without supporting data.
- Do not require a particular model provider or API key.
