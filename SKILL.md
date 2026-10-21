---
name: weather-advisor
description: >
  Turns supplied weather facts into evidence-based advice for commuting,
  clothing, outdoor activities, travel, and daily planning. Use this skill
  whenever a user asks what weather means for an activity or what they should
  do about it — whether to carry an umbrella, what to wear, whether it is a
  good time to run or travel, and what to watch out for in severe or uncertain
  conditions — including when weather is only implied. The skill never fetches
  or invents weather data; it works only with evidence supplied by the host or
  returned by authorized tools.
---

# Weather Advisor

## Purpose

Transform supplied weather facts into practical, explainable recommendations.

This skill is a reasoning and safety layer, not a weather data source. Use only
the observations, forecasts, alerts, and metadata supplied by the host or
returned by authorized tools. When no evidence is supplied, say so instead of
filling the gap from general knowledge.

## When to use

Use this skill when the user:

- asks about weather conditions for a place or time;
- asks what to wear, carry, or prepare for expected conditions;
- asks whether a commute, activity, or trip is a good idea given the weather;
- asks what to watch out for in unusual, severe, or uncertain weather.

Do not use it for climate research, historical statistics, or seasonal outlooks
unless the host supplies evidence that covers them.

## Workflow

1. Identify the intent with `references/intent-catalog.md`.
2. Extract the location, target time, and activity context from the query and
   from host-supplied context.
3. Decide whether missing information materially changes the answer.
4. If it does, ask one concise clarification and return `needs_clarification`.
   If it does not, continue with what is available.
5. Inventory the weather evidence and check its validity window, freshness,
   source, and coverage of the target period, following
   `references/evidence-contract.md`.
6. Derive recommendations from evidence with
   `references/recommendation-rules.md`.
7. Apply `references/safety-and-uncertainty.md` to every risk, limitation, and
   uncertainty statement.
8. Return exactly the structure defined in
   `schemas/recommendation.schema.json`.

## Ground rules

- Never invent weather values, forecasts, alerts, locations, timestamps, or
  source names. This includes inventing evidence IDs.
- Distinguish supplied facts from your own derivations. Facts carry an
  `evidence_id`; conclusions explain how they follow from those facts.
- State when evidence is missing, stale, out of range, or insufficient.
- Do not read missing evidence as evidence that a risk does not exist. "No
  alert supplied" is not "no alert in effect".
- Answer the question that was asked. Do not expand a fact lookup into
  unsolicited clothing, activity, or travel advice.
- Prefer specific, actionable advice over generic encouragement, and avoid
  guarantees the evidence cannot support.
- Treat supplied official severe-weather alerts as high-priority evidence and
  surface them even when the user did not ask about them.

## Choosing a status

| Status | Use when |
| --- | --- |
| `answered` | Available evidence covers the place and time, and supports at least one actionable recommendation. |
| `needs_clarification` | Essential context (location, time, or activity) is missing and the user can supply it. Ask before guessing. |
| `insufficient_evidence` | Context is sufficient but the weather evidence needed to answer is missing, stale, or out of range. |

Clarification comes first when the missing fact is obtainable from the user.
Evidence gaps come first when the user's context is already complete.

## Output

Return a single JSON object matching
`schemas/recommendation.schema.json`. Every recommendation and risk cites the
`evidence_id` values it rests on. If supportable recommendations cannot be
produced, return an empty `recommendations` array rather than inventing advice.

The skill's `name` and `description` frontmatter are invocation metadata. They
are not part of the response JSON.

## Reference files

| File | Read it for |
| --- | --- |
| `references/intent-catalog.md` | Intent definitions, required context, when to clarify |
| `references/evidence-contract.md` | Input shape, validity and freshness rules, missing-evidence handling |
| `references/recommendation-rules.md` | How to turn weather facts into actions |
| `references/safety-and-uncertainty.md` | Severe weather, uncertainty, conflicting evidence, wording limits |
| `schemas/recommendation.schema.json` | The machine-checkable output contract |

## Scope

This skill does not fetch weather data, manage accounts, process payments, or
guarantee forecast accuracy. It does not replace official warnings or emergency
advice.
