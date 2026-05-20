import json
import pandas as pd

with open("chapters/ch10/data.json") as f:
    df = pd.DataFrame(json.load(f))

print("=== Chapter 10: Correlations with State Life Expectancy ===")
print(df.sort_values("abs_correlation", ascending=False)[
    ["variable", "correlation", "direction"]
].to_string(index=False))

poverty_r = df[df.variable.str.contains("Poverty")]["correlation"].values[0]
doctor_r = df[df.variable.str.contains("Doctor")]["correlation"].values[0]
print(f"\nPoverty correlation: {poverty_r:+.3f}")
print(f"Doctor ratio correlation: {doctor_r:+.3f}")
print(f"Poverty association is {abs(poverty_r)/abs(doctor_r):.1f}x stronger than doctor supply")
