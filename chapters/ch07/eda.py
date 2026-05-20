import json
import pandas as pd

with open("data.json") as f:
    df = pd.DataFrame(json.load(f))

print("=== Chapter 7: NCD Prevalence B40 vs T20 ===")
pivot = df.pivot(index="condition", columns="group", values="prevalence")
pivot["gap_pp"] = pivot["B40"] - pivot["T20"]
pivot["ratio"]  = pivot["B40"] / pivot["T20"]
print(pivot.sort_values("gap_pp", ascending=False))
print(f"\nAverage B40 prevalence: {df[df.group=='B40']['prevalence'].mean():.1f}%")
print(f"Average T20 prevalence: {df[df.group=='T20']['prevalence'].mean():.1f}%")
