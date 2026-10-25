#!/usr/bin/env python3
"""Install the Weather Advisor Claude Code skills for the current user.

The installed layout keeps the canonical repository skill as
``CANONICAL-SKILL.md`` and writes the Claude Code entry as ``SKILL.md``, so the
skill can find the demo, schema, and validators next to it.

Two commands are installed:

* ``weather-advisor`` -- the consultation entry.
* ``weather-advisor-card`` -- renders a response as an HTML card.

The card entry is installed as ``SKILL.md`` inside ``card/``. Claude Code
derives a skill's name from its frontmatter, not its directory, so the command
name is unaffected by the nesting, and ``card/`` does not shadow the main
entry's ``SKILL.md``.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
ENTRY = SKILLS / "weather-advisor" / "SKILL.md"
CARD_ENTRY = SKILLS / "weather-advisor-card" / "SKILL.md"
CANONICAL_LINK = "../../../SKILL.md"
CARD_DIR = "card"
# Repository paths a Claude Code entry may reference. An entry installed below
# the skill root needs these prefixed so they still resolve.
REPO_DIRS = ("demo", "tests", "schemas", "references", "examples", "docs", "scripts")
REPO_PATH_RE = re.compile(
    r"`((?:\.\./)*(?:" + "|".join(REPO_DIRS) + r")/[\w./-]+)`"
)
IGNORE = shutil.ignore_patterns(
    ".git",
    ".venv",
    ".claude",
    "__pycache__",
    "*.pyc",
    ".DS_Store",
)


def write_entry(entry: Path, dest: Path, parents: int) -> int:
    """Copy a Claude Code entry, repointing its links at the installed layout.

    Two kinds of path change once installed:

    * the link to the canonical skill, which moves to the install root;
    * repository paths such as ``demo/weather_card.py``, which are relative to
      the skill root and so need a ``../`` prefix for any entry installed
      below it.

    ``parents`` is the entry's depth below the install root: the main entry
    lands at the root (``0``), the card entry one directory down (``1``).
    """
    text = entry.read_text(encoding="utf-8")
    if CANONICAL_LINK not in text:
        print(
            f"Claude Code entry does not reference {CANONICAL_LINK}: {entry}",
            file=sys.stderr,
        )
        return 1

    text = text.replace(CANONICAL_LINK, "../" * parents + "CANONICAL-SKILL.md")
    if parents:
        prefix = "../" * parents
        text = REPO_PATH_RE.sub(lambda m: f"`{prefix}{m.group(1)}`", text)

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return 0


def install(dest: Path, force: bool) -> int:
    for entry in (ENTRY, CARD_ENTRY):
        if not entry.is_file():
            print(f"Missing Claude Code entry: {entry}", file=sys.stderr)
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

    if write_entry(ENTRY, dest / "SKILL.md", 0) != 0:
        return 1
    if write_entry(CARD_ENTRY, dest / CARD_DIR / "SKILL.md", 1) != 0:
        return 1

    required = [
        dest / "SKILL.md",
        dest / "CANONICAL-SKILL.md",
        dest / CARD_DIR / "SKILL.md",
        dest / "references" / "intent-catalog.md",
        dest / "schemas" / "recommendation.schema.json",
        dest / "demo" / "weather_demo.py",
        dest / "demo" / "weather_card.py",
        dest / "demo" / "card.css",
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
    print("  /weather-advisor-card /tmp/response.json --brief /tmp/brief.json --open")
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
