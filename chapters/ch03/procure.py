import json
import os
import pandas as pd

# ── Reload doctor + population data ──────────────────────────────────────────
staff = pd.read_csv("chapters/ch03/raw/healthcare_staff_raw.csv")
docs = staff[
    (staff["type"] == "doctor") &
    (staff["date"] == "2022-01-01") &
    (staff["state"] != "Malaysia")
][["state", "staff"]].rename(columns={"staff": "doctors"})

pop = pd.read_csv("chapters/ch03/raw/population_state_raw.csv")
pop22 = pop[
    (pop["sex"] == "both") & (pop["age"] == "overall") &
    (pop["ethnicity"] == "overall") & (pop["date"] == "2022-01-01") &
    (pop["state"] != "Malaysia")
][["state", "population"]].copy()
pop22["population"] = (pop22["population"] * 1000).astype(int)

df = docs.merge(pop22, on="state")
df["doctors_per_10k"] = df["doctors"] / df["population"] * 10_000

# ── Load IMR for mortality sub-index ─────────────────────────────────────────
imr_df = pd.read_csv("chapters/ch01/raw/dosm_imr_state.csv")
imr_2023 = imr_df[
    (imr_df["type"] == "total") & (imr_df["date"] == "2023-01-01")
][["state", "rate"]].rename(columns={"rate": "imr_2023"})
# Harmonise state names
imr_2023["state"] = imr_2023["state"].replace({
    "Pulau Pinang": "Pulau Pinang",  # keep as-is for now; merge on dosm names
})
df = df.merge(imr_2023, on="state", how="left")

# ── Composite access index ────────────────────────────────────────────────────
# z-score each component; index = doctors z-score - imr z-score
# (higher doctors = better; higher IMR = worse → flip sign)
def zscore(s):
    return (s - s.mean()) / s.std()

# Exclude Putrajaya from the z-score (outlier: 172.9/10k)
# Exclude Putrajaya (federal enclave outlier: 172.9/10k doctors, unreliable small-pop IMR)
EXCLUDE_BIN = {"W.P. Putrajaya"}
mask = ~df["state"].isin(EXCLUDE_BIN)
df_main = df[mask].copy()
df_main["z_docs"] = zscore(df_main["doctors_per_10k"])
df_main["z_imr"]  = zscore(df_main["imr_2023"])
df_main["composite"] = df_main["z_docs"] - df_main["z_imr"]

# Bin into 4 tiers using qcut
tier_labels = ["Critical", "Under-resourced", "Adequate", "Well-served"]
df_main["tier_num"], bins = pd.qcut(df_main["composite"], q=4, labels=False, retbins=True)
df_main["tier"] = df_main["tier_num"].map({i: t for i, t in enumerate(tier_labels)})

# ── GADM name mapping ─────────────────────────────────────────────────────────
DOSM_TO_GADM = {
    "Johor": "Johor", "Kedah": "Kedah", "Kelantan": "Kelantan",
    "Melaka": "Melaka", "Negeri Sembilan": "NegeriSembilan",
    "Pahang": "Pahang", "Perak": "Perak", "Perlis": "Perlis",
    "Pulau Pinang": "PulauPinang", "Sabah": "Sabah", "Sarawak": "Sarawak",
    "Selangor": "Selangor", "Terengganu": "Trengganu",
    "W.P. Kuala Lumpur": "KualaLumpur", "W.P. Labuan": "Labuan",
    "W.P. Putrajaya": "Putrajaya",
}
DISPLAY = {
    "Johor": "Johor", "Kedah": "Kedah", "Kelantan": "Kelantan",
    "Melaka": "Melaka", "Negeri Sembilan": "Negeri Sembilan",
    "Pahang": "Pahang", "Perak": "Perak", "Perlis": "Perlis",
    "Pulau Pinang": "Penang", "Sabah": "Sabah", "Sarawak": "Sarawak",
    "Selangor": "Selangor", "Terengganu": "Terengganu",
    "W.P. Kuala Lumpur": "W.P. Kuala Lumpur",
    "W.P. Labuan": "W.P. Labuan", "W.P. Putrajaya": "W.P. Putrajaya",
}
# ── Regional mapping ──────────────────────────────────────────────────────────
REGION = {
    "Johor": "Peninsular", "Kedah": "Peninsular", "Kelantan": "Peninsular",
    "Melaka": "Peninsular", "Negeri Sembilan": "Peninsular", "Pahang": "Peninsular",
    "Perak": "Peninsular", "Perlis": "Peninsular", "Pulau Pinang": "Peninsular",
    "Selangor": "Peninsular", "Terengganu": "Peninsular",
    "W.P. Kuala Lumpur": "Peninsular", "W.P. Putrajaya": "Peninsular",
    "Sabah": "East Malaysia", "Sarawak": "East Malaysia", "W.P. Labuan": "East Malaysia",
}

# Add Putrajaya as Well-served (extreme outlier: 172.9/10k) so map has no gap
putrajaya = df[df["state"] == "W.P. Putrajaya"].copy()
if not putrajaya.empty:
    putrajaya["composite"] = float("nan")
    putrajaya["tier"] = "Well-served"
    df_main = pd.concat([df_main, putrajaya], ignore_index=True)

df_main["gadm_name"] = df_main["state"].map(DOSM_TO_GADM)
df_main["display"] = df_main["state"].map(DISPLAY)
df_main["region"] = df_main["state"].map(REGION)

# ── Print diagnostics ─────────────────────────────────────────────────────────
print("=== ch03 — Composite Healthcare Access Index ===\n")
print(f"{'Tier':20} {'State':30} {'Docs/10k':>10} {'IMR-2023':>10} {'Composite':>12}")
for tier in tier_labels:
    sub = df_main[df_main["tier"] == tier].sort_values("composite")
    for _, r in sub.iterrows():
        print(f"  {tier:18} {r['display']:28} {r['doctors_per_10k']:10.2f} {r['imr_2023']:10.1f} {r.get('composite', 999):12.2f}")

critical = df_main[df_main["tier"] == "Critical"]["display"].tolist()
print(f"\nCritical states: {critical}")

# ── Write data.json ───────────────────────────────────────────────────────────
records = []
for _, r in df_main.iterrows():
    composite_val = r.get("composite", 0)
    records.append({
        "gadm_name":       r["gadm_name"],
        "state":           r["display"],
        "doctors":         int(r["doctors"]),
        "population":      int(r["population"]),
        "doctors_per_10k": round(float(r["doctors_per_10k"]), 2),
        "imr_2023":        round(float(r["imr_2023"]), 1) if r["imr_2023"] == r["imr_2023"] else None,
        "composite":       round(float(composite_val), 3) if pd.notnull(composite_val) else None,
        "tier":            r["tier"],
        "region":          r["region"],
    })

with open("chapters/ch03/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\n✓ Wrote {len(records)} records → chapters/ch03/data.json")
