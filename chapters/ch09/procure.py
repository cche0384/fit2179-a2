"""
Chapter 9 — Progress, or the Illusion of It?
procure.py: Processes DOSM early childhood death rates (already downloaded in ch01/raw/)
into a heatmap-ready dataset: state × year × IMR.

Data: ch01/raw/dosm_imr_state.csv  (type=total, 2000–2023, 16 states)
Output: data.json — list of {state, year, imr, imr_change_from_2000}
"""
import pandas as pd
import json
import os

os.makedirs("chapters/ch09/raw", exist_ok=True)

df = pd.read_csv("chapters/ch01/raw/dosm_imr_state.csv")
df["year"] = pd.to_datetime(df["date"]).dt.year

total = df[df["type"] == "total"].copy()

# Exclude small territories — statistically noisy denominators
EXCLUDE = {"W.P. Labuan", "W.P. Putrajaya"}
total = total[~total["state"].isin(EXCLUDE)]

DISPLAY = {
    "Pulau Pinang": "Penang",
    "W.P. Kuala Lumpur": "Kuala Lumpur",
}

total["state"] = total["state"].replace(DISPLAY)

# Baseline: 2000 IMR per state for percent-change calculation
baseline_2000 = (
    total[total["year"] == 2000]
    .set_index("state")["rate"]
    .to_dict()
)

# Sort order: worst 2023 IMR at top (high IMR = worse outcome)
rank_2023 = (
    total[total["year"] == 2023]
    .sort_values("rate", ascending=False)["state"]
    .tolist()
)

records = []
for _, row in total.iterrows():
    state = row["state"]
    yr = int(row["year"])
    imr = round(float(row["rate"]), 2)
    base = baseline_2000.get(state)
    pct_change = round(((imr - base) / base) * 100, 1) if base else None
    records.append({
        "state": state,
        "year": yr,
        "imr": imr,
        "imr_change_pct": pct_change,
        "state_order": rank_2023.index(state) if state in rank_2023 else 99,
    })

records.sort(key=lambda r: (r["state_order"], r["year"]))

with open("chapters/ch09/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"Wrote {len(records)} records — {total['state'].nunique()} states × {total['year'].nunique()} years (2000–2023)")

print("\n2023 IMR ranking (worst → best):")
for s in rank_2023:
    v2023 = total[(total["state"] == s) & (total["year"] == 2023)]["rate"].values
    v2000 = baseline_2000.get(s, float("nan"))
    if len(v2023):
        print(f"  {s:25s}: {v2023[0]:.1f}  (2000: {v2000:.1f})")

spread_2000 = total[total["year"] == 2000]["rate"]
spread_2023 = total[total["year"] == 2023]["rate"]
print(f"\nSpread (max–min) 2000: {spread_2000.max():.1f} – {spread_2000.min():.1f} = {spread_2000.max()-spread_2000.min():.1f}")
print(f"Spread (max–min) 2023: {spread_2023.max():.1f} – {spread_2023.min():.1f} = {spread_2023.max()-spread_2023.min():.1f}")
