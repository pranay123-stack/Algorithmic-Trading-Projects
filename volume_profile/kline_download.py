#=======spot fetch =============== introduced in bybit after (2021 6 6)
import pandas as pd
import json
import requests
from datetime import datetime as dt, timedelta
import os
import shutil

def generate_kline_fetch_configs():
    start_date = dt(2020, 1, 1)
    end_date = dt(2024, 8, 25)
    delta = timedelta(days=1)

    data = []

    current_date = start_date
    while current_date < end_date:
        from_date = current_date.strftime("%d-%m-%Y")
        to_date = (current_date + delta).strftime("%d-%m-%Y")
        data.append({
            "symbol": "BTCUSDT",
            "interval": "1",
            "from_date": from_date,
            "to_date": to_date
        })
        current_date += delta
    
    return data

def download_historical_klines(symbol, interval,from_date, to_date):
    payload = {}
    headers = {}

    # Convert dates to reverse order (YYYY-MM-DD)
    from_date_dt = dt.strptime(from_date, '%d-%m-%Y')
    to_date_dt = dt.strptime(to_date, '%d-%m-%Y')
    from_date_rev = from_date_dt.strftime('%Y-%m-%d')
    to_date_rev = to_date_dt.strftime('%Y-%m-%d')
    
    # Directory and file setup
    base_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/crypto/Devine_group/volume_profile/klines'
    folder_name = f"{from_date_rev}_{to_date_rev}"
    output_dir = os.path.join(base_dir, folder_name)
    
    # Check if the folder already exists, delete if it does, then create a new one
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    
    file_name = os.path.join(output_dir, f"kline_{from_date_rev}_{to_date_rev}_output.csv")
    
    # Convert string to datetime and get epoch times in milliseconds
    start_epoch_time = int(from_date_dt.timestamp() * 1000)
    end_epoch_time = int(to_date_dt.timestamp() * 1000)
    
    columns = ['startTime', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'volume', 'turnover']
    df = pd.DataFrame(columns=columns)
    
    # Check if the file already exists, delete if it does, then create a new one
    if os.path.exists(file_name):
        os.remove(file_name)
    
    df.to_csv(file_name, mode='a', index=False, header=True)
    
    while start_epoch_time < end_epoch_time:
        url = f"https://api.bybit.com/v5/market/kline?category=linear&symbol=BTCUSDT&interval=1&limit=1000&start={start_epoch_time}"
        response = requests.get(url, headers=headers, data=payload)
        data = response.json()
        # print("RESPONSE DATA ",data)
        json_data = data['result']['list']
        df = pd.DataFrame(json_data, columns=columns)
        final_df = df.sort_values(by=['startTime'], ascending=True)
        final_df.to_csv(file_name, mode='a', index=False, header=None)
        start_epoch_time += (60 * 1000 * 1000)
    
    
    print("Output file:", file_name)

def main():  
    base_oi_dir = '/Users/pranaygaurav/Downloads/AlgoTrading/crypto/Devine_group/volume_profile/klines'
    
    # Check if the open_interest folder already exists, delete if it does, then create a new one
    if os.path.exists(base_oi_dir):
        shutil.rmtree(base_oi_dir)
    os.makedirs(base_oi_dir)
    
    # Generate open interest configurations
    configs = generate_kline_fetch_configs()
    
    for config in configs:
        symbol = config['symbol']
        interval = config['interval']
        from_date = config['from_date']
        to_date = config['to_date']
        download_historical_klines(symbol,  interval, from_date, to_date)

if __name__ == "__main__":
    main()
