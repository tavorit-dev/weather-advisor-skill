# Claude Code Integration

This page documents the Claude Code layer described in the design: a
project-level skill, a `/weather-advisor` entry, the live-weather demo, an
optional Stop hook, and a personal install script.

The canonical skill remains [`SKILL.md`](../SKILL.md). The Claude Code entry is
a thin wrapper around it, so the workflow, evidence rules, and output contract
are defined in one place.

## Layout

```text
.claude/
├── settings.json                       # Hooks are opt-in; empty by default
├── skills/
│   └── weather-advisor/
│       └── SKILL.md                    # Claude Code entry and /weather-advisor
└── hooks/
    └── validate-weather-output.py      # Optional response validator / Stop hook
scripts/
└── install_claude_skill.py             # Personal installation
```

## Use it in this repository

Open a Claude Code session at the repository root. The project skill is
discovered automatically. If the `.claude/skills/` directory did not exist when
the session started, run `/reload-skills`; restart the session if it still does
not appear. Its name becomes the slash command:

```text
/weather-advisor Tokyo outdoor running tomorrow
/weather-advisor 上海 通勤 明天
/weather-advisor --live Osaka travel tomorrow
```

`$ARGUMENTS` is passed through as the user query. Natural-language weather
questions also trigger the skill through its `description`; that decision is
made by Claude Code, not by a hook.

`--live` is a convention interpreted by the skill, not a Claude Code flag. When
the user asks for live weather, prefer the compact brief. It returns only the
requested hours, summary statistics, and evidence IDs, so one tool call is
usually enough:

```bash
python3 demo/weather_brief.py <city> --date today|tomorrow --window HH:MM-HH:MM
```

Examples:

```bash
python3 demo/weather_brief.py Tianjin --date today --window 13:00-18:00
python3 demo/weather_brief.py Tianjin --date tomorrow
python3 demo/weather_brief.py Tokyo --offline --date 2026-10-22 --window 08:00-12:00
```

The brief is typically 5–10 KB, compared with roughly 50–100 KB for a live
full-day envelope. In a Tianjin 6-hour-window check it was 6.1 KB versus 87.9 KB
for the full live envelope (about 7%). Use `demo/weather_demo.py` only when the
complete evidence set or a schema-ready input envelope is required.

`--offline` uses the synthetic Tokyo fixture and requires an explicit date
because the fixture is fixed. If the command fails, the skill must explain the
failure rather than invent values.

### Token-efficient consultation pattern

1. Use one `weather_brief.py` call with the narrowest window the user gave.
2. Cite the IDs in the brief; do not re-print the full evidence.
3. Answer in the response sections; do not read the same reference files again
   in the same session.
4. Ask for a time window only when it materially changes the answer.

The brief is a view of the demo evidence, not a new data source and not a
recommendation engine. The full contract remains
[`references/evidence-contract.md`](../references/evidence-contract.md).

## Response modes

The canonical contract defines the fields. In a conversation, the Claude Code
entry presents them as Summary, Weather evidence, Recommendations, Risks and
uncertainty, and Missing information. When the user asks for JSON, return one
object conforming to
[`schemas/recommendation.schema.json`](../schemas/recommendation.schema.json)
and validate it:

```bash
python3 tests/validate_schema.py response.json
```

## Install for personal use

Install the skill and its supporting files into
`~/.claude/skills/weather-advisor`:

```bash
python3 scripts/install_claude_skill.py
```

The installer copies the whole repository (excluding `.git`, `.venv`, and
`.claude`), renames the canonical skill to `CANONICAL-SKILL.md`, and writes the
Claude Code entry as `SKILL.md`. The installed layout therefore still contains
`references/`, `schemas/`, `demo/`, and `tests/` next to the entry.

Options:

```bash
python3 scripts/install_claude_skill.py --dest /path/to/skills/weather-advisor
python3 scripts/install_claude_skill.py --force
```

`--force` replaces an existing destination. The installer refuses to write
inside the repository.

After installing, restart Claude Code or reload skills, then try:

```text
/weather-advisor Tokyo outdoor running tomorrow
/weather-advisor --live Osaka travel tomorrow
```

## Optional Stop hook

The hook validates a weather JSON response in the final assistant turn against
the repository schema. It is **disabled by default** because it adds work to
every session and can only validate a response when the final message contains
a fenced JSON block that looks like a skill response.

Why the default is off:

- The hook cannot invent the target file when the model answered in prose.
- Schema validation is better run explicitly and reproducibly.
- The first release should not require a hook to be useful.

### Manual use

```bash
python3 .claude/hooks/validate-weather-output.py response.json
```

Exit code `0` means valid or nothing to validate; `2` means the response failed
the schema. The hook needs `jsonschema`:

```bash
python -m pip install -r tests/requirements.txt
```

If the dependency is missing while running as a hook, it prints a warning and
exits `0` instead of blocking the session.

### Enable it

Add the following to `.claude/settings.json` (or merge it into your existing
hook configuration):

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$CLAUDE_PROJECT_DIR/.claude/hooks/validate-weather-output.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

When invoked as a Stop hook, the script reads the hook payload from stdin. It
uses `last_assistant_message` when present, otherwise it reads the final
assistant turn from `transcript_path`. It validates the last fenced JSON block
that contains `schema_version`, `status`, and `recommendations`. A
conversational answer, or a transcript that cannot be read, is a no-op.

The hook is a convenience, not a security boundary. It does not prove that a
recommendation follows from the evidence; `tests/check_evidence.py` and the
test cases cover that.

## Verify the integration

- `/weather-advisor` is recognized and receives the arguments.
- `claude plugin validate .claude/skills` reports valid frontmatter (Claude
  Code v2.1.233+).
- Live mode actually calls Open-Meteo; `--offline` does not use the network.
- With no weather evidence, the skill asks for clarification or returns
  insufficient evidence instead of inventing values.
- Requested JSON passes `tests/validate_schema.py`.
- If the hook is enabled, `/hooks` lists it and the Stop event fires.
- After a personal install, `demo/weather_demo.py` runs from the installed
  directory and `CANONICAL-SKILL.md` is present.

## Limits

- `argument-hint` is a Claude Code frontmatter extension. It appears only on
  this entry, never on the canonical root `SKILL.md`, so the canonical skill
  stays portable to claude.ai and Skills API packaging (which accept only
  `name`, `description`, `license`, `compatibility`, `metadata`, and
  `allowed-tools`).
- The demo is a replaceable adapter, not part of the skill core. See
  [`demo/README.md`](../demo/README.md) for provider limits, attribution, and
  licensing.
- The personal installer copies the repository; it does not install Python
  dependencies or configure hooks.
- The Stop hook validates the JSON shape, not the factual consistency of the
  advice.
