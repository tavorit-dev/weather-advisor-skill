可以。建议把 `weather-advisor-skill` 做成 Claude Code 可直接调用的 Skill，并额外提供常用斜杠命令和自动触发配置。

这里需要区分三个概念：

- Skill：定义天气分析能力，Claude Code 可以根据用户意图自动调用，也可以显式调用。
- 斜杠命令：例如 `/weather-advisor`，让开发者主动触发。
- Hook：在 Claude Code 的特定生命周期事件发生时自动执行命令，适合做输入检查、结果校验等，不适合直接充当完整的天气对话入口。

因此，推荐的交付方式是：以原生 Skill 为核心，提供 `/weather-advisor` 显式入口，用 Hook 做辅助验证，而不是把天气查询逻辑全部写进 Hook。

## 一、推荐的仓库结构

在现有开源仓库中增加 Claude Code 支持，不需要另外开发插件服务。

```
weather-advisor-skill/
├── SKILL.md
├── README.md
├── references/
├── schemas/
├── examples/
├── tests/
└── .claude/
    ├── settings.json
    ├── skills/
    │   └── weather-advisor/
    │       └── SKILL.md
    └── hooks/
        └── validate-weather-output.py
```

不过，为了避免维护两份 Skill，我更推荐只保留一个真正的 Skill 目录：如果仓库本身就是专门给 Claude Code 使用，可以直接将 `SKILL.md` 放在 `.claude/skills/weather-advisor/SKILL.md`，再由 README 指向它。如果希望同时支持其他 Agent，则保留根目录通用 Skill，并在 Claude Code 目录中提供轻量入口或安装脚本。

Claude Code 支持通过 `.claude/skills/<skill-name>/SKILL.md` 定义项目级 Skill；Skill 名称会形成对应的斜杠命令。

[image](https://www.google.com/s2/favicons?domain=https://support.claude.com\&sz=32)

Claude Help Center

+1



## 二、支持哪些调用方式？

1\. 显式斜杠命令

适合快速验证，开发者明确告诉 Claude Code 使用天气 Skill。

```
/weather-advisor 明天东京适合户外跑步吗？
```

可支持 `$ARGUMENTS`，把命令后面的用户问题传给 Skill。

2\. 自然语言自动触发

适合日常使用。通过 Skill 的 `description` 告诉 Claude Code 在哪些天气场景下应考虑调用。

```
明天去大阪旅游，应该带什么衣服？
```

这种触发由 Claude Code 根据 Skill 描述和当前请求决定，并不是确定性 Hook。

3\. Hook 自动校验

适合测试和质量控制，例如在模型结束响应前检查指定的 JSON 输出是否符合 Schema。

不建议将每条用户消息都交给 Hook 查询天气，因为 Hook 是生命周期事件机制，不是一个面向用户的对话工具。

## 三、实现 `/weather-advisor` 命令

建议将 Claude Code 版本直接放在：

```
.claude/skills/weather-advisor/SKILL.md
```

可以使用下面这份实现，支持显式调用、自然语言触发，以及实时天气验证。

```

---
name: weather-advisor
description: >
  Analyze weather conditions and provide evidence-based advice for
  commuting, clothing, outdoor activities, and travel. Use when a user
  asks about weather-related decisions, forecasts, or activity planning.
argument-hint: "[城市] [出行场景] [日期]"
---

# Weather Advisor

## Invocation

The user may invoke this skill directly with a city, activity, and date.

Examples:
- `/weather-advisor Tokyo outdoor running tomorrow`
- `/weather-advisor 上海 通勤 明天`
- `/weather-advisor --live Osaka travel tomorrow`

## Workflow

1. Identify the intent, location, target date, and activity.
2. If required context is missing, ask a concise clarification.
3. When the user requests live weather, run:
   `python3 demo/weather_demo.py <city>`
   from the repository root.
4. Use only the returned weather evidence. Do not invent missing values.
5. Select evidence relevant to the requested time range.
6. Explain the recommendation and reference the evidence supporting it.
7. If live weather retrieval fails, explain the failure. Do not substitute
   fabricated weather values.
8. Validate structured outputs against `schemas/recommendation.schema.json`
   when JSON output is requested.

## Response Format

Provide:
- Summary
- Weather evidence
- Practical recommendations
- Risks and uncertainty
- Missing information, if any

## Constraints

- Do not claim live data was retrieved unless the request succeeded.
- Distinguish weather forecasts from actual observations.
- Do not infer that weather is safe simply because alert data is absent.
- Do not claim a specific official warning exists without supporting data.
- Do not require a particular LLM provider or API key.

```

这里的 `--live` 是约定给 Skill 识别的参数，不是 Claude Code 内置参数。对应脚本调用由 Claude Code 根据 Skill 指令执行。

官方文档也支持通过 `argument-hint` 提示命令参数，并允许 Skill 自动或显式调用。

[image](https://www.google.com/s2/favicons?domain=https://code.claude.com\&sz=32)

Claude Code Docs



## 四、Hook 应该怎样配置？

建议首版只提供一个可选 Hook：在 Claude Code 完成回答时，检查用户要求的天气 JSON 是否符合 Schema。

`.claude/settings.json` 示例：

```

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

这只是 Hook 的配置骨架。真正启用前，需要让 `validate-weather-output.py` 从输入 JSON 中识别本次会话状态，并明确要校验的目标文件或输出内容；不能假设 Hook 会自动拿到完整的最终回答。

对于首版，我更推荐直接运行：

```
python3 tests/validate_schema.py examples/commute-rain-output.json
```

这种显式验证更容易复现，也不会让所有普通对话都增加额外检查。Claude Code 的 Hook 适合在生命周期节点执行确定性检查，而不是替代 Skill 的业务流程。

[image](https://www.google.com/s2/favicons?domain=https://code.claude.com\&sz=32)

Claude Code Docs

+1



## 五、提供一键安装方式

如果希望其他开发者不需要手动复制文件，建议提供安装脚本，将 Skill 安装到个人目录：

```
~/.claude/skills/weather-advisor/SKILL.md
```

如果要同时提供实时天气脚本和 Schema，则应安装整个 Skill 目录，或让 Skill 调用仓库内的相对路径。不要只复制 `SKILL.md`，否则演示脚本可能无法找到。

安装后，在 Claude Code 中执行：

```
/weather-advisor Tokyo outdoor running tomorrow
```

再执行：

```
/weather-advisor --live Osaka travel tomorrow
```

最后可以通过以下方式确认：

- `/weather-advisor` 能否被识别。
- 实时模式是否真正调用天气服务。
- 没有天气证据时，是否拒绝编造。
- JSON 输出是否通过 Schema 校验。
- `/hooks` 中是否正确显示已配置的 Hook。

官方文档：[Claude Code Skills](https://code.claude.com/docs/en/skills?utm_source=chatgpt.com) · [Claude Code Hooks](https://code.claude.com/docs/en/hooks-guide?utm_source=chatgpt.com)。

最终建议：首版先交付原生 Skill + `/weather-advisor` + 实时天气脚本 + Schema 校验。 这套组合已经足以让开发者快速体验；Hook 作为可选增强，不应成为使用 Skill 的前置条件。
