"""
Chapter 10 — The Prescription We Keep Ignoring
procure.py: Compiles state-level data from all previous chapters and computes
Pearson correlations with life expectancy.

Sources (no downloads needed — all data already exists):
  ch01/data.json  → life_expectancy, imr by state
  ch02/data.json  → spending_per_capita by state
  ch03/data.json  → doctors_per_10k by state
  ch07/data.json  → poverty_pct, screening_pct by state

Output:
  data.json — two lists:
    "correlations"  — [{variable, correlation, direction, label}]
    "state_scatter" — [{state, life_expectancy, poverty_pct, spending_per_capita,
                        doctors_per_10k, imr}]
"""
import json
import math
import pandas as pd

def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den else 0.0


# ── Load each chapter dataset ──────────────────────────────────────────────────

with open("chapters/ch01/data.json") as f:
    ch01 = pd.DataFrame(json.load(f))

with open("chapters/ch02/data.json") as f:
    ch02 = pd.DataFrame(json.load(f))

with open("chapters/ch03/data.json") as f:
    ch03 = pd.DataFrame(json.load(f))

with open("chapters/ch07/data.json") as f:
    ch07_raw = json.load(f)
ch07 = pd.DataFrame(ch07_raw).rename(columns={"state_name": "state"})

# ── Normalise state names (Pulau Pinang → Penang) ─────────────────────────────

RENAME = {"Pulau Pinang": "Penang", "W.P. Kuala Lumpur": "Kuala Lumpur"}

for df in (ch01, ch02, ch03, ch07):
    df["state"] = df["state"].replace(RENAME)

# ── Build merged state panel ───────────────────────────────────────────────────

EXCLUDE = {"W.P. Labuan", "W.P. Putrajaya"}

base = ch01[["state", "life_expectancy", "imr"]].copy()
base = base[~base["state"].isin(EXCLUDE)].copy()

spending = ch02[["state", "spending_per_capita"]].copy()
spending = spending[~spending["state"].isin(EXCLUDE)]

doctors = ch03[["state", "doctors_per_10k"]].copy()
doctors = doctors[~doctors["state"].isin(EXCLUDE)]

poverty = ch07[["state", "poverty_pct", "screening_pct"]].copy()

merged = (
    base
    .merge(spending, on="state", how="left")
    .merge(doctors, on="state", how="left")
    .merge(poverty, on="state", how="left")
)

# Drop rows missing the LE outcome
merged = merged.dropna(subset=["life_expectancy"])

print(f"Panel: {len(merged)} states")
print(merged[["state", "life_expectancy", "imr", "spending_per_capita",
              "doctors_per_10k", "poverty_pct"]].to_string(index=False))

# ── Compute Pearson correlations with life_expectancy ─────────────────────────

le = merged["life_expectancy"].tolist()

VARS = {
    "Poverty incidence (%)":            ("poverty_pct", "negative"),
    "Health spending (per capita, RM)": ("spending_per_capita", "positive"),
    "Doctors per 10,000 pop.":          ("doctors_per_10k", "positive"),
    "B40 screening coverage (%)":       ("screening_pct", "negative"),
}

correlations = []
for label, (col, direction) in VARS.items():
    sub = merged[["life_expectancy", col]].dropna()
    if len(sub) < 4:
        print(f"  Skipped {col}: only {len(sub)} rows")
        continue
    r = pearson(sub["life_expectancy"].tolist(), sub[col].tolist())
    correlations.append({
        "variable": label,
        "correlation": round(r, 3),
        "direction": direction,
        "abs_correlation": round(abs(r), 3),
    })
    print(f"  r({label}): {r:+.3f}")

correlations.sort(key=lambda x: x["abs_correlation"], reverse=True)

# ── State scatter data (for lollipop / hover detail) ─────────────────────────

scatter = []
for _, row in merged.iterrows():
    scatter.append({
        "state": row["state"],
        "life_expectancy": round(row["life_expectancy"], 1),
        "imr": row["imr"],
        "spending_per_capita": row["spending_per_capita"],
        "doctors_per_10k": row["doctors_per_10k"],
        "poverty_pct": row["poverty_pct"],
        "screening_pct": row["screening_pct"],
    })

# ── Save ──────────────────────────────────────────────────────────────────────

# data.json = correlations array (loaded directly by chart.json)
with open("chapters/ch10/data.json", "w") as f:
    json.dump(correlations, f, indent=2)

# state_data.json = raw scatter for optional secondary view
with open("chapters/ch10/state_data.json", "w") as f:
    json.dump(scatter, f, indent=2)

print(f"\nSaved chapters/ch10/data.json ({len(correlations)} correlations)")
print(f"Saved chapters/ch10/state_data.json ({len(scatter)} states)")
print(f"\nTop predictor: {correlations[0]['variable']} (r={correlations[0]['correlation']:+.3f})")
