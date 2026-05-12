import requests
import json

def fetch_bybit_data():
    # URL to fetch data
    url = "https://api.bybit.com/v5/market/kline?category=spot&symbol=BTCUSDT&interval=1&limit=1000"

    # Sending GET request to the API
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        
        # Print the data
        print(json.dumps(data, indent=4))
        
        # Return the data for further processing if needed
        return data
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return None

# Fetch and print the data
fetch_bybit_data()
