import os
import pandas as pd

def merge_and_sort_csv_files(base_dir, output_file):
    # Create an empty dataframe to hold all the data
    merged_df = pd.DataFrame()
    
    # Iterate over yearly directories in the base directory
    for year_dir in os.listdir(base_dir):
        year_dir_path = os.path.join(base_dir, year_dir)
        
        # Check if it's a directory for a specific year
        if os.path.isdir(year_dir_path) and year_dir.startswith('volume_profile_'):
            
            # Iterate over subdirectories in the yearly directory
            for sub_dir in os.listdir(year_dir_path):
                sub_dir_path = os.path.join(year_dir_path, sub_dir)
                
                if os.path.isdir(sub_dir_path):
                    # Iterate over CSV files in the subdirectory
                    for file_name in os.listdir(sub_dir_path):
                        if file_name.endswith('_volume_profile.csv'):
                            file_path = os.path.join(sub_dir_path, file_name)
                            
                            if os.path.exists(file_path):
                                # Read the CSV file
                                df = pd.read_csv(file_path)
                                
                                # Append to the merged dataframe
                                merged_df = pd.concat([merged_df, df], ignore_index=True)
    
    # Sort the merged dataframe in ascending order based on 'Date'
    merged_df.sort_values(by='Date', ascending=True, inplace=True)
    
    # Save the merged and sorted dataframe to the output file
    merged_df.to_csv(output_file, index=False)
    print(f'Merged and sorted CSV saved to {output_file}')

# Base directory and output file path
base_directory = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/volume_profile_csv'
output_file = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/final_backtest_2020_2024.csv'

# Call the function to merge and sort CSV files
merge_and_sort_csv_files(base_directory, output_file)
