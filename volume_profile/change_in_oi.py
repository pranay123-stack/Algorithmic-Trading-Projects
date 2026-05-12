import os
import pandas as pd

def calculate_change_in_oi(df):
    # Calculate the change in open interest
    df['change_oi'] = df['openInterest'].diff().round(3)
    
    return df

def process_oi_data(base_dir):
    # Loop through all subdirectories
    for subdir, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv') and file.startswith('oi_'):
                file_path = os.path.join(subdir, file)
                
                # Load the CSV file into a DataFrame
                df = pd.read_csv(file_path, parse_dates=['timestamp'])
                
                # Calculate change in open interest
                df = calculate_change_in_oi(df)
                
                # Save the updated DataFrame back to the same CSV file
                df.to_csv(file_path, index=False)
                print(f'Processed and updated: {file_path}')

# Specify the base directory
base_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/crypto/Devine_group/volume_profile/oi'

# Process the open interest data
process_oi_data(base_dir)
