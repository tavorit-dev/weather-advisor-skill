# weather-advisor-skill

简体中文 | [English](README.en.md)

让兼容 Skill 的 Agent 在天气建议上做到：**先看证据，再给建议，输出可校验**。

这是一个纯文档 + JSON Schema + 测试用例的 Skill 仓库，不是天气 API。它不抓取
天气数据，也不内置 Agent Runtime；它约束 Agent 如何使用宿主提供的天气事实，
以及如何返回结构化、可被程序检查的建议。

## 它解决什么问题

语言模型在天气场景里常见的失败模式：

- 编造温度、降雨量、预警、地点或数据来源；
- 把「降雨概率 70%」说成「肯定下雨」；
- 缺少地点时默认使用系统所在地或随意选一个城市；
- 把「没有收到预警」当成「没有风险」；
- 推荐内容与天气证据无关，或者过度确定、无法追溯；
- 每次输出格式不同，无法自动校验。

本项目用一份入口 Skill、四份参考规范、一份 JSON Schema 和 32 条测试用例，
把这些行为固定下来。首版的交付标准不是「模型能说出天气建议」，而是：不同
Agent 在相同输入下遵循一致的分析流程，缺少必要事实时不编造，输出可以被程序
检查。

## 能力范围

首版实现：

- 标准 `SKILL.md` 及元数据；
- 6 类天气相关意图；
- 信息补全与追问规则；
- 天气证据约束与建议推导规则；
- 严重天气与不确定性处理；
- 统一输出结构（JSON Schema）；
- 6 组示例、32 条测试用例和本地校验工具；
- 免 Key 的 Open-Meteo 演示适配器（`demo/`，独立于 Skill 核心）。

首版不实现：

- Skill 核心内置的天气数据源调用；`demo/` 只是可替换的本地演示适配器；
- 独立 Agent Runtime；
- 用户账号、积分、支付；
- Web 服务、数据库和管理后台；
- 针对特定模型的专有 Prompt 优化。

## 仓库结构

```text
weather-advisor-skill/
├── SKILL.md                       # Skill 入口：工作流与强约束
├── README.md                      # 中文 README
├── README.en.md                   # English README
├── CLAUDE.md                      # 在仓库内工作的约定
├── LICENSE
├── CHANGELOG.md
├── references/
│   ├── intent-catalog.md          # 6 类意图、必要信息、追问规则
│   ├── evidence-contract.md       # 输入结构、有效期、缺失与冲突处理
│   ├── recommendation-rules.md    # 从天气事实到行动建议
│   └── safety-and-uncertainty.md  # 严重天气、不确定性、措辞边界
├── schemas/
│   └── recommendation.schema.json # 输出契约（Draft 2020-12）
├── examples/                      # 6 组输入与期望输出
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
├── demo/                          # 免 Key 演示：Open-Meteo → Evidence
│   ├── weather_demo.py
│   ├── fixtures/
│   │   ├── geocoding-tokyo.json
│   │   └── forecast-tokyo.json
│   └── README.md
└── tests/
    ├── cases.jsonl                # 32 条验收用例
    ├── validate_schema.py         # Schema 校验
    ├── check_evidence.py          # 证据引用校验
    ├── run_examples.py            # 示例批量校验
    ├── validate_cases.py          # 用例文件检查
    ├── grade_case.py              # 单条用例评分
    ├── test_demo.py               # L1 数据层测试（离线）
    ├── requirements.txt
    └── README.md
```

## 快速开始

### 1. 作为 Skill 加载

把仓库根目录作为 Skill 目录提供给宿主，入口文件是 `SKILL.md`。不同宿主的
加载方式不同，按宿主文档操作即可。

Claude Code 的个人 Skill 目录示例：

```bash
cp -r weather-advisor-skill ~/.claude/skills/weather-advisor
```

`SKILL.md` 的 `name` 是 `weather-advisor`。如果宿主要求目录名与 `name`
一致，请把目录重命名为 `weather-advisor`。

### 2. 提供天气证据

Skill 不会自己获取天气。宿主需要把查询、上下文和证据一起提供给 Agent。
最小输入如下（完整字段见 [`references/evidence-contract.md`](references/evidence-contract.md)）：

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

Agent 返回一个符合 [`schemas/recommendation.schema.json`](schemas/recommendation.schema.json)
的 JSON 对象：

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

完整示例见 [`examples/commute-rain-output.json`](examples/commute-rain-output.json)。

## 工作流程

1. 识别意图（`references/intent-catalog.md`）。
2. 提取地点、目标时间和活动上下文。
3. 判断缺失信息是否会实质影响结论。
4. 若会，提出一个简洁的追问并返回 `needs_clarification`。
5. 检查天气证据的有效期、时效、来源和对目标时段的覆盖。
6. 按 `references/recommendation-rules.md` 生成建议。
7. 按 `references/safety-and-uncertainty.md` 检查风险与不确定性。
8. 返回 `schemas/recommendation.schema.json` 定义的结构。

## 六类意图

| 意图 ID | 用户问题示例 | 处理重点 |
| --- | --- | --- |
| `weather_lookup` | 明天上海会下雨吗？ | 回答事实，不强行扩展建议 |
| `clothing_advice` | 明天穿什么合适？ | 温度、体感、降雨、活动 |
| `commute_advice` | 明早上班要带伞吗？ | 通勤时段降雨、风力、能见度、预警 |
| `outdoor_activity` | 下午适合户外跑步吗？ | 降雨、风与阵风、温度、紫外线、预警 |
| `travel_planning` | 周末去杭州需要准备什么？ | 多日天气、行程安排、预测时效 |
| `general_weather_advice` | 这种天气需要注意什么？ | 结合上下文识别目的，必要时追问 |

意图细节、必要信息和失败案例见 [`references/intent-catalog.md`](references/intent-catalog.md)。

## 输出契约

### 状态

| `status` | 含义 |
| --- | --- |
| `answered` | 证据覆盖所问地点与时间，且至少能给出 1 条有依据的建议 |
| `needs_clarification` | 缺少地点、时间或活动等关键上下文，且用户可以提供 |
| `insufficient_evidence` | 上下文完整，但所需天气证据缺失、过旧或超出有效期 |

追问优先于证据不足：能从用户处获得的必要事实，应先问，而不是猜。

### 关键设计

**引用证据，而不是重复天气数据。** 模型在 `evidence_ids` 中引用宿主提供的
ID，宿主再与原始证据比对，从而发现不存在的引用。

**Schema 校验不等于事实校验。** JSON Schema 能检查字段、类型、必填项和枚举
值，却不能单独判断「建议带伞」是否真的有天气依据。证据引用有效性和规则
一致性由 `tests/check_evidence.py` 与测试用例补充。

**不使用主观置信分数。** 首版不返回 `confidence: 0.95` 这类数字。没有校准
方法时，它只会制造虚假的精确感；优先使用可解释的不确定性描述。

## 示例

| 示例 | 状态 | 演示重点 |
| --- | --- | --- |
| [`commute-rain`](examples/commute-rain-output.json) | `answered` | 有降雨证据的通勤建议，不把概率说成确定 |
| [`clothing-cold`](examples/clothing-cold-output.json) | `answered` | 低温、体感温度与风力下的分层穿衣 |
| [`outdoor-wind`](examples/outdoor-wind-output.json) | `answered` | 大风与阵风对海边骑行的影响 |
| [`travel-planning`](examples/travel-planning-output.json) | `answered` | 多日行程、按日建议、未覆盖日期披露 |
| [`missing-location`](examples/missing-location-output.json) | `needs_clarification` | 缺地点时追问，不默认系统位置 |
| [`no-weather-evidence`](examples/no-weather-evidence-output.json) | `insufficient_evidence` | 无证据时不断言适合与否 |

所有示例天气数据均为构造数据，来源标记为 `example-provider`，不代表任何
真实预报。

## 演示：免 Key 获取真实天气证据

`demo/weather_demo.py` 用 Open-Meteo 的免费公共 API，把城市名转换为可直接
交给 Agent 的输入信封。它只依赖 Python 标准库，不需要注册或 API Key。

```bash
python demo/weather_demo.py Tokyo
python demo/weather_demo.py "New York" --days 2
python demo/weather_demo.py Tokyo --offline
python demo/weather_demo.py Tokyo \
  --query "明天东京适合户外跑步吗？" \
  --intent outdoor_activity \
  --output /tmp/tokyo-input.json
```

输出包含 `user_query`、`intent`、`context`（地点与时间窗）、`weather_evidence`、
`attribution` 和 `metadata`。把 JSON 交给加载了 `SKILL.md` 的 Agent，再用
`tests/check_evidence.py` 校验证据引用即可。

`--offline` 使用 `demo/fixtures/` 的固定东京数据，不联网，适合测试；`live`
模式请求 Open-Meteo，`--days` 支持 1–7 天。完整说明见
[`demo/README.md`](demo/README.md)。

这条链路是手动的：demo 只负责获取证据，Skill 核心不依赖联网工具；Agent 是否
能自动调用外部工具由宿主决定。

### 数据来源与授权

- 天气数据由 [Open-Meteo](https://open-meteo.com/) 提供，许可为
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)；展示数据时必须
  保留 `Weather data by Open-Meteo.com` 署名。
- 免费公共 API 面向非商业使用；官方文档当前标注免费层约每日 10,000 次请求。
  带订阅、广告等的商业产品通常属于商业使用，应选择符合用途的授权方案或自托管。
- 免费端点不保证永久免费、无限调用或生产级 SLA；条款和限额可能变化，请以
  Open-Meteo 官网为准。
- 需要换数据源时，按
  [`references/evidence-contract.md`](references/evidence-contract.md) 实现同一套
  证据结构即可，Skill 核心和 Schema 不需要修改。

## 本地校验

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py          # L1：离线数据层，无需第三方依赖
python tests/run_examples.py       # 6 组示例的 Schema 与证据引用
python tests/validate_cases.py     # 32 条用例文件
python tests/validate_schema.py examples/commute-rain-output.json
python tests/check_evidence.py examples/commute-rain-output.json examples/commute-rain.json
```

评测模型输出时：

```bash
python tests/grade_case.py normal-001 /tmp/responses/normal-001.json
```

评分器会执行 Schema 校验、证据引用校验，并按用例的 `expect` 字段检查状态、
意图、建议数量、风险等级和禁止性表述。字段说明见
[`tests/README.md`](tests/README.md)。

## 测试覆盖

| 类别 | 数量 | 验证点 |
| --- | --- | --- |
| 正常场景 | 10 | 意图识别、建议可执行、引用正确 |
| 信息缺失 | 5 | 追问必要信息，不擅自补全 |
| 证据异常 | 5 | 无证据、时间不匹配、数据过旧、缺字段、来源冲突 |
| 风险与不确定性 | 5 | 预警优先、不过度保证、披露限制 |
| 输出结构 | 7 | 必填字段、追问字段、缺失信息、引用可追溯 |

测试分三层：L1 数据层（`tests/test_demo.py`，离线 fixture）、L2 规则层
（示例、用例和校验器，不需要模型）、L3 Agent 层（由开发者用实际 Agent 运行）。
详见 [`tests/README.md`](tests/README.md)。

## 设计原则

1. **证据优先。** 天气事实只能来自宿主或授权工具，不能来自模型记忆。
2. **只问必要的。** 缺失信息确实改变结论时才追问；宿主已提供的信息不重复问。
3. **概率不是结论。** 70% 的降雨概率支持「带伞」，不支持「肯定下雨」。
4. **缺失不等于安全。** 没有预警数据，只能说无法确认，不能说没有风险。
5. **ID 与来源归宿主所有。** 模型不能创建、改写或猜测证据 ID。
6. **不发明阈值。** 高温、低温、强风、雷暴的风险判断应依据可信来源和具体活动，
   而不是模型自行拟定的数字。
7. **Schema 是接口，文档是解释。** 两者职责分离，避免规则重复定义。
8. **安全优先于完整。** 宁可返回证据不足，也不拼凑一个看起来完整的答案。

## 宿主需要提供什么

为了让 Skill 正常工作，宿主应尽量提供：

- 明确的地点与目标时间（或允许 Skill 向用户追问）；
- 结构化天气证据，包含 `id`、`type`、`source`、`observed_at`、`valid_from`、
  `valid_to`；
- 官方预警（如有），保留发布机构、等级和有效期；
- 数据时效策略，以及多来源冲突时的优先级规则（如有）。

如果宿主无法提供这些信息，Skill 会返回追问或证据不足，而不是编造天气。

可以直接采用 `demo/weather_demo.py` 生成的字段结构，或用自建适配器产出同样
结构的证据。

## 版本

当前版本 `0.1.0`，输出 `schema_version` 为 `1.0`。变更记录见
[`CHANGELOG.md`](CHANGELOG.md)。

## 发布前检查

- 确认目标宿主支持的 Skill 格式与 frontmatter 字段。
- 确认第三方天气数据和示例内容的授权条件。
- 使用 demo 时保留 Open-Meteo 署名，并确认免费 API 的非商业限制、调用配额和
  最新条款。
- 示例中的天气数据必须保持构造数据标记，不能暗示为真实预报。
- 修改 Schema 时同步更新 `schema_version`、示例、测试用例和 CHANGELOG。

## 贡献

- 新增或修改规则时，先确认它属于哪个文件，避免在多处重复定义。
- 修改 Schema 或意图后，运行全部校验命令。
- 新增测试用例时，遵循 [`tests/README.md`](tests/README.md) 的格式。
- 提交前确认没有悬空 `evidence_id`、没有虚构天气事实。

## 许可证

[MIT](LICENSE)
