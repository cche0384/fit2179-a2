"""
Chapter 8 — Dying Before Your Time
Uses DOSM crude death rate by state (ch02/raw/death_state.parquet).
YLL data requires IHME account (not scriptable); crude death rate is the
recommended fallback per STORY.md.

Writes: chapters/ch08/data.json
"""
import json
import pathlib
import pandas as pd

ROOT = pathlib.Path(__file__).parent.parent.parent

GADM_MAP = {
    "Johor": "Johor",
    "Kedah": "Kedah",
    "Kelantan": "Kelantan",
    "Melaka": "Melaka",
    "Negeri Sembilan": "NegeriSembilan",
    "Pahang": "Pahang",
    "Perak": "Perak",
    "Perlis": "Perlis",
    "Pulau Pinang": "PulauPinang",
    "Sabah": "Sabah",
    "Sarawak": "Sarawak",
    "Selangor": "Selangor",
    "Terengganu": "Trengganu",
    "W.P. Kuala Lumpur": "KualaLumpur",
    "W.P. Labuan": "Labuan",
    # W.P. Putrajaya excluded: tiny resident population skews rates
}

df = pd.read_parquet(ROOT / "chapters/ch02/raw/death_state.parquet")
df["date"] = pd.to_datetime(df["date"])
df["year"] = df["date"].dt.year

# Keep only states with a GADM mapping
df = df[df["state"].isin(GADM_MAP)]

# Pull rate in 2000 and 2023 for trend context
r2000 = df[df["year"] == 2000][["state", "rate"]].rename(columns={"rate": "rate_2000"})
r2023 = df[df["year"] == 2023][["state", "rate"]].rename(columns={"rate": "rate_2023"})

merged = r2000.merge(r2023, on="state")
merged["change"] = (merged["rate_2023"] - merged["rate_2000"]).round(1)
merged["change_pct"] = ((merged["rate_2023"] - merged["rate_2000"]) / merged["rate_2000"] * 100).round(1)
merged["gadm_name"] = merged["state"].map(GADM_MAP)

records = merged.sort_values("rate_2023", ascending=False).to_dict(orient="records")

out = ROOT / "chapters/ch08/data.json"
with open(out, "w") as f:
    json.dump(records, f, indent=2)

print(f"Wrote {len(records)} states → {out}")
print(merged.sort_values("rate_2023", ascending=False)[
    ["state", "rate_2000", "rate_2023", "change_pct"]
].to_string(index=False))
