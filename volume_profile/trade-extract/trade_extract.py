# import gzip
# import shutil

# def extract_gz_file(gz_file_path, output_file_path):
#     with gzip.open(gz_file_path, 'rb') as f_in:
#         with open(output_file_path, 'wb') as f_out:
#             shutil.copyfileobj(f_in, f_out)

# # Example usage
# gz_file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/volume_profile/BTCUSDT2024-05-20.csv.gz'
# output_file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/volume_profile/trade2.csv'
# extract_gz_file(gz_file_path, output_file_path)

import os
import gzip
import shutil

def extract_and_rename_gz_files(base_download_dir, base_target_dir):
    # Check if the base target directory exists
    if os.path.exists(base_target_dir):
        # Delete the base target directory if it exists
        shutil.rmtree(base_target_dir)
    
    # Create the base target directory
    os.makedirs(base_target_dir, exist_ok=True)

    # Iterate over subdirectories in the base download directory
    for sub_dir in os.listdir(base_download_dir):
        sub_dir_path = os.path.join(base_download_dir, sub_dir)
        
        # Check if it's a directory
        if os.path.isdir(sub_dir_path):
            # Extract start and end dates from subdirectory name
            start_date_str, end_date_str = sub_dir.split('_')
            
            # Paths for the extracted files
            trade1_path = os.path.join(sub_dir_path, 'trade1.csv')
            trade2_path = os.path.join(sub_dir_path, 'trade2.csv')

            # Iterate over files in the subdirectory
            for file_name in os.listdir(sub_dir_path):
                if file_name.endswith('.gz'):
                    gz_file_path = os.path.join(sub_dir_path, file_name)

                    # Determine which file to extract to based on date matching
                    if start_date_str in file_name:
                        extract_gz_file(gz_file_path, trade1_path)
                    elif end_date_str in file_name:
                        extract_gz_file(gz_file_path, trade2_path)

            # Ensure the target subdirectory exists
            target_sub_dir_path = os.path.join(base_target_dir, sub_dir)
            
            # Delete the subdirectory if it exists
            if os.path.exists(target_sub_dir_path):
                shutil.rmtree(target_sub_dir_path)
            
            # Create the target subdirectory
            os.makedirs(target_sub_dir_path, exist_ok=True)

            # Move the extracted trade1.csv and trade2.csv to the target subdirectory
            shutil.move(trade1_path, os.path.join(target_sub_dir_path, 'trade1.csv'))
            shutil.move(trade2_path, os.path.join(target_sub_dir_path, 'trade2.csv'))
            print(f'Moved files to {target_sub_dir_path}')

def extract_gz_file(gz_file_path, output_file_path):
    with gzip.open(gz_file_path, 'rb') as f_in:
        with open(output_file_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

# Example usage
base_download_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/AI_Driven_Crypto_AlgoTrading_strategy/Devine/volume_profile/Trades_Downloaded'
base_target_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/AI_Driven_Crypto_AlgoTrading_strategy/Devine/volume_profile/Trades'
extract_and_rename_gz_files(base_download_dir, base_target_dir)
