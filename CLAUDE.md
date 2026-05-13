# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a 4-week "build-along" educational project to develop a **Claude Skill** that automates a real-world business decision for **Capital Slice** — a two-truck premium pizza operation in Washington DC. The developer's role is a data analyst building an automated decision support system.

**Core deliverable:** Every Thursday by 11:59pm ET, the skill must produce a 2-page decision memo recommending optimal positioning for 2 food trucks across 10 permitted DC locations for the upcoming Saturday (morning and afternoon windows).

## The Business Problem

Each truck can be placed at one of 10 locations and can relocate once mid-day (morning: 7am–12pm → afternoon: 2pm–8pm). The optimization accounts for:

- **Weather** — outdoor locations (National Mall, Georgetown Waterfront) suffer in bad weather; indoor venues (Capital One Arena, Convention Center) improve
- **Events** — sports games (Nationals/Wizards/Caps/DC United), conventions, festivals, and farmers markets drive location value
- **Competition** — trucks announce positions via social media; avoid splitting pizza demand at the same location

Constraints: trucks cannot share a location, relocation takes 45–60 minutes of lost revenue, and the memo must be readable by non-technical partners.

## Key Reference Documents

All business context lives in `briefing-docs/`:

| File | Purpose |
|------|---------|
| `Capital-Slice-business-challenge-briefing.md` | Full business rules, decision factors, data sources, output format |
| `Capital Slice Site Analysis.md` | Per-location strengths, weaknesses, and optimal conditions for all 10 sites |
| `dc-locations-map.html` | Interactive map of all 10 permitted locations |

## Skill Architecture

The Claude Skill to build must:

1. **Ingest** weekly data — weather forecast, sports/event schedules, competitor social media positions
2. **Score** each of the 10 locations given current conditions
3. **Optimize** truck placement across 4 slots (Truck A morning/afternoon, Truck B morning/afternoon) with no-overlap constraint
4. **Generate** a ≤2-page decision memo (plain-language, no required data background)

## Data Sources

| Data Need | Sources |
|-----------|---------|
| Weather | NOAA/National Weather Service API, OpenWeather |
| Sports schedules | ESPN API, MLB/NBA/NHL/WNBA APIs, team websites |
| Events | Eventbrite API, washington.org, DC.gov calendar |
| Competitor positions | Instagram, Twitter/X, food truck aggregator sites |
| Historical performance | Internal tracking (built up over time) |

## Series Schedule

- **Week 1:** Build the initial skill (analysis + memo generation)
- **Week 2:** Test, evaluate, and improve the skill
- **Week 3:** Source control and documentation
- **Week 4:** Distribution and maintenance

## Claude Skills Setup

Enable "Code Execution and file creation" in Claude Desktop Settings. The `skill-creator` skill (by Anthropic) is required for Week 1 — enable it in Skills settings. Point Claude Code at this project folder as the working directory.
