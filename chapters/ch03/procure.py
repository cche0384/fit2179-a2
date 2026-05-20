"""
Chapter 3 — The Doctor Desert
procure.py: Download and merge live data, write data.json

Sources:
  1. Healthcare Staff by State — data.gov.my / Health Informatics Centre (PIK), MOH Malaysia
     https://storage.data.gov.my/healthcare/healthcare_staff.csv
     Columns: state, type, date, staff  (type includes 'doctor', 'nurse', 'dentist', ...)

  2. Population by State — OpenDOSM, DOSM Malaysia
     https://storage.dosm.gov.my/population/population_state.csv
     Columns: state, date, sex, age, ethnicity, population  (population in thousands)

  3. World Bank API — national-level physicians per 1,000 as a benchmark
     https://api.worldbank.org/v2/country/MY/indicator/SH.MED.PHYS.ZS?format=json

Output: data.json — one record per state with fields:
  state, doctors, population, doctors_per_10k,
  doctors_per_10k_moh_only (MOH public sector subset where available),
  year, region, who_threshold_gap
"""

import io, json, os, sys
import requests
import pandas as pd

STAFF_URL = "https://storage.data.gov.my/healthcare/healthcare_staff.csv"
POP_URL   = "https://storage.dosm.gov.my/population/population_state.csv"
WB_URL    = ("https://api.worldbank.org/v2/country/MY/indicator/"
             "SH.MED.PHYS.ZS?format=json&mrv=10")

WHO_THRESHOLD = 44.5   # WHO recommended 44.5 doctors per 10,000 (2016 SDG target)
YEAR = 2022            # latest year available in healthcare_staff dataset

HERE    = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(HERE, "raw")
os.makedirs(RAW_DIR, exist_ok=True)

# ── 1. Download and save healthcare staff raw CSV ─────────────────────────────
staff_raw_path = os.path.join(RAW_DIR, "healthcare_staff_raw.csv")
print("Downloading healthcare staff data …")
r = requests.get(STAFF_URL, timeout=30)
r.raise_for_status()
with open(staff_raw_path, "w", encoding="utf-8") as f:
    f.write(r.text)
print(f"  Saved raw file → {staff_raw_path}")
staff = pd.read_csv(staff_raw_path)
staff["date"] = pd.to_datetime(staff["date"])

# Filter: doctors only, target year, exclude national aggregate
doctors = (
    staff[
        (staff["type"] == "doctor") &
        (staff["date"].dt.year == YEAR) &
        (staff["state"] != "Malaysia")
    ]
    .rename(columns={"staff": "doctors"})
    [["state", "doctors"]]
    .reset_index(drop=True)
)
print(f"  {len(doctors)} state rows for doctors in {YEAR}")

# ── 2. Download and save population raw CSV ────────────────────────────────────
pop_raw_path = os.path.join(RAW_DIR, "population_state_raw.csv")
print("Downloading population data …")
r = requests.get(POP_URL, timeout=60)
r.raise_for_status()
with open(pop_raw_path, "w", encoding="utf-8") as f:
    f.write(r.text)
print(f"  Saved raw file → {pop_raw_path}")
pop = pd.read_csv(pop_raw_path)
pop["date"] = pd.to_datetime(pop["date"])

# Filter: target year, both sexes, overall age, overall ethnicity
pop_2022 = (
    pop[
        (pop["date"].dt.year == YEAR) &
        (pop["sex"] == "both") &
        (pop["age"] == "overall") &
        (pop["ethnicity"] == "overall") &
        (pop["state"] != "Malaysia")
    ]
    [["state", "population"]]
    .reset_index(drop=True)
)
# Population is in thousands in DOSM dataset — convert to absolute
pop_2022["population"] = (pop_2022["population"] * 1000).round().astype(int)
print(f"  {len(pop_2022)} state rows for population in {YEAR}")

# ── 3. Harmonise state names between the two datasets ─────────────────────────
# DOSM uses "Pulau Pinang"; data.gov.my uses "Pulau Pinang" — check for mismatches
name_map = {
    "Pulau Pinang": "Pulau Pinang",  # already identical
}

def normalise(s):
    return name_map.get(s, s)

doctors["state_norm"] = doctors["state"].apply(normalise)
pop_2022["state_norm"] = pop_2022["state"].apply(normalise)

merged = pd.merge(
    doctors.rename(columns={"state": "state_orig_staff"}),
    pop_2022.rename(columns={"state": "state_orig_pop"}),
    on="state_norm",
    how="inner",
)
print(f"  Merged: {len(merged)} states matched")

if len(merged) < len(doctors):
    staff_states = set(doctors["state_norm"])
    pop_states   = set(pop_2022["state_norm"])
    print("  Unmatched staff states:", staff_states - pop_states)
    print("  Unmatched pop states:",   pop_states - staff_states)

# ── 4. Compute doctors per 10,000 ─────────────────────────────────────────────
merged["doctors_per_10k"] = (merged["doctors"] / merged["population"] * 10_000).round(2)
merged["who_threshold_gap"] = (merged["doctors_per_10k"] - WHO_THRESHOLD).round(2)

# ── 5. Fetch World Bank national benchmark ────────────────────────────────────
print("Fetching World Bank physicians/1k data …")
try:
    wb_r = requests.get(WB_URL, timeout=15)
    wb_r.raise_for_status()
    wb_data = wb_r.json()
    # Response is [metadata_dict, [records]]
    wb_records = [x for x in wb_data[1] if x["value"] is not None]
    wb_latest  = sorted(wb_records, key=lambda x: x["date"], reverse=True)[0]
    wb_year    = int(wb_latest["date"])
    wb_val_per1k = wb_latest["value"]        # physicians per 1,000
    wb_val_per10k = round(wb_val_per1k * 10, 2)  # convert to per 10,000
    print(f"  World Bank national: {wb_val_per10k} doctors/10k in {wb_year}")
except Exception as e:
    print(f"  World Bank fetch failed ({e}); skipping")
    wb_val_per10k = None
    wb_year = None

# ── 6. Assign regions ─────────────────────────────────────────────────────────
region_map = {
    "W.P. Kuala Lumpur": "central",
    "W.P. Putrajaya":    "central",
    "Selangor":          "central",
    "Melaka":            "south",
    "Johor":             "south",
    "Negeri Sembilan":   "south",
    "Pahang":            "east",
    "Terengganu":        "east",
    "Kelantan":          "east",
    "Perak":             "north",
    "Kedah":             "north",
    "Perlis":            "north",
    "Pulau Pinang":      "north",
    "Sabah":             "east_malaysia",
    "Sarawak":           "east_malaysia",
    "W.P. Labuan":       "east_malaysia",
}
merged["region"] = merged["state_norm"].map(region_map).fillna("other")

# ── 7. Build output records ────────────────────────────────────────────────────
records = []
for _, row in merged.sort_values("doctors_per_10k").iterrows():
    records.append({
        "state":            row["state_norm"],
        "doctors":          int(row["doctors"]),
        "population":       int(row["population"]),
        "doctors_per_10k":  row["doctors_per_10k"],
        "who_threshold_gap": row["who_threshold_gap"],
        "region":           row["region"],
        "year":             YEAR,
    })

# Append national benchmark metadata (not a state record, just metadata)
metadata = {
    "_meta": {
        "source_staff":    STAFF_URL,
        "source_pop":      POP_URL,
        "year":            YEAR,
        "who_threshold":   WHO_THRESHOLD,
        "wb_national_per_10k": wb_val_per10k,
        "wb_year":         wb_year,
        "note": (
            "Population from DOSM (thousands converted to absolute). "
            "Doctor counts from MOH PIK include all registered doctors "
            "(public + private + academic). "
            "WHO threshold 44.5/10k is the 2016 SDG index benchmark."
        ),
    }
}

out_path = os.path.join(os.path.dirname(__file__), "data.json")
with open(out_path, "w") as f:
    json.dump(records + [metadata], f, indent=2, ensure_ascii=False)

print(f"\nWrote {len(records)} state records to {out_path}")
print("\nQuick check:")
print(pd.DataFrame(records)[["state", "doctors_per_10k", "population"]].to_string(index=False))
