import pandas as pd

# Read the CSV file, using the first column as the index and parsing the datetime column
df = pd.read_csv('/Users/pranaygaurav/Downloads/AlgoTrading/BTC_2019_2023_30m.csv', index_col=0, parse_dates=['datetime'])

# Reset the index and drop the old index
df = df.reset_index(drop=True)

# Save the result to a new CSV file without the index
df.to_csv('output_file.csv', index=False)

# Print the resulting DataFrame without the index
print(df.to_string(index=False))