"""
Chapter 2 — You Get What You Pay For
Sources:
  1. MNHA 2022 Report (Table 4.3) — Total Health Expenditure + Population by State
     https://storage.data.gov.my/healthcare/pub/mnha_2022.pdf
     Published by: Ministry of Health Malaysia, Planning Division
     License: Open Government Licence Malaysia

  2. OpenDOSM Deaths by State — Crude death rate per 1,000 by state, 2022
     https://storage.dosm.gov.my/demography/death_state.parquet
     Published by: Department of Statistics Malaysia (DOSM)
     License: CC BY 4.0

Run: python3 procure.py
Requires: pip install pandas pyarrow pdfplumber requests
"""

import io
import json
import os
import re

import pandas as pd
import pdfplumber
import requests

MNHA_PDF_URL = "https://storage.data.gov.my/healthcare/pub/mnha_2022.pdf"
DEATHS_PARQUET_URL = "https://storage.dosm.gov.my/demography/death_state.parquet"
TARGET_YEAR = "2022"

RAW_DIR = "raw"
RAW_PDF = os.path.join(RAW_DIR, "mnha_2022.pdf")
RAW_PARQUET = os.path.join(RAW_DIR, "death_state.parquet")

# ── MNHA name → canonical display name & OpenDOSM name ───────────────────────
MNHA_CANON = {
    "Selangor":     ("Selangor",            "Selangor"),
    "FT KL":        ("W.P. Kuala Lumpur",   "W.P. Kuala Lumpur"),
    "Johor":        ("Johor",               "Johor"),
    "Penang":       ("Penang",              "Pulau Pinang"),
    "Perak":        ("Perak",               "Perak"),
    "Sabah":        ("Sabah",               "Sabah"),
    "Sarawak":      ("Sarawak",             "Sarawak"),
    "Kedah":        ("Kedah",               "Kedah"),
    "Pahang":       ("Pahang",              "Pahang"),
    "Kelantan":     ("Kelantan",            "Kelantan"),
    "N.Sembilan":   ("Negeri Sembilan",     "Negeri Sembilan"),
    "Melaka":       ("Melaka",              "Melaka"),
    "Terengganu":   ("Terengganu",          "Terengganu"),
    "FT Putrajaya": ("W.P. Putrajaya",      "W.P. Putrajaya"),
    "Perlis":       ("Perlis",              "Perlis"),
    "FT Labuan":    ("W.P. Labuan",         "W.P. Labuan"),
}

REGION_MAP = {
    "Johor":            "south",
    "Kedah":            "north",
    "Kelantan":         "east",
    "Melaka":           "south",
    "Negeri Sembilan":  "central",
    "Pahang":           "east",
    "Perak":            "north",
    "Perlis":           "north",
    "Penang":           "north",
    "Sabah":            "east_malaysia",
    "Sarawak":          "east_malaysia",
    "Selangor":         "central",
    "Terengganu":       "east",
    "W.P. Kuala Lumpur": "central",
    "W.P. Labuan":      "east_malaysia",
    "W.P. Putrajaya":   "central",
}


def fetch_mnha_state_table() -> pd.DataFrame:
    """Download MNHA 2022 PDF, save raw file, and parse Table 4.3 (state expenditure)."""
    os.makedirs(RAW_DIR, exist_ok=True)
    if os.path.exists(RAW_PDF):
        print(f"Loading cached {RAW_PDF} …")
        with open(RAW_PDF, "rb") as f:
            raw = f.read()
    else:
        print("Downloading MNHA 2022 PDF …")
        resp = requests.get(MNHA_PDF_URL, timeout=120)
        resp.raise_for_status()
        raw = resp.content
        with open(RAW_PDF, "wb") as f:
            f.write(raw)
        print(f"  Saved {len(raw) // 1024} KB → {RAW_PDF}")

    print(f"  Parsing {RAW_PDF} …")
    pdf = pdfplumber.open(io.BytesIO(raw))
    rows = []
    for page in pdf.pages:
        text = page.extract_text() or ""
        if "State Population and Health Expenditure" not in text:
            continue
        for line in text.splitlines():
            # Match lines like: "Selangor 7,050,300 13,046"
            m = re.match(r"^(.+?)\s+([\d,]+)\s+([\d,]+)$", line.strip())
            if not m:
                continue
            name_raw = m.group(1).strip()
            if name_raw not in MNHA_CANON:
                continue
            population = int(m.group(2).replace(",", ""))
            expenditure_m = int(m.group(3).replace(",", ""))
            canon_name, dosm_name = MNHA_CANON[name_raw]
            rows.append({
                "state":          canon_name,
                "dosm_name":      dosm_name,
                "population":     population,
                "expenditure_rm_m": expenditure_m,
            })

    if not rows:
        raise ValueError("No state rows parsed from MNHA PDF — check page format")

    df = pd.DataFrame(rows)
    df["spending_per_capita"] = (
        df["expenditure_rm_m"] * 1_000_000 / df["population"]
    ).round(0)
    print(f"  Parsed {len(df)} states from Table 4.3")
    return df


def fetch_mortality_rates() -> pd.DataFrame:
    """Download OpenDOSM deaths by state, save raw parquet, return target year's crude rate."""
    os.makedirs(RAW_DIR, exist_ok=True)
    if os.path.exists(RAW_PARQUET):
        print(f"Loading cached {RAW_PARQUET} …")
        df = pd.read_parquet(RAW_PARQUET)
    else:
        print(f"Downloading OpenDOSM death_state.parquet …")
        resp = requests.get(DEATHS_PARQUET_URL, timeout=60)
        resp.raise_for_status()
        with open(RAW_PARQUET, "wb") as f:
            f.write(resp.content)
        print(f"  Saved {len(resp.content) // 1024} KB → {RAW_PARQUET}")
        df = pd.read_parquet(RAW_PARQUET)

    df["year"] = df["date"].astype(str).str[:4]
    df_year = df[df["year"] == TARGET_YEAR][["state", "rate"]].copy()
    df_year.columns = ["dosm_name", "mortality_rate"]
    print(f"  {len(df_year)} states for {TARGET_YEAR} extracted from full dataset ({len(df)} rows total)")
    return df_year


def main() -> None:
    mnha = fetch_mnha_state_table()
    deaths = fetch_mortality_rates()

    merged = mnha.merge(deaths, on="dosm_name", how="inner")

    # National average for deviation calculation
    nat_spending = (mnha["expenditure_rm_m"].sum() * 1e6 / mnha["population"].sum())
    nat_mortality = deaths["mortality_rate"].mean()

    merged["spending_deviation"] = (
        (merged["spending_per_capita"] - nat_spending) / nat_spending * 100
    ).round(1)
    merged["mortality_deviation"] = (
        (merged["mortality_rate"] - nat_mortality) / nat_mortality * 100
    ).round(1)

    # Alignment label: misaligned = high mortality + low spending, or low mortality + high spending
    def alignment_label(row):
        high_mort = row["mortality_rate"] > nat_mortality
        low_spend = row["spending_per_capita"] < nat_spending
        if high_mort and low_spend:
            return "under-resourced"      # worst: sick but underfunded
        if not high_mort and not low_spend:
            return "over-resourced"       # low mortality, high spend
        if not high_mort and low_spend:
            return "efficient"            # low mortality despite low spend
        return "spending-not-helping"     # high spend but still high mortality

    merged["alignment"] = merged.apply(alignment_label, axis=1)
    merged["region"] = merged["state"].map(REGION_MAP)
    merged["year"] = int(TARGET_YEAR)
    merged["data_note"] = "Total health expenditure (public + private), MNHA 2022"

    cols = [
        "state", "region", "year",
        "population", "expenditure_rm_m", "spending_per_capita",
        "mortality_rate", "spending_deviation", "mortality_deviation",
        "alignment", "data_note",
    ]
    out = merged[cols].sort_values("spending_per_capita", ascending=False)

    records = out.to_dict(orient="records")
    with open("data.json", "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved {len(records)} rows → data.json")
    print(out[["state", "spending_per_capita", "mortality_rate", "alignment"]].to_string(index=False))


if __name__ == "__main__":
    main()
