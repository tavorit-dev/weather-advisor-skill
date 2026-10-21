# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed

- Consolidated project-level constraints, pre-release checks, and contribution
  rules in `CLAUDE.md`; they are no longer duplicated in the README.
- Renamed the English README from `README.en.md` to `README.md`; the Chinese
  README moved to `README.zh.md`.
- Corrected the license reference from MIT to Apache-2.0, matching `LICENSE`.

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
