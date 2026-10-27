# Claude Code Integration

This page documents the Claude Code layer described in the design: two
project-level skills, the `/weather-advisor` and `/weather-advisor-card`
entries, the live-weather demo, an optional Stop hook, and a personal install
script.

The canonical skill remains [`SKILL.md`](../SKILL.md). The Claude Code entries
are thin wrappers around it, so the workflow, evidence rules, and output
contract are defined in one place.

## Layout

```text
.claude/
├── settings.json                       # Hooks are opt-in; empty by default
├── skills/
│   ├── weather-advisor/
│   │   └── SKILL.md                    # Claude Code entry and /weather-advisor
│   └── weather-advisor-card/
│       └── SKILL.md                    # /weather-advisor-card
└── hooks/
    └── validate-weather-output.py      # Optional response validator / Stop hook
scripts/
└── install_claude_skill.py             # Personal installation
```

## Use it in this repository

Open a Claude Code session at the repository root. The project skill is
discovered automatically. If the `.claude/skills/` directory did not exist when
the session started, run `/reload-skills`; restart the session if it still does
not appear. Its name becomes the slash command:

```text
/weather-advisor Tokyo outdoor running tomorrow
/weather-advisor 上海 通勤 明天
/weather-advisor --live Osaka travel tomorrow
```

`$ARGUMENTS` is passed through as the user query. Natural-language weather
questions also trigger the skill through its `description`; that decision is
made by Claude Code, not by a hook.

`--live` is a convention interpreted by the skill, not a Claude Code flag. When
the user asks for live weather, prefer the compact brief. It returns only the
requested hours, summary statistics, and evidence IDs, so one tool call is
usually enough:

```bash
# User named a time range: keep hourly rows
python3 demo/weather_brief.py <city> --date today --window 13:00-18:00 --compact

# Whole day with no time range: keep a 3-hour curve
python3 demo/weather_brief.py <city> --date tomorrow --every 3 --compact

# Only extremes are needed: summary only
python3 demo/weather_brief.py <city> --date tomorrow --summary-only --compact

# Weather only, when context is tight and air quality is not decisive
python3 demo/weather_brief.py <city> --date tomorrow --every 3 --compact --no-air-quality

# Offline fixture
python3 demo/weather_brief.py Tokyo --offline --date 2026-10-22 --window 08:00-12:00 --compact
```

Air quality is on by default: the brief carries PM2.5, PM10, and both the US and
European AQI alongside the weather, plus a separate `air_quality_attribution`.
It costs roughly a third of the payload, which is usually worth paying because
particulate levels often decide whether strenuous outdoor activity is advisable.

| Mode | What it returns | Offline 12-hour size |
| --- | --- | ---: |
| default | hourly rows + summary | 15.3 KB |
| `--compact` | hourly rows + summary, no indentation | 11.2 KB |
| `--every 3 --compact` | 3-hour curve + summary | 5.6 KB |
| `--summary-only` | summary statistics and IDs only | 4.0 KB |
| `--summary-only --compact` | summary statistics and IDs, no indentation | **2.8 KB** |
| `--no-air-quality --compact` | hourly rows + weather summary | 7.2 KB |
| `--no-air-quality --summary-only --compact` | weather statistics and IDs | 1.7 KB |

For a live 24-hour Tianjin check the hourly compact brief was 19.6 KB, the
`--every 3` compact brief was 8.4 KB, and the summary-only compact brief was
2.8 KB; with `--no-air-quality` these fell to 12.7 KB, 5.4 KB, and 1.7 KB.

The brief is typically 3–20 KB, compared with roughly 44–86 KB for a live
full-day envelope. Use `demo/weather_demo.py` only when the complete evidence
set or a schema-ready input envelope is required.

Two things to keep straight when air quality is present:

- The US and European indices share the `air_quality_index` evidence type, so
  hourly rows key them separately as `us_aqi` and `european_aqi`. Quote the scale
  by name; the numbers are not comparable, and they can move in opposite
  directions over the same day. Prefer PM2.5 concentration for a trend.
- These are modelled forecasts (CAMS), not ground-station measurements. When air
  quality drives the answer, say so and point to the local environmental
  authority for the official AQI rather than presenting the demo's numbers as a
  bulletin.

`--offline` uses the synthetic Tokyo fixture and requires an explicit date
because the fixture is fixed. If the command fails, the skill must explain the
failure rather than invent values.

### Token-efficient consultation pattern

1. Use one `weather_brief.py` call with the narrowest window the user gave.
2. Add `--compact`. For a whole-day question, use `--every 3`; use
   `--summary-only` only when extremes or a yes/no are enough.
3. Cite the IDs in the brief; do not re-print the full evidence.
4. Answer in the response sections; do not read the same reference files again
   in the same session.
5. Keep a simple suitability answer to the recommended window, 3–5 key values,
   3–4 recommendations, and 2–3 risks. Expand only when asked.

The brief is a view of the demo evidence, not a new data source and not a
recommendation engine. The full contract remains
[`references/evidence-contract.md`](../references/evidence-contract.md).

## Response modes

The canonical contract defines the fields. In a conversation, the Claude Code
entry presents them as Summary, Weather evidence, Recommendations, Risks and
uncertainty, and Missing information. When the user asks for JSON, return one
object conforming to
[`schemas/recommendation.schema.json`](../schemas/recommendation.schema.json)
and validate it:

```bash
python3 tests/validate_schema.py response.json
```

## Visual card

`/weather-advisor-card` renders a response as one self-contained HTML card. It
is a second entry, `.claude/skills/weather-advisor-card/SKILL.md`, and it
delegates the rules to the same canonical `SKILL.md`:

```text
/weather-advisor-card /tmp/response.json --brief /tmp/brief.json --open
/weather-advisor-card 上海 通勤 明天 --open
```

The renderer is [`demo/weather_card.py`](../demo/weather_card.py), part of the
replaceable demo layer:

```bash
python3 demo/weather_card.py response.json --brief brief.json --output card.html
python3 demo/weather_card.py response.json --query "今日天津天气" --output card.html
python3 demo/weather_card.py response.json --brief brief.json --print
python3 demo/weather_card.py --check card.html
```

- **Response only.** Without `--brief` the card shows the summary, status,
  intent, recommendations, risks, evidence, missing information, and
  uncertainty. No metrics or curves are drawn.
- **With a brief.** The window from `demo/weather_brief.py` is added as summary
  tiles and hourly curves — temperature, apparent temperature, rain chance,
  precipitation, wind, gusts, PM2.5, PM10 — each labelled with its peak figure.
- **Reading order.** The card is ordered by what the reader needs first: the
  summary, then the recommendations, then the window evidence behind them, the
  risks, and finally the raw evidence list. The recommendations section carries
  an accent edge, and only when there is real advice to show — an empty list is
  not highlighted.
- **Mobile layout.** The card is designed at phone width: one sheet divided by
  hairline rules rather than a stack of separately framed cards, which at 390px
  reads as box-in-box clutter and spends height on padding and gaps. The hourly
  curves are a horizontal snap-scrolling gallery rather than a vertical stack,
  because eight stacked charts made the window section two thirds of the
  document and pushed the risks and caveats far below the fold. The gallery uses
  `scroll-snap` and native overflow, so the card stays script-free; the print
  rules lay the charts out as a two-column grid, since a gallery cannot be
  swiped on paper.
- **Evidence IDs.** The card does not print an `evidence_id` under every
  recommendation, risk, and chart. Doing so put dozens of chips on one card and
  drowned the data they were meant to support. The IDs are shown once, in the
  evidence section, which is where a reader goes to audit a citation.
- **Collapsed evidence.** The evidence list folds behind a `<details>` element
  headed with its entry count, since it is the longest block on the card and
  the least useful to a reader who is not auditing a citation. `<details>` is
  markup, not script, so the card stays script-free, and a browser without it
  shows the list open. Expanding it explains what an `evidence_id` is and why
  the card shows them.
- **Uncovered metrics.** The demo's `demo_gaps` are listed one per line, with a
  line stating that the demo has no data source for them, so a reader does not
  read "not shown" as "not happening".
- **What it refuses.** A response missing a required field, an unknown `status`,
  an unknown `intent`, or a `needs_clarification` without a question is
  rejected with the reason on stderr, rather than rendered as a plausible card.
- **What it never does.** The card adds no weather values, thresholds, or
  recommendations, and never rewrites the response to look better. Every figure
  comes from the response or the brief.
- **Self-contained.** No scripts, external stylesheets, or remote images, so it
  opens offline and can be shared as a single file. It follows the viewer's
  light or dark preference.

### Language

The card's interface follows the question, not the response:

```bash
python3 demo/weather_card.py response.json --query "今日天津天气" --output card.html
python3 demo/weather_card.py response.json --lang zh --output card.html
```

`--query` takes the user's question; a question containing Han characters
selects the Chinese interface, and anything else selects English, which is the
default. `--lang zh|en` overrides it, and regional tags such as `zh-CN` or
`en-US` are accepted.

Only the card's own labels are translated. The response's prose is printed
verbatim in whatever language it was written, so a Chinese question against an
English response is a normal case: Chinese chrome, English body. The response's
text is deliberately not inspected to choose the language, because that would
make the interface follow the response instead of the user.

### Exporting as an image

```bash
python3 demo/weather_card.py response.json --brief brief.json --print --output card.html
```

`--print` opens the card and points at the browser's print dialog (Ctrl/Cmd+P),
where **Save as PDF** produces the exported file. This is the supported export
path because it keeps the card script-free: a PNG would need an inline canvas
script or a headless browser, and both would break the single-file,
offline-openable property.

The print stylesheet forces light ink on white regardless of the viewer's theme,
prevents a card from splitting across pages, and drops the on-screen print hint,
so the export reads as a document rather than a screenshot of the dark theme. It
also expands the collapsed evidence list, since a paper reader cannot click to
open it and the export would otherwise silently omit the evidence.

Output goes to a temporary file whose path is printed, or to `--output`.
`--open` opens it in the browser, and `--print` opens it and explains the export
step. `--check` verifies an existing card file is well-formed.

Because the card restates the demo's evidence, it keeps the Open-Meteo
attribution and license, states that air quality is a CAMS modelled forecast
rather than a measurement, notes that the two AQI scales are not comparable,
and carries the demo's `demo_gaps` — including that the absence of an alert is
not evidence that no alert is in effect. Keep those when the card is shared.

## Install for personal use

Install the skills and their supporting files into
`~/.claude/skills/weather-advisor`:

```bash
python3 scripts/install_claude_skill.py
```

The installer copies the whole repository (excluding `.git`, `.venv`, and
`.claude`), renames the canonical skill to `CANONICAL-SKILL.md`, and writes the
Claude Code entries as `SKILL.md` and `card/SKILL.md`. The installed layout
therefore still contains `references/`, `schemas/`, `demo/`, and `tests/` next
to the entries.

Claude Code derives a skill's name from its frontmatter rather than its
directory, so `/weather-advisor-card` works from the nested `card/` directory,
which also keeps it from shadowing the main entry's `SKILL.md`. Each entry's
relative link to the canonical skill is rewritten for its own depth during
installation.

Options:

```bash
python3 scripts/install_claude_skill.py --dest /path/to/skills/weather-advisor
python3 scripts/install_claude_skill.py --force
```

`--force` replaces an existing destination. The installer refuses to write
inside the repository.

After installing, restart Claude Code or reload skills, then try:

```text
/weather-advisor Tokyo outdoor running tomorrow
/weather-advisor --live Osaka travel tomorrow
/weather-advisor-card /tmp/response.json --brief /tmp/brief.json --open
```

## Optional Stop hook

The hook validates a weather JSON response in the final assistant turn against
the repository schema. It is **disabled by default** because it adds work to
every session and can only validate a response when the final message contains
a fenced JSON block that looks like a skill response.

Why the default is off:

- The hook cannot invent the target file when the model answered in prose.
- Schema validation is better run explicitly and reproducibly.
- The first release should not require a hook to be useful.

### Manual use

```bash
python3 .claude/hooks/validate-weather-output.py response.json
```

Exit code `0` means valid or nothing to validate; `2` means the response failed
the schema. The hook needs `jsonschema`:

```bash
python -m pip install -r tests/requirements.txt
```

If the dependency is missing while running as a hook, it prints a warning and
exits `0` instead of blocking the session.

### Enable it

Add the following to `.claude/settings.json` (or merge it into your existing
hook configuration):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/validate-weather-output.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

When invoked as a Stop hook, the script reads the hook payload from stdin. It
uses `last_assistant_message` when present, otherwise it reads the final
assistant turn from `transcript_path`. It validates the last fenced JSON block
that contains `schema_version`, `status`, and `recommendations`. A
conversational answer, or a transcript that cannot be read, is a no-op.

The hook is a convenience, not a security boundary. It does not prove that a
recommendation follows from the evidence; `tests/check_evidence.py` and the
test cases cover that.

## Verify the integration

- `/weather-advisor` is recognized and receives the arguments.
- `/weather-advisor-card` is recognized and receives the arguments.
- `claude plugin validate .claude/skills` reports valid frontmatter (Claude
  Code v2.1.233+).
- Live mode actually calls Open-Meteo; `--offline` does not use the network.
- With no weather evidence, the skill asks for clarification or returns
  insufficient evidence instead of inventing values.
- Requested JSON passes `tests/validate_schema.py`.
- A rendered card opens offline, loads nothing from the network, and every
  figure on it appears in the response or the brief it was given.
- If the hook is enabled, `/hooks` lists it and the Stop event fires.
- After a personal install, `demo/weather_demo.py` and `demo/weather_card.py`
  run from the installed directory and `CANONICAL-SKILL.md` is present.

## Limits

- `argument-hint` is a Claude Code frontmatter extension. It appears only on
  the Claude Code entries, never on the canonical root `SKILL.md`, so the
  canonical skill stays portable to claude.ai and Skills API packaging (which
  accept only `name`, `description`, `license`, `compatibility`, `metadata`,
  and `allowed-tools`).
- The card is a view of a response, not a second opinion. It cannot detect
  advice that the evidence does not support; that is what
  `tests/check_evidence.py` and the test cases are for.
- The card renders the response as given. If the response is wrong, the card is
  wrong in the same way.
- The demo is a replaceable adapter, not part of the skill core. See
  [`demo/README.md`](../demo/README.md) for provider limits, attribution, and
  licensing.
- The personal installer copies the repository; it does not install Python
  dependencies or configure hooks.
- The Stop hook validates the JSON shape, not the factual consistency of the
  advice.
