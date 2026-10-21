<p align="center">
  <img src="images/banner.png" alt="天气智言 — 基于证据的天气建议" width="100%">
</p>

<h1 align="center">
  weather-advisor-skill
</h1>

<p align="center"><a href="README.md">English</a> | 简体中文</p>

让兼容 Skill 的 Agent 在天气建议上做到：**先看证据，再给建议，输出可校验**。

这是一个纯文档 + JSON Schema + 测试用例的 Skill 仓库，不是天气 API。它不抓取
天气数据，也不内置 Agent Runtime；它约束 Agent 如何使用宿主提供的天气事实，
以及如何返回结构化、可被程序检查的建议。

## 为什么需要它

语言模型在天气场景里常见的失败模式：

- 编造温度、降雨量、预警、地点或数据来源；
- 把「降雨概率 70%」说成「肯定下雨」；
- 缺少地点时默认使用系统所在地；
- 把「没有收到预警」当成「没有风险」；
- 推荐内容与证据无关，且无法追溯；
- 每次输出格式不同，无法自动校验。

本项目用一份入口 Skill、四份参考规范、一份 JSON Schema、六组示例和 32 条
测试用例，把这些行为固定下来。交付标准不是「模型能说出天气建议」，而是：
不同 Agent 在相同输入下遵循一致的分析流程，缺少必要事实时不编造，输出可以
被程序检查。

## 快速开始

### 1. 作为 Skill 加载

把仓库根目录作为 Skill 目录提供给宿主，入口文件是 `SKILL.md`。

```bash
cp -r weather-advisor-skill ~/.claude/skills/weather-advisor
```

`SKILL.md` 的 `name` 是 `weather-advisor`。如果宿主要求目录名与 `name`
一致，请把目录重命名为 `weather-advisor`。

### 2. 提供天气证据

Skill 不会自己获取天气。宿主需要把查询、上下文和证据一起提供给 Agent：

```json
{
  "user_query": "明早上班要带伞吗？",
  "intent": "commute_advice",
  "context": {
    "location": "上海",
    "timezone": "Asia/Shanghai",
    "start": "2026-10-22T07:00:00+08:00",
    "end": "2026-10-22T09:00:00+08:00"
  },
  "weather_evidence": [
    {
      "id": "ev-rain-001",
      "type": "precipitation_probability",
      "value": 70,
      "unit": "%",
      "valid_from": "2026-10-22T07:00:00+08:00",
      "valid_to": "2026-10-22T09:00:00+08:00",
      "source": "example-provider",
      "observed_at": "2026-10-21T20:00:00+08:00"
    }
  ]
}
```

`context` 可以为空，`weather_evidence` 可以为空数组；这两种情况会触发追问或
证据不足，而不是让模型自行补全。

### 3. 获取结构化输出

Agent 返回一个符合
[`schemas/recommendation.schema.json`](schemas/recommendation.schema.json)
的 JSON 对象。每条建议和风险都必须引用其依据的 `evidence_id`。

```json
{
  "schema_version": "1.0",
  "status": "answered",
  "intent": "commute_advice",
  "summary": "明天早高峰上海存在较明显的降雨可能，建议带伞出门。",
  "evidence": [
    { "evidence_id": "ev-rain-001", "claim": "07:00–09:00 的降雨概率为 70%。" }
  ],
  "recommendations": [
    {
      "action": "通勤时携带雨伞或雨衣。",
      "reason": "通勤时段降雨概率为 70%。",
      "evidence_ids": ["ev-rain-001"]
    }
  ],
  "risks": [
    {
      "description": "降雨可能导致路面湿滑。",
      "severity": "medium",
      "evidence_ids": ["ev-rain-001"]
    }
  ],
  "missing_information": [],
  "clarification_question": null,
  "uncertainty": ["70% 是降雨概率，不代表一定下雨。"]
}
```

## Claude Code

仓库在 `.claude/skills/weather-advisor/SKILL.md` 提供 Claude Code 项目级
Skill。在仓库根目录打开会话后可直接使用斜杠命令：

```text
/weather-advisor Tokyo outdoor running tomorrow
/weather-advisor --live Osaka travel tomorrow
```

自然语言天气问题也会触发该 Skill。安装到个人目录：

```bash
python3 scripts/install_claude_skill.py
```

可选的 Stop Hook 可在用户要求 JSON 时按 Schema 校验响应，默认不启用。实时
模式、安装方式、Hook 配置与验收步骤见
[`docs/claude-code.md`](docs/claude-code.md)。

## 包含什么

- 标准 `SKILL.md` 及元数据；
- 6 类天气相关意图与追问规则；
- 天气证据约束与建议推导规则；
- 严重天气与不确定性处理；
- 统一输出契约（JSON Schema，Draft 2020-12）；
- 6 组示例、32 条测试用例和本地校验工具；
- 免 Key 的 Open-Meteo 演示适配器（`demo/`），独立于 Skill 核心。

首版**不**包含：Skill 核心内置的天气数据获取、独立 Agent Runtime、账号或支付、
Web 服务或数据库、针对特定模型的 Prompt 调优。完整范围与设计见
[`docs/architecture.md`](docs/architecture.md)。

## 文档

| 文档 | 内容 |
| --- | --- |
| [`SKILL.md`](SKILL.md) | Agent 读取的入口、工作流与强约束 |
| [`docs/getting-started.md`](docs/getting-started.md) | 宿主接入、完整输入输出、演示与校验 |
| [`docs/claude-code.md`](docs/claude-code.md) | Claude Code 入口、`/weather-advisor`、安装脚本与可选 Hook |
| [`docs/architecture.md`](docs/architecture.md) | 范围、工作流、状态模型、意图、设计决策 |
| [`docs/examples-and-tests.md`](docs/examples-and-tests.md) | 示例、测试覆盖与三层测试 |
| [`docs/repository-layout.md`](docs/repository-layout.md) | 带注释的仓库结构 |
| [`references/`](references/) | 意图目录、证据契约、建议规则、安全与不确定性 |
| [`demo/README.md`](demo/README.md) | 演示的字段映射、署名、许可与数据源替换 |
| [`tests/README.md`](tests/README.md) | 测试分层、用例格式与评分 |
| [`CLAUDE.md`](CLAUDE.md) | 贡献者的项目约束与约定 |
| [`CHANGELOG.md`](CHANGELOG.md) | 版本变更记录 |

## 演示

`demo/weather_demo.py` 用 Open-Meteo 的免费公共 API，把城市名转换为可直接
交给 Agent 的输入信封。它只依赖 Python 标准库，不需要 API Key。

```bash
python demo/weather_demo.py Tokyo
python demo/weather_demo.py "New York" --days 2
python demo/weather_demo.py Tokyo --offline

# 面向 Agent 咨询的紧凑窗口化证据
python demo/weather_brief.py Tokyo --date today --window 10:00-16:00 --compact
```

天气数据由 [Open-Meteo.com](https://open-meteo.com/) 提供，许可为 CC BY 4.0。
免费端点面向非商业使用，不提供生产级 SLA；展示数据时请保留署名。限制说明与
数据源替换见 [`demo/README.md`](demo/README.md)。

## 本地校验

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py
python tests/run_examples.py
python tests/validate_cases.py
```

三条命令都必须返回 0。单文件校验与逐用例评分见
[`docs/getting-started.md`](docs/getting-started.md)。

## 版本与许可证

当前版本 `0.1.0`，输出 `schema_version` 为 `1.0`。

[Apache License 2.0](LICENSE)。
