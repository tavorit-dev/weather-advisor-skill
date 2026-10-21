#!/usr/bin/env python3
"""Check that a response cites only evidence IDs present in its input.

Schema validation cannot detect a fabricated or mistyped evidence ID. This
script closes that gap.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def _input_evidence(input_payload: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = input_payload.get("weather_evidence", [])
    if not isinstance(evidence, list):
        raise ValueError("input.weather_evidence must be an array")
    return evidence


def _cited_entries(response: dict[str, Any]) -> list[tuple[str, Any]]:
    entries: list[tuple[str, Any]] = []

    for index, item in enumerate(response.get("evidence", [])):
        entries.append((f"evidence[{index}].evidence_id", item.get("evidence_id")))

    for field in ("recommendations", "risks"):
        for index, item in enumerate(response.get(field, [])):
            for ref_index, evidence_id in enumerate(item.get("evidence_ids", [])):
                entries.append(
                    (
                        f"{field}[{index}].evidence_ids[{ref_index}]",
                        evidence_id,
                    )
                )

    return entries


def check_evidence(
    response: dict[str, Any], input_payload: dict[str, Any]
) -> list[str]:
    """Return a list of evidence-linkage errors. Empty means consistent."""
    errors: list[str] = []

    supplied = _input_evidence(input_payload)
    supplied_ids: list[str] = []
    for index, item in enumerate(supplied):
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"FAIL input.weather_evidence[{index}].id is missing")
            continue
        if evidence_id in supplied_ids:
            errors.append(f"FAIL input.weather_evidence[{index}].id is duplicated: {evidence_id}")
        supplied_ids.append(evidence_id)

    supplied_set = set(supplied_ids)
    for location, evidence_id in _cited_entries(response):
        if not isinstance(evidence_id, str) or not evidence_id:
            errors.append(f"FAIL {location} is empty")
            continue
        if evidence_id not in supplied_set:
            errors.append(f"FAIL {location} references unknown evidence id: {evidence_id}")

    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python tests/check_evidence.py <response.json> <input.json>"
        )
        return 2

    response = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    input_payload = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    errors = check_evidence(response, input_payload)
    if errors:
        for message in errors:
            print(message)
        return 1

    print("PASS: every cited evidence id exists in the input")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
