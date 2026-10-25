<h1 align="center">
  weather-advisor-skill
</h1>

<p align="center"><a href="README.md">简体中文</a> | English</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-24292f?style=flat" alt="Apache License 2.0"></a>
  &nbsp;
  <a href="schemas/recommendation.schema.json"><img src="https://img.shields.io/badge/schema__version-1.0-24292f?style=flat" alt="Output schema_version 1.0"></a>
  &nbsp;
  <a href="examples/"><img src="https://img.shields.io/badge/examples-6-24292f?style=flat" alt="Six example pairs"></a>
  &nbsp;
  <a href="tests/cases.jsonl"><img src="https://img.shields.io/badge/acceptance__cases-32-24292f?style=flat" alt="32 acceptance cases"></a>
  &nbsp;
  <a href="demo/README.md"><img src="https://img.shields.io/badge/demo-offline__%2F__no__API__key-24292f?style=flat" alt="Demo runs offline and needs no API key"></a>
</p>

Make Skill-compatible agents give weather advice that starts with evidence and
ends with machine-checkable output.

This repository is a skill package made of documentation, a JSON Schema, and a
test suite. It is **not** a weather API. It does not fetch weather data or ship
an agent runtime. It governs how an agent uses weather facts supplied by the
host, and how it returns structured, reviewable advice.

## Why it exists

Language models commonly fail at weather advice in predictable ways:

- inventing temperatures, rainfall amounts, alerts, locations, or data sources;
- turning "70% chance of rain" into "it will definitely rain";
- defaulting to the device location when the location is missing;
- treating "no alert was supplied" as "there is no risk";
- recommending things unrelated to the evidence, with no traceable reason;
- returning a different shape every time, so output cannot be validated.

The project fixes those behaviors with one entry skill, four reference
documents, one JSON Schema, six example pairs, and 32 acceptance cases. Success
is not that a model can talk about weather; it is that different agents follow
the same analysis process, refuse to fabricate when facts are missing, and
produce output a program can check.

## Quick start

### 1. Load it as a skill

Point your host at the repository root. `SKILL.md` is the entry point.

```bash
cp -r weather-advisor-skill ~/.claude/skills/weather-advisor
```

The skill's `name` is `weather-advisor`. If the host requires the directory
name to match, rename the directory accordingly.

### 2. Supply weather evidence

The skill never fetches weather. The host supplies the query, context, and
evidence together:

```json
{
  "user_query": "Should I bring an umbrella to work tomorrow morning?",
  "intent": "commute_advice",
  "context": {
    "location": "Shanghai",
    "timezone": "Asia/Shanghai",
    "start": "2026-10-22T07:00:00+08:00",
    "end": "2026-10-22T09:00:00+08:00"
  },
  "weather_evidence": [
    {
      "id": "ev-rain-001",
      "type": "precipitation_probability",
      "value": 70,
      "unit": "%",
      "valid_from": "2026-10-22T07:00:00+08:00",
      "valid_to": "2026-10-22T09:00:00+08:00",
      "source": "example-provider",
      "observed_at": "2026-10-21T20:00:00+08:00"
    }
  ]
}
```

`context` may be empty and `weather_evidence` may be empty; both trigger
clarification or an insufficient-evidence response instead of letting the model
fill the gaps.

### 3. Get structured output

The agent returns a JSON object conforming to
[`schemas/recommendation.schema.json`](schemas/recommendation.schema.json).
Every recommendation and risk cites the `evidence_id` values it rests on.

```json
{
  "schema_version": "1.0",
  "status": "answered",
  "intent": "commute_advice",
  "summary": "Rain is fairly likely during tomorrow's morning commute in Shanghai; bring an umbrella.",
  "evidence": [
    {
      "evidence_id": "ev-rain-001",
      "claim": "The chance of rain from 07:00 to 09:00 is 70%."
    }
  ],
  "recommendations": [
    {
      "action": "Carry an umbrella or rain jacket on your commute.",
      "reason": "The chance of rain during the commute window is 70%.",
      "evidence_ids": ["ev-rain-001"]
    }
  ],
  "risks": [
    {
      "description": "Rain may make roads slippery.",
      "severity": "medium",
      "evidence_ids": ["ev-rain-001"]
    }
  ],
  "missing_information": [],
  "clarification_question": null,
  "uncertainty": ["70% is a probability, not a guarantee of rain."]
}
```

## Claude Code

This repository ships a Claude Code project skill at
`.claude/skills/weather-advisor/SKILL.md`. Open a session at the repository
root and use the slash command:

```text
/weather-advisor Tokyo outdoor running tomorrow
/weather-advisor --live Osaka travel tomorrow
```

`/weather-advisor-card` renders a structured response as a self-contained HTML
card, optionally folding in the windowed evidence to show hourly curves:

```text
/weather-advisor-card /tmp/response.json --brief /tmp/brief.json --open
```

Natural-language weather questions also trigger it. Install it for personal use
with:

```bash
python3 scripts/install_claude_skill.py
```

An optional Stop hook can validate a requested JSON response against the
schema; it is disabled by default. See
[`docs/claude-code.md`](docs/claude-code.md) for live mode, card rendering,
installation, hooks, and verification.

## What is included

- a standard `SKILL.md` with metadata;
- six weather-related intents and clarification rules;
- evidence constraints and recommendation derivation rules;
- severe-weather and uncertainty handling;
- a unified output contract (JSON Schema, Draft 2020-12);
- six example pairs, 32 acceptance cases, and local validation tooling;
- a key-free Open-Meteo demo adapter (`demo/`), separate from the skill core.

It deliberately does **not** include weather fetching in the skill core, a
standalone agent runtime, accounts/payments, a web service or database, or
model-specific prompt tuning. See
[`docs/architecture.md`](docs/architecture.md) for the full scope and design.

## Documentation

| Document | What it covers |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Entry point, workflow, and hard rules read by the agent |
| [`docs/getting-started.md`](docs/getting-started.md) | Host integration, full input/output examples, demo, validation |
| [`docs/claude-code.md`](docs/claude-code.md) | Claude Code entries, `/weather-advisor`, the card, install script, optional hook |
| [`docs/architecture.md`](docs/architecture.md) | Scope, workflow, status model, intents, design decisions |
| [`docs/examples-and-tests.md`](docs/examples-and-tests.md) | Example pairs, test coverage, three test layers |
| [`docs/repository-layout.md`](docs/repository-layout.md) | Annotated repository tree |
| [`references/`](references/) | Intent catalog, evidence contract, recommendation rules, safety |
| [`demo/README.md`](demo/README.md) | Demo field mapping, attribution, licensing, provider replacement |
| [`tests/README.md`](tests/README.md) | Test layers, case format, grading |
| [`CLAUDE.md`](CLAUDE.md) | Project constraints and conventions for contributors |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

The Chinese version is [`README.md`](README.md).

## Demo

`demo/weather_demo.py` turns a city name into a skill-ready input envelope using
Open-Meteo's free public API. It uses only the Python standard library and
needs no API key. Alongside the hourly weather it merges PM2.5, PM10, and both
the US and European AQI by default, because air quality often decides whether
strenuous outdoor activity is advisable; pass `--no-air-quality` to skip it.

```bash
python demo/weather_demo.py Tokyo
python demo/weather_demo.py "New York" --days 2
python demo/weather_demo.py Tokyo --offline

# Compact, windowed evidence for agent consultations
python demo/weather_brief.py Tokyo --date today --window 10:00-16:00 --compact

# Render a response as a visual card
python demo/weather_card.py response.json --brief brief.json --output card.html
```

`weather_brief.py` returns only the requested hours, summary statistics, and
evidence IDs. The compact mode is typically 3–20 KB, against roughly
44–86 KB for a live full-day envelope. `weather_card.py` renders those evidence
alongside the response as one self-contained HTML card, adding no new data. See
[`docs/claude-code.md`](docs/claude-code.md#token-efficient-consultation-pattern)
for the consultation pattern.

Weather and air-quality data by [Open-Meteo.com](https://open-meteo.com/),
licensed under CC BY 4.0. The free endpoint is intended for non-commercial use
and offers no production SLA; keep the attribution when displaying the data.
Air quality is CAMS modelled forecast output, not a ground-station measurement,
and does not replace official AQI bulletins. See
[`demo/README.md`](demo/README.md) for limits and provider replacement.

## Local validation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py
python tests/test_weather_brief.py
python tests/test_weather_card.py
python tests/test_claude_integration.py
python tests/run_examples.py
python tests/validate_cases.py
```

All commands must exit 0. See
[`docs/getting-started.md`](docs/getting-started.md) for the single-file
validators and the per-case grader.

## Version and license

Current version: `0.1.0`. Output `schema_version`: `1.0`.

[Apache License 2.0](LICENSE).
