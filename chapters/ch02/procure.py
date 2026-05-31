import json
import os
import pandas as pd

os.makedirs("chapters/ch02/raw", exist_ok=True)

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

# --- compute centroids from compact GeoJSON ---------------------------------
with open("chapters/ch01/malaysia-states-compact.geojson") as f:
    geo = json.load(f)

centroids = {}
for feat in geo["features"]:
    name = feat["properties"]["NAME_1"]
    geom = feat["geometry"]
    # Use the largest polygon (most vertices) to avoid island-bias on the centroid.
    # Averaging all island polygons drags coastal-state centroids into the sea.
    if geom["type"] == "MultiPolygon":
        ring = max(geom["coordinates"], key=lambda p: len(p[0]))[0]
    else:
        ring = geom["coordinates"][0]
    lons = [c[0] for c in ring]
    lats = [c[1] for c in ring]
    centroids[name] = (sum(lons) / len(lons), sum(lats) / len(lats))

# --- load healthcare staff data ---------------------------------------------
staff = pd.read_csv("chapters/ch03/raw/healthcare_staff_raw.csv")
docs = staff[
    (staff["type"] == "doctor") &
    (staff["date"] == "2022-01-01") &
    (staff["state"] != "Malaysia")
].copy()

# --- load population data ---------------------------------------------------
pop = pd.read_csv("chapters/ch03/raw/population_state_raw.csv")
pop22 = pop[
    (pop["sex"] == "both") &
    (pop["age"] == "overall") &
    (pop["ethnicity"] == "overall") &
    (pop["date"] == "2022-01-01")
][["state", "population"]].copy()
pop22["population"] = (pop22["population"] * 1000).round().astype(int)

# --- merge & compute --------------------------------------------------------
df = docs.merge(pop22, on="state")
df["doctors"] = df["staff"].astype(int)
df["doctors_per_10k"] = df["doctors"] / df["population"] * 10_000

national_avg = df["doctors"].sum() / df["population"].sum() * 10_000
df["above_avg"] = df["doctors_per_10k"] >= national_avg

df["gadm"] = df["state"].map(DOSM_TO_GADM)
df["lon"] = df["gadm"].map(lambda g: round(centroids[g][0], 4))
df["lat"] = df["gadm"].map(lambda g: round(centroids[g][1], 4))

east = {"Sabah", "Sarawak", "W.P. Labuan"}
df["region"] = df["state"].apply(lambda s: "east_malaysia" if s in east else "peninsula")

# diagnostics
pop_below = df[~df["above_avg"]]["population"].sum()
pct_below = pop_below / df["population"].sum() * 100
kl = df[df["state"] == "W.P. Kuala Lumpur"].iloc[0]
sabah = df[df["state"] == "Sabah"].iloc[0]
ratio = kl["doctors_per_10k"] / sabah["doctors_per_10k"]

print(f"National average: {national_avg:.2f} / 10k")
print(f"KL: {kl['doctors_per_10k']:.1f}  Sabah: {sabah['doctors_per_10k']:.1f}  ratio: {ratio:.1f}×")
print(f"Pop in below-avg states: {pct_below:.1f}%")
print()
for _, r in df.sort_values("doctors_per_10k", ascending=False).iterrows():
    flag = "▲" if r["above_avg"] else "▼"
    print(f"{flag} {r['state']:30} {r['doctors']:6} docs  {r['doctors_per_10k']:6.2f}/10k")

# --- write data.json --------------------------------------------------------
records = []
for _, r in df.iterrows():
    records.append({
        "gadm_name":      r["gadm"],
        "state":          DISPLAY.get(r["state"], r["state"]),
        "lon":            r["lon"],
        "lat":            r["lat"],
        "doctors":        r["doctors"],
        "population":     r["population"],
        "doctors_per_10k": round(r["doctors_per_10k"], 2),
        "above_avg":      bool(r["above_avg"]),
        "region":         r["region"],
    })

with open("chapters/ch02/data.json", "w") as f:
    json.dump(records, f, indent=2)

print(f"\n✓ Wrote {len(records)} records → chapters/ch02/data.json")
