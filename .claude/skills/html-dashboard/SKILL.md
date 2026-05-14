---
name: html-dashboard
description: >
  Dashboard generator skill for Capital Slice. Run this skill to generate a visual HTML
  dashboard from the latest saturday_scored.json positioning data. Trigger when the user
  says "generate the dashboard", "make a visual", "show me the charts", "create the HTML
  report", "build the dashboard", or "visualize the scores". Also runs automatically as
  the final step of the capital-slice-positioning skill workflow. Produces a self-contained
  saturday_dashboard.html file with interactive Chart.js charts.
---

# Capital Slice — HTML Dashboard Skill

Generate a polished, interactive HTML dashboard from the latest Saturday positioning scores.

## When to Run This Skill

- Automatically, as the final step after capital-slice-positioning completes
- On demand when the user asks for a visual summary or HTML report

## Step 1 — Locate the scored JSON file

The input file is always at:

```
.claude/skills/capital-slice-positioning/scripts/saturday_scored.json
```

Confirm it exists before proceeding.

## Step 2 — Run the dashboard generator

```bash
python .claude/skills/html-dashboard/scripts/generate_dashboard.py .claude/skills/capital-slice-positioning/scripts/saturday_scored.json
```

The script accepts the JSON file path as its only argument and writes `saturday_dashboard.html`
to the same directory as the input file.

## Step 3 — Confirm output to the user

After the script completes, confirm:

> "Dashboard generated: `.claude/skills/capital-slice-positioning/scripts/saturday_dashboard.html`
> Open this file in any browser for an interactive visual summary of this Saturday's positioning."

If the script fails, show the error output to the user and note that the text memo from
the positioning skill is still the authoritative recommendation.
