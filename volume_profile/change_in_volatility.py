import os
import pandas as pd

def calculate_volatility_changes(df):
    # Calculate the change in price volatility
    df['change_price_volatility'] = df['price_volatility'].diff().round(2)
    
    # Calculate the change in volume volatility
    df['change_volume_volatility'] = df['volume_volatility'].diff().round(2)
    
    return df

def process_volatility_data(base_dir):
    # Loop through all subdirectories
    for subdir, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv') and file.startswith('volatility_'):
                file_path = os.path.join(subdir, file)
                
                # Load the CSV file into a DataFrame
                df = pd.read_csv(file_path, parse_dates=['timestamp'])
                
                # Calculate changes in volatilities
                df = calculate_volatility_changes(df)
                
                # Save the updated DataFrame back to the same CSV file
                df.to_csv(file_path, index=False)
                print(f'Processed and updated: {file_path}')

# Specify the base directory
base_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/crypto/Devine_group/volume_profile/klines'

# Process the volatility data
process_volatility_data(base_dir)
