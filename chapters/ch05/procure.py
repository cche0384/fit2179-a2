import json
import os
import pandas as pd

# ── Read World Bank OOP data (already downloaded) ─────────────────────────────
wb = pd.read_csv("chapters/ch05/raw/raw_wb.csv")
wb = wb.dropna(subset=["oop_pct_che"]).sort_values("year", ascending=False)
latest = wb.iloc[0]
yr = int(latest["year"])
oop_pct = round(float(latest["oop_pct_che"]), 1)

# ── Public / private split from MNHA ─────────────────────────────────────────
mnha = pd.read_csv("chapters/ch05/raw/raw_dosm_mnha.csv")
mnha["year"] = pd.to_datetime(mnha["date"]).dt.year
ceh = mnha[mnha["variable"] == "ceh"]
pub_rows = ceh[(ceh["sector"] == "public") & (ceh["year"] == yr)]["expenditure"].values
tot_rows = ceh[(ceh["sector"] == "total")  & (ceh["year"] == yr)]["expenditure"].values
if len(pub_rows) and len(tot_rows):
    gov_pct = round(pub_rows[0] / tot_rows[0] * 100, 1)
else:
    pub2 = ceh[(ceh["sector"] == "public") & (ceh["year"] == 2022)]["expenditure"].values[0]
    tot2 = ceh[(ceh["sector"] == "total")  & (ceh["year"] == 2022)]["expenditure"].values[0]
    gov_pct = round(pub2 / tot2 * 100, 1)
    yr = 2022

private_ins_pct = round(100 - gov_pct - oop_pct, 1)
if private_ins_pct < 0:
    private_ins_pct = 0
    oop_pct = round(100 - gov_pct, 1)

print(f"Year: {yr}")
print(f"Government:        {gov_pct}%")
print(f"Private Insurance: {private_ins_pct}%")
print(f"Out-of-Pocket:     {oop_pct}%")

# ── Build 100-cell waffle grid ─────────────────────────────────────────────────
gov_cells = round(gov_pct)
ins_cells = round(private_ins_pct)
oop_cells = 100 - gov_cells - ins_cells

records = []
idx = 0
for _ in range(gov_cells):
    records.append({"index": idx, "row": idx // 10, "col": idx % 10,
                    "category": "Government", "pct": gov_pct})
    idx += 1
for _ in range(ins_cells):
    records.append({"index": idx, "row": idx // 10, "col": idx % 10,
                    "category": "Private Insurance", "pct": private_ins_pct})
    idx += 1
for _ in range(oop_cells):
    records.append({"index": idx, "row": idx // 10, "col": idx % 10,
                    "category": "Out-of-Pocket", "pct": oop_pct})
    idx += 1

print(f"\nWaffle: {gov_cells} gov + {ins_cells} ins + {oop_cells} oop = {len(records)} cells")

with open("chapters/ch05/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"✓ Wrote {len(records)} records → chapters/ch05/data.json")

oop_2000 = wb[wb["year"] == 2000]["oop_pc_ppp"].values
oop_now  = wb[wb["year"] == yr]["oop_pc_ppp"].values
if len(oop_2000) and len(oop_now):
    ratio = oop_now[0] / oop_2000[0]
    print(f"\nOOP per capita 2000→{yr}: ${oop_2000[0]:.0f} → ${oop_now[0]:.0f}  ({ratio:.1f}×)")
