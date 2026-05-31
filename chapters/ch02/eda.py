import json
import pandas as pd

with open("chapters/ch02/data.json") as f:
    data = json.load(f)

df = pd.DataFrame(data)
print("=== ch02 EDA — Doctor Distribution by State ===\n")
print(f"States: {len(df)}")
print(f"National avg (from data): {df['doctors'].sum() / df['population'].sum() * 10_000:.2f} / 10k")
print()

kl = df[df["state"] == "W.P. Kuala Lumpur"].iloc[0]
sabah = df[df["state"] == "Sabah"].iloc[0]
print(f"KL:    {kl['doctors']:,} doctors | {kl['doctors_per_10k']:.1f}/10k")
print(f"Sabah: {sabah['doctors']:,} doctors | {sabah['doctors_per_10k']:.1f}/10k")
print(f"Ratio KL / Sabah: {kl['doctors_per_10k'] / sabah['doctors_per_10k']:.2f}×")
print()

national_avg = df["doctors"].sum() / df["population"].sum() * 10_000
below = df[df["above_avg"] == False]
pct_pop = below["population"].sum() / df["population"].sum() * 100
print(f"States below national avg ({national_avg:.1f}/10k): {len(below)}")
print(f"Population share in below-avg states: {pct_pop:.1f}%")
print()

print("Full ranking:")
for _, r in df.sort_values("doctors_per_10k", ascending=False).iterrows():
    flag = "▲" if r["above_avg"] else "▼"
    print(f"  {flag} {r['state']:30} {r['doctors']:6,} docs  {r['doctors_per_10k']:6.2f}/10k")

print()
east = df[df["region"] == "east_malaysia"]
print(f"East Malaysia (Sabah+Sarawak+Labuan): {east['doctors'].sum():,} doctors for {east['population'].sum():,} people")
print(f"  = {east['doctors'].sum() / east['population'].sum() * 10_000:.1f}/10k")
