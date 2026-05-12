import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import pandas_ta as ta
from TradeMaster.test import EURUSD
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement


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
def calculate_daily_indicators(daily_data, ema_length=9, sma30_length=30, sma50_length=50, sma200_length=200, sma325_length=325):
    try:
     
        # Calculate EMA and SMAs
        daily_data['ema'] = ta.ema(daily_data['Close'], length=ema_length)
        daily_data['sma30'] = ta.sma(daily_data['Close'], length=sma30_length)
        daily_data['sma50'] = ta.sma(daily_data['Close'], length=sma50_length)
        daily_data['sma200'] = ta.sma(daily_data['Close'], length=sma200_length)
        daily_data['sma325'] = ta.sma(daily_data['Close'], length=sma325_length)

        print("Daily indicator calculation complete")
        return daily_data
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
            # Access values directly using iloc
            prev_ema = daily_data.iloc[i - 1]['ema']
            prev_sma30 = daily_data.iloc[i - 1]['sma30']
            current_ema = daily_data.iloc[i]['ema']
            current_sma30 = daily_data.iloc[i]['sma30']
            prev_sma50 = daily_data.iloc[i - 1]['sma50']
            current_sma50 = daily_data.iloc[i]['sma50']

            # Buy Signal Condition
            buy_signal = (prev_ema < prev_sma30) and (current_ema > current_sma30)

            # Sell Signal Condition
            sell_signal = (prev_sma30 < prev_ema and current_sma30 > current_ema) or \
                          (prev_sma50 < prev_ema and current_sma50 > current_ema)

            # Assign signals based on conditions
            if buy_signal:
                daily_data.loc[daily_data.index[i], 'signal'] = 1
            elif sell_signal:
                daily_data.loc[daily_data.index[i], 'signal'] = -1
            # No action is taken if neither condition is met (signal remains 0)

        print("Signal generation complete")
        return daily_data

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise



# Define the strategy class
class EMASMACrossoverStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
                #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)
 
            print("Strategy initialization complete")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        try:
            # print(f"Processing bar: {self.data.index[-1]} with signal {self.data.signal[-1]} at price {self.data.Close[-1]}")
            # Check for signals and execute trades based on signal value
            if self.data.signal[-1] == 1:
                print(f"Buy signal detected, close={self.data.Close[-1]}")
                self.buy()

            elif self.data.signal[-1] == -1 :
                print(f"Sell signal detected, close={self.data.Close[-1]}")
                self.position().close()

      
        except Exception as e:
            print(f"Error in next method: {e}")
            raise





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, EMASMACrossoverStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()