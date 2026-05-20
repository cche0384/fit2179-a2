"""
Chapter 5 — The Bill That Breaks Families
procure.py: Downloads OOP health expenditure + income distribution data.

Data sources (all fetched at runtime — no hard-coded values):
  1. World Bank Open Data API
       SH.XPD.OOPC.PP.CD  — OOP per capita, PPP (current int'l $)   2000–2023
       NY.GDP.PCAP.PP.CD  — GDP per capita, PPP (current int'l $)    2000–2023
       SH.XPD.OOPC.CH.ZS  — OOP as % of current health expenditure  2000–2023
       SH.XPD.CHEX.GD.ZS  — Current health exp. as % of GDP         2000–2023
       SI.DST.FRST.20     — Income share: lowest quintile (Q1)       survey yrs
       SI.DST.02ND.20     — Income share: 2nd quintile (Q2)
       SI.DST.03RD.20     — Income share: 3rd quintile (Q3)
       SI.DST.04TH.20     — Income share: 4th quintile (Q4)
       (Q5 = 1 − Q1 − Q2 − Q3 − Q4)
  2. DOSM HIES income-by-percentile CSV (2019, 2022, 2024 survey years)
       Used to validate World Bank quintile ratios for recent years.
  3. DOSM National Health Accounts CSV (2013–2022)
       Supplementary context only (public vs private health spend).

Method for B40 / M40 / T20 OOP burden:
  B40 mean income / national mean = (Q1_share + Q2_share) / 0.40
  M40 mean income / national mean = (Q3_share + Q4_share) / 0.40
  T20 mean income / national mean = (Q5_share)             / 0.20

  oop_share_group = (oop_pc_ppp / gdp_pc_ppp)
                    / (group_income_relative_to_mean)
                    × 100   (%)

  i.e. national OOP-to-GDP ratio scaled by how far below the national mean
  each income group sits, assuming equal absolute OOP per capita across groups.
  (In Malaysia's mixed public/private system, private-sector consultation fees
  are similar for all patients, making this a defensible approximation.)

Outputs : data.json
Run     : python3 procure.py
Requires: pip install pandas requests
"""

import json, os, sys
import requests
import pandas as pd
from io import StringIO

DIR     = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(DIR, "raw")

YEAR_START = 2000
YEAR_END   = 2023
WB_TIMEOUT = 120   # seconds — WB API can be slow


# ── helpers ────────────────────────────────────────────────────────────────────

def _get(url, params=None, timeout=60):
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r


# ── 1. World Bank ──────────────────────────────────────────────────────────────

WB_BASE = "https://api.worldbank.org/v2"

# (indicator_code, column_alias)
WB_HEALTH = [
    ("SH.XPD.OOPC.PP.CD", "oop_pc_ppp"),
    ("NY.GDP.PCAP.PP.CD",  "gdp_pc_ppp"),
    ("SH.XPD.OOPC.CH.ZS", "oop_pct_che"),
    ("SH.XPD.CHEX.GD.ZS", "che_pct_gdp"),
]

WB_QUINTILE = [
    ("SI.DST.FRST.20", "q1_share"),
    ("SI.DST.02ND.20", "q2_share"),
    ("SI.DST.03RD.20", "q3_share"),
    ("SI.DST.04TH.20", "q4_share"),
]


def fetch_wb_series(indicator_code, start=1995, end=YEAR_END, country="MYS"):
    url = f"{WB_BASE}/country/{country}/indicator/{indicator_code}"
    params = {"format": "json", "per_page": 100, "date": f"{start}:{end}"}
    print(f"  WB  {indicator_code:<22} ...", end="  ", flush=True)
    payload = _get(url, params=params, timeout=WB_TIMEOUT).json()
    if len(payload) < 2 or not payload[1]:
        print("no data")
        return pd.DataFrame({"year": pd.Series(dtype=int)})
    rows = [
        {"year": int(x["date"]), indicator_code: x["value"]}
        for x in payload[1]
        if x["value"] is not None
    ]
    df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
    print(f"{len(df)} pts  ({df['year'].min()}–{df['year'].max()})")
    return df


def fetch_wb_all():
    """
    Return (interpolated_df, raw_df).
    interpolated_df: one row per year, all gaps filled via linear interpolation.
    raw_df: same shape but with NaN wherever the WB didn't report a value.
    """
    years = pd.DataFrame({"year": range(YEAR_START, YEAR_END + 1)})

    base = years.copy()
    for code, alias in WB_HEALTH + WB_QUINTILE:
        raw = fetch_wb_series(code)
        if code in raw.columns:
            raw = raw.rename(columns={code: alias})
        if alias in raw.columns:
            base = base.merge(raw[["year", alias]], on="year", how="left")
        else:
            base[alias] = float("nan")

    # Save the uninterpolated frame for the raw CSV before touching it
    raw_df = base.copy()

    # Interpolate all series linearly; extend to edges
    for col in base.columns[1:]:
        base[col] = base[col].interpolate(method="linear", limit_direction="both")

    # Derive Q5 income share (WB values are in %-points; 100 - sum of Q1..Q4)
    base["q5_share"] = 100.0 - base["q1_share"] - base["q2_share"] - base["q3_share"] - base["q4_share"]

    # Derive OOP per capita from component series if primary is missing
    if base["oop_pc_ppp"].isna().any():
        derived = (
            base["oop_pct_che"].fillna(0) / 100.0
            * base["che_pct_gdp"].fillna(0) / 100.0
            * base["gdp_pc_ppp"].fillna(0)
        )
        base["oop_pc_ppp"] = base["oop_pc_ppp"].fillna(derived.where(derived > 0))

    return base, raw_df


# ── 2. DOSM HIES income percentile (recent-year validation) ───────────────────

DOSM_STORAGE = "https://storage.dosm.gov.my"


def fetch_dosm_hies():
    url = f"{DOSM_STORAGE}/hies/hies_malaysia_percentile.csv"
    print(f"  DOSM  hies_malaysia_percentile.csv ...", end="  ", flush=True)
    df = pd.read_csv(StringIO(_get(url, timeout=90).text))
    print(f"{len(df)} rows  cols: {list(df.columns)}")
    return df


def hies_quintile_ratios(raw):
    """
    From DOSM HIES percentile income data, compute the mean-income ratio of
    B40, M40, T20 relative to the national mean, for each survey year.
    Returns DataFrame: year | b40_rel | m40_rel | t20_rel
    """
    df = raw.copy()
    df.columns = [c.lower().strip() for c in df.columns]
    df = df[df["variable"].str.lower() == "mean"].copy()
    df["year"]       = pd.to_datetime(df["date"], errors="coerce").dt.year
    df["percentile"] = df["percentile"].astype(int)
    df["income"]     = pd.to_numeric(df["income"], errors="coerce")
    df = df.dropna(subset=["year", "income"])

    records = []
    for yr, g in df.groupby("year"):
        b40  = g[g["percentile"] <= 40]["income"].mean()
        m40  = g[(g["percentile"] > 40) & (g["percentile"] <= 80)]["income"].mean()
        t20  = g[g["percentile"] > 80]["income"].mean()
        natl = g["income"].mean()
        records.append({
            "year":    int(yr),
            "b40_rel": round(b40 / natl, 4),
            "m40_rel": round(m40 / natl, 4),
            "t20_rel": round(t20 / natl, 4),
        })
    return pd.DataFrame(records)


# ── 3. DOSM MNHA (supplementary) ──────────────────────────────────────────────

def fetch_dosm_mnha():
    # MNHA lives on data.gov.my, not storage.dosm.gov.my
    url = "https://storage.data.gov.my/healthcare/mnha.csv"
    print(f"  DOSM  mnha.csv ...", end="  ", flush=True)
    try:
        df = pd.read_csv(StringIO(_get(url, timeout=60).text))
        print(f"{len(df)} rows")
        return df
    except Exception as exc:
        print(f"unavailable ({exc})")
        return pd.DataFrame()


# ── 4. Build output records ────────────────────────────────────────────────────

def build_records(wb, hies_ratios):
    """
    For each year, compute OOP health expenditure as % of income for each group.

    Relative-income approach (dimensionless — units cancel):
      group_rel_income = group_mean_income / national_mean_income
      oop_share_group  = (oop_pc_ppp / gdp_pc_ppp) / group_rel_income × 100

    Primary source: WB income quintile shares (annual via interpolation).
    For recent survey years (2019, 2022, 2024) also blended with DOSM HIES
    ratios where available, taking the average of the two estimates.
    """
    # WB quintile shares are in percentage points (e.g. 4.5 means 4.5% of income)
    # Convert to fractions before computing group relative incomes.
    wb = wb.copy()
    for col in ("q1_share", "q2_share", "q3_share", "q4_share", "q5_share"):
        wb[col] = wb[col] / 100.0

    wb["b40_rel_wb"] = (wb["q1_share"] + wb["q2_share"]) / 0.40
    wb["m40_rel_wb"] = (wb["q3_share"] + wb["q4_share"]) / 0.40
    wb["t20_rel_wb"] =  wb["q5_share"]                   / 0.20

    # Merge DOSM HIES ratios (available for a handful of recent years only)
    merged = wb.merge(hies_ratios, on="year", how="left")

    # Blend WB + HIES estimates where HIES is available
    for grp in ("b40", "m40", "t20"):
        wb_col   = f"{grp}_rel_wb"
        hies_col = f"{grp}_rel"
        blend    = f"{grp}_rel_final"
        merged[blend] = merged.apply(
            lambda r, wc=wb_col, hc=hies_col: (
                (r[wc] + r[hc]) / 2.0 if not pd.isna(r.get(hc)) else r[wc]
            ),
            axis=1,
        )

    records = []
    for _, row in merged.iterrows():
        year    = int(row["year"])
        oop_pc  = row.get("oop_pc_ppp")
        gdp_pc  = row.get("gdp_pc_ppp")

        if any(pd.isna(v) or v <= 0 for v in [oop_pc, gdp_pc]):
            continue

        oop_frac = oop_pc / gdp_pc   # national OOP as fraction of per-capita GDP

        group_map = [
            ("B40", "b40_rel_final"),
            ("M40", "m40_rel_final"),
            ("T20", "t20_rel_final"),
        ]
        for grp, rel_col in group_map:
            rel = row.get(rel_col)
            if pd.isna(rel) or rel <= 0:
                continue
            oop_share = (oop_frac / rel) * 100

            records.append({
                "year":               year,
                "group":              grp,
                "oop_share":          round(oop_share, 2),
                "oop_per_capita_ppp": round(oop_pc, 1),
                "gdp_per_capita_ppp": round(gdp_pc, 1),
                "rel_income":         round(rel, 4),
                "oop_pct_che":        round(row["oop_pct_che"], 1)
                                       if not pd.isna(row.get("oop_pct_che")) else None,
                "che_pct_gdp":        round(row["che_pct_gdp"], 2)
                                       if not pd.isna(row.get("che_pct_gdp")) else None,
            })

    return records


# ── 5. Raw data downloads ──────────────────────────────────────────────────────

def save_raw_wb(wb_uninterpolated):
    """Save the uninterpolated World Bank series as raw/raw_wb.csv."""
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, "raw_wb.csv")
    wb_uninterpolated.to_csv(path, index=False)
    print(f"   Saved {len(wb_uninterpolated)} rows → raw/raw_wb.csv")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=== Chapter 5 — procure.py ===\n")

    print("1. World Bank health + income distribution data:")
    wb, wb_raw = fetch_wb_all()

    print("\n2. DOSM HIES income percentile (recent survey years for blending):")
    hies_raw    = fetch_dosm_hies()
    hies_ratios = hies_quintile_ratios(hies_raw)
    print(f"   HIES survey years: {sorted(hies_ratios['year'].tolist())}")
    print(hies_ratios.to_string(index=False))

    print("\n3. DOSM National Health Accounts (supplementary):")
    mnha = fetch_dosm_mnha()

    print("\n4. Building output records...")
    records = build_records(wb, hies_ratios)
    if not records:
        print("ERROR: no records produced.", file=sys.stderr)
        sys.exit(1)

    df = pd.DataFrame(records)
    print(f"\n   {len(df)} rows  ({df['year'].min()}–{df['year'].max()})")
    print(f"   Groups: {sorted(df['group'].unique())}")
    for grp in ["B40", "M40", "T20"]:
        g = df[df.group == grp].sort_values("year")
        print(f"   {grp}: oop_share {g['oop_share'].min():.1f}–{g['oop_share'].max():.1f}%"
              f"  rel_income {g['rel_income'].min():.3f}–{g['rel_income'].max():.3f}")

    print("\n5. Saving raw source data...")

    # Raw WB CSV (uninterpolated — NaN where survey data is absent; already in memory)
    save_raw_wb(wb_raw)

    # Raw DOSM HIES (already fetched)
    os.makedirs(RAW_DIR, exist_ok=True)
    hies_path = os.path.join(RAW_DIR, "raw_dosm_hies.csv")
    hies_raw.to_csv(hies_path, index=False)
    print(f"   Saved {len(hies_raw)} rows → raw/raw_dosm_hies.csv")

    # Raw DOSM MNHA
    if not mnha.empty:
        mnha_path = os.path.join(RAW_DIR, "raw_dosm_mnha.csv")
        mnha.to_csv(mnha_path, index=False)
        print(f"   Saved {len(mnha)} rows → raw/raw_dosm_mnha.csv")

    out_path = os.path.join(DIR, "data.json")
    with open(out_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"\nSaved {len(records)} rows → data.json")


if __name__ == "__main__":
    main()
