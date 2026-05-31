import json
import os
import numpy as np
import pandas as pd

os.makedirs("chapters/ch09/raw", exist_ok=True)

# ── Load data ─────────────────────────────────────────────────────────────────
df = pd.read_csv("chapters/ch01/raw/dosm_imr_state.csv")
df["year"] = pd.to_datetime(df["date"]).dt.year
total = df[df["type"] == "total"].copy()

EXCLUDE = {"W.P. Putrajaya", "W.P. Labuan"}
total = total[~total["state"].isin(EXCLUDE)]
total["state"] = total["state"].replace(
    {"Pulau Pinang": "Penang", "W.P. Kuala Lumpur": "Kuala Lumpur"}
)

# ── National average per year (weighted by abs deaths) ───────────────────────
nat_rows = []
for yr, grp in total.groupby("year"):
    w_mean = np.average(grp["rate"], weights=grp["abs"].clip(lower=1))
    nat_rows.append({"state": "National Average", "year": int(yr), "imr": round(float(w_mean), 2), "tier": "national"})

# ── Tier classification from 2023 rates ───────────────────────────────────────
rates_2023 = total[total["year"] == 2023].set_index("state")["rate"]
q25 = rates_2023.quantile(0.25)
q75 = rates_2023.quantile(0.75)

def get_tier(state):
    r = rates_2023.get(state)
    if r is None:
        return "middle"
    if r >= q75:
        return "bottom"
    if r <= q25:
        return "top"
    return "middle"

# ── State order ───────────────────────────────────────────────────────────────
state_order = rates_2023.sort_values(ascending=False).index.tolist()

# ── Base 2000 for change calc ─────────────────────────────────────────────────
base_2000 = total[total["year"] == 2000].set_index("state")["rate"]

records = []
for _, row in total.iterrows():
    state = row["state"]
    base = base_2000.get(state)
    pct = round((row["rate"] - base) / base * 100, 1) if base else None
    records.append({
        "state":          state,
        "year":           int(row["year"]),
        "imr":            round(float(row["rate"]), 2),
        "imr_change_pct": pct,
        "tier":           get_tier(state),
        "state_order":    state_order.index(state) if state in state_order else 99,
    })
records += nat_rows
records.sort(key=lambda r: (r.get("state_order", -1), r["year"]))

# ── Diagnostics ───────────────────────────────────────────────────────────────
print("=== ch09 — Line Chart: Diverging Fan ===\n")
print(f"Q25={q25:.1f}  Q75={q75:.1f}")
print("\n2023 rates:")
for s in state_order:
    r = rates_2023[s]
    t = get_tier(s)
    b = base_2000.get(s, float("nan"))
    print(f"  {t:8} {s:25} 2000={b:.1f}  2023={r:.1f}")

spread_2000 = total[total["year"] == 2000]["rate"]
spread_2023 = total[total["year"] == 2023]["rate"]
print(f"\nSpread 2000: {spread_2000.max():.1f}–{spread_2000.min():.1f} = {spread_2000.max()-spread_2000.min():.1f}")
print(f"Spread 2023: {spread_2023.max():.1f}–{spread_2023.min():.1f} = {spread_2023.max()-spread_2023.min():.1f}")

kelantan_2000 = float(base_2000.get("Kelantan", 0))
kelantan_2023 = float(rates_2023.get("Kelantan", 0))
print(f"\nKelantan change: {(kelantan_2023 - kelantan_2000) / kelantan_2000 * 100:+.1f}%")

with open("chapters/ch09/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\n✓ Wrote {len(records)} records → chapters/ch09/data.json")
