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

# Function to calculate indicators on the daily timeframe
def calculate_daily_indicators(daily_data, length=20, mult=2.0, ma_type='SMA'):
    try:
        print("Calculating Bollinger Bands on daily data")
        
        # Moving average calculation based on selected type
        if ma_type == 'SMA':
            daily_data['basis'] = ta.sma(daily_data['Close'], length)
        elif ma_type == 'EMA':
            daily_data['basis'] = ta.ema(daily_data['Close'], length)
        elif ma_type == 'SMMA (RMA)':
            daily_data['basis'] = ta.rma(daily_data['Close'], length)
        elif ma_type == 'WMA':
            daily_data['basis'] = ta.wma(daily_data['Close'], length)
        elif ma_type == 'VWMA':
            daily_data['basis'] = ta.vwma(daily_data['Close'], length)

        # Calculate the Bollinger Bands
        daily_data['std_dev'] = daily_data['Close'].rolling(window=length).std()
        daily_data['upper'] = daily_data['basis'] + (daily_data['std_dev'] * mult)
        daily_data['lower'] = daily_data['basis'] - (daily_data['std_dev'] * mult)

        daily_data.dropna(inplace=True)

        print(f"Daily indicator calculation complete\n{daily_data.head(20)}")
        return daily_data
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise

# Define the strategy class
class BBStrategy(Strategy):
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
            # Check for long condition: Close crosses above the upper Bollinger Band
            long_condition = (
                self.data.Close[-2] < self.data.upper[-2] and
                self.data.Close[-1] > self.data.upper[-1]
            )

            # Check for short condition: Close crosses below the lower Bollinger Band
            short_condition = (
                self.data.Close[-2] > self.data.lower[-2] and
                self.data.Close[-1] < self.data.lower[-1]
            )

            # Close long position if a short condition is met
            if self.position().is_long and short_condition:
                print(f"Sell signal detected, closing long position at close={self.data.Close[-1]}")
                self.position().close()

            # Close short position if a long condition is met
            elif self.position().is_short and long_condition:
                print(f"Buy signal detected, closing short position at close={self.data.Close[-1]}")
                self.position().close()

            # Open a long position if the long condition is met
            if long_condition and not self.position().is_long:
                print(f"Buy signal detected, opening long position at close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                self.buy()

            # Open a short position if the short condition is met
            elif short_condition and not self.position().is_short:
                print(f"Sell signal detected, opening short position at close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                self.sell()

        except Exception as e:
            print(f"Error in next method: {e}")
            raise

# Load data and apply indicators
data = load_data(data_path)
data = calculate_daily_indicators(EURUSD)

# Run backtest
bt = Backtest(data, BBStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
