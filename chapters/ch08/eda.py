import json
import pandas as pd

with open("chapters/ch08/data.json") as f:
    df = pd.DataFrame(json.load(f))

print("=== Chapter 8: Crude Death Rate by State (2023) ===\n")
print(df[["state", "rate_2000", "rate_2023", "change", "change_pct"]]
      .sort_values("rate_2023", ascending=False).to_string(index=False))

print(f"\nHighest 2023: {df.nlargest(1,'rate_2023')['state'].values[0]} = {df['rate_2023'].max()}")
print(f"Lowest  2023: {df.nsmallest(1,'rate_2023')['state'].values[0]} = {df['rate_2023'].min()}")
print(f"Gap ratio: {df['rate_2023'].max() / df['rate_2023'].min():.2f}×")
print(f"\nSteepest climb since 2000: {df.nlargest(1,'change_pct')['state'].values[0]} "
      f"(+{df['change_pct'].max():.0f}%)")
print(f"Smallest increase: {df.nsmallest(1,'change_pct')['state'].values[0]} "
      f"(+{df['change_pct'].min():.0f}%)")
