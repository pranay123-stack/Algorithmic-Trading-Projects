import pandas as pd
import os
from datetime import datetime
import pytz

def convert_and_save_csv(input_file_path, output_folder_path):
    # Load the CSV file
    df = pd.read_csv(input_file_path)

    # Rename the columns
    df.rename(columns={
        'startTime': 'timestamp',
        'openPrice': 'open',
        'highPrice': 'high',
        'lowPrice': 'low',
        'closePrice': 'close',
        'volume': 'volume',
        'turnover': 'turnover'
    }, inplace=True)

    # Convert the timestamp format to Kolkata time
    kolkata_tz = pytz.timezone('Asia/Kolkata')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms').dt.tz_localize('UTC').dt.tz_convert(kolkata_tz).dt.strftime('%Y-%m-%d %H:%M:%S')

    # Define the output file path in the same folder as the input file
    output_file_name = f"converted_{os.path.basename(input_file_path)}"
    output_file_path = os.path.join(output_folder_path, output_file_name)

    # Save the new CSV file
    df.to_csv(output_file_path, index=False)
    return output_file_path

def process_directory(main_directory):
    for root, dirs, files in os.walk(main_directory):
        for file in files:
            if file.endswith('.csv'):
                input_file_path = os.path.join(root, file)
                print(f"Processing file: {input_file_path}")
                convert_and_save_csv(input_file_path, root)

# Example usage
main_directory = '/Users/pranaygaurav/Downloads/AlgoTrading/crypto/Devine_group/volume_profile/klines'
process_directory(main_directory)
