"""
Capital Slice -- HTML Dashboard Generator
Reads saturday_scored.json and produces a self-contained saturday_dashboard.html
with Chart.js visualizations.

Usage:
    python generate_dashboard.py path/to/saturday_scored.json

Output:
    saturday_dashboard.html written to the same directory as the input file
"""

import json
import sys
import os
from datetime import datetime


LOCATION_DISPLAY = {
    "eastern_market":        "Eastern Market",
    "dupont_circle":         "Dupont Circle",
    "national_mall":         "National Mall",
    "georgetown_waterfront": "Georgetown Waterfront",
    "u_street_corridor":     "U Street Corridor",
    "convention_center":     "Convention Center",
    "capital_one_arena":     "Capital One Arena",
    "columbia_heights":      "Columbia Heights",
    "h_street_corridor":     "H Street Corridor",
    "navy_yard":             "Navy Yard",
}

LOCATION_SHORT = {
    "eastern_market":        "Eastern Mkt",
    "dupont_circle":         "Dupont Cir",
    "national_mall":         "Natl Mall",
    "georgetown_waterfront": "Georgetown",
    "u_street_corridor":     "U Street",
    "convention_center":     "Conv Ctr",
    "capital_one_arena":     "Cap One Arena",
    "columbia_heights":      "Columbia Hts",
    "h_street_corridor":     "H Street",
    "navy_yard":             "Navy Yard",
}

COMPONENT_COLORS = [
    "rgba(59,130,246,0.82)",    # base -- blue
    "rgba(34,197,94,0.82)",     # weather_adj -- green
    "rgba(168,85,247,0.82)",    # event bonuses -- purple
    "rgba(251,191,36,0.82)",    # market_day_bonus -- amber
    "rgba(239,68,68,0.82)",     # overflow -- red
]


def load_data(json_path):
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def score_to_color(score):
    if score >= 8.0:
        return "#22c55e"
    elif score >= 6.0:
        return "#84cc16"
    elif score >= 4.0:
        return "#f59e0b"
    elif score >= 2.0:
        return "#f97316"
    else:
        return "#ef4444"



def get_active_events(events):
    event_labels = {
        "nationals_home_game":     "Nationals Home Game",
        "capitals_home_game":      "Capitals Home Game",
        "wizards_home_game":       "Wizards Home Game",
        "mystics_home_game":       "Mystics Home Game",
        "dc_united_home_game":     "DC United Home Game",
        "convention_center_event": "Convention Center Event",
        "national_mall_event":     "National Mall Event",
        "h_street_event":          "H Street Event",
        "u_street_event":          "U Street Event",
    }
    active = []
    for key, label in event_labels.items():
        ev = events.get(key)
        if not ev:
            continue
        if isinstance(ev, dict) and ev.get("playing") is False:
            continue
        if isinstance(ev, dict) and (ev.get("playing") is True or "attendance_est" in ev):
            parts = []
            if ev.get("start_time"):
                parts.append(f"Start: {ev['start_time']}")
            if ev.get("attendance_est"):
                parts.append(f"Est. {ev['attendance_est']:,} fans")
            active.append((label, " &middot; ".join(parts)))
    return active


def collect_component_keys(location_scores):
    seen = {}
    for loc_data in location_scores.values():
        for slot in ("morning", "afternoon"):
            for k in loc_data.get("score_components", {}).get(slot, {}):
                seen[k] = True
    ordered = []
    for priority in ("base", "weather_adj"):
        if priority in seen:
            ordered.append(priority)
            del seen[priority]
    for k in list(seen.keys()):
        if k.startswith("event_"):
            ordered.append(k)
            del seen[k]
    ordered.extend(seen.keys())
    return ordered


def component_label(key):
    mapping = {
        "base": "Base Score",
        "weather_adj": "Weather Adj.",
        "market_day_bonus": "Market Day Bonus",
    }
    if key in mapping:
        return mapping[key]
    if key.startswith("event_"):
        return "Event: " + key[len("event_"):].replace("_", " ").title()
    return key.replace("_", " ").title()


def build_html(data, json_path):
    target_date   = data.get("target_date", "")
    generated_at  = data.get("generated_at", "")
    weather       = data.get("conditions", {}).get("weather", {})
    events        = data.get("conditions", {}).get("events", {})
    loc_scores    = data.get("location_scores", {})

    try:
        td = datetime.strptime(target_date, "%Y-%m-%d")
        target_display = td.strftime("%B %d, %Y")
    except Exception:
        target_display = target_date

    try:
        gen_dt = datetime.fromisoformat(generated_at)
        gen_display = gen_dt.strftime("%b %d, %Y at %I:%M %p")
    except Exception:
        gen_display = generated_at

    sorted_locs = sorted(
        loc_scores.items(),
        key=lambda x: max(x[1]["morning"], x[1]["afternoon"]),
        reverse=True,
    )

    stored = data["placements"]
    stored["stays"] = set(stored.get("stays", []))
    placements = stored
    active_events = get_active_events(events)
    comp_keys     = collect_component_keys(loc_scores)

    morning_w   = weather.get("morning", {})
    afternoon_w = weather.get("afternoon", {})
    mw_score    = morning_w.get("factor_score", 5.0)
    aw_score    = afternoon_w.get("factor_score", 5.0)

    tam  = placements["truck_a_morning"]
    taa  = placements["truck_a_afternoon"]
    tbm  = placements["truck_b_morning"]
    tba  = placements["truck_b_afternoon"]
    a_stays = "truck_a" in placements["stays"]
    b_stays = "truck_b" in placements["stays"]

    rec_locs = {tam, taa, tbm, tba}

    # ---- Chart data ----
    short_labels   = [LOCATION_SHORT.get(k, k)   for k, _ in sorted_locs]
    display_labels = [LOCATION_DISPLAY.get(k, k) for k, _ in sorted_locs]
    m_scores       = [v["morning"]   for _, v in sorted_locs]
    a_scores       = [v["afternoon"] for _, v in sorted_locs]
    rec_indices    = [i for i, (k, _) in enumerate(sorted_locs) if k in rec_locs]

    def comp_datasets(slot):
        datasets = []
        for i, ck in enumerate(comp_keys):
            color = COMPONENT_COLORS[min(i, len(COMPONENT_COLORS) - 1)]
            vals = [
                round(v.get("score_components", {}).get(slot, {}).get(ck, 0), 3)
                for _, v in sorted_locs
            ]
            datasets.append({
                "label": component_label(ck),
                "data": vals,
                "backgroundColor": color,
                "borderRadius": 3,
            })
        return datasets

    m_comp_ds = comp_datasets("morning")
    a_comp_ds = comp_datasets("afternoon")

    # ---- Events HTML ----
    if active_events:
        ev_html = "\n".join(
            f'<div class="event-badge">'
            f'<span class="event-dot"></span>'
            f'<div>'
            f'<span class="event-name">{label}</span>'
            f'{"<span class=event-detail>" + detail + "</span>" if detail else ""}'
            f'</div>'
            f'</div>'
            for label, detail in active_events
        )
    else:
        ev_html = '<div class="no-events">No major events this Saturday</div>'

    # ---- Ranking table rows ----
    table_rows = ""
    for rank, (loc_key, loc_data) in enumerate(sorted_locs, 1):
        display = LOCATION_DISPLAY.get(loc_key, loc_key)
        ms = loc_data["morning"]
        as_ = loc_data["afternoon"]
        row_class = "rec-row" if loc_key in rec_locs else ""
        badges = ""
        if loc_key == tam:
            badges += '<span class="tb ta">A&#8209;AM</span>'
        if loc_key == taa and not a_stays:
            badges += '<span class="tb ta">A&#8209;PM</span>'
        elif loc_key == taa and a_stays and loc_key == tam:
            badges += '<span class="tb ta">A&#8209;PM</span>'
        if loc_key == tbm:
            badges += '<span class="tb tb-b">B&#8209;AM</span>'
        if loc_key == tba and not b_stays:
            badges += '<span class="tb tb-b">B&#8209;PM</span>'
        elif loc_key == tba and b_stays and loc_key == tbm:
            badges += '<span class="tb tb-b">B&#8209;PM</span>'

        table_rows += (
            f'<tr class="{row_class}">'
            f'<td class="td-rank">#{rank}</td>'
            f'<td class="td-loc">{display} {badges}</td>'
            f'<td class="td-score">'
            f'  <div class="bar-wrap">'
            f'    <div class="bar bar-m" style="width:{ms*10:.1f}%"></div>'
            f'    <span class="bar-num bar-m-num">{ms:.1f}</span>'
            f'  </div>'
            f'</td>'
            f'<td class="td-score">'
            f'  <div class="bar-wrap">'
            f'    <div class="bar bar-a" style="width:{as_*10:.1f}%"></div>'
            f'    <span class="bar-num bar-a-num">{as_:.1f}</span>'
            f'  </div>'
            f'</td>'
            f'</tr>'
        )

    # ---- Truck card helpers ----
    def slot_row(loc_key, slot, stays_flag):
        score = loc_scores[loc_key]["morning" if slot == "AM" else "afternoon"]
        stay_tag = '<span class="stay">STAY</span>' if stays_flag and slot == "PM" else ""
        return (
            f'<div class="slot-row">'
            f'<span class="slot-time">{slot}</span>'
            f'<span class="slot-loc">{LOCATION_DISPLAY.get(loc_key, loc_key)}</span>'
            f'<span class="slot-score">{score:.1f}</span>'
            f'{stay_tag}'
            f'</div>'
        )

    truck_a_rows = slot_row(tam, "AM", False) + slot_row(taa, "PM", a_stays)
    truck_b_rows = slot_row(tbm, "AM", False) + slot_row(tba, "PM", b_stays)

    # ---- Serialise JS data ----
    sl_js    = json.dumps(short_labels)
    dl_js    = json.dumps(display_labels)
    ms_js    = json.dumps(m_scores)
    as_js    = json.dumps(a_scores)
    ri_js    = json.dumps(rec_indices)
    mcd_js   = json.dumps(m_comp_ds)
    acd_js   = json.dumps(a_comp_ds)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Capital Slice &mdash; Dashboard {target_display}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#f1f5f9;--surface:#fff;--border:#e2e8f0;
  --txt:#0f172a;--txt2:#475569;--muted:#94a3b8;
  --blue:#3b82f6;--blue-dk:#2563eb;
  --orange:#f97316;--orange-dk:#d97706;
  --green:#22c55e;--radius:12px;
  --shadow:0 1px 3px rgba(0,0,0,.07),0 4px 14px rgba(0,0,0,.06);
}}
body{{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--txt);line-height:1.5;padding-bottom:60px}}

/* Header */
.hdr{{background:var(--surface);border-bottom:1px solid var(--border);
  padding:18px 40px;display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:12px;position:sticky;top:0;z-index:20;
  box-shadow:0 1px 4px rgba(0,0,0,.07)}}
.hdr-left{{display:flex;align-items:center;gap:14px}}
.logo{{width:42px;height:42px;border-radius:10px;
  background:linear-gradient(135deg,#ef4444,#f97316);
  display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0}}
.hdr-title{{font-size:18px;font-weight:700}}
.hdr-sub{{font-size:12px;color:var(--txt2);margin-top:1px}}
.hdr-date{{font-size:14px;font-weight:600;text-align:right}}
.hdr-gen{{font-size:11px;color:var(--muted);text-align:right;margin-top:2px}}

/* Page */
.page{{max-width:1280px;margin:0 auto;padding:28px 40px 0}}
.section-label{{font-size:11px;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;color:var(--muted);margin-bottom:14px}}

/* Card */
.card{{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius);padding:22px 24px;box-shadow:var(--shadow)}}
.card-title{{font-size:13px;font-weight:600;color:var(--txt2);
  margin-bottom:14px;display:flex;align-items:center;gap:7px}}

/* Truck recommendation strip */
.rec-strip{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:24px}}
.truck-card{{border-radius:var(--radius);padding:18px 22px;border:2px solid transparent}}
.truck-card.ta{{background:linear-gradient(135deg,#eff6ff,#dbeafe);border-color:#93c5fd}}
.truck-card.tb{{background:linear-gradient(135deg,#fff7ed,#fed7aa);border-color:#fdba74}}
.truck-label{{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.09em;margin-bottom:10px}}
.ta .truck-label{{color:var(--blue-dk)}}
.tb .truck-label{{color:var(--orange-dk)}}
.slot-row{{display:flex;align-items:center;gap:10px;margin-bottom:6px}}
.slot-row:last-child{{margin-bottom:0}}
.slot-time{{font-size:10px;font-weight:700;color:var(--muted);width:28px;flex-shrink:0}}
.slot-loc{{font-size:15px;font-weight:700;flex:1}}
.slot-score{{font-size:12px;font-weight:600;padding:2px 7px;
  border-radius:20px;background:rgba(255,255,255,.75);color:var(--txt2)}}
.stay{{font-size:10px;font-weight:600;padding:1px 6px;
  border-radius:4px;background:rgba(0,0,0,.07);color:var(--muted)}}

/* Grid */
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:24px}}
.grid3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px;margin-bottom:24px}}

/* Weather */
.wx-grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.wx-slot{{border-radius:8px;padding:13px 15px;border:1px solid var(--border)}}
.wx-lbl{{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);margin-bottom:6px}}
.wx-cond{{font-size:14px;font-weight:600;margin-bottom:5px}}
.wx-stats{{display:flex;flex-wrap:wrap;gap:6px}}
.wx-stat{{font-size:11px;color:var(--txt2);background:var(--bg);
  padding:2px 7px;border-radius:5px}}
.wx-score-row{{display:flex;align-items:center;gap:8px;margin-top:9px}}
.wx-score-lbl{{font-size:10px;color:var(--muted);white-space:nowrap}}
.wx-track{{flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden}}
.wx-fill{{height:100%;border-radius:3px}}
.wx-val{{font-size:11px;font-weight:700}}

/* Events */
.event-badge{{display:flex;align-items:flex-start;gap:8px;
  padding:9px 11px;border-radius:8px;
  background:#f0fdf4;border:1px solid #bbf7d0;margin-bottom:7px}}
.event-badge:last-child{{margin-bottom:0}}
.event-dot{{width:8px;height:8px;border-radius:50%;
  background:var(--green);flex-shrink:0;margin-top:4px}}
.event-name{{font-size:13px;font-weight:600}}
.event-detail{{font-size:11px;color:var(--txt2);display:block;margin-top:1px}}
.no-events{{font-size:13px;color:var(--muted);padding:12px;
  background:var(--bg);border-radius:8px;text-align:center}}

/* Charts */
.chart-wrap canvas{{max-height:340px}}
.chart-wrap-sm canvas{{max-height:280px}}

/* Legend */
.legend{{display:flex;gap:16px;margin-bottom:10px;flex-wrap:wrap}}
.legend-item{{display:flex;align-items:center;gap:5px;font-size:12px;color:var(--txt2)}}
.legend-dot{{width:10px;height:10px;border-radius:3px;flex-shrink:0}}

/* Score table */
.score-tbl{{width:100%;border-collapse:collapse;font-size:13px}}
.score-tbl th{{font-size:10px;font-weight:700;text-transform:uppercase;
  letter-spacing:.06em;color:var(--muted);padding:7px 11px;
  text-align:left;border-bottom:2px solid var(--border)}}
.score-tbl td{{padding:9px 11px;border-bottom:1px solid var(--border);vertical-align:middle}}
.score-tbl tr:last-child td{{border-bottom:none}}
.rec-row{{background:#f8faff}}
.rec-row:hover{{background:#eef3ff}}
.score-tbl tr:not(.rec-row):hover{{background:var(--bg)}}
.td-rank{{color:var(--muted);font-size:11px;width:32px}}
.td-loc{{font-weight:500}}
.td-score{{width:200px}}
.bar-wrap{{display:flex;align-items:center;gap:7px}}
.bar{{height:7px;border-radius:4px;min-width:3px;flex-shrink:0}}
.bar-m{{background:var(--blue)}}
.bar-a{{background:var(--orange)}}
.bar-num{{font-size:12px;font-weight:600}}
.bar-m-num{{color:var(--blue-dk)}}
.bar-a-num{{color:var(--orange-dk)}}
.tb{{display:inline-flex;font-size:9px;font-weight:700;
  padding:1px 5px;border-radius:3px;margin-left:3px;white-space:nowrap}}
.ta{{background:#dbeafe;color:var(--blue-dk)}}
.tb-b{{background:#fed7aa;color:var(--orange-dk)}}

/* Footer */
.footer{{text-align:center;margin-top:44px;font-size:11px;color:var(--muted)}}

@media(max-width:860px){{
  .page{{padding:16px 16px 0}}
  .hdr{{padding:14px 16px}}
  .rec-strip,.grid2,.grid3{{grid-template-columns:1fr}}
  .td-score{{width:130px}}
}}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-left">
    <div class="logo">&#127829;</div>
    <div>
      <div class="hdr-title">Capital Slice &mdash; Positioning Dashboard</div>
      <div class="hdr-sub">Saturday truck placement analysis</div>
    </div>
  </div>
  <div>
    <div class="hdr-date">Saturday, {target_display}</div>
    <div class="hdr-gen">Generated {gen_display}</div>
  </div>
</header>

<div class="page">

  <p class="section-label" style="margin-top:26px">Recommended Placements</p>
  <div class="rec-strip">
    <div class="truck-card ta">
      <div class="truck-label">Truck A</div>
      {truck_a_rows}
    </div>
    <div class="truck-card tb">
      <div class="truck-label">Truck B</div>
      {truck_b_rows}
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-title">&#127780; Weather Forecast</div>
      <div class="wx-grid">
        <div class="wx-slot">
          <div class="wx-lbl">Morning &mdash; 7am&ndash;12pm</div>
          <div class="wx-cond">{morning_w.get('condition','Unknown')}</div>
          <div class="wx-stats">
            <span class="wx-stat">&#127777; {morning_w.get('temp_f','&mdash;')}&deg;F</span>
            <span class="wx-stat">&#9748; {morning_w.get('precip_pct',0)}% rain</span>
            <span class="wx-stat">&#127788; {morning_w.get('wind_mph',0)} mph</span>
          </div>
          <div class="wx-score-row">
            <span class="wx-score-lbl">Score</span>
            <div class="wx-track">
              <div class="wx-fill" style="width:{mw_score*10:.1f}%;background:{score_to_color(mw_score)}"></div>
            </div>
            <span class="wx-val">{mw_score:.1f}/10</span>
          </div>
        </div>
        <div class="wx-slot">
          <div class="wx-lbl">Afternoon &mdash; 2pm&ndash;8pm</div>
          <div class="wx-cond">{afternoon_w.get('condition','Unknown')}</div>
          <div class="wx-stats">
            <span class="wx-stat">&#127777; {afternoon_w.get('temp_f','&mdash;')}&deg;F</span>
            <span class="wx-stat">&#9748; {afternoon_w.get('precip_pct',0)}% rain</span>
            <span class="wx-stat">&#127788; {afternoon_w.get('wind_mph',0)} mph</span>
          </div>
          <div class="wx-score-row">
            <span class="wx-score-lbl">Score</span>
            <div class="wx-track">
              <div class="wx-fill" style="width:{aw_score*10:.1f}%;background:{score_to_color(aw_score)}"></div>
            </div>
            <span class="wx-val">{aw_score:.1f}/10</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title">&#127903; Active Events</div>
      {ev_html}
    </div>
  </div>

  <div class="card" style="margin-bottom:24px">
    <div class="card-title">&#128202; Location Scores &mdash; Morning vs Afternoon</div>
    <div class="legend">
      <div class="legend-item">
        <div class="legend-dot" style="background:rgba(59,130,246,0.85)"></div>
        Morning (7am&ndash;12pm)
      </div>
      <div class="legend-item">
        <div class="legend-dot" style="background:rgba(249,115,22,0.85)"></div>
        Afternoon (2pm&ndash;8pm)
      </div>
      <div class="legend-item" style="color:#94a3b8;font-size:11px">
        &#9642; Darker bars = recommended placement
      </div>
    </div>
    <div class="chart-wrap">
      <canvas id="mainChart"></canvas>
    </div>
  </div>

  <div class="grid2">
    <div class="card">
      <div class="card-title">&#129513; Morning Score Breakdown</div>
      <div class="chart-wrap chart-wrap-sm">
        <canvas id="mCompChart"></canvas>
      </div>
    </div>
    <div class="card">
      <div class="card-title">&#129513; Afternoon Score Breakdown</div>
      <div class="chart-wrap chart-wrap-sm">
        <canvas id="aCompChart"></canvas>
      </div>
    </div>
  </div>

  <div class="card" style="margin-bottom:24px">
    <div class="card-title">&#128203; Full Location Rankings</div>
    <table class="score-tbl">
      <thead>
        <tr>
          <th>#</th>
          <th>Location</th>
          <th>Morning Score</th>
          <th>Afternoon Score</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

</div>

<div class="footer">
  Capital Slice Positioning Dashboard &middot; Generated from {os.path.basename(json_path)}
</div>

<script>
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 12;

const shortLabels    = {sl_js};
const displayLabels  = {dl_js};
const mScores        = {ms_js};
const aScores        = {as_js};
const recIdx         = {ri_js};
const mCompDatasets  = {mcd_js};
const aCompDatasets  = {acd_js};

const mBlue  = i => recIdx.includes(i) ? 'rgba(37,99,235,0.92)'   : 'rgba(59,130,246,0.60)';
const aOrang = i => recIdx.includes(i) ? 'rgba(217,119,6,0.92)'   : 'rgba(249,115,22,0.60)';

new Chart(document.getElementById('mainChart'), {{
  type: 'bar',
  data: {{
    labels: shortLabels,
    datasets: [
      {{
        label: 'Morning',
        data: mScores,
        backgroundColor: mScores.map((_, i) => mBlue(i)),
        borderColor: mScores.map((_, i) => recIdx.includes(i) ? 'rgb(37,99,235)' : 'transparent'),
        borderWidth: 1.5,
        borderRadius: 4,
      }},
      {{
        label: 'Afternoon',
        data: aScores,
        backgroundColor: aScores.map((_, i) => aOrang(i)),
        borderColor: aScores.map((_, i) => recIdx.includes(i) ? 'rgb(217,119,6)' : 'transparent'),
        borderWidth: 1.5,
        borderRadius: 4,
      }},
    ]
  }},
  options: {{
    responsive: true,
    plugins: {{
      legend: {{ position: 'top', labels: {{ boxWidth: 11, padding: 14 }} }},
      tooltip: {{
        callbacks: {{
          title: ctx => displayLabels[ctx[0].dataIndex],
          label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(1)}} / 10`,
        }}
      }}
    }},
    scales: {{
      x: {{ grid: {{ display: false }}, ticks: {{ maxRotation: 25 }} }},
      y: {{ min: 0, max: 10, grid: {{ color: 'rgba(0,0,0,.045)' }}, ticks: {{ stepSize: 2 }} }}
    }}
  }}
}});

function makeStackedChart(canvasId, datasets) {{
  new Chart(document.getElementById(canvasId), {{
    type: 'bar',
    data: {{ labels: shortLabels, datasets }},
    options: {{
      responsive: true,
      plugins: {{
        legend: {{ position: 'bottom', labels: {{ boxWidth: 10, padding: 9, font: {{ size: 11 }} }} }},
        tooltip: {{
          callbacks: {{
            title: ctx => displayLabels[ctx[0].dataIndex],
            label: ctx => ` ${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(2)}}`,
          }}
        }}
      }},
      scales: {{
        x: {{ stacked: true, grid: {{ display: false }}, ticks: {{ maxRotation: 25 }} }},
        y: {{ stacked: true, min: 0, suggestedMax: 10,
              grid: {{ color: 'rgba(0,0,0,.045)' }}, ticks: {{ stepSize: 2 }} }}
      }}
    }}
  }});
}}

makeStackedChart('mCompChart', mCompDatasets);
makeStackedChart('aCompChart', aCompDatasets);
</script>
</body>
</html>"""

    return html


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_dashboard.py path/to/saturday_scored.json")
        sys.exit(1)

    json_path = sys.argv[1]
    if not os.path.exists(json_path):
        print(f"Error: file not found: {json_path}")
        sys.exit(1)

    print(f"Reading: {json_path}")
    data = load_data(json_path)

    html = build_html(data, json_path)

    out_dir  = os.path.dirname(os.path.abspath(json_path))
    out_path = os.path.join(out_dir, "saturday_dashboard.html")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard written to: {out_path}")
    return out_path


if __name__ == "__main__":
    main()
