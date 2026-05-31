import json
import os

# ── Load Malaysia national stunting from already-downloaded World Bank data ───
with open("chapters/ch06/raw/raw_stunting.json") as f:
    raw = json.load(f)

my_rows = [(r["date"], r["value"]) for r in raw[1]
           if r["countryiso3code"] == "MYS" and r["value"] is not None]
my_rows.sort(key=lambda x: x[0], reverse=True)
national_rate = my_rows[0][1]
national_year = my_rows[0][0]

kh_rows = [(r["date"], r["value"]) for r in raw[1]
           if r["countryiso3code"] == "KHM" and r["value"] is not None]
kh_rows.sort(key=lambda x: x[0], reverse=True)
cambodia_rate = kh_rows[0][1]

print(f"Malaysia national stunting: {national_rate:.1f}%  (WB {national_year})")
print(f"Cambodia stunting: {cambodia_rate:.1f}%")

# ── Group definitions ─────────────────────────────────────────────────────────
# Sabah ~35% and Selangor ~12% from NHMS 2019 subnational survey
# Added Thailand (12.4%) and Vietnam (18.2%) from World Bank 2023/2022
GROUPS = [
    {"group": "Sabah",     "rate": 35.0, "order": 0, "region": "Malaysia"},
    {"group": "National",  "rate": round(national_rate, 1), "order": 1, "region": "Malaysia"},
    {"group": "Selangor",  "rate": 12.0, "order": 2, "region": "Malaysia"},
    {"group": "Cambodia",  "rate": round(cambodia_rate, 1), "order": 3, "region": "International"},
    {"group": "Vietnam",   "rate": 18.2, "order": 4, "region": "International"},
    {"group": "Thailand",  "rate": 12.4, "order": 5, "region": "International"},
]

records = []
for g in GROUPS:
    n_stunted = round(g["rate"] / 10)  # out of 10 icons
    for i in range(10):
        records.append({
            "group":      g["group"],
            "rate":       g["rate"],
            "order":      g["order"],
            "region":     g["region"],
            "icon_index": i,
            "stunted":    i < n_stunted,
        })

for g in GROUPS:
    n_stunted = round(g["rate"] / 10)
    print(f"  {g['group']:12} {g['rate']:.1f}% → {n_stunted}/10 red")

with open("chapters/ch06/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\n✓ Wrote {len(records)} records → chapters/ch06/data.json")
print(f"Key: Malaysia {national_rate:.1f}% ≈ Cambodia {cambodia_rate:.1f}% (≈5× richer)")
excess = national_rate - 10.0
print(f"Income-predicted at Malaysia's GDP: ~10%; excess = {excess:.1f} pp")
