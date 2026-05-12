import pandas as pd

# Load the CSV file
file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/CRYPTO/1.CRYPTO_STRATEGIES/1.Zelta_Labs/2020_30min_signals.csv'
df = pd.read_csv(file_path)

# Define a function to check and append time if only date is given
def add_time_if_missing(date_str):
    # If the date string contains only the date and not the time
    if len(date_str) == 10:  # 'YYYY-MM-DD' is 10 characters long
        return date_str + ' 00:00:00'
    return date_str

# Apply the function to the 'datetime' column
df['datetime'] = df['datetime'].apply(add_time_if_missing)

# Save the modified DataFrame back to the CSV
df.to_csv(file_path, index=False)

print("Time appended where missing.")
