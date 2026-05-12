#price volaitility using kline-(closeprice - openprice)/ openprice
import os
import pandas as pd

def calculate_volatility(df):
    # Calculate price volatility as the difference between high and low prices
    df['price_volatility'] = (df['high'] - df['low']).round(2)
    
    # Calculate volume volatility as the absolute change in volume
    df['volume_volatility'] = df['volume'].diff().abs().round(2)
    
    # Return only the necessary columns
    return df[['timestamp', 'price_volatility', 'volume_volatility']]


def process_kline_data(base_dir):
    # Loop through all subdirectories
    for subdir, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv') and file.startswith('converted_'):
                file_path = os.path.join(subdir, file)
                
                # Load the CSV file into a DataFrame
                df = pd.read_csv(file_path, parse_dates=['timestamp'])
                
                # Calculate volatility
                volatility_df = calculate_volatility(df)
                
                # Save the results to a new CSV file with "volatility_" prefix
                output_file = os.path.join(subdir, f'volatility_{file}')
                volatility_df.to_csv(output_file, index=False)
                print(f'Processed and saved: {output_file}')

# Specify the base directory
base_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/crypto/Devine_group/volume_profile/klines'

# Process the kline data
process_kline_data(base_dir)
