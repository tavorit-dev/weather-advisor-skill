#!/usr/bin/env python3
"""Grade one generated response against one case in tests/cases.jsonl.

This is the execution half of the test suite: run the skill with the case
input, save the model's JSON response, then grade it here.

Usage:
    python tests/grade_case.py <case_id> <response.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_evidence import check_evidence  # noqa: E402
from validate_cases import CASES_PATH, load_cases  # noqa: E402
from validate_schema import load_schema, validate_response  # noqa: E402

# Phrases that assert certainty the evidence cannot support. These are global:
# they apply to every case, in addition to any case-specific terms.
GLOBAL_FORBIDDEN_TERMS = [
    "绝对安全",
    "百分之百",
    "肯定不会下雨",
    "一定不会下雨",
    "保证不会",
]


def _iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _cited_ids(response: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for item in response.get("evidence", []):
        evidence_id = item.get("evidence_id")
        if isinstance(evidence_id, str):
            ids.add(evidence_id)
    for field in ("recommendations", "risks"):
        for item in response.get(field, []):
            for evidence_id in item.get("evidence_ids", []):
                if isinstance(evidence_id, str):
                    ids.add(evidence_id)
    return ids


def _check(name: str, passed: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, passed, detail)


def grade(response: dict[str, Any], case: dict[str, Any]) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []
    expect = case["expect"]

    schema_errors = validate_response(response, load_schema())
    results.append(
        _check("schema", not schema_errors, "; ".join(schema_errors))
    )

    evidence_errors = check_evidence(response, case["input"])
    results.append(
        _check("evidence linkage", not evidence_errors, "; ".join(evidence_errors))
    )

    text = "\n".join(_iter_strings(response))

    if "status" in expect:
        actual = response.get("status")
        results.append(
            _check(
                f"status == {expect['status']}",
                actual == expect["status"],
                f"actual: {actual!r}",
            )
        )
    if "status_in" in expect:
        actual = response.get("status")
        results.append(
            _check(
                f"status in {expect['status_in']}",
                actual in expect["status_in"],
                f"actual: {actual!r}",
            )
        )

    if "intent" in expect:
        actual = response.get("intent")
        results.append(
            _check(
                f"intent == {expect['intent']}",
                actual == expect["intent"],
                f"actual: {actual!r}",
            )
        )
    if "intent_in" in expect:
        actual = response.get("intent")
        results.append(
            _check(
                f"intent in {expect['intent_in']}",
                actual in expect["intent_in"],
                f"actual: {actual!r}",
            )
        )

    recommendations = response.get("recommendations", [])
    risks = response.get("risks", [])

    if "min_recommendations" in expect:
        results.append(
            _check(
                f"recommendations >= {expect['min_recommendations']}",
                len(recommendations) >= expect["min_recommendations"],
                f"actual: {len(recommendations)}",
            )
        )
    if "max_recommendations" in expect:
        results.append(
            _check(
                f"recommendations <= {expect['max_recommendations']}",
                len(recommendations) <= expect["max_recommendations"],
                f"actual: {len(recommendations)}",
            )
        )
    if "min_risks" in expect:
        results.append(
            _check(
                f"risks >= {expect['min_risks']}",
                len(risks) >= expect["min_risks"],
                f"actual: {len(risks)}",
            )
        )

    medium_or_higher = sum(
        1 for risk in risks if risk.get("severity") in {"medium", "high"}
    )
    if "min_medium_or_higher_risks" in expect:
        results.append(
            _check(
                f"medium/high risks >= {expect['min_medium_or_higher_risks']}",
                medium_or_higher >= expect["min_medium_or_higher_risks"],
                f"actual: {medium_or_higher}",
            )
        )

    high = sum(1 for risk in risks if risk.get("severity") == "high")
    if "min_high_severity_risks" in expect:
        results.append(
            _check(
                f"high risks >= {expect['min_high_severity_risks']}",
                high >= expect["min_high_severity_risks"],
                f"actual: {high}",
            )
        )

    cited = _cited_ids(response)

    if "required_evidence_ids" in expect:
        missing = [eid for eid in expect["required_evidence_ids"] if eid not in cited]
        results.append(
            _check(
                "required evidence cited",
                not missing,
                f"missing: {missing}",
            )
        )

    if expect.get("must_cite_all_evidence"):
        supplied = {
            item.get("id")
            for item in case["input"].get("weather_evidence", [])
            if isinstance(item.get("id"), str)
        }
        missing = sorted(supplied - cited)
        results.append(
            _check("all supplied evidence cited", not missing, f"missing: {missing}")
        )

    if expect.get("requires_clarification"):
        question = response.get("clarification_question")
        results.append(
            _check(
                "clarification_question is non-empty",
                isinstance(question, str) and bool(question.strip()),
                f"actual: {question!r}",
            )
        )

    if expect.get("requires_missing_information"):
        info = response.get("missing_information", [])
        results.append(
            _check(
                "missing_information is non-empty",
                isinstance(info, list) and bool(info),
                f"actual: {info!r}",
            )
        )

    if expect.get("requires_uncertainty"):
        uncertainty = response.get("uncertainty", [])
        results.append(
            _check(
                "uncertainty is non-empty",
                isinstance(uncertainty, list) and bool(uncertainty),
                f"actual: {uncertainty!r}",
            )
        )

    forbidden = list(GLOBAL_FORBIDDEN_TERMS) + list(expect.get("forbidden_terms", []))
    hits = [term for term in forbidden if term in text]
    results.append(
        _check("no forbidden phrases", not hits, f"found: {hits}")
    )

    if "keywords_any" in expect:
        matched = [term for term in expect["keywords_any"] if term in text]
        results.append(
            _check(
                f"mentions one of {expect['keywords_any']}",
                bool(matched),
                "none found",
            )
        )

    return results


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python tests/grade_case.py <case_id> <response.json>")
        return 2

    case_id = sys.argv[1]
    response_path = Path(sys.argv[2])

    try:
        cases = load_cases(CASES_PATH)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        return 1

    case = next((item for item in cases if item.get("id") == case_id), None)
    if case is None:
        print(f"FAIL: unknown case id: {case_id}")
        return 2

    try:
        response = json.loads(response_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL: cannot read response ({error})")
        return 1

    results = grade(response, case)
    failures = 0
    for name, passed, detail in results:
        if passed:
            print(f"PASS {name}")
        else:
            failures += 1
            print(f"FAIL {name}" + (f" ({detail})" if detail else ""))

    print(f"\n{len(results) - failures}/{len(results)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
