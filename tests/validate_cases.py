#!/usr/bin/env python3
"""Lint tests/cases.jsonl as a specification file.

This does not run a model. It checks that every case is well-formed, that
expectations use supported fields, and that cited evidence IDs exist in the
case input.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "tests" / "cases.jsonl"

CATEGORIES = {
    "normal",
    "missing_information",
    "evidence_anomaly",
    "risk_uncertainty",
    "output_structure",
}
STATUSES = {"answered", "needs_clarification", "insufficient_evidence"}
INTENTS = {
    "weather_lookup",
    "clothing_advice",
    "commute_advice",
    "outdoor_activity",
    "travel_planning",
    "general_weather_advice",
}
EXPECT_KEYS = {
    "status",
    "status_in",
    "intent",
    "intent_in",
    "min_recommendations",
    "max_recommendations",
    "min_risks",
    "min_medium_or_higher_risks",
    "min_high_severity_risks",
    "required_evidence_ids",
    "must_cite_all_evidence",
    "requires_clarification",
    "requires_missing_information",
    "requires_uncertainty",
    "forbidden_terms",
    "keywords_any",
}
CONTEXT_KEYS = {"location", "timezone", "start", "end", "date", "activity"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MIN_TOTAL = 30
MIN_PER_CATEGORY = 5


def _check_evidence_list(
    evidence: Any, case_id: str, errors: list[str]
) -> set[str]:
    ids: set[str] = set()
    if not isinstance(evidence, list):
        errors.append(f"{case_id}: input.weather_evidence must be an array")
        return ids

    for index, item in enumerate(evidence):
        where = f"{case_id}: input.weather_evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where} must be an object")
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"{where}.id is required")
        elif evidence_id in ids:
            errors.append(f"{where}.id is duplicated: {evidence_id}")
        else:
            ids.add(evidence_id)
        if not isinstance(item.get("type"), str) or not item.get("type"):
            errors.append(f"{where}.type is required")
        for field in ("valid_from", "valid_to", "source", "observed_at"):
            if field in item and not isinstance(item[field], str):
                errors.append(f"{where}.{field} must be a string")

    return ids


def _check_expect(
    expect: Any,
    case_id: str,
    supplied_ids: set[str],
    errors: list[str],
) -> None:
    if not isinstance(expect, dict) or not expect:
        errors.append(f"{case_id}: expect must be a non-empty object")
        return

    unknown = set(expect) - EXPECT_KEYS
    if unknown:
        errors.append(f"{case_id}: unsupported expect keys: {sorted(unknown)}")

    if "status" in expect and expect["status"] not in STATUSES:
        errors.append(f"{case_id}: invalid expect.status {expect['status']!r}")
    if "status_in" in expect:
        values = expect["status_in"]
        if not isinstance(values, list) or not values:
            errors.append(f"{case_id}: expect.status_in must be a non-empty array")
        elif set(values) - STATUSES:
            errors.append(f"{case_id}: invalid expect.status_in value")

    if "intent" in expect and expect["intent"] not in INTENTS:
        errors.append(f"{case_id}: invalid expect.intent {expect['intent']!r}")
    if "intent_in" in expect:
        values = expect["intent_in"]
        if not isinstance(values, list) or not values:
            errors.append(f"{case_id}: expect.intent_in must be a non-empty array")
        elif set(values) - INTENTS:
            errors.append(f"{case_id}: invalid expect.intent_in value")

    for field in (
        "min_recommendations",
        "max_recommendations",
        "min_risks",
        "min_medium_or_higher_risks",
        "min_high_severity_risks",
    ):
        if field in expect and (
            not isinstance(expect[field], int) or expect[field] < 0
        ):
            errors.append(f"{case_id}: expect.{field} must be a non-negative integer")

    if "required_evidence_ids" in expect:
        values = expect["required_evidence_ids"]
        if not isinstance(values, list) or not all(
            isinstance(value, str) for value in values
        ):
            errors.append(
                f"{case_id}: expect.required_evidence_ids must be an array of strings"
            )
        else:
            unknown_ids = set(values) - supplied_ids
            if unknown_ids:
                errors.append(
                    f"{case_id}: required evidence ids not in input: {sorted(unknown_ids)}"
                )

    for field in ("forbidden_terms", "keywords_any"):
        if field in expect and (
            not isinstance(expect[field], list)
            or not all(isinstance(value, str) and value for value in expect[field])
        ):
            errors.append(
                f"{case_id}: expect.{field} must be a non-empty array of strings"
            )

    for field in (
        "must_cite_all_evidence",
        "requires_clarification",
        "requires_missing_information",
        "requires_uncertainty",
    ):
        if field in expect and not isinstance(expect[field], bool):
            errors.append(f"{case_id}: expect.{field} must be a boolean")


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    cases = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"line {line_number}: invalid JSON ({error})") from error
        if not isinstance(case, dict):
            raise ValueError(f"line {line_number}: case must be an object")
        cases.append(case)
    return cases


def validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    category_counts: Counter[str] = Counter()

    for index, case in enumerate(cases, start=1):
        case_id = case.get("id")
        if not isinstance(case_id, str) or not ID_PATTERN.match(case_id):
            errors.append(
                f"case {index}: id must be kebab-case matching {ID_PATTERN.pattern}"
            )
            case_id = f"case-{index}"
        elif case_id in seen_ids:
            errors.append(f"{case_id}: duplicate case id")
        else:
            seen_ids.add(case_id)

        category = case.get("category")
        if category not in CATEGORIES:
            errors.append(f"{case_id}: invalid category {category!r}")
        else:
            category_counts[category] += 1

        if not isinstance(case.get("name"), str) or not case["name"]:
            errors.append(f"{case_id}: name is required")

        input_payload = case.get("input")
        if not isinstance(input_payload, dict):
            errors.append(f"{case_id}: input must be an object")
            continue

        if not isinstance(input_payload.get("user_query"), str) or not input_payload.get("user_query"):
            errors.append(f"{case_id}: input.user_query is required")

        if "intent" in input_payload and input_payload["intent"] not in INTENTS:
            errors.append(f"{case_id}: input.intent is invalid")

        context = input_payload.get("context", {})
        if not isinstance(context, dict):
            errors.append(f"{case_id}: input.context must be an object")
        else:
            unknown = set(context) - CONTEXT_KEYS
            if unknown:
                errors.append(f"{case_id}: unsupported context keys: {sorted(unknown)}")

        if "weather_evidence" not in input_payload:
            errors.append(f"{case_id}: input.weather_evidence is required (may be [])")
            supplied_ids: set[str] = set()
        else:
            supplied_ids = _check_evidence_list(
                input_payload["weather_evidence"], case_id, errors
            )

        _check_expect(case.get("expect"), case_id, supplied_ids, errors)

    if len(cases) < MIN_TOTAL:
        errors.append(f"expected at least {MIN_TOTAL} cases, found {len(cases)}")

    for category in sorted(CATEGORIES):
        if category_counts[category] < MIN_PER_CATEGORY:
            errors.append(
                f"category {category!r} has {category_counts[category]} cases, "
                f"expected at least {MIN_PER_CATEGORY}"
            )

    return errors


def main() -> int:
    try:
        cases = load_cases()
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1

    errors = validate_cases(cases)
    if errors:
        for message in errors:
            print(f"FAIL {message}")
        return 1

    counts = Counter(case["category"] for case in cases)
    print(f"PASS: {len(cases)} cases are well-formed")
    for category in sorted(counts):
        print(f"  {category}: {counts[category]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
