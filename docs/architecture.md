# Architecture

This document explains what the skill covers, how an agent moves from a query
to a response, and why the contract is shaped the way it is. The binding rules
live in [`SKILL.md`](../SKILL.md) and [`references/`](../references/); this page
is the map.

## Scope

The first release includes:

- a standard `SKILL.md` with metadata;
- six weather-related intents;
- clarification and missing-information rules;
- evidence constraints and recommendation derivation rules;
- severe-weather and uncertainty handling;
- a unified output contract (JSON Schema, Draft 2020-12);
- six example pairs, 32 test cases, and local validation tooling;
- a key-free Open-Meteo demo adapter (`demo/`), separate from the skill core.

The first release does not include:

- weather fetching built into the skill core; `demo/` is a replaceable local
  adapter for verification only;
- a standalone agent runtime;
- user accounts, credits, or payments;
- a web service, database, or admin console;
- model-specific prompt optimization.

## Workflow

1. Identify the intent with
   [`references/intent-catalog.md`](../references/intent-catalog.md).
2. Extract the location, target time, and activity context.
3. Decide whether missing information materially changes the answer.
4. If it does, ask one concise clarification and return `needs_clarification`.
5. Check each evidence item's validity window, freshness, source, and coverage
   of the target period in
   [`references/evidence-contract.md`](../references/evidence-contract.md).
6. Derive recommendations following
   [`references/recommendation-rules.md`](../references/recommendation-rules.md).
7. Apply [`references/safety-and-uncertainty.md`](../references/safety-and-uncertainty.md)
   to risks and uncertainty.
8. Return the structure defined by
   [`schemas/recommendation.schema.json`](../schemas/recommendation.schema.json).

## Intents

| Intent ID | Example query | Focus |
| --- | --- | --- |
| `weather_lookup` | Will it rain in Shanghai tomorrow? | Report the fact; do not expand into unrelated advice |
| `clothing_advice` | What should I wear tomorrow? | Temperature, apparent temperature, rain, activity |
| `commute_advice` | Should I bring an umbrella to work tomorrow? | Commute-window rain, wind, visibility, alerts |
| `outdoor_activity` | Is it a good time for a run this afternoon? | Rain, wind and gusts, temperature, UV, alerts |
| `travel_planning` | What should I prepare for a weekend in Hangzhou? | Multi-day weather, itinerary fit, forecast horizon |
| `general_weather_advice` | What should I watch out for in this weather? | Infer the purpose from context; clarify only when needed |

Classification order, required context, and failure examples are owned by
[`references/intent-catalog.md`](../references/intent-catalog.md).

## Status model

| `status` | Meaning |
| --- | --- |
| `answered` | Evidence covers the asked place and time, and supports at least one actionable recommendation |
| `needs_clarification` | Essential context (location, time, activity) is missing and the user can supply it |
| `insufficient_evidence` | Context is complete, but the needed weather evidence is missing, stale, or out of range |

Clarification comes before insufficient evidence: if the user can supply a
missing fact, ask rather than guess.

## Key design decisions

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

The enforceable versions of these principles are the invariants in
[`CLAUDE.md`](../CLAUDE.md).
