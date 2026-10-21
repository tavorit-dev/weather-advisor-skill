# Examples and Tests

This page summarizes the bundled examples and test coverage. The test
machinery itself is documented in [`tests/README.md`](../tests/README.md).

## Examples

Each example is a pair: `<name>.json` (input) and `<name>-output.json`
(expected response).

| Example | Status | What it demonstrates |
| --- | --- | --- |
| [`commute-rain`](../examples/commute-rain-output.json) | `answered` | A commute recommendation with rain evidence; probability is not treated as certainty |
| [`clothing-cold`](../examples/clothing-cold-output.json) | `answered` | Layering for low temperature, apparent temperature, and wind |
| [`outdoor-wind`](../examples/outdoor-wind-output.json) | `answered` | How strong wind and gusts affect coastal cycling |
| [`travel-planning`](../examples/travel-planning-output.json) | `answered` | Multi-day advice, day-by-day structure, disclosure of uncovered days |
| [`missing-location`](../examples/missing-location-output.json) | `needs_clarification` | Ask for a location instead of defaulting to the device location |
| [`no-weather-evidence`](../examples/no-weather-evidence-output.json) | `insufficient_evidence` | Do not declare an activity suitable or unsuitable without evidence |

All example weather values are synthetic and marked with the source
`example-provider`. They do not represent any real forecast.

## Test coverage

| Category | Count | What it verifies |
| --- | --- | --- |
| Normal | 10 | Intent identification, actionable advice, correct references |
| Missing information | 5 | Ask for essential facts; do not fill gaps |
| Evidence anomaly | 5 | No evidence, time mismatch, stale data, missing fields, conflicting sources |
| Risk and uncertainty | 5 | Alert priority, no overconfidence, disclosed limitations |
| Output structure | 7 | Required fields, clarification field, missing information, traceable citations |

Total: 32 cases in [`tests/cases.jsonl`](../tests/cases.jsonl).

## Three test layers

- **L1 — data layer.** `tests/test_demo.py`, offline fixtures, no third-party
  dependency and no network access.
- **L2 — rule layer.** Examples, cases, and validators; no model required.
- **L3 — agent layer.** Run by a developer with an actual agent and graded per
  case with `tests/grade_case.py`.

See [`tests/README.md`](../tests/README.md) for commands, the `expect` field,
case structure, and known limitations.
