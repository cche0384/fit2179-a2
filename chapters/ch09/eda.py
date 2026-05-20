import json
import pandas as pd

with open("chapters/ch09/data.json") as f:
    df = pd.DataFrame(json.load(f))

print("=== Chapter 9: Early Childhood Death Rate Heatmap ===")
print(f"States: {df['state'].nunique()}, Years: {df['year'].nunique()}")

pivot = df.pivot(index="state", columns="year", values="imr")
y2000 = pivot[2000] if 2000 in pivot.columns else None
y2023 = pivot[2023] if 2023 in pivot.columns else None
comparison = pd.DataFrame({"2000": y2000, "2023": y2023}).dropna()
comparison["change"] = comparison["2023"] - comparison["2000"]
comparison["pct_change"] = ((comparison["change"] / comparison["2000"]) * 100).round(1)
print("\n2000 vs 2023 (sorted by 2023 IMR):")
print(comparison.sort_values("2023", ascending=False).to_string())

print(f"\nNational trend (min/median/max across states):")
for yr in [2000, 2005, 2010, 2015, 2020, 2023]:
    if yr in pivot.columns:
        vals = pivot[yr].dropna()
        print(f"  {yr}: min={vals.min():.1f}  median={vals.median():.1f}  max={vals.max():.1f}  spread={vals.max()-vals.min():.1f}")
