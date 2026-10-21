# Getting Started

This document covers host integration in detail: loading the skill, supplying
evidence, reading the response, running the demo, and validating output. For
the reasoning behind the design, see [`architecture.md`](architecture.md).

## Load the skill

Point the host at the repository root. [`SKILL.md`](../SKILL.md) is the entry
point; loading mechanics differ between hosts, so follow the host's
documentation.

Claude Code personal skill directory example:

```bash
cp -r weather-advisor-skill ~/.claude/skills/weather-advisor
```

The skill's `name` is `weather-advisor`. If the host requires the directory
name to match, rename the directory to `weather-advisor`.

For Claude Code specifically, this repository also ships a project skill,
`/weather-advisor` slash command, optional hook, and install script. See
[`claude-code.md`](claude-code.md).

## Supply weather evidence

The skill never fetches weather data itself. The host provides the query,
context, and evidence together. Minimal input:

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

The full field contract, validity windows, freshness rules, and handling of
missing or conflicting evidence are in
[`references/evidence-contract.md`](../references/evidence-contract.md).

### What the host should provide

- a clear location and target time, or a way for the skill to ask the user;
- structured evidence with `id`, `type`, `source`, `observed_at`,
  `valid_from`, and `valid_to`;
- official alerts when available, preserving issuer, severity, and validity
  window;
- a freshness policy and source-priority rules for conflicting data, if any.

If the host cannot provide these, the skill returns a clarification or an
insufficient-evidence response instead of fabricating weather. You can use the
shape produced by `demo/weather_demo.py` directly, or build an adapter that
emits the same shape.

## Read the response

The agent returns one JSON object conforming to
[`schemas/recommendation.schema.json`](../schemas/recommendation.schema.json):

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

A complete pair is in
[`examples/commute-rain.json`](../examples/commute-rain.json) and
[`examples/commute-rain-output.json`](../examples/commute-rain-output.json).
Statuses, key design decisions, and the intent list are documented in
[`architecture.md`](architecture.md).

## Run the demo

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
supports `--days` from 1 to 7.

This chain is manual: the demo only fetches evidence, the skill core does not
depend on network tools, and whether an agent can call external tools is up to
the host. See [`demo/README.md`](../demo/README.md) for field mapping, licensing
limits, and how to replace the provider.

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
  [`references/evidence-contract.md`](../references/evidence-contract.md). The
  skill core and the schema do not need to change.

## Validate locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py          # L1: offline data layer, no third-party dependency
python tests/run_examples.py       # Schema and evidence linkage for all six examples
python tests/validate_cases.py     # Lint the 32 cases
```

Validate one output file or one input/output pair:

```bash
python tests/validate_schema.py examples/commute-rain-output.json
python tests/check_evidence.py examples/commute-rain-output.json examples/commute-rain.json
```

Grade model output against a case:

```bash
python tests/grade_case.py normal-001 /tmp/responses/normal-001.json
```

The grader runs schema validation, evidence-linkage checks, and the case's
`expect` assertions covering status, intent, recommendation count, risk
severity, and forbidden phrases. Field definitions are in
[`tests/README.md`](../tests/README.md). Test coverage and the three test layers
are summarized in [`examples-and-tests.md`](examples-and-tests.md).
