import json
import os
import pandas as pd

os.makedirs("chapters/ch07/raw", exist_ok=True)

# ── Load World Bank health expenditure data ────────────────────────────────────
wb = pd.read_csv("chapters/ch05/raw/raw_wb.csv")
# Columns: year, oop_pc_ppp, gdp_pc_ppp, oop_pct_che, che_pct_gdp, ...
wb = wb[wb["year"].between(2000, 2023)].copy()
wb = wb.sort_values("year")

# Total CHE per capita (PPP) = GDP per capita * che_pct_gdp / 100
wb["che_pc"] = wb["gdp_pc_ppp"] * wb["che_pct_gdp"] / 100

# OOP per capita (PPP) — already in raw_wb.csv
# wb["oop_pc"] = wb["oop_pc_ppp"]

# ── Load MNHA for public/private split (2013–2022) ────────────────────────────
mnha = pd.read_csv("chapters/ch05/raw/raw_dosm_mnha.csv")
mnha["year"] = pd.to_datetime(mnha["date"]).dt.year
# Use current health expenditure (ceh), total sector gives correct denominator
ceh_pub = mnha[(mnha["variable"] == "ceh") & (mnha["sector"] == "public")]
ceh_tot = mnha[(mnha["variable"] == "ceh") & (mnha["sector"] == "total")]

pub_share = (
    ceh_pub.set_index("year")["expenditure"] /
    ceh_tot.set_index("year")["expenditure"]
).rename("pub_share")

# For 2000–2012, use the 2013 public share as approximation
earliest_pub_share = pub_share.loc[2013]
pub_share_full = pd.Series(
    index=range(2000, 2024),
    data=[pub_share.get(y, earliest_pub_share) for y in range(2000, 2024)]
)

# ── Compute 3 components per year ─────────────────────────────────────────────
records = []
for _, row in wb.iterrows():
    yr = int(row["year"])
    che = row["che_pc"]
    oop = row["oop_pc_ppp"]
    pub = pub_share_full.get(yr, earliest_pub_share)
    gov = che * pub
    ins = che - gov - oop
    if ins < 0:
        ins = 0
    records += [
        {"year": yr, "category": "Government",        "value": round(gov, 1)},
        {"year": yr, "category": "Private Insurance",  "value": round(ins, 1)},
        {"year": yr, "category": "Out-of-Pocket",      "value": round(oop, 1)},
    ]

with open("chapters/ch07/data.json", "w") as f:
    json.dump(records, f, indent=2)

# ── Diagnostics ───────────────────────────────────────────────────────────────
print("=== ch07 — Health Expenditure by Source (PPP $ per capita) ===\n")
df = pd.DataFrame(records)
pivot = df.pivot(index="year", columns="category", values="value")
pivot["Total"] = pivot.sum(axis=1)
print(pivot[["Government", "Private Insurance", "Out-of-Pocket", "Total"]].to_string())

oop_2000 = pivot.loc[2000, "Out-of-Pocket"]
oop_last = pivot["Out-of-Pocket"].dropna().iloc[-1]
yr_last  = pivot["Out-of-Pocket"].dropna().index[-1]
ratio = oop_last / oop_2000

print(f"\nOOP 2000: ${oop_2000:.0f}  →  {yr_last}: ${oop_last:.0f}  ({ratio:.1f}×)")
print(f"✓ Wrote {len(records)} records → chapters/ch07/data.json")
