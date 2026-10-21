# Evidence Contract

This is the most important constraint in the skill: **the model may derive
recommendations, but it may not create weather facts.**

Every weather claim in the output must trace back to an evidence item supplied
by the host or returned by an authorized tool. If a fact is not in the
evidence set, it does not exist for this response.

## Input envelope

The host supplies a query, optional context, and a list of evidence items.

```json
{
  "user_query": "明早上班要带伞吗？",
  "intent": "commute_advice",
  "context": {
    "location": {
      "name": "上海",
      "timezone": "Asia/Shanghai"
    },
    "start": "2026-10-22T07:00:00+08:00",
    "end": "2026-10-22T09:00:00+08:00",
    "activity": "步行 + 地铁通勤"
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

This is a contract example. It is not a real forecast for Shanghai.

### Envelope fields

| Field | Required | Notes |
| --- | --- | --- |
| `user_query` | Yes | The user's message, verbatim |
| `intent` | No | Host hint; the skill still validates it against the query |
| `context.location` | No | String, or object with `name` and optional `timezone`, `latitude`, `longitude` |
| `context.start`, `context.end` | No | ISO 8601 timestamps with UTC offset |
| `context.date` | No | Day-level target when a window is not supplied |
| `context.activity` | No | Free text describing what the user will do |
| `weather_evidence` | Yes | Array; may be empty |

`context` may be an empty object. An empty context is missing information, not
permission to assume the host's own location.

## Evidence item

### Required fields

| Field | Type | Meaning |
| --- | --- | --- |
| `id` | string | Unique reference ID assigned by the host; the only valid citation key |
| `type` | string | Weather element, from the vocabulary below |
| `source` | string | Provider, authority, or tool name |
| `observed_at` | string (ISO 8601) | When the data was produced or retrieved |
| `valid_from` | string (ISO 8601) | Start of the period the data describes |
| `valid_to` | string (ISO 8601) | End of the period the data describes |

### Value fields

Numeric evidence also requires:

- `value`: number
- `unit`: string. Use `%`, `°C`, `mm`, `km/h`, `m/s`, `km`, `hPa`.

Descriptive evidence (alerts, condition text) uses `description` instead of
`value` and `unit`. It still requires the temporal and source fields.

### Vocabulary

Use these `type` values when the host can map its provider to them. Hosts may
add types, but they must document their units and semantics.

| Type | Typical unit | Notes |
| --- | --- | --- |
| `temperature` | °C | Instantaneous or period value |
| `temperature_min` | °C | Period minimum |
| `temperature_max` | °C | Period maximum |
| `apparent_temperature` | °C | "Feels like" value |
| `precipitation_probability` | % | Probability, not amount |
| `precipitation_amount` | mm | Accumulation |
| `precipitation_type` | — | Rain, snow, sleet, hail |
| `wind_speed` | km/h | Sustained wind |
| `wind_gust` | km/h | Gust speed |
| `humidity` | % | Relative humidity |
| `visibility` | km | Horizontal visibility |
| `uv_index` | — | Standard UV index |
| `air_quality_index` | — | Must state the index scale in `description` or metadata |
| `weather_description` | — | Qualitative condition from the source |
| `severe_weather_alert` | — | Official alert; use `description` plus `severity`, `issuer` when supplied |

### Alert evidence

An official alert is an evidence item of type `severe_weather_alert`.

```json
{
  "id": "ev-alert-001",
  "type": "severe_weather_alert",
  "description": "台风橙色预警：预计 24 小时内沿海阵风可达 12 级。",
  "severity": "orange",
  "issuer": "示例气象台",
  "valid_from": "2026-10-24T18:00:00+08:00",
  "valid_to": "2026-10-25T18:00:00+08:00",
  "source": "example-provider",
  "observed_at": "2026-10-24T17:30:00+08:00"
}
```

The skill must not upgrade, downgrade, or reissue the alert. Quote its meaning
and keep the issuer and validity window attached.

## Non-negotiable rules

1. **Validity must match the target.** Do not apply evidence outside
   `valid_from`–`valid_to` to the user's requested period. Partial coverage must
   be stated. A mismatch is not a gap to fill with a plausible value.
2. **Freshness depends on type and policy.** Do not apply one universal expiry.
   Use any freshness or validity policy the host supplies. If none is supplied,
   treat old data as a limitation: describe it, do not present it as current.
3. **Missing means unknown.** Never fill a missing element with a typical,
   reasonable, or remembered value. Never infer a value from a neighboring
   period.
4. **IDs and sources are host-owned.** Do not create, renumber, or guess an
   evidence ID or source. If nothing fits, cite nothing and explain the gap.
5. **Keep data kinds distinct.** Observed values, forecast values, and
   probabilities are different claims. A 70% probability is not an observation
   and not a guarantee.
6. **Respect coverage.** Evidence for a single hour does not describe a whole
   day. Evidence for two days does not describe a week.
7. **Disclose conflicts.** If two supplied items disagree, report both and the
   disagreement. Do not silently pick one unless the host supplied an
   authority or priority rule.
8. **Do not convert silently.** If a unit conversion is necessary, state it.
   Do not convert a probability into a binary outcome.
9. **Cite only supplied IDs.** Every `evidence_id` in the response must exist
   in the input's evidence list. Every material weather statement should cite
   one or more IDs.

## Time alignment

- The user's window and the evidence window must overlap enough to answer the
  question. Exact alignment is not required, but the part that is covered must
  be stated.
- An observation is valid for the moment it was taken, not for the next day.
- A forecast's `observed_at` is when it was issued; its `valid_from`/`valid_to`
  is when it applies. Do not confuse the two.
- When the request is a day and the evidence is an hour, answer for that hour
  and say the rest of the day is uncovered.
- Forecast reliability generally decreases with lead time. Describe this as
  uncertainty; do not invent a numerical confidence.

## Missing evidence handling

| Situation | Response |
| --- | --- |
| No evidence at all, context complete | `insufficient_evidence`; list what is missing |
| Evidence for a different date/place | `insufficient_evidence`; state the mismatch |
| Partial evidence, core question still answerable | `answered`; state the uncovered part in `uncertainty` |
| Non-critical element missing | `answered`; note the limitation; do not assert about that element |
| Severity or alert status unknown | Do not claim conditions are safe; say the alert status is unknown |

"Missing" is not "absent in reality." A missing alert record means the skill
cannot confirm an alert, not that no alert exists.

## Linking output to input

The response has two layers:

- `evidence[]`: `{ evidence_id, claim }` pairs restating what the cited item
  supports.
- `recommendations[].evidence_ids` and `risks[].evidence_ids`: the IDs those
  statements depend on.

A host can verify every cited ID against the input. An ID that does not exist
is a fabricated fact, even if the surrounding sentence is true in the real
world.

## Invalid reasoning examples

| Invalid move | Why it fails |
| --- | --- |
| "There is no rain evidence, so it will not rain." | Absence of evidence is not evidence of absence. |
| Using yesterday's observation for tomorrow's commute. | Validity window mismatch. |
| Reporting 70% as "it will rain". | Probability treated as certainty. |
| Inventing `ev-rain-002` to support a second claim. | IDs and facts are host-owned. |
| "No alert supplied, so no warning is in effect." | Silence is not confirmation. |
| Averaging two conflicting sources without disclosure. | Hides a material conflict. |
| Filling a missing humidity value with 60%. | Fabricated fact. |
