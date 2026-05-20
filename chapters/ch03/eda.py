"""
Chapter 3 — The Doctor Desert
eda.py: Exploratory data analysis on data.json produced by procure.py

Run from the fit2179-a2 root:
    source .venv/bin/activate
    python3 chapters/ch03/eda.py
"""

import json
import pandas as pd
import numpy as np

# ── Load ───────────────────────────────────────────────────────────────────────
with open("chapters/ch03/data.json") as f:
    raw = json.load(f)

# Separate metadata record from state records
meta   = next(r for r in raw if "_meta" in r)["_meta"]
states = pd.DataFrame([r for r in raw if "_meta" not in r])

WHO_THRESHOLD  = meta["who_threshold"]    # 44.5 skilled health professionals / 10k (SDG)
PHYSICIAN_MIN  = 10.0                     # WHO minimum physician density / 10k
WB_NATIONAL    = meta["wb_national_per_10k"]   # 23.41 / 10k  (World Bank 2023)
YEAR           = meta["year"]

print("=" * 66)
print(f"CHAPTER 3 — THE DOCTOR DESERT  ({YEAR} data)")
print("=" * 66)

# ── 1. Summary statistics ──────────────────────────────────────────────────────
print("\n[1] NATIONAL SUMMARY")
print(f"  States in dataset : {len(states)}")
print(f"  Total doctors     : {states['doctors'].sum():,}")
print(f"  Total population  : {states['population'].sum():,}")
national_ratio = states["doctors"].sum() / states["population"].sum() * 10_000
print(f"  Computed national ratio : {national_ratio:.2f} per 10,000")
print(f"  World Bank national     : {WB_NATIONAL:.2f} per 10,000  (includes private sector)")
print(f"  WHO SDG threshold (all skilled HPs) : {WHO_THRESHOLD} per 10,000")
print(f"  WHO physician minimum               : {PHYSICIAN_MIN} per 10,000")

# ── 2. Full ranking ────────────────────────────────────────────────────────────
print("\n[2] ALL STATES RANKED (lowest to highest doctors/10k)")
print(f"  {'State':<25} {'Doctors':>8} {'Population':>12} {'per 10k':>9} {'Gap to WB natl':>15}")
print("  " + "-" * 72)
for _, r in states.sort_values("doctors_per_10k").iterrows():
    gap = r["doctors_per_10k"] - WB_NATIONAL
    flag = " ◄ BELOW national avg" if gap < 0 else ""
    print(f"  {r['state']:<25} {r['doctors']:>8,} {r['population']:>12,} "
          f"{r['doctors_per_10k']:>9.2f} {gap:>+15.2f}{flag}")

# ── 3. Putrajaya outlier ───────────────────────────────────────────────────────
print("\n[3] PUTRAJAYA OUTLIER")
putrajaya = states[states["state"] == "W.P. Putrajaya"].iloc[0]
print(f"  W.P. Putrajaya: {putrajaya['doctors_per_10k']:.1f} / 10k")
print(f"  Population: {putrajaya['population']:,}  |  Doctors: {putrajaya['doctors']:,}")
print("  NOTE: Putrajaya is the federal administrative capital. The high ratio")
print("  reflects government ministry hospitals serving a tiny resident population.")
print("  It should be treated as a statistical outlier for geographic storytelling.")

# Exclude Putrajaya for core analysis
core = states[states["state"] != "W.P. Putrajaya"].copy()

# ── 4. Urban–rural gap ────────────────────────────────────────────────────────
print("\n[4] URBAN–RURAL / PENINSULAR–EAST MALAYSIA GAP")
top3 = core.nlargest(3, "doctors_per_10k")[["state", "doctors_per_10k"]]
bot3 = core.nsmallest(3, "doctors_per_10k")[["state", "doctors_per_10k"]]
print("  Top 3 (excluding Putrajaya):")
for _, r in top3.iterrows():
    print(f"    {r['state']:<25} {r['doctors_per_10k']:.2f} / 10k")
print("  Bottom 3:")
for _, r in bot3.iterrows():
    print(f"    {r['state']:<25} {r['doctors_per_10k']:.2f} / 10k")

kl_val    = core[core["state"] == "W.P. Kuala Lumpur"]["doctors_per_10k"].values[0]
sabah_val = core[core["state"] == "Sabah"]["doctors_per_10k"].values[0]
labuan_val = core[core["state"] == "W.P. Labuan"]["doctors_per_10k"].values[0]
print(f"\n  KL vs Sabah ratio     : {kl_val:.2f} / {sabah_val:.2f} = {kl_val/sabah_val:.1f}×")
print(f"  KL vs Labuan ratio    : {kl_val:.2f} / {labuan_val:.2f} = {kl_val/labuan_val:.1f}×")
print(f"  Max/Min ratio (excl Putrajaya): "
      f"{core['doctors_per_10k'].max():.2f} / {core['doctors_per_10k'].min():.2f} "
      f"= {core['doctors_per_10k'].max() / core['doctors_per_10k'].min():.1f}×")

# ── 5. States below national average ──────────────────────────────────────────
print("\n[5] STATES BELOW NATIONAL AVERAGE (WHO / World Bank: ~23 per 10k)")
below_natl = core[core["doctors_per_10k"] < WB_NATIONAL].sort_values("doctors_per_10k")
above_natl = core[core["doctors_per_10k"] >= WB_NATIONAL]
print(f"  {len(below_natl)} of {len(core)} states (excl. Putrajaya) are below the national average:")
for _, r in below_natl.iterrows():
    pop_m = r["population"] / 1_000_000
    print(f"    {r['state']:<25} {r['doctors_per_10k']:.2f} / 10k  (pop {pop_m:.2f}M)")
print(f"\n  Combined population living below national average: "
      f"{below_natl['population'].sum():,} "
      f"({below_natl['population'].sum()/core['population'].sum()*100:.1f}% of total)")

# ── 6. Regional breakdown ─────────────────────────────────────────────────────
print("\n[6] REGIONAL BREAKDOWN")
region_stats = (
    core.groupby("region")
    .agg(
        states=("state", "count"),
        total_doctors=("doctors", "sum"),
        total_pop=("population", "sum"),
    )
    .assign(doctors_per_10k=lambda d: (d["total_doctors"] / d["total_pop"] * 10_000).round(2))
    .sort_values("doctors_per_10k")
)
print(region_stats[["states", "total_doctors", "total_pop", "doctors_per_10k"]].to_string())

# ── 7. East Malaysia deep-dive ────────────────────────────────────────────────
print("\n[7] EAST MALAYSIA DEEP-DIVE")
em = core[core["region"] == "east_malaysia"]
for _, r in em.sort_values("doctors_per_10k").iterrows():
    doctors_needed = int((WB_NATIONAL - r["doctors_per_10k"]) / 10_000 * r["population"])
    print(f"  {r['state']:<20} {r['doctors_per_10k']:.2f}/10k  "
          f"→ needs +{max(0,doctors_needed):,} more doctors to reach national avg")

# ── 8. Distribution statistics ────────────────────────────────────────────────
print("\n[8] DISTRIBUTION STATISTICS (excl. Putrajaya)")
desc = core["doctors_per_10k"].describe()
print(f"  Mean   : {desc['mean']:.2f}")
print(f"  Median : {desc['50%']:.2f}")
print(f"  Std dev: {desc['std']:.2f}")
print(f"  CV (coeff of variation): {desc['std']/desc['mean']*100:.1f}%")
print("  (CV > 30% indicates high inequality in distribution)")

# Gini-like: ratio of top-quartile to bottom-quartile ratio
q75 = core["doctors_per_10k"].quantile(0.75)
q25 = core["doctors_per_10k"].quantile(0.25)
print(f"  IQR ratio (Q3/Q1): {q75/q25:.2f}×")

# ── 9. Population-weighted analysis ───────────────────────────────────────────
print("\n[9] POPULATION-WEIGHTED ANALYSIS")
# What ratio does the average Malaysian actually experience?
pw_ratio = np.average(core["doctors_per_10k"], weights=core["population"])
print(f"  Population-weighted mean ratio: {pw_ratio:.2f} per 10,000")
print(f"  Unweighted mean ratio         : {core['doctors_per_10k'].mean():.2f} per 10,000")
print(f"  Gap (pop-weighted vs unweighted): {pw_ratio - core['doctors_per_10k'].mean():.2f}")
print("  NOTE: Population-weighted mean is close to the unweighted mean — the")
print("  maldistribution is not primarily driven by population size alone.")

# ── 10. Key data story findings ────────────────────────────────────────────────
print("\n" + "=" * 66)
print("FINDINGS SUMMARY FOR CHAPTER 3 NARRATIVE")
print("=" * 66)

print(f"""
DATA YEAR: {YEAR}  |  Source: MOH PIK (data.gov.my) + OpenDOSM

KEY NUMBERS:
  • National ratio  : ~{national_ratio:.0f} doctors per 10,000 people
  • World Bank (2023): {WB_NATIONAL} per 10,000 (includes public + private sector)
  • KL (highest*)   : {kl_val:.1f} per 10,000
  • Sabah (lowest*) : {sabah_val:.1f} per 10,000  (* excl. W.P. Putrajaya outlier)
  • KL-to-Sabah gap : {kl_val/sabah_val:.1f}× more doctors per capita in KL vs Sabah

STATES BELOW NATIONAL AVERAGE ({len(below_natl)} of {len(core)}):
  {', '.join(below_natl['state'].tolist())}
  These states together hold {below_natl['population'].sum()/core['population'].sum()*100:.0f}% of Malaysia's population.

EAST MALAYSIA:
  Sabah ({sabah_val:.1f}/10k) and Sarawak ({states[states['state']=='Sarawak']['doctors_per_10k'].values[0]:.1f}/10k)
  are among the lowest in the country, despite being the largest states by land area.
  The geographic challenge compounds the statistical one: a doctor in Kota Kinabalu
  does not serve the interior of Sabah.

PUTRAJAYA ANOMALY:
  Putrajaya ({putrajaya['doctors_per_10k']:.0f}/10k) should be excluded from maps
  as it is a federal administrative enclave, not a normal residential state.
  Including it would visually distort any choropleth or bar chart.

CHART IMPLICATION:
  The dot density map will be visually dramatic: nearly all dots cluster
  in the KL–Selangor–Penang corridor. Sabah + Sarawak together have
  {states[states['state'].isin(['Sabah','Sarawak'])]['doctors'].sum():,} doctors
  for {states[states['state'].isin(['Sabah','Sarawak'])]['population'].sum():,} people
  across an area larger than Peninsular Malaysia.

NOTE ON DATA SCOPE:
  These counts include ALL registered doctors (public MOH + private + academic).
  In practice, private-sector doctors in KL serve higher-income patients and
  are not accessible to B40 rural communities — so the effective public-sector
  ratio for ordinary Sabahans is considerably worse than {sabah_val:.1f}/10k.

STORY ADJUSTMENT VS ORIGINAL SCRIPT:
  The original script estimated KL at 42.1 and Sabah at 5.1 (8× gap).
  Live data shows KL at {kl_val:.1f} and Sabah at {sabah_val:.1f} ({kl_val/sabah_val:.1f}× gap).
  The gap is real but smaller than initially written — because the data.gov.my
  dataset aggregates ALL doctors, not just MOH public-sector doctors.
  The narrative should reflect the 3× figure and add context about private-sector
  inaccessibility to explain the real-world severity for rural communities.
""")
