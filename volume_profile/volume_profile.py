import os
import pandas as pd
import shutil

def calculate_volume_profile(base_dir, volume_profile_csv_store_dir):
    # Ensure the base output directory exists
    os.makedirs(volume_profile_csv_store_dir, exist_ok=True)

    # Iterate over yearly subdirectories
    for year_dir in os.listdir(base_dir):
        year_dir_path = os.path.join(base_dir, year_dir)
        
        # Check if it's a directory for trades of a specific year
        if os.path.isdir(year_dir_path) and year_dir.startswith('trades_'):
            year = year_dir.split('_')[1]  # Extract year from directory name
            
            # Create a directory for storing the volume profiles for this year
            year_volume_profile_dir = os.path.join(volume_profile_csv_store_dir, f'volume_profile_{year}')
            if os.path.exists(year_volume_profile_dir):
                shutil.rmtree(year_volume_profile_dir)
            os.makedirs(year_volume_profile_dir)
            
            # Iterate over subdirectories in the yearly directory
            for sub_dir in os.listdir(year_dir_path):
                sub_dir_path = os.path.join(year_dir_path, sub_dir)
                
                # Check if it's a directory and contains the required trade files
                if os.path.isdir(sub_dir_path):
                    trade1_path = os.path.join(sub_dir_path, 'trade1.csv')
                    trade2_path = os.path.join(sub_dir_path, 'trade2.csv')
                    
                    if os.path.exists(trade1_path) and os.path.exists(trade2_path):
                        # Read the trade data from trade1.csv and trade2.csv
                        df_trade1 = pd.read_csv(trade1_path)
                        df_trade2 = pd.read_csv(trade2_path)

                        # Concatenate the trade data from both files
                        df = pd.concat([df_trade1, df_trade2])

                        # Convert timestamp column to datetime format
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

                        # Extract start and end dates from subdirectory name
                        start_date_str, end_date_str = sub_dir.split('_')
                        start_date = pd.Timestamp(start_date_str)
                        end_date = pd.Timestamp(end_date_str)

                        # Filter data for the specified date range
                        df_filtered = df[(df['timestamp'] >= start_date) & (df['timestamp'] <= end_date)]

                        # Calculate total volume traded (total buys and sells)
                        total_volume = df_filtered['size'].sum()

                        # Calculate 70% of the total volume
                        value_area_threshold = total_volume * 0.7

                        # Group by price and sum the sizes (volumes)
                        volume_profile = df_filtered.groupby('price')['size'].sum().reset_index()

                        # Sort by price ascending to start from the lowest price
                        volume_profile = volume_profile.sort_values(by='price').reset_index(drop=True)

                        # Find the Point of Control (POC)
                        poc_index = volume_profile['size'].idxmax()
                        poc = volume_profile.loc[poc_index, 'price']

                        # Initialize the Value Area with the POC volume
                        value_area_volume = volume_profile.loc[poc_index, 'size']
                        vah_index = poc_index
                        val_index = poc_index

                        # Initialize the indices for the rows above and below the POC
                        i_up = poc_index - 1  # up is actually calculating down side from poc
                        i_down = poc_index + 1  # down is actually calculating up side from poc

                        # Continue adding the larger of the next two volumes to the value area
                        while value_area_volume < value_area_threshold:
                            # Look at the two rows above the POC (the initial value area)
                            if i_up >= 1:
                                above_poc_volume = volume_profile.loc[i_up - 1:i_up, 'size'].sum()
                            else:
                                above_poc_volume = volume_profile.loc[:i_up, 'size'].sum() if i_up >= 0 else 0

                            # Look at the two rows beneath the POC (the initial value area)
                            if i_down + 1 < len(volume_profile):
                                below_poc_volume = volume_profile.loc[i_down:i_down + 1, 'size'].sum()
                            else:
                                below_poc_volume = volume_profile.loc[i_down:, 'size'].sum() if i_down < len(volume_profile) else 0

                            # Determine which of the total volume numbers is larger and add it to the total volume number of the POC
                            if above_poc_volume >= below_poc_volume:
                                value_area_volume += above_poc_volume
                                if i_up >= 1:
                                    val_index = i_up - 1
                                    i_up -= 2
                                else:
                                    i_up -= 1
                            else:
                                value_area_volume += below_poc_volume
                                if i_down + 1 < len(volume_profile):
                                    vah_index = i_down + 1
                                    i_down += 2
                                else:
                                    i_down += 1

                        # Determine VAH and VAL from the indices
                        vah = volume_profile.loc[vah_index, 'price']
                        val = volume_profile.loc[val_index, 'price']

                        # Create a subdirectory within the yearly volume profile directory
                        sub_output_dir = os.path.join(year_volume_profile_dir, sub_dir)
                        if os.path.exists(sub_output_dir):
                            shutil.rmtree(sub_output_dir)
                        os.makedirs(sub_output_dir)


                        # Assuming vah, val, poc, and start_date_str are already defined
                        vah = round(vah, 2)
                        val = round(val, 2)
                        poc = round(poc, 2)
                                                
                        # Save the volume profile results to a CSV file in the subdirectory
                        result_df = pd.DataFrame({
                            'Date': [start_date_str],
                            'VAH': [vah],
                            'VAL': [val],
                            'POC': [poc]
                        })

                        output_file_path = os.path.join(sub_output_dir, f'{start_date_str}_volume_profile.csv')
                        
                        # Check if the output file already exists and delete it
                        if os.path.exists(output_file_path):
                            os.remove(output_file_path)
                        
                        result_df.to_csv(output_file_path, index=False)
                        print(f'Saved volume profile to {output_file_path}')

# Base directory for input trades
trades_input_base_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/trades'

# Base directory for saving the volume profile CSV files
volume_profile_csv_store_base_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/volume_profile_csv'

# Call the function with the base directory path
calculate_volume_profile(trades_input_base_dir, volume_profile_csv_store_base_dir)
