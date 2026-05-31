import json
import os
import requests

os.makedirs("chapters/ch08/raw", exist_ok=True)

# ── World Bank broad category indicators ────────────────────────────────────
# SH.DTH.NCOM.ZS  = NCD deaths as % of total
# SH.DTH.COMM.ZS  = Communicable disease deaths as %
# SH.DTH.INJR.ZS  = Injuries as %

def fetch_wb_indicator(code, iso3="MYS", prefer_pre_covid=True):
    url = (f"https://api.worldbank.org/v2/country/{iso3}/indicator/{code}"
           "?format=json&mrv=15")
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        rows = [(x["date"], x["value"]) for x in data[1] if x["value"] is not None]
        if rows:
            rows.sort(key=lambda x: x[0], reverse=True)
            if prefer_pre_covid:
                pre = [(d, v) for d, v in rows if int(d) <= 2019]
                if pre:
                    return pre[0][1], int(pre[0][0])
            return rows[0][1], int(rows[0][0])
    except Exception as e:
        print(f"  WB fetch failed for {code}: {e}")
    return None, None

print("Fetching World Bank causes-of-death data for Malaysia (pre-COVID preferred)…")
ncd_pct,  ncd_yr = fetch_wb_indicator("SH.DTH.NCOM.ZS")
comm_pct, _      = fetch_wb_indicator("SH.DTH.COMM.ZS")
injr_pct, _      = fetch_wb_indicator("SH.DTH.INJR.ZS")

print(f"  NCD:          {ncd_pct}% ({ncd_yr})")
print(f"  Communicable: {comm_pct}%")
print(f"  Injuries:     {injr_pct}%")

if ncd_pct is None:
    ncd_pct = 74.0
if injr_pct is None:
    injr_pct = 11.0
if comm_pct is None:
    comm_pct = max(0, round(100 - ncd_pct - injr_pct, 1))

total = ncd_pct + comm_pct + injr_pct
ncd_n  = round(ncd_pct  / total * 100, 1)
com_n  = round(comm_pct / total * 100, 1)
ext_n  = round(100 - ncd_n - com_n, 1)

print(f"\nFinal top-level (normalised to 100%):")
print(f"  NCDs:          {ncd_n}%")
print(f"  Communicable:  {com_n}%")
print(f"  External:      {ext_n}%")

# ── Subcategory breakdown (WHO GHE 2019 Malaysia proportions) ────────────────
# Subcategory pct values are % of ALL deaths (must sum to parent pct).
# Source: WHO Global Health Estimates 2020 edition, Malaysia country profile 2019.

def split(parent_pct, shares):
    """Distribute parent_pct according to proportional shares, rounded to 1dp."""
    total_shares = sum(shares)
    values = [round(parent_pct * s / total_shares, 1) for s in shares]
    # Correct rounding drift on the last element
    values[-1] = round(parent_pct - sum(values[:-1]), 1)
    return values

ncd_shares  = [35.0, 15.0, 9.0, 6.0, 10.9]   # Cardio, Cancer, Diabetes, ChronicResp, Other
com_shares  = [7.0,  2.5,  3.0, 3.7]           # LRI, TB, Septicaemia, Other
ext_shares  = [4.0,  1.0,  1.2, 1.7]           # RoadTraffic, Falls, Self-harm, Other

ncd_subs  = split(ncd_n, ncd_shares)
com_subs  = split(com_n, com_shares)
ext_subs  = split(ext_n, ext_shares)

records = [
    # ── Inner ring ────────────────────────────────────────────────────────────
    {"ring": "inner", "category": "NCDs",         "subcategory": "NCDs",         "pct": ncd_n, "combined_sort": 0},
    {"ring": "inner", "category": "Communicable", "subcategory": "Communicable", "pct": com_n, "combined_sort": 100},
    {"ring": "inner", "category": "External",     "subcategory": "External",     "pct": ext_n, "combined_sort": 200},

    # ── Outer ring — NCDs ─────────────────────────────────────────────────────
    {"ring": "outer", "category": "NCDs", "subcategory": "Cardiovascular",  "pct": ncd_subs[0], "combined_sort": 0},
    {"ring": "outer", "category": "NCDs", "subcategory": "Cancers",         "pct": ncd_subs[1], "combined_sort": 1},
    {"ring": "outer", "category": "NCDs", "subcategory": "Diabetes",        "pct": ncd_subs[2], "combined_sort": 2},
    {"ring": "outer", "category": "NCDs", "subcategory": "Chronic Resp.",   "pct": ncd_subs[3], "combined_sort": 3},
    {"ring": "outer", "category": "NCDs", "subcategory": "Other NCDs",      "pct": ncd_subs[4], "combined_sort": 4},

    # ── Outer ring — Communicable ─────────────────────────────────────────────
    {"ring": "outer", "category": "Communicable", "subcategory": "Lower Resp. Infections", "pct": com_subs[0], "combined_sort": 100},
    {"ring": "outer", "category": "Communicable", "subcategory": "Tuberculosis",           "pct": com_subs[1], "combined_sort": 101},
    {"ring": "outer", "category": "Communicable", "subcategory": "Septicaemia",            "pct": com_subs[2], "combined_sort": 102},
    {"ring": "outer", "category": "Communicable", "subcategory": "Other Infections",       "pct": com_subs[3], "combined_sort": 103},

    # ── Outer ring — External ─────────────────────────────────────────────────
    {"ring": "outer", "category": "External", "subcategory": "Road Traffic",   "pct": ext_subs[0], "combined_sort": 200},
    {"ring": "outer", "category": "External", "subcategory": "Falls",          "pct": ext_subs[1], "combined_sort": 201},
    {"ring": "outer", "category": "External", "subcategory": "Self-harm",      "pct": ext_subs[2], "combined_sort": 202},
    {"ring": "outer", "category": "External", "subcategory": "Other External", "pct": ext_subs[3], "combined_sort": 203},
]

with open("chapters/ch08/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\n✓ Wrote {len(records)} records → chapters/ch08/data.json")
