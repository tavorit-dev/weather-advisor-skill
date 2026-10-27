# Open-Meteo 演示

[`weather_demo.py`](weather_demo.py) 是一个零依赖脚本：输入城市名，调用
Open-Meteo 的免费公共 API，输出符合
[`references/evidence-contract.md`](../references/evidence-contract.md) 的天气
Evidence，并包装成 Skill 可直接消费的输入信封。

除天气外，它默认还会调用 Open-Meteo 的空气质量端点，把 PM2.5、PM10 和
US / European AQI 合并到同一条逐小时时间线上。空气质量往往是判断剧烈户外
活动是否适宜的决定因素，因此默认开启；用 `--no-air-quality` 可以关掉。

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

# 只要天气证据，不查空气质量
python demo/weather_demo.py Tokyo --no-air-quality

# 指定 user_query / intent，并写入文件
python demo/weather_demo.py Tokyo \
  --query "明天东京适合户外跑步吗？" \
  --intent outdoor_activity \
  --output /tmp/tokyo-input.json
```

`--days` 取值 1–7，默认 3，只在 `live` 模式下生效。`--intent` 必须是
`SKILL.md` 定义的六种意图之一。`--no-air-quality` 跳过空气质量端点，只输出
六类天气证据。

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
    },
    {
      "id": "ev-aq-000-pm2_5",
      "type": "particulate_matter_2_5",
      "value": 12.0,
      "unit": "μg/m³",
      "valid_from": "2026-10-22T08:00:00+09:00",
      "valid_to": "2026-10-22T09:00:00+09:00",
      "source": "Open-Meteo Air Quality (CAMS)",
      "observed_at": "2026-10-21T21:00:00+09:00",
      "description": "Fine particulate matter (PM2.5), modelled hourly forecast."
    },
    {
      "id": "ev-aq-000-us_aqi",
      "type": "air_quality_index",
      "value": 69,
      "unit": "USAQI",
      "valid_from": "2026-10-22T08:00:00+09:00",
      "valid_to": "2026-10-22T09:00:00+09:00",
      "source": "Open-Meteo Air Quality (CAMS)",
      "observed_at": "2026-10-21T21:00:00+09:00",
      "description": "Air quality index on the US AQI scale; modelled hourly forecast. Scales are not directly comparable to each other."
    }
  ],
  "attribution": "Weather data by Open-Meteo.com | Air quality data by Open-Meteo.com (CAMS)",
  "metadata": {
    "provider": "Open-Meteo",
    "mode": "live",
    "retrieved_at": "2026-10-21T21:00:00+09:00",
    "data_license": "CC BY 4.0",
    "source_urls": [
      "https://geocoding-api.open-meteo.com/v1/search",
      "https://api.open-meteo.com/v1/forecast",
      "https://air-quality-api.open-meteo.com/v1/air-quality"
    ],
    "data_note": "Live forecast data; values change over time and are not guaranteed. Air-quality values are modelled forecasts (CAMS), not ground-station measurements, and do not replace official air-quality bulletins."
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
| `attribution` | Open-Meteo 署名（含空气质量），展示时应保留 |
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

# 不查空气质量
python demo/weather_brief.py Tianjin --date tomorrow --every 3 --compact --no-air-quality

# 离线 fixture（日期固定为 2026-10-22）
python demo/weather_brief.py Tokyo --offline --date 2026-10-22 --window 08:00-12:00
```

输出包含：

- `coverage`：日期、窗口、明细模式（`summary` / `sparse` / `hourly`）、步长、窗口小时数、实际输出小时数、源证据覆盖范围；
- `summary`：温度/体感的 min/max、降雨概率最大值、降水量合计、风速/阵风最大值；开启空气质量时还有 PM2.5 / PM10 的 min/max；
- `air_quality`：仅在使用空气质量时出现，包含 `kind`（预报模型而非实测）、`index_scales`（两套 AQI 标度）、`us_aqi` / `european_aqi` 的 min/max 与证据 ID，以及"两套标度不可直接比较"的说明；
- `hours`：每个小时的数值与对应 `evidence_id`（`--summary-only` 时省略）；
- `source`：提供方、模式、获取时间、署名与许可；开启空气质量时另有 `air_quality_attribution`；
- `demo_gaps`：demo 不提供的证据类型（官方预警、紫外线、湿度、能见度等）。

`hours[].values` 中两种 AQI 分别以 `us_aqi` 和 `european_aqi` 为键，因为它们
共用 `air_quality_index` 这一证据类型，必须按标度区分。

与完整 envelope 的区别：

| 项目 | `weather_demo.py` | `weather_brief.py` |
| --- | --- | --- |
| 输出 | 完整 `weather_evidence` | 窗口化摘要 + 证据 ID |
| 默认体积（离线 12 小时，含空气质量） | 43.7 KB | 15.3 KB |
| `--compact` | — | 11.2 KB |
| `--every 3 --compact` | — | 5.6 KB |
| `--summary-only` | — | 4.0 KB |
| `--summary-only --compact` | — | **2.8 KB** |
| `--no-air-quality`（12 小时） | 22.6 KB | 9.9 KB |
| `--no-air-quality --summary-only --compact` | — | 1.7 KB |
| 用途 | 校验、调试、完整输入 | Agent 日常咨询 |

`--summary-only` 只保留统计值和对应证据 ID；需要时间分布时用 `--every 3` 保留每 3 小时一个真实证据点。`--compact` 去掉 JSON 缩进，适合直接交给 Agent。

实时 24 小时实测（天津）：hourly compact 约 19.6 KB，`--every 3 --compact` 约 8.4 KB，`--summary-only --compact` 约 2.8 KB；用 `--no-air-quality` 时分别为约 12.7 KB、5.4 KB、1.7 KB。全天完整信封约 86 KB。

空气质量约占体积的 1/3。上下文紧张且问题只关心天气时用 `--no-air-quality`；
但涉及跑步、骑行等剧烈户外活动时，空气质量往往才是决定性的那一项。

`weather_brief.py` 不产生建议，也不替代官方预警或空气质量公报；它只是
`weather_demo.py` 证据的紧凑投影。两者都保留 Open-Meteo 署名和许可信息。

## 可视化卡片（weather_card.py）

`weather_card.py` 把一份符合
[`schemas/recommendation.schema.json`](../schemas/recommendation.schema.json)
的响应渲染成一张自包含的 HTML 卡片，可选地叠加 `weather_brief.py` 的窗口化
证据，让卡片带上建议背后的逐小时曲线。

```bash
# 只渲染响应
python demo/weather_card.py response.json --output card.html

# 叠加窗口证据
python demo/weather_card.py response.json --brief brief.json --output card.html

# 中文界面（由提问语言决定）
python demo/weather_card.py response.json --query "今日天津天气" --output card.html

# 打开浏览器 / 导出 / 校验已有卡片
python demo/weather_card.py response.json --brief brief.json --open
python demo/weather_card.py response.json --brief brief.json --print
python demo/weather_card.py --check card.html
```

它只做渲染，不做分析：不新增天气数值、阈值或建议，也不改写响应。卡片上的每个
数字都来自传入的响应或 brief。

| 输入 | 卡片内容 |
| --- | --- |
| 仅响应 | 状态、意图、摘要、建议、风险、证据、缺失信息、不确定性 |
| 响应 + brief | 追加窗口摘要磁贴与逐小时曲线（温度、体感、降雨概率、降水量、风速、阵风、PM2.5、PM10），每条曲线标注峰值 |

卡片按「读者需要的顺序」排列：摘要之后紧跟**建议**（带强调色左边框，只有确实
有建议时才加），然后是支撑建议的时段证据、风险，最后是折叠的原始证据列表。

### 移动端布局

卡片按手机宽度设计，再向上适配：整体是**一张 sheet + 细分隔线分节**，而不是一摞
各自带边框的独立卡片——后者在 390px 下会变成 box-in-box 的视觉噪音，并把高度花在
内边距和卡片间隙上。正文 16px，摘要磁贴数字 20px。

逐小时曲线是**横向滑动条**（CSS `scroll-snap`，无脚本），不是纵向堆叠：八张曲线
竖排会让「时段证据」占掉整份文档的三分之二，把风险和免责说明挤到很下面。滑动条
左右出血到 sheet 边缘，露出下一张曲线的一角，提示可以横滑。

打印时滑动条改为**两栏网格**：纸上不能横滑，而一张被页面边缘截断的曲线比一张小
曲线更糟，所以打印会一次铺开全部曲线。

`total` / `peak` 这类「合计／峰值」磁贴独占整行：它是唯一一个「短语」而非纯数字的
值，因而也是唯一会折行的，而网格行高由该行最高的磁贴决定，会让旁边的数字磁贴被
撑出半空的框。

证据 ID（`evidence_id`）**不再**逐条印在建议、风险和每张曲线下面——那样一张卡片上
会有几十个 chip，反而淹没它们本该支撑的数据。ID 只在「证据」一节里集中出现，那也
是读者真正要核对引用时才会去的地方。

证据列表默认**折叠**，标题显示条数（如「证据（2 条）」）。它是卡片上最长、对
非审计读者信息量最低的一块（只有 ID 加一句 claim），折叠后仍一键可达，不会把
建议挤出首屏。折叠用 HTML 的 `<details>`，不是脚本，因此卡片保持无脚本；不支持
`<details>` 的浏览器会直接展开显示。展开后有一句说明 `evidence_id` 是什么、为
什么显示它。

「本 demo 未覆盖」的指标（`demo_gaps`）逐项分行列出，并说明「本 demo 没有接入
这些数据源」，避免读者把「未显示」误读为「不存在」。

卡片另外保留 Open-Meteo 署名与许可、空气质量为 CAMS 预报模型的说明、两套 AQI
标度不可直接比较的提示，以及「没有提供预警不等于没有预警」的说明。分享卡片时
应一并保留。

响应缺少必填字段、`status` 或 `intent` 不在枚举内、或 `needs_clarification`
没有追问问题时，脚本会报错退出并说明原因，而不是渲染成一张看起来合理的卡片。

卡片不引用任何外部资源（无脚本、无外链样式、无远程图片），因此可以离线打开并
作为单个文件分享；配色跟随查看者的浅色/深色偏好。默认写入临时文件并打印路径，
`--output` 指定路径，`--open` 用浏览器打开，`--check` 校验已有卡片文件。

横向滑动条只用 CSS `scroll-snap` 与原生滚动，没有脚本；打印时改为两栏网格。因此
「导出为图片」仍然只走浏览器打印（`--print` → 另存为 PDF），不需要截图库或无头
浏览器。

### 界面语言

卡片界面跟随**提问**的语言，而不是响应的语言：

```bash
python demo/weather_card.py response.json --query "今日天津天气" --output card.html
python demo/weather_card.py response.json --lang zh --output card.html
```

`--query` 传入用户的问题：含汉字的选中文界面，其余一律英文（默认）。
`--lang zh|en` 可强制指定，也接受 `zh-CN`、`en-US` 这类地区标签。

只有卡片自己的界面标签会被翻译。响应的正文（摘要、证据、建议、风险、不确定性）
按原样输出，保持它本来的语言——所以「中文提问 + 英文响应」是完全正常的情况：
中文界面、英文正文。渲染器**不会**根据响应正文判断语言，否则界面就会跟着响应
走，而不是跟着用户走。

### 导出为图片

```bash
python demo/weather_card.py response.json --brief brief.json --print --output card.html
```

`--print` 打开卡片并提示使用浏览器打印对话框（Ctrl/Cmd+P），选择**另存为
PDF** 即完成导出。这是受支持的导出路径，因为它让卡片保持无脚本：要生成 PNG
就得内联 canvas 脚本或引入无头浏览器，两者都会破坏「单文件、可离线打开」这一
性质。

打印样式强制白底深字（不跟随深色主题）、避免卡片跨页断开、并隐藏屏幕上的打印
提示，因此导出结果读起来是一份文档，而不是深色主题的截图。折叠的证据列表在
打印时**始终展开**：纸质文件上无法点击展开，若照搬屏幕上的折叠状态，导出的 PDF
会静默丢掉整段证据。

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

天气字段来自 `api.open-meteo.com/v1/forecast`：

| Open-Meteo hourly 字段 | Evidence `type` | 单位 |
| --- | --- | --- |
| `temperature_2m` | `temperature` | `°C` |
| `apparent_temperature` | `apparent_temperature` | `°C` |
| `precipitation_probability` | `precipitation_probability` | `%` |
| `precipitation` | `precipitation_amount` | `mm` |
| `wind_speed_10m` | `wind_speed` | `km/h` |
| `wind_gusts_10m` | `wind_gust` | `km/h` |

空气质量字段来自 `air-quality-api.open-meteo.com/v1/air-quality`：

| Open-Meteo hourly 字段 | Evidence `type` | 单位 |
| --- | --- | --- |
| `pm2_5` | `particulate_matter_2_5` | `μg/m³` |
| `pm10` | `particulate_matter_10` | `μg/m³` |
| `us_aqi` | `air_quality_index` | `USAQI` |
| `european_aqi` | `air_quality_index` | `EAQI` |

- 时间按地点时区返回，带 UTC 偏移；每个证据的有效期是 1 小时。
- `observed_at` 是本次请求时间，不是气象观测时间。
- 值为 `null` 的字段会跳过，不会补零或补默认值。
- `id` 形如 `ev-000-temperature_2m` 或 `ev-aq-000-pm2_5`，同一次输出内唯一。
- 两个端点各自返回逐小时数组，按时间戳合并；某个小时只在一边存在时，该小时
  在另一边缺席，不会错位对齐。
- 两个 AQI 字段共用 `air_quality_index` 类型，因此都带 `description` 说明标度，
  这是 [`references/evidence-contract.md`](../references/evidence-contract.md)
  对索引类证据的要求。两套标度数值不可直接比较。

## offline 与 live

| 模式 | 命令 | 数据来源 | 是否联网 |
| --- | --- | --- | --- |
| `live` | `python demo/weather_demo.py Tokyo` | Open-Meteo 公共 API（天气 + 空气质量） | 是 |
| `offline` | `python demo/weather_demo.py Tokyo --offline` | `demo/fixtures/` 固定数据 | 否 |

`offline` 只内置东京 fixture（`forecast-tokyo.json` 与
`air-quality-tokyo.json`），用于测试与演示，输出中的 `metadata.data_note`
会明确标记为合成数据。其他城市请使用 `live` 模式。

## 数据来源、署名与限制

- 天气数据由 [Open-Meteo](https://open-meteo.com/) 提供，数据许可为
  [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。展示数据时应保留
  `Weather data by Open-Meteo.com` 署名。
- 空气质量数据来自 Open-Meteo 的空气质量端点，底层为 CAMS 预报模型，同样适用
  CC BY 4.0，署名保留 `Air quality data by Open-Meteo.com (CAMS)`。它是**预报
  模型输出，不是地面监测站实测值**，可能与环境监测部门的站点数据存在偏差。
  判断是否适宜户外活动时，应以当地生态环境部门发布的 AQI 和官方公报为准。
- AQI 有多种标度。本 demo 同时给出 US AQI 与 European AQI，并在证据
  `description` 和 brief 的 `air_quality.index_scales` 中说明标度；两者数值
  不可直接比较，跨时段比较趋势时应优先看 PM2.5 / PM10 浓度。
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
6. 如果提供方有空气质量或花粉等额外维度，同样映射为证据类型并保留 `source`；
   索引类数据必须说明标度。

也可以参考 `weather_demo.py` 的 `geocode`、`fetch_forecast`、
`fetch_air_quality`、`build_evidence` 四个函数的边界，替换其中任意一层。
`build_evidence` 接受可选的 `air_quality` 载荷，把它合并到天气时间线上；
传 `None` 就只输出天气证据。

## 测试

```bash
python tests/test_demo.py
```

这是 L1 数据层测试：使用离线 fixture，覆盖地理编码、字段映射、单位、有效期、
ID 唯一性、信封结构、空气质量合并与 `--no-air-quality`，以及 CLI，不访问网络。
完整的 L1/L2/L3 分层说明见 [`tests/README.md`](../tests/README.md)。

## 生产化缺口

这份实现用于演示，不是生产级适配器。投入生产前至少需要补上：

- 同名地点的歧义处理（当前直接取地理编码的第一条结果）。
- 请求重试、退避、限流和配额监控。
- HTTP 错误、限流错误和上游数据异常的细分处理。
- 预报发布时间与有效期的独立校验（当前 `observed_at` 记录的是获取时间）。
- 缺失字段的业务处理（当前直接跳过，不推断默认值）。
- 数据缓存、审计和提供方切换时的兼容性测试。
- 空气质量数据源的可替换性（当前硬编码 Open-Meteo 的 CAMS 端点；官方监测站
  数据需要另接提供方）。

## 错误处理

脚本遇到 HTTP 错误、网络失败、地点不存在、响应缺少 `hourly` 数据、时间格式
错误或未知意图时，会向 stderr 输出一行错误并以非零状态退出，不打印 traceback。
