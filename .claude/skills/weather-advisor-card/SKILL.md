---
name: weather-advisor-card
description: >
  Render a Weather Advisor response as a visual HTML card. Use when the user
  asks for a card, a visual summary, a shareable page, or a picture of a
  weather recommendation, or invokes /weather-advisor-card.
argument-hint: "[response.json] [--brief brief.json] [--stats stats.json] [--lang zh|en] [--open] [--print]"
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
/weather-advisor-card /tmp/response.json --stats /tmp/stats.json
/weather-advisor-card /tmp/response.json
/weather-advisor-card 上海 通勤 明天 --open
/weather-advisor-card /tmp/response.json --brief /tmp/brief.json --print
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
3. **Collect generation stats.** Measure the round's real cost from the
   session transcript:

   ```bash
   python3 scripts/claude_session_stats.py --output /tmp/stats.json
   ```

   The helper locates the current session through `$CLAUDE_CODE_SESSION_ID`,
   sums token usage since the last prompt, and measures elapsed time to now.
   If it fails — not running under Claude Code, no session id, no transcript,
   or no usage yet — render without `--stats` and tell the user the card has
   no cost block and why. Never estimate or hand-write these numbers.
4. **Render.**

   ```bash
   python3 demo/weather_card.py /tmp/response.json --brief /tmp/brief.json \
     --stats /tmp/stats.json --output /tmp/card.html
   ```

5. **Report the path** and offer to open it. Pass `--open` only when the user
   asked to see it, or offer it once. Without `--output` the card is written to
   a temporary file and its path is printed.

The stats cover the round up to the moment the card is rendered; the request
that actually renders it has not finished, so it is not yet in the transcript.
The card says so rather than implying the figure is the final bill.

## Language

The card's interface follows the language of the question:

```bash
# Chinese question -> Chinese interface
python3 demo/weather_card.py /tmp/response.json --brief /tmp/brief.json \
  --query "今日天津天气" --output /tmp/card.html

# Explicit override
python3 demo/weather_card.py /tmp/response.json --lang zh --output /tmp/card.html
```

- Pass the user's question with `--query`. A question containing Han characters
  selects Chinese; anything else selects English, which is the default.
- Use `--lang zh|en` to force a language regardless of the question. Regional
  tags such as `zh-CN` or `en-US` are accepted.
- Only the card's own labels are translated. The response's prose — summary,
  claims, actions, reasons, risks, uncertainty — is printed verbatim in
  whatever language the response used. Never translate it, and never let the
  response's language decide the interface: a Chinese question with an English
  response is a normal case and must keep a Chinese interface.
- Never pass the response's own text as `--query`; that would make the
  interface follow the response instead of the user.

## Exporting as an image

Export is a browser print, which keeps the card free of scripts:

```bash
python3 demo/weather_card.py /tmp/response.json --brief /tmp/brief.json \
  --print --output /tmp/card.html
```

- `--print` opens the card and prints the instruction to use the browser's
  print dialog (Ctrl/Cmd+P) and choose **Save as PDF**. Tell the user the same.
- The print stylesheet forces light ink on white, keeps cards from splitting
  across pages, and drops the on-screen print hint, so the exported file is
  readable rather than a screenshot of the dark theme.
- Do not add a screenshot library, a headless browser, or an inline script to
  produce a PNG. The card stays a single script-free HTML file that can be
  opened offline; a PDF export is the supported path.

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

In reading order, most useful first:

- a status badge and the intent;
- the response summary, and the clarification question when there is one;
- the recommendations, with their reasons. This section carries an accent edge,
  and only when the response actually has recommendations;
- window tiles and hourly curves, when a brief is supplied: temperature,
  apparent temperature, rain chance, precipitation, wind, gusts, PM2.5, PM10,
  each with its peak figure;
- the air-quality notice, and the demo's gaps (official alerts, UV, humidity,
  visibility, thunderstorm) listed one per line, with the note that the demo
  has no data source for them;
- the risks, each with its severity;
- the evidence list, collapsed behind a `<details>` headed with its entry
  count. Expanding it shows each claim with its ID, and explains what an
  `evidence_id` is and why the card shows them;
- missing information, uncertainty, the Open-Meteo attribution and license,
  and the statement that the card is not an official warning;
- when `--stats` is supplied, a closing generation-stats block: input, output,
  and total tokens, elapsed time, and the model, followed by the note that the
  figures come from the Claude Code session transcript and exclude the request
  that renders the card. Without `--stats` the block is absent, not zeroed.

The card is laid out for a phone: one sheet divided by hairline rules rather
than a stack of separately framed cards, and the hourly curves tiled in a grid
rather than stacked one per row. Eight full-width charts made the window section
two thirds of the document and pushed the risks and the caveats far below the
fold. Tiling keeps every series visible at once — do not put them behind a
horizontal swipe, where a reader may never scroll to a series. The grid is two
columns on a phone and widens with the sheet; print pins it to three columns.

Evidence IDs are shown once, in the evidence section, not under every
recommendation, risk, and chart. Printing them under each item put dozens of
chips on one card and drowned the data they were meant to support.

The collapse is `<details>`, which is markup rather than script, so the card
keeps its zero-script property. Do not replace it with a JavaScript toggle, and
do not remove it: the evidence list is the longest block on the card, and a
reader who is not auditing a citation should not have to scroll past it to
reach the advice.

## Constraints

- Do not edit the response to make the card look better. If it fails to render,
  report the error the script gave.
- Do not add weather values, thresholds, or recommendations to the card. If the
  user wants more analysis, change the response, not the renderer.
- Session stats are measured, not authored. Pass only a file produced by
  `scripts/claude_session_stats.py`; never fill in token counts or elapsed time
  yourself, and never render a zeroed block to stand in for a failed
  measurement. The renderer refuses a stats file whose source is not the
  transcript helper.
- Do not present the card as an official warning, an official air-quality
  bulletin, or a live measurement. Air-quality figures are CAMS modelled
  forecasts, and the two AQI scales are not comparable.
- Keep the Open-Meteo attribution when the card is shown or shared. It is a
  proper name and stays in English in both languages.
- The card is self-contained and loads nothing from the network: no scripts, no
  external stylesheets, no remote images. Keep it that way, so it can be opened
  offline and shared as a single file. Image export works through the browser's
  print dialog precisely so this stays true.
- Anything the card collapses must still appear in a printed export. A paper
  reader cannot click, so the print rules reveal collapsed content rather than
  reproducing the on-screen folded state. Never fold content away in a way that
  only a pointer can restore.
- The renderer is `demo/weather_card.py`, part of the replaceable demo layer.
  It does not belong in the canonical `SKILL.md`.
