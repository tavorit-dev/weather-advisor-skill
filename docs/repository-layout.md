# Repository Layout

```text
weather-advisor-skill/
├── SKILL.md                       # Skill entry: workflow and hard constraints
├── README.md                      # Chinese README (default)
├── README.en.md                   # English README
├── CLAUDE.md                      # Conventions and invariants for contributors
├── CHANGELOG.md
├── LICENSE
├── docs/
│   ├── getting-started.md         # Host integration, examples, demo, validation
│   ├── claude-code.md             # Claude Code entries, install script, optional hook
│   ├── architecture.md            # Scope, workflow, status model, intents, principles
│   ├── examples-and-tests.md      # Example pairs and test coverage
│   └── repository-layout.md       # This file
├── scripts/
│   └── install_claude_skill.py    # Install the skill under ~/.claude/skills
├── .claude/
│   ├── settings.json              # Hooks are opt-in; empty by default
│   ├── skills/
│   │   ├── weather-advisor/
│   │   │   └── SKILL.md           # Claude Code entry and /weather-advisor
│   │   └── weather-advisor-card/
│   │       └── SKILL.md           # /weather-advisor-card
│   └── hooks/
│       └── validate-weather-output.py  # Optional Stop hook / manual validator
├── references/
│   ├── intent-catalog.md          # Six intents, required context, clarification rules
│   ├── evidence-contract.md       # Input shape, validity, missing/conflicting evidence
│   ├── recommendation-rules.md    # From weather facts to actions
│   └── safety-and-uncertainty.md  # Severe weather, uncertainty, wording limits
├── schemas/
│   └── recommendation.schema.json # Output contract (Draft 2020-12)
├── examples/                      # Six input/output pairs
│   ├── commute-rain.json
│   ├── commute-rain-output.json
│   ├── clothing-cold.json
│   ├── clothing-cold-output.json
│   ├── outdoor-wind.json
│   ├── outdoor-wind-output.json
│   ├── travel-planning.json
│   ├── travel-planning-output.json
│   ├── missing-location.json
│   ├── missing-location-output.json
│   ├── no-weather-evidence.json
│   └── no-weather-evidence-output.json
├── demo/                          # Key-free demo: Open-Meteo -> evidence
│   ├── weather_demo.py            # Weather + air quality -> evidence envelope
│   ├── weather_brief.py           # Compact windowed evidence view for agents
│   ├── weather_card.py            # Response (+ brief) -> self-contained HTML card
│   ├── card.css                   # Card styles incl. print rules, inlined
│   ├── fixtures/                  # Synthetic Tokyo data for offline mode
│   │   ├── geocoding-tokyo.json
│   │   ├── forecast-tokyo.json
│   │   └── air-quality-tokyo.json
│   └── README.md
└── tests/
    ├── cases.jsonl                # 32 acceptance cases
    ├── validate_schema.py         # Schema validation
    ├── check_evidence.py          # Evidence reference validation
    ├── run_examples.py            # Batch example validation
    ├── validate_cases.py          # Case file linting
    ├── grade_case.py              # Grade one response against one case
    ├── test_demo.py               # L1 data-layer tests (offline)
    ├── test_weather_brief.py      # Compact brief tests (offline)
    ├── test_weather_card.py       # HTML card renderer tests (offline)
    ├── test_claude_integration.py # Claude Code entries, installer, and hook tests
    ├── requirements.txt
    └── README.md
```

Which file owns which rule is defined in [`CLAUDE.md`](../CLAUDE.md); do not
duplicate a rule across files.
