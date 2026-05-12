import os
import pandas as pd

def calculate_vwap(df):
    # Ensure no empty rows are processed
    df.dropna(inplace=True)
    
    # Calculate the Typical Price
    df['Typical_Price'] = (df['highPrice'] + df['lowPrice'] + df['closePrice']) / 3
    
    # Multiply the Typical Price by the period Volume
    df['TPxVolume'] = df['Typical_Price'] * df['volume']
    
    # Cumulative total of Typical Price x Volume
    df['Cumulative_TP_Volume'] = df['TPxVolume'].cumsum()
    
    # Cumulative total of Volume
    df['Cumulative_Volume'] = df['volume'].cumsum()
    
    # Divide the cumulative totals to get VWAP
    df['VWAP'] = df['Cumulative_TP_Volume'] / df['Cumulative_Volume']
    
    return df['VWAP']

def process_vwap(base_dir, output_dir):
    # Iterate over yearly directories in the base directory
    for year_dir in os.listdir(base_dir):
        year_dir_path = os.path.join(base_dir, year_dir)
        
        # Check if it's a directory for klines of a specific year
        if os.path.isdir(year_dir_path) and year_dir.startswith('klines_'):
            year = year_dir.split('_')[1]  # Extract year from directory name
            
            # Iterate over subdirectories in the yearly directory
            for sub_dir in os.listdir(year_dir_path):
                sub_dir_path = os.path.join(year_dir_path, sub_dir)
                
                if os.path.isdir(sub_dir_path):
                    # Check for kline files in the subdirectory
                    for file_name in os.listdir(sub_dir_path):
                        if file_name.startswith('kline_') and file_name.endswith('_output.csv'):
                            file_path = os.path.join(sub_dir_path, file_name)
                            
                            if os.path.exists(file_path):
                                # Read the CSV file
                                df = pd.read_csv(file_path)
                                
                                # Calculate VWAP
                                vwap_series = calculate_vwap(df)
                                
                                # Get the first VWAP value
                                first_vwap_value = vwap_series.iloc[0]
                                
                                # Extract the first date from the file name
                                first_date = file_name.split('_')[1]
                                
                                # Construct the volume profile file path based on the first date
                                volume_profile_file = os.path.join(output_dir, f'volume_profile_{year}', sub_dir, f"{first_date}_volume_profile.csv")
                                
                                if os.path.exists(volume_profile_file):
                                    # Read the volume profile CSV file
                                    volume_profile_df = pd.read_csv(volume_profile_file)
                                    
                                    # Add VWAP column to volume profile dataframe
                                    volume_profile_df['VWAP'] = round(first_vwap_value,2)
                                    
                                    # Save the updated volume profile dataframe
                                    volume_profile_df.to_csv(volume_profile_file, index=False)
                                    print(f'Updated {volume_profile_file} with VWAP')
                                else:
                                    print(f'Volume profile file {volume_profile_file} not found.')

# Call the function with the base directory path and output directory path
klines_input_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/klines'
vwap_value_output_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/volume_profile_csv'

process_vwap(klines_input_dir, vwap_value_output_dir)
