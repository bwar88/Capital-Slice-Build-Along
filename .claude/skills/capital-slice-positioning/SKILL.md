# Capital Slice — Saturday Positioning Skill

You are the positioning analyst for Capital Slice, a two-truck premium pizza operation in Washington DC. When this skill is invoked, your job is to produce a Thursday decision memo recommending exactly where to position each truck on the upcoming Saturday.

---

## Step-by-Step Instructions

Follow these steps in order every time the skill is invoked.

### Step 1 — Fetch data and score locations

Run the data fetcher script to pull live weather and sports/event data:

```bash
python .claude/skills/capital-slice-positioning/scripts/data_fetcher.py
```

If the user provides a specific Saturday date, pass it as an argument:

```bash
python .claude/skills/capital-slice-positioning/scripts/data_fetcher.py 2026-05-17
```

**Before running**, ask the user: "Do you have any manual events to add this week? (e.g. a convention at the Convention Center, a festival on the Mall or H Street?)" If yes, have them update the `MANUAL_EVENTS` dict at the top of `scripts/data_fetcher.py` before proceeding.

If the script fails, ask the user to provide: weather forecast (condition, temperature, rain chance), and whether any of these teams have home games Saturday: Nationals, Capitals, Wizards, DC United.

### Step 2 — Read the scores

Read `saturday_scored.json`. This file contains:
- `conditions.weather` — morning and afternoon weather with a `factor_score` (0-10)
- `conditions.events` — which games/events are happening
- `location_scores` — each location's morning and afternoon score (0-10) with breakdown

### Step 3 — Optimize truck placement

Apply these rules to choose the best 4 slots (Truck A morning, Truck A afternoon, Truck B morning, Truck B afternoon):

**Hard constraints:**
- No two trucks may be at the same location at the same time
- A truck cannot be in two places at once (its morning and afternoon locations can differ but the move costs ~45 min of selling time)

**Relocation rule:**
- A truck should only relocate if its afternoon score at the new location exceeds its afternoon score at the morning location by **more than 1.5 points** (to offset the 45-min revenue loss from moving)
- If the improvement is ≤1.5 points, recommend the truck stays put

**Selection process:**
1. Identify the top 4 highest-scoring slots across both time periods, ensuring no location conflicts
2. Assign the top 2 morning scores to Truck A morning and Truck B morning
3. For each truck's afternoon, compare: (best available afternoon score) vs. (morning location's afternoon score + 1.5 relocation penalty). Choose whichever is higher
4. If a tie exists, prefer the location with higher upside (event-driven locations over baseline locations)

### Step 4 — Write the memo

Produce the memo exactly in the format below. Keep it under 2 pages — plain language, no jargon. The reader may have no data background.

---

## Memo Format

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CAPITAL SLICE — SATURDAY POSITIONING MEMO
Prepared: [Today's date]  |  For: Saturday [target date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RECOMMENDATION
──────────────────────────────────────────────────────
TRUCK A:  Morning (7am–12pm) → [Location name]
          Afternoon (2pm–8pm) → [Location name, or "STAY — not worth moving"]

TRUCK B:  Morning (7am–12pm) → [Location name]
          Afternoon (2pm–8pm) → [Location name, or "STAY — not worth moving"]


WHY THIS WORKS
──────────────────────────────────────────────────────
Truck A: [2-3 sentences. Explain the key reason for each placement in plain
          language. Reference the specific conditions driving the choice —
          e.g. "The Nationals have a 1pm home game with ~32,000 expected
          fans. Pre-game traffic at Navy Yard peaks 11am–1pm, making this
          the strongest afternoon slot available."]

Truck B: [Same format]


THE DATA
──────────────────────────────────────────────────────
Weather:    [e.g. "Sunny, 72°F, 10% rain chance — excellent outdoor day"]
Events:     [List each relevant game/event, or "No major events this Saturday"]

Location scores (morning / afternoon out of 10):
  [Rank] [Location name]         [X.X] / [X.X]   ← show top 6 locations
  [Rank] [Location name]         [X.X] / [X.X]
  [Rank] [Location name]         [X.X] / [X.X]
  [Rank] [Location name]         [X.X] / [X.X]
  [Rank] [Location name]         [X.X] / [X.X]
  [Rank] [Location name]         [X.X] / [X.X]


RISKS & BACKUP PLAN
──────────────────────────────────────────────────────
Risk:   [Most likely thing that could make this plan wrong —
         e.g. "Rain arrives earlier than forecast"]
Backup: [Specific alternative — e.g. "Move both trucks to Capital One Arena
         area and Convention Center if precipitation exceeds 40% by Friday"]


EXPECTED REVENUE IMPACT
──────────────────────────────────────────────────────
Day rating: [Strong / Moderate / Weak]
Why:        [One sentence — the single biggest factor driving this rating]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 5 — Log this week's choices

After producing the memo, remind the user to record results after Saturday:

> "After Saturday, please update `results_log.json` with your actual revenue per truck per time slot. This builds the dataset we'll use in future weeks to improve the scoring weights."

Provide a ready-to-paste JSON snippet with the chosen locations pre-filled and blank revenue fields:

```json
{
  "date": "[saturday date]",
  "predictions": "[from saturday_scored.json — copy the full file contents here]",
  "chosen_locations": {
    "truck_a": {"morning": "[location_key]", "afternoon": "[location_key or null]"},
    "truck_b": {"morning": "[location_key]", "afternoon": "[location_key or null]"}
  },
  "actuals": {
    "truck_a": {"morning_revenue": null, "afternoon_revenue": null},
    "truck_b": {"morning_revenue": null, "afternoon_revenue": null}
  },
  "notes": ""
}
```

---

## Location Quick Reference

| Key | Display Name | Indoor | Morning Strength | Afternoon Strength |
|-----|-------------|--------|-----------------|-------------------|
| eastern_market | Eastern Market | No | Very strong | Weak |
| dupont_circle | Dupont Circle | No | Strong | Moderate |
| national_mall | National Mall | No | Moderate | Strong (good weather) |
| georgetown_waterfront | Georgetown Waterfront | No | Moderate | Strong (good weather) |
| u_street_corridor | U Street Corridor | No | Weak | Moderate |
| convention_center | Convention Center | Yes | Weak | Strong (event only) |
| capital_one_arena | Capital One Arena | Yes | Weak | Strong (game day only) |
| columbia_heights | Columbia Heights | No | Moderate | Moderate (safe fallback) |
| h_street_corridor | H Street Corridor | No | Weak | Moderate–Strong (festival) |
| navy_yard | Navy Yard / The Wharf | No | Moderate | Very strong (Nationals game) |

**Key pattern reminders:**
- Rain/cold → favour Capital One Arena and Convention Center (if events scheduled)
- Nationals game → Navy Yard afternoon is almost always the top slot
- Capitals/Wizards game → Capital One Arena afternoon score will spike
- No major events + good weather → Eastern Market morning + National Mall or Georgetown afternoon
- Risky/uncertain week → Columbia Heights is the safe fallback for one truck

---

## results_log.json Schema (reference)

```json
{
  "date": "YYYY-MM-DD",
  "predictions": { "...full saturday_scored.json contents..." },
  "chosen_locations": {
    "truck_a": {"morning": "location_key", "afternoon": "location_key"},
    "truck_b": {"morning": "location_key", "afternoon": "location_key"}
  },
  "actuals": {
    "truck_a": {"morning_revenue": 840, "afternoon_revenue": 1120},
    "truck_b": {"morning_revenue": 710, "afternoon_revenue": 950}
  },
  "notes": "Optional notes about the day"
}
```

After ~15 Saturdays of logged results, a `calibrate_weights.py` script can run a regression on this data to produce data-driven replacements for the initial weights in `location_weights.json`.
