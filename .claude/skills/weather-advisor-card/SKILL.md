---
name: weather-advisor-card
description: >
  Render a Weather Advisor response as a visual HTML card. Use when the user
  asks for a card, a visual summary, a shareable page, or a picture of a
  weather recommendation, or invokes /weather-advisor-card.
argument-hint: "[response.json] [--brief brief.json] [--open]"
---

# Weather Advisor Card (Claude Code entry)

Turns a response that already conforms to
`schemas/recommendation.schema.json` into one self-contained HTML card, and
optionally folds in the windowed evidence from `demo/weather_brief.py` so the
card carries the hourly curves behind the advice.

The card is a rendering, not a new analysis. It adds no weather facts, invents
no evidence IDs, and generates no recommendations. Everything on it comes from
the response and the brief it was given. The rules for producing those stay in
the canonical skill at `../../../SKILL.md`.

## Invocation

```text
/weather-advisor-card /tmp/response.json --brief /tmp/brief.json --open
/weather-advisor-card /tmp/response.json
/weather-advisor-card 上海 通勤 明天 --open
```

`$ARGUMENTS` is the text after the command.

## Workflow

1. **Get a response.** If the user supplied a response JSON, use it. If they
   named a city or an activity instead, run the consultation entry
   (`/weather-advisor`, or the `weather-advisor` skill) first, and write its
   JSON response to a file.
2. **Get a brief.** If the response came from a live consultation, also write
   the brief it was based on. Without a brief the card still renders, but it
   shows the advice alone with no window evidence.
3. **Render.**

   ```bash
   python3 demo/weather_card.py /tmp/response.json --brief /tmp/brief.json \
     --output /tmp/card.html
   ```

4. **Report the path** and offer to open it. Pass `--open` only when the user
   asked to see it, or offer it once. Without `--output` the card is written to
   a temporary file and its path is printed.

## Producing the inputs

```bash
# Windowed evidence for the consultation
python3 demo/weather_brief.py Tokyo --date tomorrow --window 13:00-18:00 --compact \
  --output /tmp/brief.json

# The response must match the schema
python3 tests/validate_schema.py /tmp/response.json
```

Write the response with the Write tool rather than a shell heredoc, so the JSON
is not mangled by quoting. Validate it before rendering: the card rejects a
missing field, an unknown `status`, and an unknown `intent`, and reports which
one failed.

## What the card shows

- a status badge and the intent;
- the response summary, and the clarification question when there is one;
- window tiles and hourly curves, when a brief is supplied: temperature,
  apparent temperature, rain chance, precipitation, wind, gusts, PM2.5, PM10,
  with the peak figure and the evidence IDs behind each curve;
- the air-quality notice, and the demo's gaps (official alerts, UV, humidity,
  visibility, thunderstorm);
- evidence, recommendations, and risks, each citing its `evidence_id` values;
- missing information, uncertainty, the Open-Meteo attribution and license,
  and the statement that the card is not an official warning.

## Constraints

- Do not edit the response to make the card look better. If it fails to render,
  report the error the script gave.
- Do not add weather values, thresholds, or recommendations to the card. If the
  user wants more analysis, change the response, not the renderer.
- Do not present the card as an official warning, an official air-quality
  bulletin, or a live measurement. Air-quality figures are CAMS modelled
  forecasts, and the two AQI scales are not comparable.
- Keep the Open-Meteo attribution when the card is shown or shared.
- The card is self-contained and loads nothing from the network: no scripts, no
  external stylesheets, no remote images. Keep it that way, so it can be opened
  offline and shared as a single file.
- The renderer is `demo/weather_card.py`, part of the replaceable demo layer.
  It does not belong in the canonical `SKILL.md`.
