# This is trademaster_fmz_strategy33.py
# https://www.fmz.com/strategy/468349
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
from TradeMaster.test import EURUSD
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

# Load data function
def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_data: {e}")
        raise

# Calculate indicators (Bollinger Bands, %b, and 200-day SMA)
def calculate_indicators(data, length=20, mult=2.0):
    try:
        data['sma200'] = data['Close'].rolling(window=200).mean()
        data['basis'] = data['Close'].rolling(window=length).mean()
        data['dev'] = data['Close'].rolling(window=length).std()
        data['upperBand'] = data['basis'] + mult * data['dev']
        data['lowerBand'] = data['basis'] - mult * data['dev']
        
        # Calculate %b
        data['percentB'] = (data['Close'] - data['lowerBand']) / (data['upperBand'] - data['lowerBand'])
        
        # Drop rows with NaN values resulting from rolling calculations
        data.dropna(inplace=True)
        print("Indicator calculation complete")
        return data
    except Exception as e:
        print(f"Error in calculate_indicators: {e}")
        raise

# Strategy class
class LarryConnorsBollingerStrategy(Strategy):
    def init(self):
        print("Strategy initialization complete")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        close = self.data.Close[-1]
        sma200 = self.data.sma200[-1]
        percentB = self.data.percentB[-1]


                # Ensure there are at least two data points to avoid IndexError
        if len(self.data) < 3:
            return  # Skip this iteration if there's not enough data
 

        # Buy condition: Close > SMA200 and %b below 0.2 for the last three days
        if close > sma200 and all(self.data.percentB[-i] < 0.2 for i in range(1, 4)):
            self.buy()
            print(f"Entered long position at {close} ")

        # Sell condition: %b closes above 0.8
        elif percentB > 0.8 and self.position().is_long:
            self.position().close()
            print(f"Exited long position at {close}  due to %b > 0.8")

# Main code
data = load_data(data_path)
data = calculate_indicators(EURUSD, length=20, mult=2.0)
bt = Backtest(data, LarryConnorsBollingerStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()