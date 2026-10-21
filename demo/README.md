# Open-Meteo 演示

[`weather_demo.py`](weather_demo.py) 是一个零依赖脚本：输入城市名，调用
Open-Meteo 的免费公共 API，输出符合
[`references/evidence-contract.md`](../references/evidence-contract.md) 的天气
Evidence，并包装成 Skill 可直接消费的输入信封。

它只演示**数据获取与标准化**，不是 Skill 的一部分，也不是生产级天气适配器。
Skill 核心仍然不抓取天气数据。

## 前置条件

- Python 3.9+（使用标准库 `zoneinfo`）。
- `live` 模式需要网络；`offline` 模式不需要。
- 不需要注册账号、API Key 或第三方 Python 包。

## 快速开始

```bash
# 实时查询东京未来 3 天逐小时天气
python demo/weather_demo.py Tokyo

# 多词城市名
python demo/weather_demo.py "New York" --days 2

# 不联网，使用仓库内的东京 fixture
python demo/weather_demo.py Tokyo --offline

# 指定 user_query / intent，并写入文件
python demo/weather_demo.py Tokyo \
  --query "明天东京适合户外跑步吗？" \
  --intent outdoor_activity \
  --output /tmp/tokyo-input.json
```

`--days` 取值 1–7，默认 3，只在 `live` 模式下生效。`--intent` 必须是
`SKILL.md` 定义的六种意图之一。

## 输出结构

```json
{
  "user_query": "What will the weather be like in Tokyo?",
  "intent": "weather_lookup",
  "context": {
    "location": {
      "name": "Tokyo",
      "country": "Japan",
      "latitude": 35.6895,
      "longitude": 139.69171,
      "timezone": "Asia/Tokyo"
    },
    "start": "2026-10-22T08:00:00+09:00",
    "end": "2026-10-22T20:00:00+09:00"
  },
  "weather_evidence": [
    {
      "id": "ev-000-temperature_2m",
      "type": "temperature",
      "value": 18.4,
      "unit": "°C",
      "valid_from": "2026-10-22T08:00:00+09:00",
      "valid_to": "2026-10-22T09:00:00+09:00",
      "source": "Open-Meteo",
      "observed_at": "2026-10-21T21:00:00+09:00"
    }
  ],
  "attribution": "Weather data by Open-Meteo.com",
  "metadata": {
    "provider": "Open-Meteo",
    "mode": "live",
    "retrieved_at": "2026-10-21T21:00:00+09:00",
    "data_license": "CC BY 4.0",
    "source_urls": [
      "https://geocoding-api.open-meteo.com/v1/search",
      "https://api.open-meteo.com/v1/forecast"
    ],
    "data_note": "Live forecast data; values change over time and are not guaranteed."
  }
}
```

| 字段 | 说明 |
| --- | --- |
| `user_query` | 默认是通用查询，可用 `--query` 覆盖 |
| `intent` | 默认 `weather_lookup`，可用 `--intent` 覆盖 |
| `context.location` | 地理编码结果，包含名称、国家、经纬度和时区 |
| `context.start` / `end` | 输出证据覆盖的整体时间窗 |
| `weather_evidence` | 逐小时标准化证据，字段符合证据契约 |
| `attribution` | Open-Meteo 署名，展示时应保留 |
| `metadata` | 数据提供方、模式、获取时间、许可和说明 |

`live` 模式返回的是 Open-Meteo 给出的完整逐小时窗口，通常从当地 00:00 开始，
因此可能包含当天已经过去的时段。只关心未来时段时，按 `valid_from` 过滤即可。

## 紧凑摘要（weather_brief.py）

完整信封适合校验和调试，但把 144–288 条逐小时证据直接交给 Agent 会消耗较多
上下文。`weather_brief.py` 是同一份证据的窗口化视图：只保留指定日期/时段的
小时数据、统计值和证据 ID。

```bash
# 今天剩余时段
python demo/weather_brief.py Tianjin --date today

# 指定窗口，紧凑 JSON
python demo/weather_brief.py Tianjin --date tomorrow --window 10:00-16:00 --compact

# 全天但没有指定时段：每 3 小时保留一个点
python demo/weather_brief.py Tianjin --date tomorrow --every 3 --compact

# 只需要极值：只看统计值
python demo/weather_brief.py Tianjin --date tomorrow --summary-only --compact

# 离线 fixture（日期固定为 2026-10-22）
python demo/weather_brief.py Tokyo --offline --date 2026-10-22 --window 08:00-12:00
```

输出包含：

- `coverage`：日期、窗口、明细模式（`summary` / `sparse` / `hourly`）、步长、窗口小时数、实际输出小时数、源证据覆盖范围；
- `summary`：温度/体感的 min/max、降雨概率最大值、降水量合计、风速/阵风最大值；
- `hours`：每个小时的数值与对应 `evidence_id`（`--summary-only` 时省略）；
- `source`：提供方、模式、获取时间、署名与许可；
- `demo_gaps`：demo 不提供的证据类型（官方预警、空气质量、紫外线等）。

与完整 envelope 的区别：

| 项目 | `weather_demo.py` | `weather_brief.py` |
| --- | --- | --- |
| 输出 | 完整 `weather_evidence` | 窗口化摘要 + 证据 ID |
| 默认体积（离线 12 小时） | 约 22 KB | 9.9 KB |
| `--compact` | — | 7.2 KB |
| `--every 3 --compact` | — | 3.6 KB |
| `--summary-only` | — | 2.4 KB |
| `--summary-only --compact` | — | **1.7 KB** |
| 用途 | 校验、调试、完整输入 | Agent 日常咨询 |

`--summary-only` 只保留统计值和对应证据 ID；需要时间分布时用 `--every 3` 保留每 3 小时一个真实证据点。`--compact` 去掉 JSON 缩进，适合直接交给 Agent。

实时 24 小时实测：hourly compact 约 12.7 KB，`--every 3 --compact` 约 5.4 KB，`--summary-only --compact` 约 1.7 KB。

`weather_brief.py` 不产生建议，也不替代官方预警或空气质量数据；它只是
`weather_demo.py` 证据的紧凑投影。两者都保留 Open-Meteo 署名和许可信息。

## 交给 Agent 使用

```bash
python demo/weather_demo.py Tokyo \
  --query "明天东京适合户外跑步吗？" \
  --intent outdoor_activity \
  --output /tmp/tokyo-input.json
```

然后把 `/tmp/tokyo-input.json` 交给加载了 [`SKILL.md`](../SKILL.md) 的 Agent。
输出建议后再校验：

```bash
python tests/validate_schema.py /tmp/tokyo-response.json
python tests/check_evidence.py /tmp/tokyo-response.json /tmp/tokyo-input.json
```

`check_evidence.py` 会确认 Agent 引用的每个 `evidence_id` 都来自 demo 输出。

## 字段映射

| Open-Meteo hourly 字段 | Evidence `type` | 单位 |
| --- | --- | --- |
| `temperature_2m` | `temperature` | `°C` |
| `apparent_temperature` | `apparent_temperature` | `°C` |
| `precipitation_probability` | `precipitation_probability` | `%` |
| `precipitation` | `precipitation_amount` | `mm` |
| `wind_speed_10m` | `wind_speed` | `km/h` |
| `wind_gusts_10m` | `wind_gust` | `km/h` |

- 时间按地点时区返回，带 UTC 偏移；每个证据的有效期是 1 小时。
- `observed_at` 是本次请求时间，不是气象观测时间。
- 值为 `null` 的字段会跳过，不会补零或补默认值。
- `id` 形如 `ev-000-temperature_2m`，同一次输出内唯一。

## offline 与 live

| 模式 | 命令 | 数据来源 | 是否联网 |
| --- | --- | --- | --- |
| `live` | `python demo/weather_demo.py Tokyo` | Open-Meteo 公共 API | 是 |
| `offline` | `python demo/weather_demo.py Tokyo --offline` | `demo/fixtures/` 固定数据 | 否 |

`offline` 只内置东京 fixture，用于测试与演示，输出中的 `metadata.data_note`
会明确标记为合成数据。其他城市请使用 `live` 模式。

## 数据来源、署名与限制

- 天气数据由 [Open-Meteo](https://open-meteo.com/) 提供，数据许可为
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。展示数据时应保留
  `Weather data by Open-Meteo.com` 署名。
- Open-Meteo 的免费公共 API 面向非商业使用；官方文档当前标注免费层约每日
  10,000 次请求。带订阅、广告等商业产品通常属于商业使用，需要选择符合用途的
  授权方案或自托管。
- 免费端点不保证永久免费、无限调用或生产级 SLA。条款和限额可能变化，使用前
  请以 Open-Meteo 官网为准。
- 如果需要更稳定的演示环境或更大调用量，可以评估自托管 Open-Meteo，但需要
  自行部署和维护，不适合作为首版体验的前置条件。
- 本 demo 不缓存数据、不做重试，也没有为生产环境做限流控制。

## 替换为其他天气数据源

Demo 与 Skill 核心分离，替换数据源不需要改 `SKILL.md` 或 Schema：

1. 实现地理编码，得到地点名称、经纬度和时区。
2. 请求天气数据，保留来源、发布时间和有效期。
3. 按 [`references/evidence-contract.md`](../references/evidence-contract.md)
   转换为 `weather_evidence`。
4. 输出同样的输入信封，把 `source` 换成新提供方，并保留其署名和许可信息。
5. 如果提供方有官方预警，映射为 `severe_weather_alert`，保留发布机构、等级和
   有效期。

也可以参考 `weather_demo.py` 的 `geocode`、`fetch_forecast`、
`build_evidence` 三个函数的边界，替换其中任意一层。

## 测试

```bash
python tests/test_demo.py
```

这是 L1 数据层测试：使用离线 fixture，覆盖地理编码、字段映射、单位、有效期、
ID 唯一性、信封结构和 CLI，不访问网络。完整的 L1/L2/L3 分层说明见
[`tests/README.md`](../tests/README.md)。

## 生产化缺口

这份实现用于演示，不是生产级适配器。投入生产前至少需要补上：

- 同名地点的歧义处理（当前直接取地理编码的第一条结果）。
- 请求重试、退避、限流和配额监控。
- HTTP 错误、限流错误和上游数据异常的细分处理。
- 预报发布时间与有效期的独立校验（当前 `observed_at` 记录的是获取时间）。
- 缺失字段的业务处理（当前直接跳过，不推断默认值）。
- 数据缓存、审计和提供方切换时的兼容性测试。

## 错误处理

脚本遇到 HTTP 错误、网络失败、地点不存在、响应缺少 `hourly` 数据、时间格式
错误或未知意图时，会向 stderr 输出一行错误并以非零状态退出，不打印 traceback。
