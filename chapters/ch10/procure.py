import json
import os
import requests
import pandas as pd

os.makedirs("chapters/ch10/raw", exist_ok=True)

# ── ASEAN countries ────────────────────────────────────────────────────────────
ASEAN = {
    "MY": "Malaysia",
    "TH": "Thailand",
    "ID": "Indonesia",
    "PH": "Philippines",
    "VN": "Vietnam",
    "KH": "Cambodia",
    "LA": "Laos",
    "MM": "Myanmar",
    "SG": "Singapore",
    "BN": "Brunei",
}

FLAGS = {
    "MY": "🇲🇾",
    "TH": "🇹🇭",
    "ID": "🇮🇩",
    "PH": "🇵🇭",
    "VN": "🇻🇳",
    "KH": "🇰🇭",
    "LA": "🇱🇦",
    "MM": "🇲🇲",
    "SG": "🇸🇬",
    "BN": "🇧🇳",
}

# ── Fetch infant mortality rate from World Bank ────────────────────────────────
iso_list = ";".join(ASEAN.keys())
# Use life expectancy (SP.DYN.LE00.IN): rank 1 = highest LE = best
INDICATOR = "SP.DYN.LE00.IN"
url = (f"https://api.worldbank.org/v2/country/{iso_list}/indicator/{INDICATOR}"
       "?format=json&date=2000:2022&per_page=2000")

print(f"Fetching ASEAN life expectancy ({INDICATOR})…")
try:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    raw = r.json()
    rows_raw = [x for x in raw[1] if x["value"] is not None]
    print(f"  Got {len(rows_raw)} records")
    with open("chapters/ch10/raw/raw_asean_le.json", "w") as f:
        json.dump(raw, f, indent=2)
except Exception as e:
    print(f"  Fetch failed: {e}. Loading from cache if available…")
    try:
        with open("chapters/ch10/raw/raw_asean_le.json") as f:
            raw = json.load(f)
        rows_raw = [x for x in raw[1] if x["value"] is not None]
        print(f"  Loaded {len(rows_raw)} records from cache")
    except FileNotFoundError:
        print("  No cache. Using fallback data…")
        rows_raw = None

# ── Build records ─────────────────────────────────────────────────────────────
if rows_raw:
    records = []
    for row in rows_raw:
        iso2 = row["country"]["id"]
        if iso2 in ASEAN:
            records.append({
                "iso2":    iso2,
                "country": ASEAN[iso2],
                "year":    int(row["date"]),
                "value":   round(float(row["value"]), 2),
                "flag":    FLAGS.get(iso2, ""),
            })
    df = pd.DataFrame(records)
else:
    # Fallback: approximation
    rows = []
    fallback_le = {
        "SG": 78.0, "BN": 74.0, "VN": 72.8, "MY": 72.7, "TH": 71.2,
        "PH": 67.8, "ID": 66.3, "MM": 60.4, "KH": 59.5, "LA": 58.3
    }
    for iso2, le_start in fallback_le.items():
        for yr in range(2000, 2023):
            # linear-ish growth for fallback
            val = le_start + (yr - 2000) * 0.2
            rows.append({
                "iso2": iso2, 
                "country": ASEAN[iso2], 
                "year": yr, 
                "value": val,
                "flag": FLAGS.get(iso2, ""),
            })
    df = pd.DataFrame(rows)

# ── Compute rank per year (1 = highest LE = best) ─────────────────────────────
df["rank"] = df.groupby("year")["value"].rank(method="min", ascending=False).astype(int)

# ── Select all years 2000-2022 ────────────────────────────────────────────────
df_target = df.copy()

# ── Write data.json ────────────────────────────────────────────────────────────
out = df_target[["country", "iso2", "year", "rank", "value", "flag"]].copy()
out = out.rename(columns={"value": "le"})
out["is_malaysia"] = out["iso2"] == "MY"

records = out.to_dict(orient="records")
for r in records:
    r["le"] = round(float(r["le"]), 2)
    r["rank"] = int(r["rank"])
    r["year"] = int(r["year"])

with open("chapters/ch10/data.json", "w") as f:
    json.dump(records, f, indent=2, ensure_ascii=False)

print(f"\n✓ Wrote {len(records)} records (all years) → chapters/ch10/data.json")

