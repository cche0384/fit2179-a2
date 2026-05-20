"""
Chapter 2 — You Get What You Pay For
EDA: Total health expenditure per capita vs crude death rate by state (2022)

Data sources:
  - MNHA 2022 Table 4.3 (MOH Malaysia): total health expenditure + population by state
  - OpenDOSM deaths_state: crude death rate per 1,000 population by state

Run: python3 eda.py   (requires data.json from procure.py)

FINDINGS
========
1. Correlation (spending ↔ mortality):
   Overall Pearson r ≈ −0.47 (moderate negative) — but driven by two outliers:
   W.P. Putrajaya (RM 6,154 pc, rate 2.2) and W.P. KL (RM 5,631 pc, rate 5.1).
   Both are urban federal territories with massive private-hospital concentrations
   and a younger, wealthier population. Excluding them → r ≈ −0.05 (near zero).

2. Under-resourced states (high mortality, below-average spending):
   Perak      — RM 1,852 pc,  death rate 8.9  (highest in Malaysia)
   Kedah      — RM 1,506 pc,  death rate 8.2
   Perlis     — RM 2,133 pc,  death rate 8.4  (small state, older population)
   Terengganu — RM 1,599 pc,  death rate 7.3
   Kelantan   — RM 1,516 pc,  death rate 7.3
   Pahang     — RM 1,825 pc,  death rate 6.8
   Sarawak    — RM 1,816 pc,  death rate 6.7

3. Spending gap (max vs min, excluding federal territories):
   Penang (highest peninsular): RM 2,870 pc
   Sabah  (lowest overall):     RM 1,347 pc
   → Sabah receives 53% LESS per capita than Penang despite similar crude mortality.
     This understates Sabah's true health burden: its crude death rate (5.1) is
     artificially low because of its young/migrant-heavy population pyramid.

4. The "spending-not-helping" cluster (high spend, still high mortality):
   Penang, Melaka, Perlis, Negeri Sembilan all spend above the national average
   (~RM 1,990 pc) yet record death rates of 6.6–8.4. This is consistent with
   older population age structures — crude death rate is NOT age-standardised.

5. Caveat — spending measure:
   MNHA Table 4.3 reports TOTAL health expenditure (public + private). Private
   spending heavily inflates KL and Penang figures. A public-only (MOH-budget)
   breakdown by state is not published in open data. The narrative should note
   this and frame it as total health investment rather than government allocation.
   The under-resourced finding still holds: low-income rural states attract
   little private investment AND receive less public funding per capita.

6. National averages used as divergence baseline:
   Mean spending: RM 2,516 pc  (or RM 1,990 pc excluding KL/Putrajaya)
   Mean death rate: 6.56 per 1,000
"""

import json
import math

import pandas as pd

with open("data.json") as f:
    df = pd.DataFrame(json.load(f))

print("=" * 65)
print("Chapter 2 — Health Spending vs Mortality by State (2022)")
print("=" * 65)

print("\n── All states ranked by spending per capita ──────────────────")
print(df[["state", "spending_per_capita", "mortality_rate", "alignment"]]
      .sort_values("spending_per_capita", ascending=False)
      .to_string(index=False))

print("\n── Summary statistics ────────────────────────────────────────")
for col, label in [("spending_per_capita", "Spending (RM pc)"),
                   ("mortality_rate",       "Death rate / 1,000")]:
    s = df[col]
    print(f"{label:25s}  min={s.min():.0f}  max={s.max():.0f}"
          f"  mean={s.mean():.1f}  median={s.median():.1f}")

print("\n── Pearson correlation (all 16 states) ───────────────────────")
r_all = df["spending_per_capita"].corr(df["mortality_rate"])
print(f"  r = {r_all:.3f}  (moderate negative)")

excl = df[~df["state"].isin(["W.P. Putrajaya", "W.P. Kuala Lumpur"])]
r_excl = excl["spending_per_capita"].corr(excl["mortality_rate"])
print(f"  r = {r_excl:.3f}  (excluding KL & Putrajaya — near zero)")
print("  Outlier effect: KL/Putrajaya inflate the correlation artificially.")

print("\n── Alignment breakdown ───────────────────────────────────────")
print(df["alignment"].value_counts().to_string())

print("\n── Under-resourced states (high mortality, below-avg spending) ─")
under = df[df["alignment"] == "under-resourced"].sort_values("mortality_rate", ascending=False)
print(under[["state", "spending_per_capita", "mortality_rate"]].to_string(index=False))

print("\n── Spending gap: highest vs lowest peninsular states ─────────")
peninsular = df[~df["state"].isin(["W.P. Labuan", "W.P. Putrajaya",
                                    "W.P. Kuala Lumpur", "Sabah", "Sarawak"])]
hi = peninsular.loc[peninsular["spending_per_capita"].idxmax()]
lo = peninsular.loc[peninsular["spending_per_capita"].idxmin()]
gap_pct = (hi["spending_per_capita"] - lo["spending_per_capita"]) / lo["spending_per_capita"] * 100
print(f"  Highest: {hi['state']} RM {hi['spending_per_capita']:.0f} pc")
print(f"  Lowest : {lo['state']} RM {lo['spending_per_capita']:.0f} pc")
print(f"  Gap    : {gap_pct:.0f}% more in {hi['state']} vs {lo['state']}")

print("\n── Sabah detail ──────────────────────────────────────────────")
sabah = df[df["state"] == "Sabah"].iloc[0]
print(f"  Spending : RM {sabah['spending_per_capita']:.0f} pc (lowest nationally)")
print(f"  Death rt : {sabah['mortality_rate']} per 1,000 (below national avg 6.6)")
print(f"  Note: crude rate understates burden — young/migrant population pyramid")

print("\n── Chart config note ─────────────────────────────────────────")
print("  Diverging bar chart: x = spending deviation from mean (%)")
print("  Second axis (line/dot): mortality_rate")
print("  Colour: alignment category (red=under-resourced, green=efficient)")
print("  Exclude KL & Putrajaya from main chart (add as footnote outliers)")
print("  National avg spending (excl. KL/Putrajaya): RM",
      round(excl["spending_per_capita"].mean()))
