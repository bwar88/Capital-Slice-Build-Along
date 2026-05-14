"""
Capital Slice — Data Fetcher
Fetches weather and sports/event data for a target Saturday, scores all 10
locations using location_weights.json, and writes saturday_scored.json.

Usage:
    python data_fetcher.py                  # scores next Saturday
    python data_fetcher.py 2026-05-17       # scores a specific date

Manual events (convention bookings, festivals not auto-detected) can be added
directly to the MANUAL_EVENTS dict below before running.
"""

import json
import sys
import os
from datetime import date, datetime, timedelta
import requests

# ---------------------------------------------------------------------------
# Manual events — fill these in before running each Thursday
# Set to None if no event, or a string description + estimated attendance
# ---------------------------------------------------------------------------
# TODO: calibrate_weights.py
# After 15+ Saturdays of logged results, a calibrate_weights.py script should:
#   1. Read all entries from results_log.json
#   2. Run regression on actuals vs. predictions
#   3. Produce updated location_weights.json with data-driven coefficients
# This will improve scoring accuracy over time.
MANUAL_EVENTS = {
    "convention_center_event": None,
    # Example: "convention_center_event": {"description": "AWS Summit", "attendance_est": 10000},
    "national_mall_event": None,
    # Example: "national_mall_event": {"description": "National Cherry Blossom Festival", "attendance_est": 50000},
    "h_street_event": None,
    # Example: "h_street_event": {"description": "H Street Festival", "attendance_est": 4000},
    "u_street_event": None,
}

# DC centre coordinates for NOAA weather lookup
DC_LAT = 38.8951
DC_LON = -77.0364

WEIGHTS_FILE = os.path.join(os.path.dirname(__file__), "location_weights.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "saturday_scored.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def next_saturday(from_date: date = None) -> date:
    d = from_date or date.today()
    days_ahead = 5 - d.weekday()  # Saturday = weekday 5
    if days_ahead <= 0:
        days_ahead += 7
    return d + timedelta(days=days_ahead)


def weather_factor(avg_temp_f: float, max_precip_pct: float, avg_wind_mph: float) -> float:
    """Return a 0-10 score where 10 = perfect outdoor weather."""
    score = 10.0

    # Precipitation penalty
    if max_precip_pct >= 70:
        score -= 5.0
    elif max_precip_pct >= 50:
        score -= 3.5
    elif max_precip_pct >= 30:
        score -= 1.5
    elif max_precip_pct >= 15:
        score -= 0.5

    # Temperature penalty
    if avg_temp_f < 32:
        score -= 4.0
    elif avg_temp_f < 45:
        score -= 2.5
    elif avg_temp_f < 55:
        score -= 1.0
    elif avg_temp_f > 95:
        score -= 3.5
    elif avg_temp_f > 85:
        score -= 2.0

    # Wind penalty
    if avg_wind_mph > 25:
        score -= 2.0
    elif avg_wind_mph > 18:
        score -= 1.0
    elif avg_wind_mph > 12:
        score -= 0.5

    return round(max(0.0, min(10.0, score)), 2)


# ---------------------------------------------------------------------------
# Weather — NOAA api.weather.gov (no API key required)
# ---------------------------------------------------------------------------

def fetch_weather(target_date: date) -> dict:
    print(f"  Fetching weather for {target_date}...")
    headers = {"User-Agent": "CapitalSliceSkill/1.0 (contact: operator@capitalslice.com)"}

    # Step 1: resolve gridpoint
    points_url = f"https://api.weather.gov/points/{DC_LAT},{DC_LON}"
    r = requests.get(points_url, headers=headers, timeout=10)
    r.raise_for_status()
    forecast_hourly_url = r.json()["properties"]["forecastHourly"]

    # Step 2: fetch hourly forecast
    r2 = requests.get(forecast_hourly_url, headers=headers, timeout=10)
    r2.raise_for_status()
    periods = r2.json()["properties"]["periods"]

    target_str = target_date.isoformat()
    morning_periods = []   # 7am-12pm
    afternoon_periods = [] # 2pm-8pm

    for p in periods:
        start = p["startTime"][:16]  # "2026-05-17T07:00"
        if not start.startswith(target_str):
            continue
        hour = int(start[11:13])
        if 7 <= hour < 12:
            morning_periods.append(p)
        elif 14 <= hour <= 20:
            afternoon_periods.append(p)

    def summarise(periods_list):
        if not periods_list:
            return {"temp_f": 65, "precip_pct": 0, "wind_mph": 5, "condition": "Unknown", "factor_score": 7.0}
        temps = [p["temperature"] for p in periods_list]
        precips = [p.get("probabilityOfPrecipitation", {}).get("value") or 0 for p in periods_list]
        winds = []
        for p in periods_list:
            w = p.get("windSpeed", "0 mph")
            try:
                winds.append(int(str(w).split()[0]))
            except (ValueError, IndexError):
                winds.append(0)
        avg_temp = round(sum(temps) / len(temps), 1)
        max_precip = max(precips)
        avg_wind = round(sum(winds) / len(winds), 1)
        condition = periods_list[len(periods_list) // 2].get("shortForecast", "")
        return {
            "temp_f": avg_temp,
            "precip_pct": max_precip,
            "wind_mph": avg_wind,
            "condition": condition,
            "factor_score": weather_factor(avg_temp, max_precip, avg_wind),
        }

    morning = summarise(morning_periods)
    afternoon = summarise(afternoon_periods)

    if not morning_periods:
        print("    Warning: no morning forecast periods found — using defaults")
    if not afternoon_periods:
        print("    Warning: no afternoon forecast periods found — using defaults")

    return {"morning": morning, "afternoon": afternoon}


# ---------------------------------------------------------------------------
# Sports — free official APIs
# ---------------------------------------------------------------------------

def fetch_nationals(target_date: date) -> dict:
    """MLB Stats API — Washington Nationals team ID 120."""
    print("  Fetching Nationals schedule...")
    url = f"https://statsapi.mlb.com/api/v1/schedule?teamId=120&date={target_date.isoformat()}&sportId=1"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        dates = r.json().get("dates", [])
        for d in dates:
            for game in d.get("games", []):
                if game.get("teams", {}).get("home", {}).get("team", {}).get("id") == 120:
                    start = game.get("gameDate", "")[:16]
                    return {
                        "playing": True,
                        "home": True,
                        "start_time": start[11:16] if len(start) > 10 else "TBD",
                        "attendance_est": 32000,
                        "game_id": game.get("gamePk"),
                    }
        return {"playing": False}
    except Exception as e:
        print(f"    Warning: Nationals API error — {e}")
        return {"playing": False, "error": str(e)}


def fetch_capitals(target_date: date) -> dict:
    """NHL API — Washington Capitals."""
    print("  Fetching Capitals schedule...")
    url = f"https://api-web.nhle.com/v1/club-schedule/WSH/week/{target_date.isoformat()}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        games = r.json().get("games", [])
        for game in games:
            game_date = game.get("gameDate", "")[:10]
            if game_date == target_date.isoformat():
                home_team = game.get("homeTeam", {}).get("abbrev", "")
                if home_team == "WSH":
                    start_utc = game.get("startTimeUTC", "")
                    return {
                        "playing": True,
                        "home": True,
                        "start_time": start_utc[11:16] + " UTC" if len(start_utc) > 10 else "TBD",
                        "attendance_est": 18000,
                    }
        return {"playing": False}
    except Exception as e:
        print(f"    Warning: Capitals API error — {e}")
        return {"playing": False, "error": str(e)}


def fetch_wizards(target_date: date) -> dict:
    """ESPN unofficial API — Washington Wizards (team ID 27)."""
    print("  Fetching Wizards schedule...")
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/27/schedule"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        events = r.json().get("events", [])
        target_str = target_date.isoformat()
        for event in events:
            event_date = event.get("date", "")[:10]
            if event_date == target_str:
                competitions = event.get("competitions", [{}])
                comp = competitions[0] if competitions else {}
                home = any(
                    c.get("homeAway") == "home" and "Washington" in c.get("team", {}).get("displayName", "")
                    for c in comp.get("competitors", [])
                )
                if home:
                    return {
                        "playing": True,
                        "home": True,
                        "start_time": event.get("date", "")[:16],
                        "attendance_est": 18000,
                    }
        return {"playing": False}
    except Exception as e:
        print(f"    Warning: Wizards API error — {e}")
        return {"playing": False, "error": str(e)}


def fetch_dc_united(target_date: date) -> dict:
    """ESPN unofficial API — DC United (team ID 193)."""
    print("  Fetching DC United schedule...")
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/teams/193/schedule"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        events = r.json().get("events", [])
        target_str = target_date.isoformat()
        for event in events:
            event_date = event.get("date", "")[:10]
            if event_date == target_str:
                competitions = event.get("competitions", [{}])
                comp = competitions[0] if competitions else {}
                home = any(
                    c.get("homeAway") == "home"
                    for c in comp.get("competitors", [])
                )
                if home:
                    return {
                        "playing": True,
                        "home": True,
                        "start_time": event.get("date", "")[:16],
                        "attendance_est": 20000,
                    }
        return {"playing": False}
    except Exception as e:
        print(f"    Warning: DC United API error — {e}")
        return {"playing": False, "error": str(e)}


def fetch_mystics(target_date: date) -> dict:
    """ESPN unofficial API — Washington Mystics."""
    print("  Fetching Mystics schedule...")
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/wnba/teams/wsh/schedule"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        events = r.json().get("events", [])
        target_str = target_date.isoformat()
        for event in events:
            event_date = event.get("date", "")[:10]
            if event_date == target_str:
                competitions = event.get("competitions", [{}])
                comp = competitions[0] if competitions else {}
                home = any(
                    c.get("homeAway") == "home" and "Washington" in c.get("team", {}).get("displayName", "")
                    for c in comp.get("competitors", [])
                )
                if home:
                    return {
                        "playing": True,
                        "home": True,
                        "start_time": event.get("date", "")[:16],
                        "attendance_est": 10000,
                    }
        return {"playing": False}
    except Exception as e:
        print(f"    Warning: Mystics API error — {e}")
        return {"playing": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_location(location_key: str, loc: dict, weather: dict, events: dict) -> dict:
    """
    Compute morning and afternoon scores for one location.
    Returns {"morning": float, "afternoon": float, "score_components": dict}
    """
    w = loc["weights"]
    components = {}

    def score_slot(slot: str) -> float:
        base = loc["base_scores"][slot]
        components[slot] = {"base": base}

        # Weather adjustment
        wf = weather[slot]["factor_score"]
        if loc["indoor"]:
            # Indoor locations are nearly weather-neutral, but bad weather gives a small boost
            bad_weather = 10.0 - wf  # 0 = perfect weather, 10 = terrible weather
            weather_adj = bad_weather * w["bad_weather_indoor_bonus"]
        else:
            weather_adj = (wf - 5.0) * w["weather_sensitivity"]
        components[slot]["weather_adj"] = round(weather_adj, 3)

        # Event adjustment — only boost the slot closest to the event start time.
        # morning slot = events starting before 14:00 local
        # afternoon slot = events starting 14:00 or later (or unknown time)
        event_adj = 0.0
        for event_key in loc.get("event_keys", []):
            event_data = events.get(event_key)
            if not event_data or event_data.get("playing") is False:
                continue
            if isinstance(event_data, dict) and "attendance_est" in event_data:
                # Determine which slot this event falls in
                start = event_data.get("start_time", "")
                try:
                    # start_time may be "HH:MM", "HH:MM UTC", or a full ISO string
                    hour = int(str(start).replace(" UTC", "")[:5].split(":")[0])
                    # For UTC times, approximate ET offset (-4 in summer, -5 in winter)
                    if "UTC" in str(start):
                        hour = (hour - 4) % 24
                    event_slot = "morning" if hour < 14 else "afternoon"
                except (ValueError, IndexError):
                    event_slot = "afternoon"  # default to afternoon if time unknown

                if slot == event_slot:
                    att = event_data.get("attendance_est", 0) or 0
                    adj = (att / 1000) * w["event_per_1k_attendees"]
                    event_adj += adj
                    components[slot][f"event_{event_key}"] = round(adj, 3)

        # Market day bonus (Eastern Market is always open Saturday mornings)
        market_adj = 0.0
        if slot == "morning" and w.get("market_day_bonus", 0) > 0:
            market_adj = w["market_day_bonus"]
            components[slot]["market_day_bonus"] = market_adj

        raw = base + weather_adj + event_adj + market_adj
        return round(max(0.0, min(10.0, raw)), 2)

    morning_score = score_slot("morning")
    afternoon_score = score_slot("afternoon")

    return {
        "morning": morning_score,
        "afternoon": afternoon_score,
        "score_components": components,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Determine target date
    if len(sys.argv) > 1:
        try:
            target_date = date.fromisoformat(sys.argv[1])
        except ValueError:
            print(f"Invalid date '{sys.argv[1]}'. Use YYYY-MM-DD format.")
            sys.exit(1)
    else:
        target_date = next_saturday()

    print(f"\nCapital Slice — fetching data for Saturday {target_date}\n")

    # Load location weights
    with open(WEIGHTS_FILE) as f:
        location_weights = json.load(f)
    location_weights = {k: v for k, v in location_weights.items() if not k.startswith("_")}

    # Fetch data
    weather = fetch_weather(target_date)

    events = {
        "nationals_home_game": fetch_nationals(target_date),
        "capitals_home_game": fetch_capitals(target_date),
        "wizards_home_game": fetch_wizards(target_date),
        "mystics_home_game": fetch_mystics(target_date),
        "dc_united_home_game": fetch_dc_united(target_date),
        **MANUAL_EVENTS,
    }

    print()

    # Score locations
    location_scores = {}
    for key, loc in location_weights.items():
        location_scores[key] = score_location(key, loc, weather, events)

    # Build output
    output = {
        "target_date": target_date.isoformat(),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "conditions": {
            "weather": weather,
            "events": events,
        },
        "location_scores": location_scores,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Scores written to: {OUTPUT_FILE}\n")

    # Print a quick summary table
    print(f"{'Location':<28} {'Morning':>8} {'Afternoon':>10}")
    print("-" * 50)
    sorted_locs = sorted(
        location_scores.items(),
        key=lambda x: max(x[1]["morning"], x[1]["afternoon"]),
        reverse=True,
    )
    for key, scores in sorted_locs:
        display = location_weights[key]["display_name"]
        print(f"{display:<28} {scores['morning']:>8.1f} {scores['afternoon']:>10.1f}")
    print()


if __name__ == "__main__":
    main()
