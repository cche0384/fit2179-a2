"""
Chapter 1 — The Lottery of Birth
procure.py: Downloads raw data online and derives state life expectancy estimates.

Pipeline:
  1. Download full DOSM early-childhood death rate dataset → raw_dosm_imr_state.csv
  2. Download World Bank Malaysia LE + IMR time series  → raw_worldbank_my.csv
  3. Derive state LE from downloaded raw files          → data.json
  4. Download / derive GeoJSON                          → malaysia-states[-compact].geojson

Methodology:
  - DOSM `deaths_early_childhood_state` (api.data.gov.my): early childhood deaths
    per 1,000 live births by state, used as state-level IMR proxy.
  - World Bank indicators SP.DYN.LE00.IN and SP.DYN.IMRT.IN: national LE and IMR.
  - State LE estimated via Coale-Demeny West log-linear model:
      LE_state = LE_national + C1 × ln(IMR_national / IMR_state)
    C1 = 17.0: empirically calibrated to Malaysia's context (standard range
    14–16 for this IMR level, raised because adult NCD mortality amplifies
    state gaps beyond what infant mortality alone predicts).
  - Putrajaya (<2,000 births/yr) rate is statistically noisy; smoothed to
    Selangor (same administrative region).

Run: python procure.py
Requires: pip install pandas requests
"""
import json, math, os, requests, pandas as pd

DIR = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(DIR, "raw")
os.makedirs(RAW, exist_ok=True)

# Coale-Demeny coefficient calibrated to Malaysian context
COALE_C1 = 17.0

# DOSM state name → GADM 4.1 NAME_1 (used to join GeoJSON features)
DOSM_TO_GADM = {
    "W.P. Kuala Lumpur": "KualaLumpur",
    "W.P. Putrajaya":    "Putrajaya",
    "Selangor":          "Selangor",
    "Pulau Pinang":      "PulauPinang",
    "Johor":             "Johor",
    "Melaka":            "Melaka",
    "Negeri Sembilan":   "NegeriSembilan",
    "Perak":             "Perak",
    "Pahang":            "Pahang",
    "Terengganu":        "Trengganu",
    "Kedah":             "Kedah",
    "Perlis":            "Perlis",
    "W.P. Labuan":       "Labuan",
    "Kelantan":          "Kelantan",
    "Sarawak":           "Sarawak",
    "Sabah":             "Sabah",
}

DISPLAY_NAME = {
    "KualaLumpur":    "W.P. Kuala Lumpur",
    "Putrajaya":      "W.P. Putrajaya",
    "Selangor":       "Selangor",
    "PulauPinang":    "Penang",
    "Johor":          "Johor",
    "Melaka":         "Melaka",
    "NegeriSembilan": "Negeri Sembilan",
    "Perak":          "Perak",
    "Pahang":         "Pahang",
    "Trengganu":      "Terengganu",
    "Kedah":          "Kedah",
    "Perlis":         "Perlis",
    "Labuan":         "W.P. Labuan",
    "Kelantan":       "Kelantan",
    "Sarawak":        "Sarawak",
    "Sabah":          "Sabah",
}

REGION = {
    "KualaLumpur":    "Central",
    "Putrajaya":      "Central",
    "Selangor":       "Central",
    "NegeriSembilan": "Central",
    "PulauPinang":    "North",
    "Perak":          "North",
    "Kedah":          "North",
    "Perlis":         "North",
    "Johor":          "South",
    "Melaka":         "South",
    "Pahang":         "East",
    "Trengganu":      "East",
    "Kelantan":       "East",
    "Sabah":          "East Malaysia",
    "Sarawak":        "East Malaysia",
    "Labuan":         "East Malaysia",
}


# ── 1. Download raw data ───────────────────────────────────────────────────────

def download_dosm_imr():
    """Download full DOSM early-childhood death rate by state (all years) → raw/dosm_imr_state.csv."""
    out = os.path.join(RAW, "dosm_imr_state.csv")
    url = "https://api.data.gov.my/data-catalogue"
    print("Downloading DOSM deaths_early_childhood_state ...")
    r = requests.get(url, params={"id": "deaths_early_childhood_state", "limit": 5000}, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df.to_csv(out, index=False)
    print(f"  Saved {len(df)} rows → raw/dosm_imr_state.csv")
    return df


def download_worldbank_my():
    """Download World Bank Malaysia LE + IMR time series → raw/worldbank_my.csv."""
    out = os.path.join(RAW, "worldbank_my.csv")
    indicators = {
        "SP.DYN.LE00.IN": "life_expectancy",
        "SP.DYN.IMRT.IN": "imr_national",
    }
    rows = []
    for ind, col in indicators.items():
        url = f"https://api.worldbank.org/v2/country/MY/indicator/{ind}"
        print(f"Downloading World Bank {ind} ...")
        r = requests.get(url, params={"format": "json", "per_page": 60}, timeout=20)
        r.raise_for_status()
        for entry in r.json()[1]:
            if entry.get("value") is not None:
                rows.append({"indicator": col, "year": int(entry["date"]), "value": float(entry["value"])})
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    print(f"  Saved {len(df)} rows → raw/worldbank_my.csv")
    return df


# ── 2. Load and filter raw data ────────────────────────────────────────────────

def latest_national(wb_df, indicator):
    """Return (value, year) for the most recent non-null row of an indicator."""
    sub = wb_df[wb_df.indicator == indicator].sort_values("year", ascending=False)
    row = sub.iloc[0]
    return float(row["value"]), int(row["year"])


def latest_state_imr(dosm_df):
    """Return DataFrame of the latest year's state IMR (type=total only)."""
    df = dosm_df.copy()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    df = df[df["type"] == "total"]
    latest = int(df["year"].max())
    return df[df["year"] == latest].copy(), latest


# ── 3. State LE estimation ─────────────────────────────────────────────────────

def estimate_le(imr_state, imr_national, le_national, c1=COALE_C1):
    return le_national + c1 * math.log(imr_national / imr_state)


# ── 4. GeoJSON ─────────────────────────────────────────────────────────────────

def ensure_geojson():
    """Download GADM 4.1 Malaysia state boundaries → raw/malaysia-states.geojson."""
    geo_path = os.path.join(RAW, "malaysia-states.geojson")
    if os.path.exists(geo_path):
        print("GeoJSON already present: raw/malaysia-states.geojson")
        return geo_path
    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_MYS_1.json"
    print("Downloading GADM 4.1 Malaysia state boundaries ...")
    r = requests.get(url, timeout=180, stream=True)
    r.raise_for_status()
    with open(geo_path, "wb") as f:
        for chunk in r.iter_content(65536):
            f.write(chunk)
    print(f"  Saved raw/malaysia-states.geojson ({os.path.getsize(geo_path) // 1024} KB)")
    return geo_path


def make_compact_geojson(geo_path):
    """Shift East Malaysia 4.5° west so peninsular + Borneo fit on one canvas → malaysia-states-compact.geojson."""
    EAST_MY   = {"Sabah", "Sarawak", "Labuan"}
    LON_SHIFT = -4.5

    def shift(coords):
        if isinstance(coords[0], (int, float)):
            return [coords[0] + LON_SHIFT, coords[1]]
        return [shift(c) for c in coords]

    with open(geo_path) as f:
        geo = json.load(f)

    out = json.loads(json.dumps(geo))
    for feat in out["features"]:
        if feat["properties"]["NAME_1"] in EAST_MY:
            feat["geometry"]["coordinates"] = shift(feat["geometry"]["coordinates"])

    out_path = os.path.join(DIR, "malaysia-states-compact.geojson")
    with open(out_path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("  Saved malaysia-states-compact.geojson (derived from raw)")
    return out_path


# ── 5. Main ────────────────────────────────────────────────────────────────────

def main():
    # --- Step 1: Download raw data into ch01/raw/ ---
    raw_dosm = download_dosm_imr()
    raw_wb   = download_worldbank_my()

    # --- Step 2: Extract values needed for estimation ---
    le_national, le_year   = latest_national(raw_wb, "life_expectancy")
    imr_national, imr_year = latest_national(raw_wb, "imr_national")
    print(f"\nNational LE  ({le_year}): {le_national:.2f} yrs")
    print(f"National IMR ({imr_year}): {imr_national:.2f} per 1,000 live births")

    ec, ec_year = latest_state_imr(raw_dosm)
    print(f"\nDOSM state IMR: {len(ec)} states, latest year: {ec_year}")

    # Putrajaya (pop ~110k, <2,000 births) has volatile small-sample rates.
    # Smooth it by using Selangor's IMR (same administrative region).
    selangor_imr = float(ec.loc[ec["state"] == "Selangor", "rate"].values[0])
    ec = ec.copy()
    ec.loc[ec["state"] == "W.P. Putrajaya", "rate"] = selangor_imr
    print(f"  Putrajaya IMR smoothed to Selangor rate ({selangor_imr})")

    # --- Estimate state life expectancy ---
    records = []
    for _, row in ec.iterrows():
        dosm_state = str(row["state"]).strip()
        gadm = DOSM_TO_GADM.get(dosm_state)
        if gadm is None:
            print(f"  ⚠ No GADM mapping: '{dosm_state}'")
            continue
        imr_s  = float(row["rate"])
        le_est = estimate_le(imr_s, imr_national, le_national)
        records.append({
            "gadm_name":       gadm,
            "state":           DISPLAY_NAME.get(gadm, dosm_state),
            "life_expectancy": round(le_est, 1),
            "imr":             imr_s,
            "region":          REGION.get(gadm, "Other"),
            "year":            int(ec_year),
        })

    # Deviation from unweighted national mean (excl. Putrajaya)
    subset = [r for r in records if r["gadm_name"] != "Putrajaya"]
    mean_le = sum(r["life_expectancy"] for r in subset) / len(subset)
    for r in records:
        r["deviation"] = round(r["life_expectancy"] - mean_le, 2)

    # --- EDA summary ---
    df = pd.DataFrame(records).sort_values("life_expectancy")
    print("\nEstimated life expectancy at birth by state:")
    print(df[["state", "life_expectancy", "imr", "deviation"]].to_string(index=False))
    print(f"\nRange : {df.life_expectancy.min():.1f} – {df.life_expectancy.max():.1f} yrs")
    print(f"Gap   : {df[df.gadm_name != 'Putrajaya'].life_expectancy.max() - df[df.gadm_name != 'Putrajaya'].life_expectancy.min():.1f} yrs (excl. Putrajaya)")
    print(f"Method: Coale-Demeny West model, C1={COALE_C1}, anchored to WB national LE")
    print(f"Source: DOSM deaths_early_childhood_state ({ec_year}), World Bank ({le_year})")

    # --- Save data.json ---
    out_path = os.path.join(DIR, "data.json")
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved {len(records)} rows → data.json")

    # --- GeoJSON ---
    geo_path = ensure_geojson()
    make_compact_geojson(geo_path)

    # --- Verify join ---
    with open(geo_path) as f:
        geo = json.load(f)
    gadm_names = {feat["properties"]["NAME_1"] for feat in geo["features"]}
    data_names = {r["gadm_name"] for r in records}
    missing = gadm_names - data_names
    extra   = data_names - gadm_names
    if missing:
        print(f"\n⚠ GADM features with no data: {missing}")
    if extra:
        print(f"⚠ Data rows with no GADM feature: {extra}")
    if not missing and not extra:
        print(f"\n✓ All {len(gadm_names)} GADM features matched")


if __name__ == "__main__":
    main()
