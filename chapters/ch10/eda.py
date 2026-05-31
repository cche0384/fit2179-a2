import json; import pandas as pd
d = json.load(open('chapters/ch10/data.json'))
df = pd.DataFrame(d)
print(df.describe())
print(df.head())

