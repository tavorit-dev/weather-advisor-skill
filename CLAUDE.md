# CLAUDE.md

本文件面向在此仓库中工作的 Claude Code 会话。开始修改前先读本文件，再按需读
`SKILL.md` 和相关 `references/`。

## 项目性质

这是一个**纯文档 + JSON Schema + 测试用例**的开源 Skill 仓库，不是应用程序。

- 不引入天气 API、HTTP 客户端、Agent Runtime、数据库、Web 服务或后台。
- 不加入模型特定的 Prompt 调优；规范应保持宿主无关。
- 不把真实天气数据写进示例。示例必须使用构造数据和 `example-provider` 来源。
- `design.md` 是最初的实现方案，保留作设计记录；不要在没有要求时修改它。

## 语言约定

- `SKILL.md`、`references/*.md`：英文。这些文件会被 Agent 直接读取，术语保持
  与 Schema 一致。
- `README.md`：简体中文；`README.en.md`：英文。两版必须同步修改，章节结构保持
  一致。
- `CLAUDE.md`、`tests/README.md`、`demo/README.md`、`CHANGELOG.md`：中文。
- 代码标识符、JSON 字段名、意图 ID、状态值：保持英文原样。

## 目录职责

同一规则只写一处。新增内容前先判断它属于哪个文件，避免在多个文档重复定义。

| 文件 | 只负责 |
| --- | --- |
| `SKILL.md` | 入口、工作流、通用强约束、状态选择、文件索引 |
| `README.md` / `README.en.md` | 面向用户的项目说明；中英文两版内容同步 |
| `references/intent-catalog.md` | 意图分类、必要上下文、追问时机 |
| `references/evidence-contract.md` | 输入结构、证据字段、有效期与时效、缺失/冲突处理 |
| `references/recommendation-rules.md` | 从事实到建议的推导、措辞原则 |
| `references/safety-and-uncertainty.md` | 严重天气、风险等级、不确定性措辞 |
| `schemas/recommendation.schema.json` | 输出字段、类型、必填项、枚举、条件约束 |
| `examples/` | 可阅读的输入/输出对 |
| `demo/` | Open-Meteo 演示适配器与离线 fixture；不属于 Skill 核心 |
| `tests/` | 验收用例与校验工具 |

`SKILL.md` 的 `name`/`description` 是调用元数据，不属于响应 JSON。不要把
Skill 元数据写进输出契约。

## 不变量

修改任何文件时，以下约束不能被破坏：

1. 响应中的天气事实只能来自输入的 `weather_evidence`；不得创造数值、时间、
   地点、来源或证据 ID。
2. `evidence[]`、`recommendations[].evidence_ids`、`risks[].evidence_ids`
   中的每个 ID 都必须存在于输入证据列表。
3. 证据的 `valid_from`–`valid_to` 必须覆盖用户目标时段；部分覆盖要在
   `uncertainty` 或 `missing_information` 中说明。
4. 缺少证据不等于风险不存在。「没有提供预警」不能表述为「没有预警」。
5. `answered` 至少 1 条 recommendation；`needs_clarification` 必须有非空
   `clarification_question`；`insufficient_evidence` 应有缺失信息说明。
6. Schema 使用 `additionalProperties: false`，输出不得包含未定义字段。
7. 不引入主观置信分数（如 `confidence: 0.95`）。
8. 不发明安全阈值。风险判断应引用来源、预警等级或具体活动标准。
9. `demo/` 只使用 Python 标准库，不要求 API Key；`offline` 模式和 L1 测试不得
   联网。
10. demo 输出必须保留 `source`、`observed_at`、有效期和 Open-Meteo 署名；
    离线 fixture 必须标明合成数据，不能暗示为真实预报。

## 常用命令

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py
python tests/run_examples.py
python tests/validate_cases.py
python tests/validate_schema.py examples/commute-rain-output.json
python tests/check_evidence.py examples/commute-rain-output.json examples/commute-rain.json
python tests/grade_case.py normal-001 examples/commute-rain-output.json
```

依赖只有 `jsonschema`。`tests/test_demo.py` 只用标准库。不要为了测试引入
pytest、pydantic 或网络依赖。

离线演示：

```bash
python demo/weather_demo.py Tokyo --offline
```

实时演示需要网络，仅用于手动验证：

```bash
python demo/weather_demo.py Tokyo --days 2
```

## 修改指引

### 新增或修改意图

按顺序同步：

1. `references/intent-catalog.md`：触发/排除条件、必要上下文、证据要素、行为。
2. `schemas/recommendation.schema.json`：`intent` 枚举。
3. `tests/cases.jsonl`：至少一条正常场景和一条缺失信息场景。
4. `README.md`：意图表。
5. `CHANGELOG.md`：记录变更。

如果只是澄清某个意图的行为，不需要改 Schema。

### 修改输出契约

- 保持 JSON Schema Draft 2020-12。
- 破坏性变更必须提升 `schema_version` 的 `const` 值，并同步更新全部期望输出、
  测试用例、`README.md` 和 `CHANGELOG.md`。
- 新增可选字段时，确认 `additionalProperties: false` 不会误伤现有示例。
- 不要放宽「answered 至少一条建议」和「clarification 必须有问题」两个条件。

### 新增示例

- 文件名成对：`<name>.json`（输入）与 `<name>-output.json`（输出）。
- 输入证据 ID 唯一，输出只能引用这些 ID。
- 示例应覆盖一个有代表性的行为，不要只改措辞重复已有示例。
- 新增后运行 `python tests/run_examples.py`。
- 示例数据保持构造性质，`source` 用 `example-provider`。

### 新增测试用例

- 追加到 `tests/cases.jsonl`，一行一个 JSON 对象。
- `id` 使用 kebab-case 且唯一；`category` 只能是
  `normal`、`missing_information`、`evidence_anomaly`、`risk_uncertainty`、
  `output_structure`。
- `expect` 只能使用 `tests/README.md` 列出的字段。
- `required_evidence_ids` 必须存在于该用例的输入证据中。
- 运行 `python tests/validate_cases.py`。

### 修改 demo 或天气数据源

- `demo/weather_demo.py` 必须保持零第三方依赖和免 API Key。
- 新数据源必须输出与 `references/evidence-contract.md` 相同的字段，并保留
  `source`、`observed_at`、`valid_from`、`valid_to`。
- 不得在 `offline` 模式或测试中发网络请求；新增 fixture 放在 `demo/fixtures/`，
  并标注为合成数据。
- 更换默认提供方时，同步更新 `demo/README.md`、`README.md`、`README.en.md`
  中的署名、许可和限制说明，以及 `CHANGELOG.md`。
- 保持“demo 不属于 Skill 核心”的边界，不要把数据获取写进 `SKILL.md`。

### 文档改动

- 改规则时只改一个文件，其他文件用链接指向它。
- 改完检查 `README.md` 与 `README.en.md` 中的目录树、示例表和测试数量是否
  仍然准确，并确认两版内容一致。
- 变更面向用户时更新 `CHANGELOG.md`。

## 提交前验证

至少运行：

```bash
python tests/test_demo.py
python tests/run_examples.py
python tests/validate_cases.py
```

要求两项都返回 0，并且：

- 没有悬空 `evidence_id`；
- 示例数量、用例数量与 README 描述一致；
- 新增或修改的文档没有把同一规则复制到多个文件。

## 不要做

- 不要给 Skill 核心加入天气抓取或 API 调用。`demo/weather_demo.py` 是唯一
  允许的数据获取示例，必须保持独立、可替换。
- 不要在测试或 `offline` 模式中联网，不要提交 API Key 或实时抓取结果。
- 不要把 `design.md` 的内容整段复制进 `SKILL.md`。
- 不要为了让测试通过而放宽 Schema 或删除断言。
- 不要在示例、测试或文档中写入真实预报、真实预警或未经授权的数据。
- 不要用「绝对安全」「肯定不会下雨」这类无证据表述作为示例文案。
