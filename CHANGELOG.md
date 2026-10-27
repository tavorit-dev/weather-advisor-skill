# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `/weather-advisor-card`, a second Claude Code entry at
  `.claude/skills/weather-advisor-card/SKILL.md`, which renders a schema-valid
  response as one self-contained HTML card. It delegates the rules to the same
  canonical `SKILL.md`.
- `demo/weather_card.py` and `demo/card.css`: the card renderer and its styles.
  Given a response alone it shows the status, intent, summary, evidence,
  recommendations, risks, missing information, and uncertainty; given a brief
  from `demo/weather_brief.py` it adds window tiles and hourly curves for
  temperature, apparent temperature, rain chance, precipitation, wind, gusts,
  PM2.5, and PM10, each labelled with its peak figure and the evidence IDs
  behind it. It adds no weather facts of its own, never rewrites the response,
  and rejects a response with a missing required field, an unknown `status` or
  `intent`, or a `needs_clarification` without a question. The output is a
  single file with no scripts, external stylesheets, or remote images, so it
  opens offline and follows the viewer's light or dark preference.
  `--check` verifies an existing card file; `--open` opens the result.
- A Chinese interface for the card, selected by the language of the question:
  `--query` with Han characters renders the labels in Chinese, anything else
  stays English, and `--lang zh|en` overrides it (regional tags such as `zh-CN`
  are accepted). Only the card's own labels are translated — the response's
  prose is printed verbatim in whatever language it was written, so a Chinese
  question against an English response yields Chinese chrome and an English
  body. The response's text is deliberately not inspected, so the interface
  follows the user rather than the response.
- Image export by printing to PDF: `--print` opens the card and points at the
  browser's print dialog, and `demo/card.css` gains print rules that force light
  ink on white regardless of the viewer's theme, keep a card from splitting
  across pages, and drop the on-screen print hint. Export goes through the
  browser precisely so the card stays script-free; a PNG would need an inline
  canvas script or a headless browser and would break the single-file,
  offline-openable property.
- `tests/test_weather_card.py`, an offline L1 suite covering self-containment,
  verbatim rendering of the response, curves and their evidence IDs,
  attribution and gap disclosure, the no-brief and summary-only paths, HTML
  escaping, rejection of invalid input, language selection in both directions,
  that every key exists in every language, the reading order, the collapsed
  evidence list and its print behaviour, and the print-export rules.
- Generation stats on the card, optionally supplied with `--stats`:
  `scripts/claude_session_stats.py` reads the current Claude Code transcript,
  deduplicates assistant messages by `message.id`, and reports input, output,
  and cache token usage plus elapsed time since the last prompt. The card closes
  with the measured input, output, and total tokens, the elapsed time, and the
  model, and states that the request rendering the card is not counted yet.
  Without a stats file the block is omitted rather than zeroed; the renderer
  rejects an unknown source or invalid figures. Covered offline by
  `tests/test_session_stats.py` and the new cases in `tests/test_weather_card.py`.
- English README as the default (`README.md`), with the Chinese version in
  `README.zh.md`; both are maintained as a synchronized pair.
- Detailed guides under `docs/`: getting started and host integration,
  architecture and design decisions, examples and test coverage, and repository
  layout. The root README is now a short introduction that links to them.
- Zero-dependency Open-Meteo demo (`demo/weather_demo.py`) that converts a city
  name into a skill-ready input envelope, with `live` and `offline` modes.
- Offline Tokyo fixtures under `demo/fixtures/` and L1 data-layer tests in
  `tests/test_demo.py`.
- `demo/README.md` documenting field mapping, attribution, licensing limits,
  and how to replace the weather provider.
- Claude Code project skill at `.claude/skills/weather-advisor/SKILL.md`,
  exposing `/weather-advisor` and the live demo workflow while delegating rules
  to the canonical `SKILL.md`. Claude Code-only metadata such as
  `argument-hint` stays in the entry, keeping the canonical skill portable.
- `scripts/install_claude_skill.py` for installing the skill and its supporting
  files under `~/.claude/skills/weather-advisor`.
- Optional Stop hook (`.claude/hooks/validate-weather-output.py`) that validates
  a requested JSON response against the schema. It is disabled by default.
- `docs/claude-code.md` covering invocation, live mode, installation, hook
  configuration, and verification.
- `tests/test_claude_integration.py` covering the entry metadata, installer,
  and hook behavior.
- `demo/weather_brief.py`, a compact windowed view of the demo evidence with
  summary statistics and evidence IDs, plus `tests/test_weather_brief.py`.
  It reduces live-consultation round trips and context size without adding a
  new data source.
- `weather_brief.py --compact`, `--summary-only`, and `--every N`: a 12-hour
  offline brief drops from 9.9 KB to 7.2 KB compact, 3.6 KB at `--every 3`, or
  1.7 KB with summary-only compact.

- Project banner and logo under `images/`, shown at the top of the READMEs.
- Air-quality support in the demo, on by default. `demo/weather_demo.py` now
  fetches Open-Meteo's air-quality endpoint and merges PM2.5, PM10, and the US
  and European AQI onto the same hourly timeline as the weather evidence, so a
  consultation about running, cycling, or other strenuous activity can weigh
  particulate levels against the forecast. `--no-air-quality` restores the
  weather-only envelope. Adds `demo/fixtures/air-quality-tokyo.json` (synthetic)
  and `AIR_QUALITY_FIELDS` / `fetch_air_quality` in `demo/weather_demo.py`.
- `air_quality`, `summary.particulate_matter_2_5`, and
  `summary.particulate_matter_10` sections in `demo/weather_brief.py`, with
  `source.air_quality_attribution`. The two indices share one evidence type, so
  hourly rows key them separately as `us_aqi` and `european_aqi`; `--no-air-quality`
  omits all of it. `air_quality` is no longer listed in `demo_gaps`.
- Coverage in `tests/test_demo.py` and `tests/test_weather_brief.py` for the
  merged timeline, the index-scale descriptions, the two-index keying, and the
  `--no-air-quality` path.

### Removed

- The README banner (`images/banner.png`). It was a 1280×640 image at
  `width="100%"`, so it took most of the first screen while carrying almost no
  information; both READMEs now open on the title and language switch instead.
- `images/logo.png` and the `images/` directory. The logo was a 200×200 square
  with a white background, so it could not serve as a wordmark on a dark theme;
  the header is now text and badges only, and nothing else referenced it.

### Changed

- Consolidated project-level constraints, pre-release checks, and contribution
  rules in `CLAUDE.md`; they are no longer duplicated in the README.
- Renamed the English README from `README.en.md` to `README.md`; the Chinese
  README moved to `README.zh.md`.
- Corrected the license reference from MIT to Apache-2.0, matching `LICENSE`.
- `demo/weather_demo.py` offline output grew from 72 to 120 evidence items and
  from 22.6 KB to 43.7 KB, and the offline compact brief from 7.2 KB to 11.2 KB,
  because air quality is now included by default. Use `--no-air-quality` for the
  previous sizes. `metadata.data_note` now states that air quality is modelled
  forecast data, and `attribution` carries both sources.
- Aligned both READMEs with the current test layout: the local-validation block
  now lists `test_weather_brief.py` and `test_claude_integration.py` alongside
  `test_demo.py`, matching the five commands required before a commit.
- Added the compact brief size range (1.7–13 KB against roughly 50–100 KB for a
  live full-day envelope) to both READMEs, so the token-saving claim is
  quantified where the demo commands are shown.
- Referred to the 32 entries in `tests/cases.jsonl` as acceptance cases rather
  than test cases, matching `tests/README.md`.
- Made Simplified Chinese the default README. `README.md` is now the Chinese
  version and the English version moved to `README.en.md`; both were updated in
  place, and `CLAUDE.md`, `docs/repository-layout.md`, and this file now point
  at the new paths.
- `scripts/install_claude_skill.py` now installs both Claude Code entries. The
  card entry lands at `card/SKILL.md` inside the installed skill, and each
  entry's relative link to the canonical skill is rewritten for its own depth.
  Claude Code derives a skill's name from its frontmatter, so the nesting does
  not change the command name and does not shadow the main `SKILL.md`.
- The pre-commit validation list now has six commands:
  `tests/test_weather_card.py` joins the five required checks, in `CLAUDE.md`,
  `README.md`, `README.en.md`, `tests/README.md`, and
  `docs/getting-started.md`.
- Reordered the card so it reads by what the reader needs first: the summary,
  then the recommendations, then the window evidence behind them, the risks, and
  finally the evidence list. Previously the window tiles and curves came first
  and the recommendations sat below the evidence. The recommendations card
  carries an accent edge, and only when the response has recommendations — an
  empty list keeps a plain card rather than highlighting a placeholder.
- The card's evidence list is now collapsed behind a `<details>` element headed
  with its entry count (for example "Evidence (2)"), since it is the longest
  block on the card and the least useful to a reader who is not auditing a
  citation. `<details>` is markup rather than script, so the card keeps its
  zero-script property, and a browser without it shows the list open. Expanding
  it explains what an `evidence_id` is and why the card shows them. The print
  rules reveal the list unconditionally: a paper reader cannot click, so an
  export would otherwise silently omit the evidence.
- The card's `demo_gaps` notice now lists each uncovered metric on its own line
  instead of a comma-separated run, and states that the demo has no data source
  for them, so "not shown" is not read as "not happening". The "absence of an
  alert is not evidence that no alert is in effect" caveat is now a separate
  sentence below the list rather than the tail of one long line.
- The card's window-evidence and recommendations sections gained a one-line
  explanation of what they contain, and the recommendations section is
  introduced as "what to do, and why".
- Redesigned the card for phone-sized screens. The layout was a stack of a
  dozen separately framed cards, which at 390px read as box-in-box clutter and
  spent height on padding and gaps the advice needed. It is now one sheet with
  hairline-separated sections, and body text is 16px with the summary figures
  set in tiles. The same card measured 3934px tall before and 2867px after.
- The card's hourly curves are now tiled in a grid instead of stacked one per
  row. Eight full-width charts made the window section two thirds of the
  document (2606px of 3934px) and pushed the risks and the caveats far below
  the fold; tiled, all eight are visible at once and the section is 8 tiles in
  four rows. The grid is two columns on a phone and adds a column as the sheet
  widens. Print pins it to three columns so the layout does not depend on the
  paper size or margin the reader picked.
- A curve tile's caption is two fixed lines, the label above the peak figure.
  On one line, "PM2.5  16.4 μg/m³" does not fit a two-column tile at 360px, and
  letting it wrap would push that tile's chart down so the charts in a row no
  longer lined up.
- Curve captions no longer print the unit twice. The peak figure already ends
  with its unit, so the caption read "18.4 °C °C".
- The card no longer prints an `evidence_id` under every recommendation, risk,
  and chart. Doing so put 59 chips on one card and drowned the data they were
  meant to support; the IDs are shown once, in the evidence section, which is
  where a reader goes to audit a citation, and the section explains why they are
  there. A test asserts that every ID the card prints resolves to an entry in
  the response's evidence list, so a dangling reference fails the suite.
- A `total`/`peak` summary tile now spans the full width of the metrics grid. It
  is the only value that is a phrase rather than a number, so it was the only
  one that wrapped, and a grid row is as tall as its tallest tile — leaving the
  numbers beside it stretched into half-empty boxes. Tiles in a row are now
  equal at every tested width from 320px to 640px.
- The metrics grid is a fixed two columns. `auto-fit` produced three at phone
  width, which left an empty cell beside the full-width total/peak tile and made
  each tile narrow enough that "16.1 km/h" wrapped onto two lines.
- The collapsed evidence list's tap target is 44px tall. At 24px it was below
  the minimum comfortable touch size.

### Fixed

- `tests/test_weather_brief.py` compared the full JSON of two separate
  `weather_brief.py` runs, including the wall-clock `retrieved_at` each run
  stamps. When the two processes straddled a second boundary the test failed
  with no real defect behind it. The comparison now excludes that one field,
  which is what "`--compact` changes serialization only" was meant to assert.

## [0.1.0] - 2026-10-21

### Added

- `SKILL.md` with the weather-advisor workflow, evidence rules, safety rules,
  and output pointer.
- Four reference documents: intent catalog, evidence contract, recommendation
  rules, and safety/uncertainty guidance.
- `schemas/recommendation.schema.json` defining the machine-checkable response
  contract, including clarification and insufficient-evidence states.
- Six input/output example pairs covering commute rain, cold-weather clothing,
  outdoor wind, multi-day travel, missing location, and missing weather
  evidence.
- 32 test cases across normal, missing-information, evidence-anomaly,
  risk/uncertainty, and output-structure categories.
- Validation tooling: schema validation, evidence-linkage checks, example
  runner, case linter, and per-case grader.

### Notes

- The skill does not fetch weather data. Hosts supply evidence in the structure
  described in `references/evidence-contract.md`.
- All example weather values are synthetic and marked with the source
  `example-provider`.
