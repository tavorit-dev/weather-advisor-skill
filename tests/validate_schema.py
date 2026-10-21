#!/usr/bin/env python3
"""Validate a Weather Advisor response against the JSON Schema contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ModuleNotFoundError:  # pragma: no cover - depends on the environment
    print(
        "Missing dependency: run `python -m pip install -r tests/requirements.txt`",
        file=sys.stderr,
    )
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "recommendation.schema.json"


def load_schema(path: Path = SCHEMA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_response(
    response: Any, schema: dict[str, Any] | None = None
) -> list[str]:
    """Return a list of human-readable schema errors. Empty means valid."""
    validator = Draft202012Validator(schema or load_schema())
    errors = sorted(
        validator.iter_errors(response),
        key=lambda error: list(error.path),
    )
    messages = []
    for error in errors:
        path = ".".join(map(str, error.path)) or "$"
        messages.append(f"FAIL {path}: {error.message}")
    return messages


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tests/validate_schema.py <response.json>")
        return 2

    response_path = Path(sys.argv[1])
    response = json.loads(response_path.read_text(encoding="utf-8"))
    errors = validate_response(response)

    if errors:
        for message in errors:
            print(message)
        return 1

    print("PASS: response matches recommendation schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
