import pandas as pd

def calculate_price_range(input_file, output_file):
    # Read the CSV file
    df = pd.read_csv(input_file)
    
    # Check if 'VAH' and 'VAL' columns exist in the dataframe
    if 'VAH' in df.columns and 'VAL' in df.columns:
        # Calculate the price range (VAH_t - VAL_t)
        df['Price_Range[VAH-VAL]'] = df['VAH'] - df['VAL']
        
        # Save the updated dataframe to a new CSV file
        df.to_csv(output_file, index=False)
        print(f'Updated CSV with price range saved to {output_file}')
    else:
        print('Error: VAH and/or VAL columns are missing in the input file.')

# Input and output file paths
input_file = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/final_backtest_2020_2024.csv'
output_file = '/Users/pranaygaurav/Downloads/AlgoTrading/Crypto_AlgoTrading/Devine/volume_profile/final_backtest_2020_2024_with_range.csv'

# Call the function to calculate the price range and update the CSV file
calculate_price_range(input_file, output_file)
