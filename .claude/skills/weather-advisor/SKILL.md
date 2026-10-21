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

When the user asks for live weather (for example with `--live`), run the demo
from the repository root (the directory containing the canonical `SKILL.md`)
and use only the evidence it returns:

```bash
python3 demo/weather_demo.py <city>
```

Add `--days` (1–7), `--query`, and `--intent` as needed. `--offline` uses the
bundled synthetic Tokyo fixtures and makes no network call.

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

## Constraints

- Do not claim live data was retrieved unless the command succeeded.
- Distinguish forecasts from observations.
- Absence of alert evidence is not evidence of safety.
- Do not claim a specific official warning exists without supporting data.
- Do not require a particular model provider or API key.
