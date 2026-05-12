import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import pandas_ta as ta
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement
from TradeMaster.test import EURUSD
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_and_prepare_data: {e}")
        raise

def calculate_daily_indicators(data):
    # Calculate the 50-period and 200-period Simple Moving Averages (SMA)
    data['ma_50'] = ta.sma(data['Close'], length=50)
    data['ma_200'] = ta.sma(data['Close'], length=200)

    # Define lengths for retracement levels
    len_21, len_50, len_9 = 21, 50, 9

    # Initialize Fibonacci levels with NaN
    data['fib_50_level'] = np.nan
    data['fib_786_level'] = np.nan

    # Calculate retracement levels only when close > MA_200 and close > MA_50
    condition = (data['Close'] > data['ma_200']) & (data['Close'] > data['ma_50'])

    data.loc[condition, 'retrace_21_high'] = data['High'].rolling(window=len_21).max()
    data.loc[condition, 'retrace_21_low'] = data['Low'].rolling(window=len_21).min()
    data.loc[condition, 'retrace_21_mid'] = (data['retrace_21_high'] + data['retrace_21_low']) / 2

    data.loc[condition, 'retrace_50_high'] = data['High'].rolling(window=len_50).max()
    data.loc[condition, 'retrace_50_low'] = data['Low'].rolling(window=len_50).min()
    data.loc[condition, 'retrace_50_mid'] = (data['retrace_50_high'] + data['retrace_50_low']) / 2

    data.loc[condition, 'retrace_9_high'] = data['High'].rolling(window=len_9).max()
    data.loc[condition, 'retrace_9_low'] = data['Low'].rolling(window=len_9).min()
    data.loc[condition, 'retrace_9_mid'] = (data['retrace_9_high'] + data['retrace_9_low']) / 2

    # Calculate the Fibonacci levels only for the filtered rows
    data.loc[condition, 'fib_50_level'] = (data['retrace_21_mid'] + data['retrace_50_mid'] + data['retrace_9_mid']) / 3
    data.loc[condition, 'fib_786_level'] = (
        (data.loc[condition, 'retrace_21_high'] + data.loc[condition, 'retrace_50_high'] + data.loc[condition, 'retrace_9_high']) / 3 -
        ((data.loc[condition, 'retrace_21_high'] + data.loc[condition, 'retrace_50_high'] + data.loc[condition, 'retrace_9_high'] -
          data.loc[condition, 'retrace_21_low'] - data.loc[condition, 'retrace_50_low'] - data.loc[condition, 'retrace_9_low']) * 0.786)
    )

    return data.dropna()

class RetracementStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
            self.entry_price = None
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
            # Ensure enough data for calculation
            if len(self.data) < 2:
                return
            
            # Generate the long condition within next()
            long_condition = (
                (self.data.Close[-1] > self.data.ma_200[-1]) &
                (self.data.Close[-1] > self.data.ma_50[-1]) &
                (self.data.Close[-1] <= self.data.fib_50_level[-1])
            )

            # Buy logic if long condition is met
            if long_condition:
                print(f"Buy signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                risk_reward_ratio = 2.0
                take_profit_level = self.entry_price + (self.entry_price - self.data.fib_786_level[-1]) * risk_reward_ratio
                stop_loss_level = self.data.fib_786_level[-1]
                
                self.buy(sl=stop_loss_level, tp=take_profit_level)
        
        except Exception as e:
            print(f"Error in next method: {e}")
            raise

# Load data and calculate indicators
# data = load_data(data_path)
data = calculate_daily_indicators(EURUSD)
# Run backtest
bt = Backtest(data, RetracementStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()

