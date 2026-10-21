# Intent Catalog

Six intents cover first-release weather consultation. Choose one primary intent
per response. A single query may contain a lookup and an advice request; select
the intent that matches the user's main decision.

## Classification order

1. An explicit activity that weather affects → `outdoor_activity`,
   `commute_advice`, or `travel_planning`, depending on the activity and time
   frame.
2. An explicit preparation question (what to wear, what to bring) →
   `clothing_advice` or `travel_planning`.
3. A pure fact question (will it rain, how hot, is there a warning) →
   `weather_lookup`.
4. Multiple days or a trip with preparation → `travel_planning`.
5. Purpose unclear and the answer would change with purpose →
   `general_weather_advice`, and ask one question only if it materially helps.

Do not force a specific intent when the query is genuinely generic. A wrong
narrow intent produces advice the user did not ask for.

## Summary

| Intent ID | Example query | Focus |
| --- | --- | --- |
| `weather_lookup` | 明天上海会下雨吗？ | Report the fact; do not expand into unrelated advice |
| `clothing_advice` | 明天穿什么合适？ | Temperature, apparent temperature, precipitation, wind, activity |
| `commute_advice` | 明早上班要带伞吗？ | Commute-window precipitation, wind, visibility, alerts |
| `outdoor_activity` | 下午适合户外跑步吗？ | Precipitation, wind and gusts, temperature, UV, visibility, alerts |
| `travel_planning` | 周末去杭州需要准备什么？ | Multi-day weather, itinerary fit, forecast uncertainty |
| `general_weather_advice` | 这种天气需要注意什么？ | Infer the purpose from context; clarify only when necessary |

## Required context by intent

| Intent | Location | Target time | Activity / destination |
| --- | --- | --- | --- |
| `weather_lookup` | Required | Required (date or window) | Not needed |
| `clothing_advice` | Required | Required (at least a day) | Optional; ask only if it changes the answer |
| `commute_advice` | Required | Required (commute window) | Optional (mode of transport) |
| `outdoor_activity` | Required | Required (window) | Required (what activity) |
| `travel_planning` | Required (destination) | Required (date range) | Optional (itinerary, transport) |
| `general_weather_advice` | Required | Required | Often needed to interpret the question |

"Required" means required before a confident answer, not required before any
answer. If host context already supplies the value, never ask for it again.

---

## weather_lookup

### Triggers

- "明天会下雨吗？" "现在多少度？" "有没有大风预警？" "这周末天气怎么样？"
- Fact-seeking phrasing with no requested action.

### Exclude when

- The user asks what to do about the weather → use an advice intent.
- The user asks about multiple days and preparation → `travel_planning`.

### Relevant evidence

- The specific element asked about (precipitation, temperature, wind, alert,
  visibility, weather description).
- Validity window covering the requested time.

### Behavior

- Answer the fact directly and attach evidence. Report a probability as a
  probability, not as a certainty.
- Include only the action the fact directly implies (for example, carry rain
  protection when precipitation is forecast for the requested window). Do not
  volunteer clothing, activity, or travel advice.
- If the requested time is only partly covered, state which part is covered.
- If no evidence covers the request, return `insufficient_evidence`.
- If an official alert is supplied, mention it even if the user only asked
  about rain.

### Typical output

`status: answered`, one or two recommendations scoped to the requested fact,
`risks` only when the evidence implies one.

### Failure example

User asks "明天上海会下雨吗", evidence says 70% probability. Answering "会下雨，
记得穿防水鞋、带雨衣、别骑车" invents certainty and expands a lookup into
unsolicited advice.

---

## clothing_advice

### Triggers

- "穿什么" "需要外套吗" "给孩子怎么穿" "要不要穿羽绒服".
- Any dressing decision tied to expected conditions.

### Exclude when

- The user asks about gear for a specific activity → `outdoor_activity`.
- The user asks what to pack for a trip → `travel_planning`.

### Relevant evidence

- Minimum and maximum temperature for the relevant period.
- Apparent temperature, wind, humidity when supplied.
- Precipitation and UV when they affect clothing choice.
- Whether the user will be indoors or outdoors, if stated.

### Behavior

- Recommend layers and adjust for the stated activity and time outdoors.
- Base advice on the temperature range that matches the user's time window. A
  single morning reading does not describe the whole day.
- Ask about indoor/outdoor context only when it changes the recommendation
  materially (for example, a full day outdoors versus a short commute).
- Do not infer personal physiology, medical conditions, or preferences that the
  user did not state.
- When only part of the day is covered, say so and avoid absolute dress codes.

### Typical output

`status: answered`, recommendations describing layers, outerwear, and
accessories tied to temperature and precipitation evidence.

### Failure example

One 5 °C morning observation, no daytime range, produces "穿羽绒服就够了" for an
outdoor afternoon. The evidence does not cover the afternoon.

---

## commute_advice

### Triggers

- "明早上班要带伞吗" "骑车通勤安全吗" "下班会不会淋雨".
- Questions about a recurring or specific commute window.

### Exclude when

- The trip is long-distance or multi-day → `travel_planning`.
- The user asks about an outdoor workout → `outdoor_activity`.

### Required context

- Location.
- Target commute time, or an unambiguous date/time context.

### Relevant evidence

- Precipitation probability and amount during the commute window.
- Wind speed and gusts when available.
- Visibility, temperature, and official alerts when available.

### Behavior

- Scope the answer to the commute window, not the whole day.
- Recommend rain protection only when precipitation evidence supports it, or
  state the uncertainty explicitly.
- Do not infer traffic congestion, delays, or transit disruptions from weather
  evidence alone. Weather can make travel slower; only evidence about
  conditions supports a claim about conditions.
- If the location is missing and cannot be resolved from context, ask.
- If the time is ambiguous and materially changes the answer, clarify. A user
  who says "上班路上" has supplied a window; do not re-ask.

### Typical output

`status: answered`, recommendations about rain protection, footwear, wind
exposure, and extra time, each citing evidence.

### Failure example

"降雨概率 70%，地铁一定晚点，建议请假" — invents a transit consequence and an
extreme action unsupported by the evidence.

---

## outdoor_activity

### Triggers

- "适合跑步吗" "能去海边吗" "下午可以骑行吗" "带孩子去公园合适吗".
- Any activity whose comfort or safety depends on weather.

### Exclude when

- The question is only about what to wear → `clothing_advice`.
- The question is about a multi-day trip → `travel_planning`.

### Required context

- Location, activity, and time window. Activity is required because wind,
  lightning, heat, and water conditions affect activities differently.

### Relevant evidence

- Precipitation, thunderstorm indicators, and official alerts.
- Wind speed and gusts for exposed or elevated activities.
- Temperature and apparent temperature; UV for sun exposure.
- Visibility, humidity, air quality when supplied.

### Behavior

- Judge the activity against the supplied evidence, not against a generic
  comfort standard.
- If a hazard-relevant element is missing (for example, wind for a coastal
  activity), do not declare the activity safe. State the gap and return
  `insufficient_evidence` when the gap prevents a useful answer.
- If the activity is missing and different activities would get different
  answers, ask which activity.
- Recommend postponement or an alternative only when the evidence supports the
  risk; otherwise present the trade-off and suggest checking official sources.
- Never state that an activity is safe.

### Typical output

`status: answered` or `insufficient_evidence`; risks carry severity and
evidence IDs; recommendations name concrete alternatives or preparations.

### Failure example

"没有收到预警，所以海边骑车没问题" — absence of a supplied alert is not evidence
of safety, and wind/wave data is missing.

---

## travel_planning

### Triggers

- "周末去杭州要带什么" "下周去广州出差怎么安排" "假期去云南合适吗".
- Multi-day or destination-level preparation.

### Exclude when

- The user asks about a single commute or single activity → the narrower intent.
- The user asks only for a forecast fact → `weather_lookup`.

### Required context

- Destination.
- Date range or unambiguous travel window.

### Relevant evidence

- Forecasts for each day or sub-window, with validity ranges.
- Alerts.
- Temperature range, precipitation, wind, and UV across the trip.

### Behavior

- Organize advice by day or by segment when the evidence differs across days.
- Cover only the days the evidence covers. Say which days are uncovered.
- Forecast uncertainty grows with lead time. Describe this in plain language
  rather than inventing a confidence score.
- Separate essentials (documents, medication, weather protection) from
  optional comfort items. Do not turn the answer into a generic packing list.
- Do not assume an itinerary. If the user's plans change the advice, ask or
  state the assumption.

### Typical output

`status: answered`, day-by-day recommendations, an uncertainty note about
forecast horizon, and risks for any severe day.

### Failure example

Four-day trip, evidence covers two days, and the answer promises "全程晴朗"
for all four days.

---

## general_weather_advice

### Triggers

- "这种天气需要注意什么" "今天天气怎么样" "出门有什么要注意的".
- Weather is relevant but the purpose is not explicit.

### Exclude when

- The query clearly names a specific activity, commute, trip, or clothing
  decision → use that intent.

### Behavior

- Use the supplied context (location, time, activity, prior conversation) to
  infer the purpose.
- If purpose is unclear and different purposes would produce materially
  different advice, ask one short question.
- If context is rich enough, answer with evidence-linked general precautions
  and state the assumption you used.
- Do not use this intent to avoid clarifying when clarification is genuinely
  needed, and do not ask when context already answers the question.

### Typical output

`status: answered` or `needs_clarification`, short summary, a small set of
precautions tied to the most consequential evidence.

### Failure example

Context says the user is hiking with children, but the answer asks "你是要出门
吗？" — the context already answered it.

---

## Cross-intent rules

- Ask at most one clarification question per turn. Ask the question whose
  answer changes the recommendation most.
- Never ask for optional information the user did not imply needing.
- If the host supplies location/time/activity, treat it as known. Re-asking is
  a failure.
- If the user changes intent mid-conversation, classify again from the latest
  message and retained context.
- When two intents are plausible, choose the one matching the user's decision.
  Mention the narrower reading in the summary if it matters.
