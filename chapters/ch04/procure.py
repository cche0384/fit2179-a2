import json
import os
import pandas as pd

os.makedirs("chapters/ch04/raw", exist_ok=True)

# ── Load DOSM early childhood death rates ────────────────────────────────────
df = pd.read_csv("chapters/ch01/raw/dosm_imr_state.csv")
df = df[df["type"] == "total"].copy()
df["year"] = pd.to_datetime(df["date"]).dt.year

# Exclude small territories with unreliable data
EXCLUDE = {"W.P. Putrajaya", "W.P. Labuan"}
df = df[~df["state"].isin(EXCLUDE)]

# Harmonise display names
NAME_MAP = {"Pulau Pinang": "Penang", "W.P. Kuala Lumpur": "Kuala Lumpur"}
df["state"] = df["state"].replace(NAME_MAP)

# ── Compute change since 2000 for each state ─────────────────────────────────
base_2000 = (
    df[df["year"] == 2000]
    .set_index("state")["rate"]
    .rename("base_rate")
)
df = df.join(base_2000, on="state")
df["imr_change_pct"] = (
    (df["rate"] - df["base_rate"]) / df["base_rate"] * 100
).round(1)
df.loc[df["base_rate"].isna(), "imr_change_pct"] = None

# ── State order: sorted by 2023 rate descending (worst at top) ───────────────
rates_2023 = (
    df[df["year"] == 2023]
    .sort_values("rate", ascending=False)
    .reset_index(drop=True)
)
state_order = {row["state"]: i for i, row in rates_2023.iterrows()}
df["state_order"] = df["state"].map(state_order)

# ── Print diagnostics ─────────────────────────────────────────────────────────
print("=== ch04 — Early Childhood Death Rate by State × Year ===\n")
print(f"States: {df['state'].nunique()}, Years: {df['year'].nunique()}")
print(f"Year range: {df['year'].min()}–{df['year'].max()}")
print()
print("2023 rates (worst first):")
for _, r in rates_2023.iterrows():
    chg = df[(df["state"] == r["state"]) & (df["year"] == 2023)]["imr_change_pct"].values
    chg_str = f"{chg[0]:+.1f}%" if len(chg) and chg[0] == chg[0] else "n/a"
    print(f"  {r['state']:25} {r['rate']:.1f}/1k  ({chg_str} since 2000)")
print()
print("NOTE: Sabah 2000-2013 rates are anomalously low due to underreporting;")
print("      rates jump in 2014 following improved registration systems.")

# ── Write data.json ───────────────────────────────────────────────────────────
records = []
for _, row in df.sort_values(["state_order", "year"]).iterrows():
    records.append({
        "state":           row["state"],
        "year":            int(row["year"]),
        "imr":             round(float(row["rate"]), 2),
        "imr_change_pct":  round(float(row["imr_change_pct"]), 1) if row["imr_change_pct"] == row["imr_change_pct"] else None,
        "state_order":     int(row["state_order"]),
    })

with open("chapters/ch04/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\n✓ Wrote {len(records)} records → chapters/ch04/data.json")
