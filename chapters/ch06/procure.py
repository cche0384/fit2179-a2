#!/usr/bin/env python3
"""
ch06 — The Infrastructure of Illness
Story: Malaysia's stunting rate is anomalously high for its income level.
Downloads stunting, GDP per capita (PPP), and population from World Bank API
for ASEAN + high-income + lower-income country comparison.
Also uses ch01/raw/dosm_imr_state.csv for within-Malaysia state annotation.
Run from repo root: python3 chapters/ch06/procure.py
"""

import json, os, requests, pandas as pd

RAW = "chapters/ch06/raw"
os.makedirs(RAW, exist_ok=True)

# ── Country groups ────────────────────────────────────────────────────────────
ASEAN      = ["MY", "TH", "ID", "PH", "VN", "KH", "LA", "MM", "SG", "BN"]
RICH       = ["US", "GB", "AU", "JP", "DE", "KR", "NZ", "FR", "CA", "NL",
              "SE", "NO", "CH", "AT", "IE", "DK", "FI", "BE", "NZ", "IL"]
AFRICA     = ["NG", "KE", "TZ", "ZA", "ET", "GH", "UG", "MZ", "ZM", "CI",
              "RW", "MW", "SN", "CM", "SD"]
OTHER_ASIA = ["CN", "IN", "PK", "BD", "LK", "NP", "MN", "AF"]

ALL_COUNTRIES = list(set(ASEAN + RICH + AFRICA + OTHER_ASIA))

GROUP_MAP = {c: "ASEAN" for c in ASEAN}
GROUP_MAP["MY"] = "Malaysia"
for c in RICH:        GROUP_MAP.setdefault(c, "High Income")
for c in AFRICA:      GROUP_MAP.setdefault(c, "Africa")
for c in OTHER_ASIA:  GROUP_MAP.setdefault(c, "Other Asia")

# Countries to label in the chart (key anchors for storytelling)
LABEL_SET = {"MY", "SG", "TH", "ID", "VN", "PH", "KH", "MM",
             "US", "AU", "NG", "ET", "IN", "CN"}

# ── World Bank fetch ──────────────────────────────────────────────────────────
def fetch_wb(code, countries, label):
    url = (f"https://api.worldbank.org/v2/country/"
           f"{';'.join(countries)}/indicator/{code}")
    params = {"format": "json", "per_page": 3000, "mrv": 15}
    r = requests.get(url, params=params, timeout=40)
    r.raise_for_status()
    data = r.json()
    path = f"{RAW}/raw_{label}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    n = len(data[1]) if len(data) > 1 and data[1] else 0
    print(f"  Saved {path} ({n} records)")
    return data

def most_recent(data, field):
    """Return dict iso2 → most recent non-null value for `field`."""
    result = {}
    if len(data) < 2 or not data[1]:
        return result
    for item in data[1]:
        if item["value"] is None:
            continue
        iso2 = item["country"]["id"]
        year = int(item["date"])
        year_key = f"{field}_year"
        if iso2 not in result or year > result[iso2][year_key]:
            result[iso2] = {
                "iso2":    iso2,
                "country": item["country"]["value"],
                field:     round(float(item["value"]), 2),
                year_key:  year,
            }
    return result

print("Fetching stunting (SH.STA.STNT.ZS)…")
stunting_rec = most_recent(
    fetch_wb("SH.STA.STNT.ZS", ALL_COUNTRIES, "stunting"), "stunting")

print("Fetching GDP per capita PPP (NY.GDP.PCAP.PP.CD)…")
gdp_rec = most_recent(
    fetch_wb("NY.GDP.PCAP.PP.CD", ALL_COUNTRIES, "gdp_ppp"), "gdp_ppp")

print("Fetching population (SP.POP.TOTL)…")
pop_rec = most_recent(
    fetch_wb("SP.POP.TOTL", ALL_COUNTRIES, "population"), "population")

# ── Merge ─────────────────────────────────────────────────────────────────────
rows = []
for iso2, g in gdp_rec.items():
    if iso2 not in stunting_rec:
        continue
    s = stunting_rec[iso2]
    p = pop_rec.get(iso2, {})
    row = {
        "iso2":          iso2,
        "country":       g["country"],
        "gdp_ppp":       round(g["gdp_ppp"], 0),
        "gdp_year":      g["gdp_ppp_year"],
        "stunting":      s["stunting"],
        "stunting_year": s["stunting_year"],
        "population":    p.get("population"),
        "group":         GROUP_MAP.get(iso2, "Other"),
        "highlight":     iso2 == "MY",
        "label":         g["country"] if iso2 in LABEL_SET else "",
    }
    rows.append(row)

rows.sort(key=lambda r: r["gdp_ppp"])

print(f"\n{len(rows)} countries with both stunting + GDP data:")
for r in rows:
    print(f"  {r['iso2']:3s}  {r['country'][:28]:28s}  "
          f"GDP={r['gdp_ppp']:>8,.0f}  Stunting={r['stunting']:5.1f}%  ({r['stunting_year']})")

# ── Malaysia state child mortality (from existing ch01 data) ──────────────────
print("\nLoading Malaysia state IMR from ch01/raw/dosm_imr_state.csv…")
imr = pd.read_csv("chapters/ch01/raw/dosm_imr_state.csv", parse_dates=["date"])
imr = imr[imr["type"] == "total"]
latest = imr["date"].max()
imr = imr[imr["date"] == latest].copy()

GADM_MAP = {
    "Johor":            "Johor",
    "Kedah":            "Kedah",
    "Kelantan":         "Kelantan",
    "Melaka":           "Melaka",
    "Negeri Sembilan":  "NegeriSembilan",
    "Pahang":           "Pahang",
    "Perak":            "Perak",
    "Perlis":           "Perlis",
    "Pulau Pinang":     "PulauPinang",
    "Sabah":            "Sabah",
    "Sarawak":          "Sarawak",
    "Selangor":         "Selangor",
    "Terengganu":       "Terengganu",
    "W.P. Kuala Lumpur": "KualaLumpur",
    "W.P. Labuan":      "Labuan",
    "W.P. Putrajaya":   "Putrajaya",
}

state_rows = []
for _, r in imr.iterrows():
    gadm = GADM_MAP.get(r["state"])
    if gadm and gadm != "Putrajaya":   # exclude statistical outlier
        state_rows.append({
            "state":     r["state"],
            "gadm_name": gadm,
            "imr":       round(float(r["rate"]), 2),
            "year":      int(r["date"].year),
        })

print(f"  {len(state_rows)} states loaded (year {state_rows[0]['year'] if state_rows else '?'})")

# ── Write data.json ───────────────────────────────────────────────────────────
output = {
    "countries":      rows,
    "malaysia_states": state_rows,
}
with open("chapters/ch06/data.json", "w") as f:
    json.dump(output, f, indent=2)
print(f"\nWrote chapters/ch06/data.json  "
      f"({len(rows)} countries · {len(state_rows)} states)")
