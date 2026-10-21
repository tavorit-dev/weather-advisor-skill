#!/usr/bin/env python3
"""Install the Weather Advisor Claude Code skill for the current user.

The installed layout keeps the canonical repository skill as
``CANONICAL-SKILL.md`` and writes the Claude Code entry as ``SKILL.md``, so the
skill can find the demo, schema, and validators next to it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / ".claude" / "skills" / "weather-advisor" / "SKILL.md"
CANONICAL_LINK = "../../../SKILL.md"
IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    ".claude",
    "__pycache__",
    "*.pyc",
    ".DS_Store",
)


def install(dest: Path, force: bool) -> int:
    if not ENTRY.is_file():
        print(f"Missing Claude Code entry: {ENTRY}", file=sys.stderr)
        return 1

    dest = dest.expanduser().resolve()
    if dest == ROOT or ROOT in dest.parents:
        print(
            f"Refusing to install inside the repository: {dest}",
            file=sys.stderr,
        )
        return 1

    if dest.exists():
        if not force:
            print(
                f"Destination already exists: {dest}\n"
                "Use --force to replace it.",
                file=sys.stderr,
            )
            return 1
        shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT, dest, ignore=IGNORE)

    canonical = dest / "SKILL.md"
    if not canonical.is_file():
        print(f"Copied repository is missing SKILL.md: {dest}", file=sys.stderr)
        return 1
    canonical.rename(dest / "CANONICAL-SKILL.md")

    entry = ENTRY.read_text(encoding="utf-8")
    if CANONICAL_LINK not in entry:
        print(
            f"Claude Code entry does not reference {CANONICAL_LINK}: {ENTRY}",
            file=sys.stderr,
        )
        return 1
    (dest / "SKILL.md").write_text(
        entry.replace(CANONICAL_LINK, "CANONICAL-SKILL.md"),
        encoding="utf-8",
    )

    required = [
        dest / "SKILL.md",
        dest / "CANONICAL-SKILL.md",
        dest / "references" / "intent-catalog.md",
        dest / "schemas" / "recommendation.schema.json",
        dest / "demo" / "weather_demo.py",
        dest / "tests" / "validate_schema.py",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        print("Installation is incomplete; missing:", file=sys.stderr)
        for path in missing:
            print(f"  {path}", file=sys.stderr)
        return 1

    print(f"Installed weather-advisor to {dest}")
    print()
    print("Try it in Claude Code:")
    print("  /weather-advisor Tokyo outdoor running tomorrow")
    print("  /weather-advisor --live Osaka travel tomorrow")
    print()
    print("Offline demo check:")
    print(f"  python3 {dest / 'demo' / 'weather_demo.py'} Tokyo --offline")
    print()
    print("Schema validation requires jsonschema:")
    print(f"  python3 -m pip install -r {dest / 'tests' / 'requirements.txt'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the Weather Advisor Claude Code skill."
    )
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path.home() / ".claude" / "skills" / "weather-advisor",
        help="target skill directory (default: ~/.claude/skills/weather-advisor)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace the destination if it already exists",
    )
    args = parser.parse_args()
    return install(args.dest, args.force)


if __name__ == "__main__":
    raise SystemExit(main())
