# weather-advisor-skill

[简体中文](README.md) | English

Make Skill-compatible agents give weather advice that starts with evidence and
ends with machine-checkable output.

This repository is a skill package made of documentation, a JSON Schema, and a
test suite. It is **not** a weather API. It does not fetch weather data or ship
an agent runtime. It governs how an agent uses weather facts supplied by the
host, and how it returns structured, reviewable advice.

## What it solves

Common failure modes when language models give weather advice:

- inventing temperatures, rainfall amounts, alerts, locations, or data sources;
- turning "70% chance of rain" into "it will definitely rain";
- defaulting to the device location or picking an arbitrary city when the
  location is missing;
- treating "no alert was supplied" as "there is no risk";
- recommending things unrelated to the weather evidence, with no traceable
  justification;
- returning a different shape every time, so output cannot be validated.

This project fixes those behaviors with one entry skill, four reference
documents, one JSON Schema, and 32 test cases. The first release is not judged
by whether a model can produce weather advice. It is judged by whether
different agents follow the same analysis process for the same input, refuse to
fabricate when essential facts are missing, and produce output a program can
check.

## Scope

The first release includes:

- a standard `SKILL.md` with metadata;
- six weather-related intents;
- clarification and missing-information rules;
- evidence constraints and recommendation derivation rules;
- severe-weather and uncertainty handling;
- a unified output contract (JSON Schema);
- six example pairs, 32 test cases, and local validation tooling;
- a key-free Open-Meteo demo adapter (`demo/`, separate from the skill core).

The first release does not include:

- weather fetching built into the skill core; `demo/` is a replaceable local
  adapter for verification only;
- a standalone agent runtime;
- user accounts, credits, or payments;
- a web service, database, or admin console;
- model-specific prompt optimization.

## Repository layout

```text
weather-advisor-skill/
├── SKILL.md                       # Skill entry: workflow and hard constraints
├── README.md                      # Chinese README
├── README.en.md                   # English README
├── CLAUDE.md                      # Conventions for working in this repository
├── LICENSE
├── CHANGELOG.md
├── references/
│   ├── intent-catalog.md          # Six intents, required context, clarification rules
│   ├── evidence-contract.md       # Input shape, validity, missing/conflicting evidence
│   ├── recommendation-rules.md    # From weather facts to actions
│   └── safety-and-uncertainty.md  # Severe weather, uncertainty, wording limits
├── schemas/
│   └── recommendation.schema.json # Output contract (Draft 2020-12)
├── examples/                      # Six input/output pairs
│   ├── commute-rain.json
│   ├── commute-rain-output.json
│   ├── clothing-cold.json
│   ├── clothing-cold-output.json
│   ├── outdoor-wind.json
│   ├── outdoor-wind-output.json
│   ├── travel-planning.json
│   ├── travel-planning-output.json
│   ├── missing-location.json
│   ├── missing-location-output.json
│   ├── no-weather-evidence.json
│   └── no-weather-evidence-output.json
├── demo/                          # Key-free demo: Open-Meteo -> evidence
│   ├── weather_demo.py
│   ├── fixtures/
│   │   ├── geocoding-tokyo.json
│   │   └── forecast-tokyo.json
│   └── README.md
└── tests/
    ├── cases.jsonl                # 32 acceptance cases
    ├── validate_schema.py         # Schema validation
    ├── check_evidence.py          # Evidence reference validation
    ├── run_examples.py            # Batch example validation
    ├── validate_cases.py          # Case file linting
    ├── grade_case.py              # Grade one response against one case
    ├── test_demo.py               # L1 data-layer tests (offline)
    ├── requirements.txt
    └── README.md
```

## Quick start

### 1. Load it as a skill

Point your host at the repository root. `SKILL.md` is the entry point. Loading
mechanics differ between hosts; follow the host's documentation.

Example for a Claude Code personal skill directory:

```bash
cp -r weather-advisor-skill ~/.claude/skills/weather-advisor
```

The skill's `name` is `weather-advisor`. If the host requires the directory
name to match, rename the directory to `weather-advisor`.

### 2. Supply weather evidence

The skill never fetches weather data itself. The host must provide the query,
context, and evidence together. The minimal input looks like this; see
[`references/evidence-contract.md`](references/evidence-contract.md) for the
full field contract:

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

`context` may be empty and `weather_evidence` may be an empty array. Both cases
trigger clarification or an insufficient-evidence response instead of letting
the model fill the gaps.

### 3. Get structured output

The agent returns a JSON object that conforms to
[`schemas/recommendation.schema.json`](schemas/recommendation.schema.json):

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

For a complete example, see
[`examples/commute-rain-output.json`](examples/commute-rain-output.json).

## Workflow

1. Identify the intent ([`references/intent-catalog.md`](references/intent-catalog.md)).
2. Extract the location, target time, and activity context.
3. Decide whether missing information materially changes the answer.
4. If it does, ask one concise clarification and return `needs_clarification`.
5. Check each evidence item's validity window, freshness, source, and coverage
   of the target period.
6. Derive recommendations following
   [`references/recommendation-rules.md`](references/recommendation-rules.md).
7. Apply [`references/safety-and-uncertainty.md`](references/safety-and-uncertainty.md)
   to risks and uncertainty.
8. Return the structure defined by
   [`schemas/recommendation.schema.json`](schemas/recommendation.schema.json).

## Six intents

| Intent ID | Example query | Focus |
| --- | --- | --- |
| `weather_lookup` | Will it rain in Shanghai tomorrow? | Report the fact; do not expand into unrelated advice |
| `clothing_advice` | What should I wear tomorrow? | Temperature, apparent temperature, rain, activity |
| `commute_advice` | Should I bring an umbrella to work tomorrow? | Commute-window rain, wind, visibility, alerts |
| `outdoor_activity` | Is it a good time for a run this afternoon? | Rain, wind and gusts, temperature, UV, alerts |
| `travel_planning` | What should I prepare for a weekend in Hangzhou? | Multi-day weather, itinerary fit, forecast horizon |
| `general_weather_advice` | What should I watch out for in this weather? | Infer the purpose from context; clarify only when needed |

Intent details, required context, and failure examples are in
[`references/intent-catalog.md`](references/intent-catalog.md).

## Output contract

### Status

| `status` | Meaning |
| --- | --- |
| `answered` | Evidence covers the asked place and time, and supports at least one actionable recommendation |
| `needs_clarification` | Essential context (location, time, activity) is missing and the user can supply it |
| `insufficient_evidence` | Context is complete, but the needed weather evidence is missing, stale, or out of range |

Clarification comes before insufficient evidence: if the user can supply a
missing fact, ask rather than guess.

### Key design decisions

**Cite evidence instead of restating weather data.** The model references
host-supplied IDs in `evidence_ids`; the host can then compare them with the
original evidence and detect nonexistent references.

**Schema validation is not fact validation.** JSON Schema checks fields, types,
required properties, and enums. It cannot by itself determine whether "carry an
umbrella" is actually supported by the rain evidence. Evidence linkage and rule
consistency are covered by `tests/check_evidence.py` and the test cases.

**No subjective confidence scores.** The first release does not return values
such as `confidence: 0.95`. Without a calibration method, such numbers create
false precision. Explainable uncertainty language is preferred.

## Examples

| Example | Status | What it demonstrates |
| --- | --- | --- |
| [`commute-rain`](examples/commute-rain-output.json) | `answered` | A commute recommendation with rain evidence; probability is not treated as certainty |
| [`clothing-cold`](examples/clothing-cold-output.json) | `answered` | Layering for low temperature, apparent temperature, and wind |
| [`outdoor-wind`](examples/outdoor-wind-output.json) | `answered` | How strong wind and gusts affect coastal cycling |
| [`travel-planning`](examples/travel-planning-output.json) | `answered` | Multi-day advice, day-by-day structure, disclosure of uncovered days |
| [`missing-location`](examples/missing-location-output.json) | `needs_clarification` | Ask for a location instead of defaulting to the device location |
| [`no-weather-evidence`](examples/no-weather-evidence-output.json) | `insufficient_evidence` | Do not declare an activity suitable or unsuitable without evidence |

All example weather values are synthetic and marked with the source
`example-provider`. They do not represent any real forecast.

## Demo: real weather evidence without an API key

`demo/weather_demo.py` uses Open-Meteo's free public API to turn a city name
into a skill-ready input envelope. It depends only on the Python standard
library and needs no registration or API key.

```bash
python demo/weather_demo.py Tokyo
python demo/weather_demo.py "New York" --days 2
python demo/weather_demo.py Tokyo --offline
python demo/weather_demo.py Tokyo \
  --query "Is it a good time for an outdoor run in Tokyo tomorrow?" \
  --intent outdoor_activity \
  --output /tmp/tokyo-input.json
```

The output contains `user_query`, `intent`, `context` (location and time
window), `weather_evidence`, `attribution`, and `metadata`. Hand the JSON to an
agent that has loaded `SKILL.md`, then validate the agent's evidence references
with `tests/check_evidence.py`.

`--offline` uses the bundled Tokyo fixtures under `demo/fixtures/`, makes no
network calls, and is intended for tests. `live` mode queries Open-Meteo and
supports `--days` from 1 to 7. See [`demo/README.md`](demo/README.md) for
details.

This chain is manual: the demo only fetches evidence, the skill core does not
depend on network tools, and whether an agent can call external tools is up to
the host.

### Data source and licensing

- Weather data is provided by [Open-Meteo](https://open-meteo.com/) under the
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) license. Keep the
  `Weather data by Open-Meteo.com` attribution when displaying the data.
- The free public API is intended for non-commercial use. Its documentation
  currently states a free-tier limit of about 10,000 requests per day.
  Products with subscriptions or advertising generally count as commercial
  use; choose an appropriate license or self-host.
- The free endpoint does not guarantee permanent free access, unlimited calls,
  or a production SLA. Terms and limits may change; check the Open-Meteo site
  for the current terms.
- To switch providers, implement the same evidence structure described in
  [`references/evidence-contract.md`](references/evidence-contract.md). The
  skill core and the schema do not need to change.

## Local validation

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py          # L1: offline data layer, no third-party dependency
python tests/run_examples.py       # Schema and evidence linkage for all six examples
python tests/validate_cases.py     # Lint the 32 cases
python tests/validate_schema.py examples/commute-rain-output.json
python tests/check_evidence.py examples/commute-rain-output.json examples/commute-rain.json
```

To grade model output:

```bash
python tests/grade_case.py normal-001 /tmp/responses/normal-001.json
```

The grader runs schema validation, evidence-linkage checks, and the case's
`expect` assertions covering status, intent, recommendation count, risk
severity, and forbidden phrases. Field definitions are in
[`tests/README.md`](tests/README.md).

## Test coverage

| Category | Count | What it verifies |
| --- | --- | --- |
| Normal | 10 | Intent identification, actionable advice, correct references |
| Missing information | 5 | Ask for essential facts; do not fill gaps |
| Evidence anomaly | 5 | No evidence, time mismatch, stale data, missing fields, conflicting sources |
| Risk and uncertainty | 5 | Alert priority, no overconfidence, disclosed limitations |
| Output structure | 7 | Required fields, clarification field, missing information, traceable citations |

Testing has three layers: L1 data layer (`tests/test_demo.py`, offline
fixtures), L2 rule layer (examples, cases, and validators; no model required),
and L3 agent layer (run by a developer with an actual agent). See
[`tests/README.md`](tests/README.md).

## Design principles

1. **Evidence first.** Weather facts come only from the host or authorized
   tools, never from model memory.
2. **Ask only when necessary.** Clarify only when missing information changes
   the answer; never re-ask for context the host already supplied.
3. **Probability is not a conclusion.** A 70% chance of rain supports carrying
   an umbrella; it does not support "it will definitely rain."
4. **Missing is not safe.** Without alert data, the honest statement is that
   status is unknown, not that there is no risk.
5. **IDs and sources belong to the host.** The model must not create, rewrite,
   or guess evidence IDs.
6. **Do not invent thresholds.** Judgments about heat, cold, wind, or
   thunderstorms should rely on trusted sources and activity-specific
   standards, not numbers the model makes up.
7. **The schema is the interface; the docs are the explanation.** Keep their
   responsibilities separate to avoid duplicating rules.
8. **Safety before completeness.** Return insufficient evidence rather than
   assembling an answer that looks complete.

## What the host must provide

For the skill to work well, the host should provide:

- a clear location and target time, or allow the skill to ask the user;
- structured weather evidence with `id`, `type`, `source`, `observed_at`,
  `valid_from`, and `valid_to`;
- official alerts when available, preserving issuer, severity, and validity
  window;
- a freshness policy and source-priority rules for conflicting data, if any.

If the host cannot provide these, the skill returns a clarification or an
insufficient-evidence response instead of fabricating weather.

You can use the field structure produced by `demo/weather_demo.py` directly, or
build your own adapter that emits evidence in the same shape.

## Version

Current version: `0.1.0`. Output `schema_version`: `1.0`. See
[`CHANGELOG.md`](CHANGELOG.md).

## Pre-release checklist

- Confirm that the target host supports the skill format and frontmatter fields.
- Confirm licensing terms for third-party weather data and example content.
- When using the demo, keep the Open-Meteo attribution and confirm the
  non-commercial restriction, request limits, and current terms of the free API.
- Keep example weather data marked as synthetic; never imply it is a real
  forecast.
- When changing the schema, update `schema_version`, examples, test cases, and
  the changelog together.

## Contributing

- Before adding or changing a rule, decide which file owns it; do not duplicate
  rules across documents.
- After changing the schema or intents, run all validation commands.
- Follow [`tests/README.md`](tests/README.md) when adding test cases.
- Before committing, confirm there are no dangling `evidence_id` references and
  no fabricated weather facts.

## License

[MIT](LICENSE)
