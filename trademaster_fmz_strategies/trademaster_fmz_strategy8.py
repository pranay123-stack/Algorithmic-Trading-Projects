import pandas as pd
import numpy as np
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement


import pandas_ta as ta
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
from TradeMaster.test import EURUSD
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'


def load_data(csv_file_path):
    try:
        
        data = pd.read_csv(csv_file_path)
        # data['timestamp'] = pd.to_datetime(data['timestamp'])
        # data.set_index('timestamp', inplace=True)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
       
        return data
    except Exception as e:
        print(f"Error in load_and_prepare_data: {e}")
        raise


# Function to calculate indicators on the daily timeframe
def calculate_daily_indicators(daily_data):
    try:
     
        # Calculate EMAs
        daily_data['ema8'] = ta.ema(daily_data['Close'], length=8)
        daily_data['ema21'] = ta.ema(daily_data['Close'], length=21)
        daily_data['ema50'] = ta.ema(daily_data['Close'], length=50)
        daily_data['ema200'] = ta.ema(daily_data['Close'], length=200)

        # Condition: All short-term EMAs must be above the 200-period EMA
        daily_data['all_above_200'] = (daily_data['ema8'] > daily_data['ema200']) & \
                                      (daily_data['ema21'] > daily_data['ema200']) & \
                                      (daily_data['ema50'] > daily_data['ema200'])

        print(f"Data after indicator calculation: {daily_data}")
        return daily_data.dropna()
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise

# Function to generate buy/sell signals based on the strategy logic
def generate_signals(daily_data):
    try:
        print("Generating signals based on strategy logic")

        # Initialize the 'signal' column
        daily_data['signal'] = 0

        # Loop through each row in the DataFrame, starting from index 1
        for i in range(1, len(daily_data)):
            # Access values directly using iloc and column names
            prev_ema8 = daily_data.iloc[i - 1]['ema8']
            prev_ema21 = daily_data.iloc[i - 1]['ema21']
            current_ema8 = daily_data.iloc[i]['ema8']
            current_ema21 = daily_data.iloc[i]['ema21']
            all_above_200 = daily_data.iloc[i]['all_above_200']

            # Check buy condition
            buy_condition = (prev_ema8 < prev_ema21) and \
                            (current_ema8 > current_ema21) and \
                            all_above_200

            # Check sell condition
            sell_condition = (prev_ema8 > prev_ema21) and \
                             (current_ema8 < current_ema21)

            # Assign signals based on conditions
            if buy_condition:
                daily_data.loc[daily_data.index[i], 'signal'] = 1
            elif sell_condition:
                daily_data.loc[daily_data.index[i], 'signal'] = -1
            # No action is taken if neither condition is met (signal remains 0)

        print(f"Data after Signal generation {daily_data}")
        return daily_data

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise



# Define the strategy class
class MultiEMAStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
               #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)

            
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        try:
            
            # Check for signals and execute trades based on signal value
            if self.data.signal[-1] == 1:
                print(f"Buy signal detected, close={self.data.Close[-1]}")
                self.buy()

            elif self.data.signal[-1] == -1:
                print(f"Sell signal detected, close={self.data.Close[-1]}")
                self.position().close()

        except Exception as e:
            print(f"Error in next method: {e}")
            raise




data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data,  MultiEMAStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()