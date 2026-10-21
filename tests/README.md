# 测试说明

本目录不依赖天气 API，也不内置 Agent。它提供两类东西：

1. **可执行的检查工具**：校验输出结构、证据引用和用例文件本身。
2. **可执行的验收用例**：`cases.jsonl`，描述输入与可检查的预期行为。

自然语言文案不要求逐字一致。检查的是状态、意图、证据引用、风险等级和
禁止性表述，而不是措辞是否漂亮。

## 目录

| 文件 | 作用 |
| --- | --- |
| `cases.jsonl` | 32 条验收用例，每行一个 JSON 对象 |
| `validate_schema.py` | 校验单份响应是否符合 `schemas/recommendation.schema.json` |
| `check_evidence.py` | 校验响应引用的 `evidence_id` 是否都存在于输入证据中 |
| `run_examples.py` | 对 `examples/` 下 6 组输入/输出执行上述两项检查 |
| `validate_cases.py` | 检查 `cases.jsonl` 本身的格式、枚举值和证据引用 |
| `grade_case.py` | 用指定用例评分一份模型响应 |
| `test_demo.py` | L1 数据层测试：离线验证 demo 的地理编码与字段转换 |
| `requirements.txt` | Python 依赖（`test_demo.py` 只用标准库） |

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r tests/requirements.txt
```

## 三层测试

测试分为三层，避免把“天气接口调用成功”误认为“Skill 测试通过”。

| 层次 | 测试内容 | 命令 | 需要 LLM |
| --- | --- | --- | --- |
| L1 数据层 | 地理编码、天气 API 返回有效数据、字段与单位转换、证据 ID 唯一性 | `python tests/test_demo.py` | 否 |
| L2 规则层 | 地点缺失时追问、证据缺失时不编造、证据引用有效、输出结构 | `python tests/run_examples.py`、`python tests/validate_cases.py`、`python tests/grade_case.py` | 否，使用固定输入/输出 |
| L3 Agent 层 | 实际加载 `SKILL.md` 后，能否基于真实或固定天气数据给出合理建议 | 由开发者用自己选择的 Agent 运行 | 是 |

`offline` 模式（`demo/weather_demo.py --offline`）和 L1 测试使用固定 fixture，
不依赖天气 API；`live` 模式由开发者按需运行。这样公共 API 暂时不可用时，
基础测试仍然可以执行。

## 快速运行

```bash
# 0. L1 数据层：离线 fixture，无需第三方依赖
python tests/test_demo.py

# 1. 校验全部示例
python tests/run_examples.py

# 2. 校验用例文件
python tests/validate_cases.py

# 3. 校验单份输出
python tests/validate_schema.py examples/commute-rain-output.json

# 4. 校验证据引用
python tests/check_evidence.py \
  examples/commute-rain-output.json \
  examples/commute-rain.json
```

## 如何评测一个 Agent

测试集不负责调用模型。流程是：

1. 让被测 Agent 读取 `SKILL.md` 与相关 `references/`，输入某条用例的 `input`。
2. 将响应保存为 JSON，例如 `/tmp/responses/normal-001.json`。
3. 运行评分器：

```bash
python tests/grade_case.py normal-001 /tmp/responses/normal-001.json
```

评分器先执行 Schema 校验和证据引用校验，再逐条检查 `expect`。

## 全局检查

每条用例的响应都必须满足：

- 能通过 `recommendation.schema.json`。
- `evidence[]`、`recommendations[].evidence_ids`、`risks[].evidence_ids`
  中出现的每个 ID，都存在于输入的 `weather_evidence` 中。
- 不包含无证据支持的确定性表述：`绝对安全`、`百分之百`、
  `肯定不会下雨`、`一定不会下雨`、`保证不会`。
- `needs_clarification` 必须给出非空的 `clarification_question`。
- `answered` 至少包含一条 recommendation（Schema 已约束）。

## `expect` 字段

| 字段 | 含义 |
| --- | --- |
| `status` | 期望状态，精确匹配 |
| `status_in` | 期望状态属于给定集合 |
| `intent` | 期望意图，精确匹配 |
| `intent_in` | 期望意图属于给定集合 |
| `min_recommendations` / `max_recommendations` | 建议条数范围 |
| `min_risks` | 风险条数下限 |
| `min_medium_or_higher_risks` | `medium` 或 `high` 风险条数下限 |
| `min_high_severity_risks` | `high` 风险条数下限 |
| `required_evidence_ids` | 必须在输出中被引用的证据 ID |
| `must_cite_all_evidence` | 输入中的全部证据都必须被引用 |
| `requires_clarification` | `clarification_question` 必须是非空字符串 |
| `requires_missing_information` | `missing_information` 必须非空 |
| `requires_uncertainty` | `uncertainty` 必须非空 |
| `forbidden_terms` | 响应任意字符串中不得出现的子串 |
| `keywords_any` | 响应任意字符串中至少出现一个给定子串 |

`keywords_any` 只用于“必须披露冲突”这类无法从结构上判断的要求。不要用它
检查具体措辞；措辞检查会制造误报。

## 用例结构

```json
{
  "id": "normal-001",
  "category": "normal",
  "name": "通勤时段降雨建议带伞",
  "input": {
    "user_query": "明早上班要带伞吗？",
    "intent": "commute_advice",
    "context": {},
    "weather_evidence": []
  },
  "expect": {
    "status": "answered",
    "intent": "commute_advice",
    "min_recommendations": 1,
    "required_evidence_ids": ["ev-rain-001"],
    "requires_uncertainty": true
  }
}
```

`input.intent` 是宿主提示，可省略；省略时用例同时检查意图识别。

## 用例覆盖

| 类别 | 数量 | 重点 |
| --- | --- | --- |
| `normal` | 10 | 意图识别、建议可执行、引用正确 |
| `missing_information` | 5 | 追问必要信息，不擅自补全 |
| `evidence_anomaly` | 5 | 无证据、时间不匹配、数据过旧、缺字段、来源冲突 |
| `risk_uncertainty` | 5 | 预警优先、不过度保证、披露限制 |
| `output_structure` | 7 | 必填字段、追问字段、缺失信息、引用可追溯 |

当前共 32 条，满足首版“至少 30 条”的要求。

## 新增用例

1. 在 `cases.jsonl` 末尾追加一行 JSON，不要拆成多行。
2. `id` 使用 kebab-case 且全局唯一；`category` 必须是上面五类之一。
3. 输入中的 `weather_evidence[].id` 必须唯一，`required_evidence_ids`
   只能引用这些 ID。
4. `expect` 只能使用上表中的字段；`validate_cases.py` 会拒绝未知字段。
5. 运行 `python tests/validate_cases.py` 和 `python tests/run_examples.py`。

如果新增了意图或状态，先改 Schema 和 `references/`，再改测试。

## 已知限制

- Schema 校验不等于事实校验。它能发现缺字段和悬空引用，不能判断“建议带伞”
  是否真的由降雨证据支持；这需要人工或模型评审。
- `forbidden_terms` 是子串匹配，可能误报（例如引用中包含该词）。用例应尽量
  只禁止明确的危险断言。
- 未提供自动运行 Agent 的评测平台。L3 需要开发者把 demo 输出或固定输入交给
  实际 Agent，再人工判断建议质量。首版以可复现的 L1/L2 检查和独立校验器为目标。
- 示例中的天气数据全部为构造数据，来源标记为 `example-provider`，不代表任何
  真实预报。
