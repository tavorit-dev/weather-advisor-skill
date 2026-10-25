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
- `tests/test_weather_card.py`, an offline L1 suite covering self-containment,
  verbatim rendering of the response, curves and their evidence IDs,
  attribution and gap disclosure, the no-brief and summary-only paths, HTML
  escaping, and rejection of invalid input.
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
