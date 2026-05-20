"""
Chapter 4 — The Return of the Forgotten Killers
EDA: ASEAN TB incidence vs. poverty rate + Malaysia state poverty breakdown.

Run: python eda.py   (from chapters/ch04/ after running procure.py)
"""

import json
import os

import numpy as np
import pandas as pd

data_path = os.path.join(os.path.dirname(__file__), "data.json")
with open(data_path) as f:
    raw = json.load(f)

scatter = pd.DataFrame(raw["asean_scatter"])
states = pd.DataFrame(raw["malaysia_states"])


# ── 1. ASEAN overview ─────────────────────────────────────────────────────────

print("=" * 60)
print("CHAPTER 4 — TB vs Poverty: ASEAN Country Scatter")
print("=" * 60)
print(f"\nData source (TB):      {raw['metadata']['tb_source']}")
print(f"Data source (poverty): {raw['metadata']['poverty_source_asean']}")
print()

display_cols = ["country", "poverty_rate", "poverty_year", "tb_per_100k", "tb_year"]
print(scatter[display_cols].sort_values("poverty_rate").to_string(index=False))

print(f"\nTB range:      {scatter.tb_per_100k.min():.0f} – {scatter.tb_per_100k.max():.0f} per 100k")
print(f"Poverty range: {scatter.poverty_rate.min():.1f}% – {scatter.poverty_rate.max():.1f}%")


# ── 2. Correlation ────────────────────────────────────────────────────────────

corr_pearson = scatter["poverty_rate"].corr(scatter["tb_per_100k"])
# Spearman manually (no scipy)
rx = scatter["poverty_rate"].rank().values
ry = scatter["tb_per_100k"].rank().values
d2 = ((rx - ry) ** 2).sum()
n_sp = len(rx)
corr_spearman = 1 - 6 * d2 / (n_sp * (n_sp ** 2 - 1))

print(f"\nCorrelation (poverty vs TB):")
print(f"  Pearson  r = {corr_pearson:.3f}")
print(f"  Spearman ρ = {corr_spearman:.3f}")

# Simple linear regression (numpy only)
x = scatter["poverty_rate"].values
y = scatter["tb_per_100k"].values
slope = np.cov(x, y)[0, 1] / np.var(x)
intercept = y.mean() - slope * x.mean()
r_sq = corr_pearson ** 2

print(f"\nLinear fit (OLS):  TB = {slope:.1f} × poverty% + {intercept:.0f}")
print(f"  R²  = {r_sq:.3f}  → poverty rate explains {r_sq*100:.0f}% of variance in TB rate")


# ── 3. Residuals — who over/under-performs? ───────────────────────────────────

scatter = scatter.copy()
scatter["tb_predicted"] = slope * scatter["poverty_rate"] + intercept
scatter["residual"] = scatter["tb_per_100k"] - scatter["tb_predicted"]

print("\nResiduals (actual TB − predicted from poverty):")
for _, row in scatter.sort_values("residual", ascending=False).iterrows():
    direction = "↑ higher TB than poverty predicts" if row.residual > 0 else "↓ lower TB than poverty predicts"
    flag = " ← MALAYSIA" if row.iso2 == "MY" else ""
    print(f"  {row.country:20s}  residual={row.residual:+6.0f}  {direction}{flag}")


# ── 4. Malaysia: where does it stand? ────────────────────────────────────────

my = scatter[scatter.iso2 == "MY"].iloc[0]
rank_pov = int((scatter["poverty_rate"] < my.poverty_rate).sum()) + 1
rank_tb = int((scatter["tb_per_100k"] < my.tb_per_100k).sum()) + 1
n = len(scatter)

print(f"\nMalaysia's position in ASEAN ({n} countries with data):")
print(f"  Poverty rate: {my.poverty_rate:.1f}% — rank {rank_pov}/{n} (1=lowest poverty)")
print(f"  TB incidence: {my.tb_per_100k:.0f}/100k — rank {rank_tb}/{n} (1=lowest TB)")
print(f"  Malaysia's TB is {my.residual:+.0f}/100k vs. what poverty level predicts")


# ── 5. Data quality flags ─────────────────────────────────────────────────────

print("\nData quality flags:")
for _, row in scatter.iterrows():
    yr_gap = abs(row.tb_year - row.poverty_year)
    if yr_gap > 2:
        print(f"  ⚠ {row.country}: poverty data from {row.poverty_year}, TB from {row.tb_year} ({yr_gap}yr gap)")
    else:
        print(f"  ✓ {row.country}: TB {row.tb_year}, poverty {row.poverty_year}")


# ── 6. Malaysia state poverty breakdown ──────────────────────────────────────

print("\n" + "=" * 60)
print("Malaysia State Poverty Breakdown (DOSM 2022)")
print("=" * 60)
print()
print(states[["state", "poverty_absolute", "poverty_hardcore"]].sort_values("poverty_absolute", ascending=False).to_string(index=False))

national_avg = states["poverty_absolute"].mean()
print(f"\nSimple average across states: {national_avg:.1f}%")
print(f"National rate (from World Bank): {my.poverty_rate:.1f}%")

sabah = states[states.state == "Sabah"].iloc[0]
print(f"\nSabah poverty rate ({sabah.year}): {sabah.poverty_absolute:.1f}%")
print(f"  → On ASEAN poverty-TB curve, that poverty level predicts ~{slope * sabah.poverty_absolute + intercept:.0f}/100k TB")
print(f"  → National Malaysia average: {my.tb_per_100k:.0f}/100k")

top3_poverty = states.nlargest(3, "poverty_absolute")
bottom3_poverty = states.nsmallest(3, "poverty_absolute")
poverty_gap = top3_poverty.poverty_absolute.mean() - bottom3_poverty.poverty_absolute.mean()
print(f"\nTop-3 highest poverty states: {', '.join(top3_poverty.state.tolist())} (avg {top3_poverty.poverty_absolute.mean():.1f}%)")
print(f"Top-3 lowest poverty states:  {', '.join(bottom3_poverty.state.tolist())} (avg {bottom3_poverty.poverty_absolute.mean():.1f}%)")
print(f"Internal poverty gap: {poverty_gap:.1f} percentage points")


# ── 7. Key insights for visualisation ────────────────────────────────────────

print("\n" + "=" * 60)
print("KEY FINDINGS FOR VISUALISATION")
print("=" * 60)
print(f"""
1. STRONG correlation (Spearman ρ={corr_spearman:.2f}) between national poverty
   rate and TB incidence across ASEAN: richer countries have fewer TB cases.

2. Philippines (poverty 15.5%, TB 627/100k) and Myanmar (poverty 24.8%,
   TB 434/100k) are the extreme high end; Vietnam (4.2%, 178/100k) and
   Malaysia (5.1%, 98/100k) cluster at the lower end.

3. Malaysia's TB rate of {my.tb_per_100k:.0f}/100k is {abs(my.residual):.0f}/100k
   {'ABOVE' if my.residual > 0 else 'below'} what its poverty level predicts —
   suggesting structural health system factors beyond income alone.

4. Within Malaysia, Sabah (19.7% poverty) has a poverty rate comparable to
   Lao PDR (15%) and Philippines (15.5%), the two highest-TB nations in
   the dataset. Kelantan (13.2%) and Sarawak (10.8%) also sit in the
   high-poverty tier.

5. The poverty gap within Malaysia (Sabah 19.7% vs KL 1.4%) spans
   {states.poverty_absolute.max() - states.poverty_absolute.min():.1f} percentage points — wider than the distance between
   Malaysia and Thailand at the ASEAN level ({abs(my.poverty_rate - scatter[scatter.iso2=='TH'].iloc[0].poverty_rate):.1f} pts).

6. DATA QUALITY: Myanmar poverty data is from 2017 (5yr gap to TB 2022).
   Should be rendered with reduced opacity or asterisked in the chart.

CHART DESIGN NOTES:
  - Primary: scatter plot (poverty_rate x-axis, tb_per_100k y-axis,
    circle size = population)
  - Highlight Malaysia in red (#C8102E); trend line in grey
  - Secondary: inset bar chart of Malaysia state poverty_absolute rates
    to show Sabah/Kelantan sit in high-risk territory
  - Annotate Philippines and Myanmar as extreme outliers
  - Myanmar: lighter opacity / asterisk for data year mismatch
""")
