#!/usr/bin/env python3
"""
ch06 EDA — explore the international stunting vs. GDP comparison.
Run from repo root: python3 chapters/ch06/eda.py
"""

import json, math, statistics

with open("chapters/ch06/data.json") as f:
    d = json.load(f)

countries = d["countries"]
states    = d["malaysia_states"]

countries_by_gdp = sorted(countries, key=lambda r: r["gdp_ppp"])

print("=" * 70)
print("STUNTING vs. GDP PER CAPITA — all countries with data")
print("=" * 70)
print(f"{'ISO2':5} {'Country':28} {'GDP PPP':>10} {'Stunting':>9} {'Year':>6}")
print("-" * 65)
for r in countries_by_gdp:
    flag = " ◄ MALAYSIA" if r["iso2"] == "MY" else ""
    print(f"{r['iso2']:5} {r['country'][:28]:28} "
          f"{r['gdp_ppp']:>10,.0f} {r['stunting']:>8.1f}%  {r['stunting_year']:>5}{flag}")

# ── Malaysia key stats ────────────────────────────────────────────────────────
my = next(r for r in countries if r["iso2"] == "MY")
print(f"\n{'=' * 70}")
print(f"MALAYSIA DEEP-DIVE")
print(f"  GDP per capita PPP : ${my['gdp_ppp']:,.0f} ({my['gdp_year']})")
print(f"  Stunting rate      : {my['stunting']}% ({my['stunting_year']})")

similar_stunt = [r for r in countries
                 if abs(r["stunting"] - my["stunting"]) < 5 and r["iso2"] != "MY"]
print("\nCountries with similar stunting (±5pp) — income comparison:")
for r in sorted(similar_stunt, key=lambda x: x["gdp_ppp"]):
    ratio = my["gdp_ppp"] / r["gdp_ppp"]
    print(f"  {r['iso2']:3} {r['country'][:25]:25}  "
          f"GDP ${r['gdp_ppp']:>7,.0f}  Stunting {r['stunting']:5.1f}%  "
          f"  (Malaysia is {ratio:.1f}x richer)")

richer_better = [r for r in countries
                 if r["gdp_ppp"] > my["gdp_ppp"] and r["stunting"] < my["stunting"]]
print(f"\nAll {len(richer_better)} countries richer than Malaysia — their stunting:")
for r in sorted(richer_better, key=lambda x: x["gdp_ppp"]):
    print(f"  {r['iso2']:3} {r['country'][:25]:25}  "
          f"GDP ${r['gdp_ppp']:>8,.0f}  Stunting {r['stunting']:4.1f}%")

# ── ASEAN breakdown ───────────────────────────────────────────────────────────
asean_iso = {"MY", "TH", "ID", "PH", "VN", "KH", "LA", "MM", "SG", "BN"}
asean = [r for r in countries if r["iso2"] in asean_iso]
print(f"\n{'=' * 70}")
print("ASEAN COMPARISON")
for r in sorted(asean, key=lambda x: x["gdp_ppp"]):
    print(f"  {r['iso2']:3} {r['country'][:22]:22}  "
          f"GDP ${r['gdp_ppp']:>7,.0f}  Stunting {r['stunting']:5.1f}%  ({r['stunting_year']})")

# ── Malaysia state child mortality ────────────────────────────────────────────
print(f"\n{'=' * 70}")
print(f"MALAYSIA STATE IMR (year {states[0]['year'] if states else '?'})")
for r in sorted(states, key=lambda x: x["imr"], reverse=True):
    bar = "█" * int(r["imr"])
    print(f"  {r['state'][:22]:22}  {r['imr']:5.1f}  {bar}")

worst = max(states, key=lambda x: x["imr"])
best  = min(states, key=lambda x: x["imr"])
print(f"\n  Worst:  {worst['state']} — {worst['imr']} per 1,000")
print(f"  Best:   {best['state']} — {best['imr']} per 1,000")
print(f"  Ratio:  {worst['imr'] / best['imr']:.1f}x")

# ── Log-linear regression ─────────────────────────────────────────────────────
log_gdps  = [math.log(r["gdp_ppp"]) for r in countries]
stuntings = [r["stunting"] for r in countries]
mean_lg   = statistics.mean(log_gdps)
mean_st   = statistics.mean(stuntings)
cov  = sum((x - mean_lg) * (y - mean_st) for x, y in zip(log_gdps, stuntings)) / len(countries)
var  = sum((x - mean_lg) ** 2 for x in log_gdps) / len(countries)
beta  = cov / var
alpha = mean_st - beta * mean_lg
expected = alpha + beta * math.log(my["gdp_ppp"])
print(f"\n{'=' * 70}")
print(f"LOG-LINEAR REGRESSION: stunting ~ log(gdp_ppp)  (n={len(countries)})")
print(f"  Expected stunting at Malaysia's income: {expected:.1f}%")
print(f"  Actual:                                 {my['stunting']}%")
print(f"  Excess above expectation:               {my['stunting'] - expected:.1f} pp")
