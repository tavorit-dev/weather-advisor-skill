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

### 与用户交流

- **默认使用简体中文**回复：说明、总结、计划、提问、提交信息正文、代码评审
  意见，一律用中文。
- 不要因为仓库里英文文件多、或上一轮回答是英文，就切回英文。除非用户明确要求
  换语言，或用户自己改用其他语言提问。
- 面向用户的新文档默认写中文；确需英文版本时按下面的「文件语言」成对维护。

### 文件语言

- `SKILL.md`、`references/*.md`、`docs/*.md`、
  `.claude/skills/weather-advisor/SKILL.md`、
  `.claude/skills/weather-advisor-card/SKILL.md`：英文。`SKILL.md` 与
  `references/` 会被 Agent 直接读取，术语保持与 Schema 一致。
- `.claude/hooks/*.py`、`scripts/*.py`、`demo/*.py`：代码标识符英文，注释与
  docstring 英文。
- `README.md`：简体中文，默认版本；`README.en.md`：英文。两版必须同步修改，
  章节结构保持一致。
- `CLAUDE.md`、`tests/README.md`、`demo/README.md`：中文。
- `CHANGELOG.md`：沿用现有英文格式（Keep a Changelog）。
- 代码标识符、JSON 字段名、意图 ID、状态值：保持英文原样。
- 文件名、路径、命令、代码片段、字段名在中文行文里保持英文原样，不要翻译。

## 目录职责

同一规则只写一处。新增内容前先判断它属于哪个文件，避免在多个文档重复定义。

| 文件 | 只负责 |
| --- | --- |
| `SKILL.md` | 入口、工作流、通用强约束、状态选择、文件索引 |
| `README.md` / `README.en.md` | 面向用户的项目简介；中文为默认版本，中英文同步 |
| `docs/*.md` | 详细使用、架构、示例与测试、目录结构；不重复 `references/` 的规则 |
| `.claude/skills/weather-advisor/SKILL.md` | Claude Code 入口：调用方式、实时 demo、展示格式；规则委托给根 `SKILL.md` |
| `.claude/skills/weather-advisor-card/SKILL.md` | `/weather-advisor-card` 入口：渲染流程、卡片边界；规则委托给根 `SKILL.md` |
| `.claude/hooks/validate-weather-output.py` | 可选 Stop Hook 与手动 Schema 校验；默认不启用 |
| `scripts/install_claude_skill.py` | 把 Skill 安装到个人 `~/.claude/skills` |
| `references/intent-catalog.md` | 意图分类、必要上下文、追问时机 |
| `references/evidence-contract.md` | 输入结构、证据字段、有效期与时效、缺失/冲突处理 |
| `references/recommendation-rules.md` | 从事实到建议的推导、措辞原则 |
| `references/safety-and-uncertainty.md` | 严重天气、风险等级、不确定性措辞 |
| `schemas/recommendation.schema.json` | 输出字段、类型、必填项、枚举、条件约束 |
| `examples/` | 可阅读的输入/输出对 |
| `demo/` | Open-Meteo 演示适配器、离线 fixture、紧凑证据摘要与卡片渲染；不属于 Skill 核心 |
| `demo/weather_card.py` / `demo/card.css` | 响应（+ brief）到自包含 HTML 卡片的渲染与样式；不新增天气事实 |
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

上面 10 条是可执行的约束。面向读者的设计原则（证据优先、概率不是结论、
缺失不等于安全等）说明在 `docs/architecture.md`；修改时不要在两处重复展开。

## 常用命令

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt

python tests/test_demo.py
python tests/test_weather_brief.py
python tests/test_weather_card.py
python tests/test_claude_integration.py
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
4. `docs/architecture.md`：意图摘要表；README 不重复意图细节。
5. `CHANGELOG.md`：记录变更。

如果只是澄清某个意图的行为，不需要改 Schema。

### 修改输出契约

- 保持 JSON Schema Draft 2020-12。
- 破坏性变更必须提升 `schema_version` 的 `const` 值，并同步更新全部期望输出、
  测试用例、`README.md`、`README.en.md`、相关 `docs/` 文档和 `CHANGELOG.md`。
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
- 更换默认提供方时，同步更新 `demo/README.md`、`README.md`、`README.en.md`、
  `docs/getting-started.md`、`docs/claude-code.md` 中的署名、许可和限制说明，
  以及 `CHANGELOG.md`。
- demo 的命令行接口变化时，同步更新 `.claude/skills/weather-advisor/SKILL.md`
  中的调用示例。
- `demo/weather_brief.py` 只是 `weather_demo.py` 证据的窗口化摘要：保留
  `evidence_id`、`source`、`retrieved_at`、署名和许可，不生成建议，不引入新
  数据源；字段变化时同步更新 `demo/README.md` 与
  `docs/claude-code.md`。
- `demo/weather_card.py` 只是渲染层：只读取已定义的响应字段与 brief 字段，
  不新增天气数值、阈值或建议，不改写响应；样式在 `demo/card.css`，渲染时内联
  进卡片，保持单文件、离线可打开、不引用任何外部资源。卡片必须保留 Open-Meteo
  署名与许可、空气质量为 CAMS 预报的说明、两套 AQI 不可比较的提示，以及 brief
  的 `demo_gaps`。响应缺少必填字段、`status`/`intent` 非枚举值、或
  `needs_clarification` 无追问时，脚本应报错退出而不是渲染。字段或 CLI 变化时
  同步更新 `demo/README.md`、`docs/claude-code.md` 与
  `.claude/skills/weather-advisor-card/SKILL.md`。
- `--summary-only` 只能省略 `hours`，不得省略 `summary`、`source`、`demo_gaps`
  或证据 ID；`--compact` 只改变 JSON 序列化，不改变字段；`--every N` 只能
  稀疏化 `hours`，`summary` 必须继续覆盖整个窗口。
- 保持“demo 不属于 Skill 核心”的边界，不要把数据获取写进 `SKILL.md`。

### 文档改动

- 改规则时只改一个文件，其他文件用链接指向它。
- 改完检查 `README.md` 与 `README.en.md` 的章节结构、链接和数字是否一致；
  目录树以 `docs/repository-layout.md` 为准，示例与测试数量以
  `docs/examples-and-tests.md` 为准。
- README 头部的 badge 是硬编码计数，不是动态生成的：新增或删除示例、用例，
  或改动 `schema_version`、许可证时，必须同步修改 `README.md` 与
  `README.en.md` 中对应的 badge，并确认其链接目标仍然存在。计数以
  `docs/examples-and-tests.md` 为准，两版 README 的 badge 必须逐字一致。
- 变更面向用户时更新 `CHANGELOG.md`。

## 提交前验证

至少运行：

```bash
python tests/test_demo.py
python tests/test_weather_brief.py
python tests/test_claude_integration.py
python tests/run_examples.py
python tests/validate_cases.py
```

要求六条命令都返回 0，并且：

- 没有悬空 `evidence_id`；
- 示例数量、用例数量与 `docs/examples-and-tests.md` 描述一致；
- 新增或修改的文档没有把同一规则复制到多个文件。

## 发布前检查

- 确认目标宿主支持的 Skill 格式与 frontmatter 字段。
- 确认第三方天气数据和示例内容的授权条件。
- 使用 demo 时保留 Open-Meteo 署名，并确认免费 API 的非商业限制、调用配额和
  最新条款。
- 示例中的天气数据必须保持构造数据标记，不能暗示为真实预报。
- 修改 Schema 时同步更新 `schema_version`、示例、测试用例和 `CHANGELOG.md`。

## 贡献规则

- 新增或修改规则前，先按「目录职责」确认归属文件，只在它所属的文件里展开。
- 修改 Schema 或意图后，运行全部校验命令，并同步 `CHANGELOG.md`。
- 新增测试用例时遵循 `tests/README.md` 的格式。
- 提交前确认没有悬空 `evidence_id`、没有虚构天气事实。

## 不要做

- 不要给 Skill 核心加入天气抓取或 API 调用。`demo/weather_demo.py` 是唯一
  允许的数据获取示例，必须保持独立、可替换。
- 不要在测试或 `offline` 模式中联网，不要提交 API Key 或实时抓取结果。
- 不要把 `design.md` 的内容整段复制进 `SKILL.md`。
- 不要为了让测试通过而放宽 Schema 或删除断言。
- 不要在示例、测试或文档中写入真实预报、真实预警或未经授权的数据。
- 不要用「绝对安全」「肯定不会下雨」这类无证据表述作为示例文案。
- 不要把 Claude Code 特有的调用方式、实时 demo 指令或 Hook 逻辑写进根
  `SKILL.md`；这些属于 `.claude/skills/weather-advisor/SKILL.md`，根文件保持
  宿主无关。
- 不要把 `argument-hint` 等 Claude Code 专有 frontmatter 加到根 `SKILL.md`。
  根 Skill 需要保持可分发；Claude Code 的 `argument-hint` 只放在
  `.claude/skills/weather-advisor/SKILL.md`。
- 不要默认启用 Stop Hook。Hook 是可选增强，必须在 `docs/claude-code.md` 中
  说明启用方式与限制。
- 不要让 `demo/weather_brief.py` 输出完整证据、生成建议或替代官方预警；它只
  做窗口化摘要，完整证据仍以 `weather_demo.py` 为准。
- 不要让 `demo/weather_card.py` 生成或改写建议、补全缺失字段，或把卡片做成
  官方预警、官方 AQI 公报或实测数据的样式。卡片只渲染已有响应与 brief。
- 不要让卡片引用外部资源（脚本、外链样式、远程图片、CDN）；它必须保持单文件、
  离线可打开。
