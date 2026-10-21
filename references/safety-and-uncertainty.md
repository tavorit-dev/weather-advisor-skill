# Safety and Uncertainty

Weather advice can affect whether someone travels, exercises, or exposes
themselves to hazardous conditions. The cost of overconfidence is higher than
the cost of saying "I don't have enough evidence."

## Status selection

Choose the status before writing the summary:

| Situation | Status |
| --- | --- |
| Evidence covers the asked place/time and supports an action | `answered` |
| Essential context missing and obtainable from the user | `needs_clarification` |
| Context complete but evidence missing, stale, or out of range | `insufficient_evidence` |

Do not return `answered` merely because you can write plausible advice. The
answer must be supported by supplied evidence.

## Severe weather

- Treat a supplied official alert as high-priority evidence. Surface it even
  when the user asked about something else.
- Preserve the alert's issuer, severity, and validity window. Do not upgrade,
  downgrade, or paraphrase it into a stronger or weaker claim.
- Do not claim an official warning exists unless it was supplied by a trusted
  source.
- If critical safety information is unavailable, say so. Do not assert that
  conditions are safe.
- When an alert is in effect, prefer advice consistent with the alert and with
  local authority guidance over generic comfort advice.
- Do not provide emergency-response instructions beyond directing the user to
  local emergency services and official updates.

## Missing data

- Name the missing element and its effect on the conclusion. "缺少风力数据，
  无法判断海边骑行是否安全" is useful; "海边骑行没问题" is not.
- Do not fill gaps with typical conditions, seasonal averages, or model memory.
- Distinguish "no data" from "data indicating no risk". These are different
  facts and often get conflated.
- If only a non-critical element is missing, answer what is supported and put
  the limitation in `uncertainty`.

## Time mismatch

- **Observation:** describes the moment it was taken. Do not extend it to the
  rest of the day or to tomorrow.
- **Short-range forecast:** applies to its stated validity window. Forecast
  issued time and validity window are different fields.
- **Long-range forecast:** less reliable. Describe the horizon; do not invent a
  confidence percentage.
- If the target period is only partly covered, say which part. Do not answer
  for the uncovered part.
- If evidence applies to a different day, do not "adjust" it to fit. Return
  `insufficient_evidence` when nothing else covers the request.

## Ambiguous location

- Do not default to the user's device location, the host's location, or a
  familiar city.
- Do not pick a city because it is the most likely match. If the location is
  missing or ambiguous (for example, two cities share a name), ask.
- A location supplied in host context counts as known; do not re-ask.
- When the location is approximate, state the granularity ("该城市范围" versus
  "某区") if it matters.

## Activity risk

- Weather risk is activity-specific. A temperature is not a verdict.
- Wind matters more for cycling, boating, and exposed ridges than for a short
  walk. Rain matters more for long outdoor exposure than for a covered commute.
- Do not declare an activity safe from a single variable. If the elements that
  drive the activity's risk are missing, say so.
- Do not give medical, physiological, or training prescriptions. Suggest
  consulting a qualified professional when health is at stake.
- Consider vulnerable groups only from stated context (children, older adults,
  health conditions). Do not infer them.

## Over-certainty

Avoid these constructions:

- "绝对安全" "肯定没问题" "百分之百" "肯定不会下雨" "一定不会" "保证"
- "没有任何风险" "可以放心" (when evidence is partial)
- Confidence scores such as `0.95` without a calibration method. Use
  explainable uncertainty instead.

Prefer:

- "根据当前证据，可能性较高/较低"
- "数据只覆盖到 X 点，之后的情况无法确认"
- "建议出发前复核官方最新预报"
- "如果出现 X，建议改为 Y"

## Conflicting evidence

- Disclose the conflict when two supplied items disagree on the same element
  and window.
- Do not silently average, pick the higher number, or choose the source you
  recognize.
- If the host supplies a source priority rule, apply it and say so.
- If there is no priority rule, present both and recommend rechecking before
  acting. Put the conflict in `uncertainty` and, when it affects safety, in
  `risks`.
- Conflicting evidence is a reason for caution, not a reason to fabricate a
  tiebreaker.

## Uncertainty writing

Each `uncertainty` entry should say:

1. what is uncertain,
2. why (missing coverage, stale data, forecast horizon, conflict), and
3. how it limits the conclusion.

Weak: "天气不确定。"

Strong: "降雨证据只覆盖 07:00–09:00，之后是否持续降雨无法确认，返程安排
建议出发前再查一次。"

Do not use `uncertainty` as a dumping ground for disclaimers unrelated to the
answer.

## Risks section

- Include a risk when the evidence implies a hazard the user should know about,
  even if the recommendation already addresses it.
- `severity` is `low`, `medium`, `high`, or `unknown`. Use `unknown` when the
  element that determines severity is missing. Do not invent a severity from a
  generic memory of what "sounds bad".
- Cite the evidence that implies the risk. If the risk is "unknown due to
  missing data", leave `evidence_ids` empty and explain the gap in the
  description.
- Do not list every possible weather hazard. List what the evidence and the
  user's activity make relevant.

## Final safety check

Before returning:

- [ ] Did I cite only IDs that exist in the input?
- [ ] Did I avoid asserting safety when evidence is missing?
- [ ] Did I preserve official alerts without altering them?
- [ ] Did I name uncovered periods and missing elements?
- [ ] Did I avoid guarantees and invented thresholds?
- [ ] Did I disclose conflicts instead of resolving them silently?
- [ ] Is the status consistent with the evidence I actually had?
