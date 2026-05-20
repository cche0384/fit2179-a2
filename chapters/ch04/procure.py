"""
Chapter 4 — The Return of the Forgotten Killers
Data procurement — downloads everything from public APIs, no hardcoding.

Sources:
  - World Bank API: TB incidence per 100k (SH.TBS.INCD) — WHO modelled estimates
  - World Bank API: National poverty headcount % (SI.POV.NAHC)
  - World Bank API: Total population (SP.POP.TOTL)
  - DOSM open data: State-level absolute poverty rates (Malaysia)

Run:  python procure.py   (from chapters/ch04/)

Outputs
-------
raw/raw_wb_tb.json         — raw World Bank TB indicator API response
raw/raw_wb_poverty.json    — raw World Bank poverty indicator API response
raw/raw_wb_population.json — raw World Bank population indicator API response
raw/raw_dosm_poverty.csv   — raw DOSM state poverty CSV
asean_scatter.json         — processed flat array for the ASEAN scatter chart
malaysia_states.json       — processed flat array for the Malaysia state bar chart
data.json                  — combined metadata + both arrays (used by eda.py)
"""

import io
import json
import os
import warnings
from datetime import date

import pandas as pd
import requests

warnings.filterwarnings("ignore")

# ── Config ────────────────────────────────────────────────────────────────────

ASEAN_ISO2 = "MY;TH;ID;PH;VN;LA;MM;KH;BN;SG"
TARGET_YEAR = 2022
MAX_POVERTY_LAG = 5       # years we'll tolerate between TB year and poverty year

WB_BASE = "https://api.worldbank.org/v2"
DOSM_POVERTY_URL = "https://storage.dosm.gov.my/hies/hh_poverty_state.csv"

HERE = os.path.dirname(os.path.abspath(__file__))
RAW  = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)


def save(filename, content, raw=False):
    path = os.path.join(RAW if raw else HERE, filename)
    with open(path, "w", encoding="utf-8") as f:
        if isinstance(content, str):
            f.write(content)
        else:
            json.dump(content, f, indent=2, ensure_ascii=False)
    print(f"  → saved {filename}")


# ── 1. Fetch from World Bank API ──────────────────────────────────────────────

def wb_fetch(indicator, countries, mrv=15):
    url = (
        f"{WB_BASE}/country/{countries}/indicator/{indicator}"
        f"?format=json&per_page=500&mrv={mrv}"
    )
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    if len(payload) < 2 or payload[1] is None:
        return []
    return [r for r in payload[1] if r["value"] is not None]


print("Fetching World Bank indicators...")
tb_records  = wb_fetch("SH.TBS.INCD", ASEAN_ISO2)
pov_records = wb_fetch("SI.POV.NAHC",  ASEAN_ISO2)
pop_records = wb_fetch("SP.POP.TOTL",  ASEAN_ISO2, mrv=3)

print(f"  TB records:         {len(tb_records)}")
print(f"  Poverty records:    {len(pov_records)}")
print(f"  Population records: {len(pop_records)}")

save("raw_wb_tb.json",         tb_records,  raw=True)
save("raw_wb_poverty.json",    pov_records, raw=True)
save("raw_wb_population.json", pop_records, raw=True)


# ── 2. Fetch DOSM state poverty CSV ──────────────────────────────────────────

print("\nFetching DOSM state poverty CSV...")
dosm_resp = requests.get(DOSM_POVERTY_URL, timeout=20)
dosm_resp.raise_for_status()
save("raw_dosm_poverty.csv", dosm_resp.text, raw=True)
print(f"  {len(dosm_resp.text.splitlines())} lines")


# ── 3. Helper: pick closest year ──────────────────────────────────────────────

def closest(records, iso2, target, max_lag):
    """Return (value, year) for iso2 closest to target, or (None, None)."""
    hits = [r for r in records if r["country"]["id"] == iso2]
    if not hits:
        return None, None
    hits.sort(key=lambda r: abs(int(r["date"]) - target))
    best = hits[0]
    yr = int(best["date"])
    if abs(yr - target) > max_lag:
        return None, None
    return best["value"], yr


# ── 4. Build ASEAN scatter ────────────────────────────────────────────────────

print(f"\nBuilding ASEAN scatter (reference year {TARGET_YEAR})...")

seen = {}
for r in tb_records:
    cid = r["country"]["id"]
    if cid not in seen:
        seen[cid] = r["country"]["value"]

asean_scatter = []
for iso2, name in sorted(seen.items(), key=lambda x: x[1]):
    tb_val,  tb_yr  = closest(tb_records,  iso2, TARGET_YEAR, MAX_POVERTY_LAG)
    pov_val, pov_yr = closest(pov_records, iso2, TARGET_YEAR, MAX_POVERTY_LAG)
    pop_val, _      = closest(pop_records, iso2, TARGET_YEAR, max_lag=3)

    if tb_val is None:
        print(f"  SKIP {name}: no TB data near {TARGET_YEAR}")
        continue
    if pov_val is None:
        print(f"  SKIP {name}: no national poverty data")
        continue

    yr_gap = abs(tb_yr - pov_yr)
    stale  = yr_gap > 2

    asean_scatter.append({
        "country":      name,
        "label":        f"{name}*" if stale else name,
        "iso2":         iso2,
        "tb_per_100k":  round(float(tb_val),  1),
        "tb_year":      tb_yr,
        "poverty_rate": round(float(pov_val), 1),
        "poverty_year": pov_yr,
        "population":   int(pop_val) if pop_val is not None else None,
        "highlight":    iso2 == "MY",
        "stale_poverty": stale,
    })

    marker = " ← MALAYSIA" if iso2 == "MY" else (" [STALE poverty]" if stale else "")
    print(f"  {name:22s}  poverty={pov_val:4.1f}% ({pov_yr})  TB={tb_val:5.1f}/100k ({tb_yr}){marker}")

print(f"\n  {len(asean_scatter)} countries included")
save("asean_scatter.json", asean_scatter)


# ── 5. Build Malaysia state list ──────────────────────────────────────────────

print("\nBuilding Malaysia state poverty breakdown...")
state_df = pd.read_csv(io.StringIO(dosm_resp.text))
state_df["date"] = pd.to_datetime(state_df["date"])

latest_states = (
    state_df.sort_values("date")
    .groupby("state").last()
    .reset_index()
)

# Mark top-poverty states for chart highlight
HIGHLIGHT_THRESHOLD = 10.0   # states above this get special colour

malaysia_states = []
for _, row in latest_states.sort_values("poverty_absolute", ascending=False).iterrows():
    pov = float(row["poverty_absolute"])
    hardcore = float(row["poverty_hardcore"]) if pd.notna(row.get("poverty_hardcore")) else None
    malaysia_states.append({
        "state":            row["state"],
        "poverty_absolute": pov,
        "poverty_hardcore": hardcore,
        "year":             row["date"].year,
        "highlight":        pov >= HIGHLIGHT_THRESHOLD,
    })

print(f"  {len(malaysia_states)} states (year {malaysia_states[0]['year']})")
save("malaysia_states.json", malaysia_states)


# ── 6. Write combined data.json (used by eda.py) ─────────────────────────────

combined = {
    "metadata": {
        "generated":             str(date.today()),
        "tb_source":             "World Bank API / WHO estimates (SH.TBS.INCD)",
        "poverty_source_asean":  "World Bank API / national poverty lines (SI.POV.NAHC)",
        "poverty_source_states": "DOSM Household Expenditure Survey (open.dosm.gov.my)",
        "note": (
            "TB figures are WHO modelled estimates (account for under-reporting). "
            "National poverty lines are defined independently by each country and "
            "are not directly comparable across borders. "
            "Countries marked * have poverty data >2 years from TB reference year."
        ),
    },
    "asean_scatter":   asean_scatter,
    "malaysia_states": malaysia_states,
}

save("data.json", combined)

print(f"\nDone. Files written to {HERE}/")
print(f"  asean_scatter:   {len(asean_scatter)} records")
print(f"  malaysia_states: {len(malaysia_states)} records")
