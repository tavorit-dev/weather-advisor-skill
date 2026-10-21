#!/usr/bin/env python3
"""Validate every example input/output pair in examples/.

Each `<name>-output.json` must pass schema validation and cite only evidence
IDs supplied by the matching `<name>.json` input.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_evidence import check_evidence  # noqa: E402
from validate_schema import load_schema, validate_response  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = ROOT / "examples"


def main() -> int:
    schema = load_schema()
    output_paths = sorted(EXAMPLES_DIR.glob("*-output.json"))

    if not output_paths:
        print("FAIL: no example outputs found")
        return 1

    failures = 0
    for output_path in output_paths:
        name = output_path.name.removesuffix("-output.json")
        input_path = output_path.with_name(f"{name}.json")

        if not input_path.exists():
            print(f"FAIL {name}: missing input file {input_path.name}")
            failures += 1
            continue

        try:
            response = json.loads(output_path.read_text(encoding="utf-8"))
            input_payload = json.loads(input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            print(f"FAIL {name}: invalid JSON ({error})")
            failures += 1
            continue

        errors = validate_response(response, schema)
        errors += check_evidence(response, input_payload)

        if errors:
            failures += 1
            print(f"FAIL {name}")
            for message in errors:
                print(f"  {message}")
        else:
            print(f"PASS {name}")

    total = len(output_paths)
    print(f"\n{total - failures}/{total} example pairs passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
