# Recommendation Rules

This file defines how to move from weather facts to actions. It is deliberately
not a weather encyclopedia. Thresholds, activity standards, and official
guidance belong to authoritative sources, not to the model's memory.

## The derivation chain

Use this chain for every recommendation:

> weather fact → effect on the user's activity → action → evidence reference →
> uncertainty or limitation

A recommendation that cannot be traced through the chain should be removed.

## Core rules

1. **Lead with the conclusion.** `summary` answers the user's question in one
   or two sentences before any detail.
2. **Every material recommendation cites evidence.** If it rests on a
   derivation, cite the facts that derivation used.
3. **Scope to the user's context.** Match the location, time window, activity,
   and transport mode the user stated. Do not generalize a commute answer to a
   full day without saying so.
4. **Be specific where the evidence is specific.** "带一把结实的伞，鞋子选防滑的"
   is better than "注意天气" when rain and wind are supported. Do not add
   precision the evidence lacks, such as exact temperatures implied by a range.
5. **Do not invent thresholds.** Do not declare a wind speed, temperature, or
   UV level "safe" or "dangerous" from an unsourced cutoff. Use supplied
   guidance, the alert's own severity, or the activity's official guidance. If
   none is available, describe the condition and point to an authoritative
   source instead of inventing a line.
6. **Separate fact from inference.** Say what the evidence reports, then say
   what you conclude from it. Do not present a derived statement as if the
   provider said it.
7. **No guarantees.** Avoid "肯定", "绝对不会", "百分之百", "保证". Probabilities
   remain probabilities.
8. **Do not convert probability into a binary.** A 70% chance justifies
   preparing for rain; it does not justify "一定会下雨".
9. **Prefer reversible actions.** When evidence is uncertain, recommend
   carrying, checking again, or preparing an alternative rather than cancelling
   plans.
10. **Prioritize by consequence.** Safety and essential preparation first,
    comfort second, optimization last. Return at most a handful of
    recommendations; a long list is not more useful.
11. **Answer only what was asked.** A fact lookup gets the fact and at most the
    action it directly implies. Do not append clothing, exercise, and travel
    advice to every answer.
12. **Do not infer consequences outside the evidence.** Weather evidence can
    support statements about conditions. It cannot by itself prove traffic
    congestion, transit delays, closures, or crowd levels.

## Mapping examples

These are derivation patterns, not universal safety thresholds.

| Weather fact | Plausible effect | Recommendation |
| --- | --- | --- |
| Precipitation forecast during the commute window | Walking and cycling may get wet | Carry rain protection; allow extra time; choose a covered route |
| Low temperature plus outdoor activity | Greater heat loss, especially when stationary | Use layers; adjust for activity intensity; cover extremities |
| Strong wind or gusts plus exposed activity | Balance and comfort affected; loose items blow away | Choose a sheltered route or postpone; secure loose items; avoid exposed edges |
| High UV plus midday outdoor activity | Sunburn risk rises with exposure | Shade, hat, sunscreen, and timing adjustments |
| Key weather element missing | The effect cannot be judged | State the missing element; do not give a definitive conclusion |
| Official severe-weather alert | Conditions may be hazardous | Follow the alert's guidance; avoid the affected activity; check official updates |
| Conflicting sources | The true condition is uncertain | Disclose both; recommend rechecking before acting |

## Probability and uncertainty language

- Report the number when it was supplied: "降雨概率 70%".
- Pair it with a qualitative gloss that does not contradict the number:
  "较有可能下雨", "存在明显降雨可能". Do not use "肯定" or "绝不会".
- Distinguish "观测" (observed), "预报" (forecast), and "概率" (probability).
- When evidence is stale, say how old it is and that conditions may have
  changed.
- When coverage is partial, name the covered and uncovered periods.

## Multi-day and multi-segment answers

- Group recommendations by day or segment when the weather differs.
- Keep the order chronological.
- State forecast-horizon uncertainty once, clearly, instead of repeating it in
  every bullet.
- Do not fill uncovered days with typical seasonal conditions.
- For each day, include only recommendations that day's evidence supports.

## Recommendation quality checklist

Before returning, check each recommendation:

- [ ] Is there a weather fact behind it? Is that fact cited?
- [ ] Is it scoped to the user's place, time, and activity?
- [ ] Is it an action the user can actually take?
- [ ] Does it avoid guarantees and invented thresholds?
- [ ] Does it avoid consequences the evidence cannot support?
- [ ] Is it something the user asked for, or a direct implication of it?

## Good and bad examples

**Input fact:** 07:00–09:00 precipitation probability 70%, wind 18 km/h.

Good:

- "通勤时带伞或雨衣。" (cites the rain evidence)
- "比平时早出门 10–15 分钟。" (cites the rain evidence; framed as preparation)

Bad:

- "今天一定会下大雨，地铁会延误。" (certainty + unsupported transit claim)
- "建议取消上班。" (disproportionate and unsupported)
- "记得涂防晒、穿羽绒服。" (unrelated to the evidence and the question)

**Input fact:** Temperature range 2–9 °C, apparent minimum −3 °C, outdoor
afternoon planned.

Good:

- "分层穿：贴身排汗层 + 保暖层 + 防风外层，下午活动时方便增减。"
- "手部和耳部保暖，风大时体感更低。"

Bad:

- "穿羽绒服就行。" (ignores activity and range)
- "零下 3 度会冻伤，不要出门。" (invented medical threshold)

**Input fact:** Evidence covers Saturday and Sunday only; trip runs Friday to
Monday.

Good:

- "周六、周日有预报覆盖；周五和周一没有可用数据，建议出发前复核。"

Bad:

- "四天都晴朗。" (fabricates coverage)

## When to give fewer recommendations

Return fewer, or an empty list, when:

- the evidence does not support any action;
- the only honest answer is that data is missing;
- the user asked a pure fact question and no action follows directly;
- recommendations would repeat each other.

An empty `recommendations` array is valid for `needs_clarification` and
`insufficient_evidence`. For `answered`, at least one actionable
recommendation is required.
