import os
from distutils.dir_util import copy_tree

# Function to copy subfolders
def copy_subfolders(src_dir, dest_dir):
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.isdir(s):
            copy_tree(s, d)
            print(f"Copied {s} to {d}")

# Function to handle the copy process for a given year
def copy_yearly_subfolders(year):
    source_directory = f"/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/Trades_{year}"
    destination_directory = f"/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/trades/trades_{year}"
    
    # Ensure destination directory exists
    os.makedirs(destination_directory, exist_ok=True)
    
    # List of months in short and full form
    months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
              'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
    
    # Search and copy subfolders from each month folder
    for month in months:
        month_folder_short = f"Trades_{year}_{month[:3]}"
        month_folder_full = f"Trades_{year}_{month}"
        
        short_path = os.path.join(source_directory, month_folder_short)
        full_path = os.path.join(source_directory, month_folder_full)
        
        if os.path.exists(short_path):
            copy_subfolders(short_path, destination_directory)
        if os.path.exists(full_path):
            copy_subfolders(full_path, destination_directory)
    
    print("Subfolders copied successfully.")

# Example usage
copy_yearly_subfolders(2020)  # Change the year as needed
