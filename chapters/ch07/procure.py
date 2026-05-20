"""
Chapter 7 — The Slow Burn
Downloads PEKA B40 screening coverage by state (MoH GitHub) and
absolute poverty rates by state (DOSM), then joins them for a choropleth.
"""

import io
import json
import requests
import pandas as pd
from pathlib import Path

RAW = Path("chapters/ch07/raw")
RAW.mkdir(parents=True, exist_ok=True)

GADM_NAME = {
    "Johor":             "Johor",
    "Kedah":             "Kedah",
    "Kelantan":          "Kelantan",
    "Melaka":            "Melaka",
    "Negeri Sembilan":   "NegeriSembilan",
    "Pahang":            "Pahang",
    "Perak":             "Perak",
    "Perlis":            "Perlis",
    "Pulau Pinang":      "PulauPinang",
    "Sabah":             "Sabah",
    "Sarawak":           "Sarawak",
    "Selangor":          "Selangor",
    "Terengganu":        "Trengganu",
    "W.P. Kuala Lumpur": "KualaLumpur",
    "W.P. Labuan":       "Labuan",
    "W.P. Putrajaya":    "Putrajaya",
}

DISPLAY_NAME = {
    "Johor":             "Johor",
    "Kedah":             "Kedah",
    "Kelantan":          "Kelantan",
    "Melaka":            "Melaka",
    "Negeri Sembilan":   "Negeri Sembilan",
    "Pahang":            "Pahang",
    "Perak":             "Perak",
    "Perlis":            "Perlis",
    "Pulau Pinang":      "Penang",
    "Sabah":             "Sabah",
    "Sarawak":           "Sarawak",
    "Selangor":          "Selangor",
    "Terengganu":        "Terengganu",
    "W.P. Kuala Lumpur": "W.P. Kuala Lumpur",
    "W.P. Labuan":       "W.P. Labuan",
    "W.P. Putrajaya":    "W.P. Putrajaya",
}

# 1 — PEKA B40 screening coverage by state
peka_url = (
    "https://raw.githubusercontent.com/MoH-Malaysia/kkmnow-data/main/"
    "pekab40_03_choropleth_msia.parquet"
)
print("Downloading PEKA B40 choropleth...")
r = requests.get(peka_url, timeout=30)
r.raise_for_status()
peka_path = RAW / "pekab40_choropleth.parquet"
peka_path.write_bytes(r.content)
peka = pd.read_parquet(io.BytesIO(r.content))
print(f"  {len(peka)} states, perc range: {peka['perc'].min():.1f}–{peka['perc'].max():.1f}%")

# 2 — DOSM poverty by state (already in ch04/raw but re-download for independence)
poverty_url = "https://storage.dosm.gov.my/hies/hh_poverty_state.csv"
print("Downloading DOSM poverty by state...")
rp = requests.get(poverty_url, timeout=30)
rp.raise_for_status()
poverty_path = RAW / "hh_poverty_state.csv"
poverty_path.write_bytes(rp.content)
poverty = pd.read_csv(io.StringIO(rp.text))
poverty["date"] = pd.to_datetime(poverty["date"])
poverty_latest = (
    poverty[poverty["date"] == poverty["date"].max()]
    .set_index("state")[["poverty_absolute"]]
    .rename(columns={"poverty_absolute": "poverty_pct"})
)
print(f"  Poverty year: {poverty['date'].max().year}, {len(poverty_latest)} states")

# 3 — Join
peka = peka[peka["state"] != "Malaysia"].copy()
peka["gadm_name"]  = peka["state"].map(GADM_NAME)
peka["state_name"] = peka["state"].map(DISPLAY_NAME)
peka = peka.join(poverty_latest, on="state")
peka = peka.rename(columns={"perc": "screening_pct"})

# Drop W.P. Putrajaya (tiny, statistical outlier like in ch03)
peka = peka[peka["state"] != "W.P. Putrajaya"]

records = peka[["gadm_name", "state_name", "screening_pct", "poverty_pct"]].to_dict(orient="records")
for r in records:
    r["screening_pct"] = round(r["screening_pct"], 2)
    r["poverty_pct"]   = round(float(r["poverty_pct"]), 1)

out = Path("chapters/ch07/data.json")
out.write_text(json.dumps(records, indent=2))
print(f"\nWrote {len(records)} rows → {out}")
print(peka[["state_name", "screening_pct", "poverty_pct"]].sort_values("screening_pct", ascending=False).to_string(index=False))
