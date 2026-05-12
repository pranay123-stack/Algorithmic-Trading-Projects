# This is trademaster_fmz_strategy40.py
# https://www.fmz.com/strategy/454732
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
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import EURUSD
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

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

# Calculate Bollinger Bands indicators
def calculate_bollinger_bands(data, length=20, mult=2.0):
    data['basis'] = data['Close'].rolling(window=length).mean()
    data['dev'] = data['Close'].rolling(window=length).std()
    data['upper_band'] = data['basis'] + mult * data['dev']
    data['lower_band'] = data['basis'] - mult * data['dev']
    data.dropna(inplace=True)
    print("Bollinger Bands calculation complete")
    return data

# Strategy class
class BollingerBandsStrategy(Strategy):
    def init(self):
        # Variables to track position status
        self.in_long = False
        self.in_short = False
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        print("Strategy initialization complete")

    def next(self):
        close = self.data.Close[-1]
        upper_band = self.data.upper_band[-1]
        lower_band = self.data.lower_band[-1]

        # Buy condition: close below the lower Bollinger Band
        if close < lower_band and not self.in_long:
            self.buy()
            self.in_long = True
            self.in_short = False  # Reset short position flag if going long
            print(f"Entered long position at {close} on {self.data.index[-1]}")

        # Sell condition: close above the upper Bollinger Band
        elif close > upper_band and not self.in_short:
            self.sell()
            self.in_short = True
            self.in_long = False  # Reset long position flag if going short
            print(f"Entered short position at {close} on {self.data.index[-1]}")

        # Close long position if sell condition is met
        if self.in_long and close > upper_band:
            self.position().close()
            self.in_long = False
            print(f"Closed long position at {close} on {self.data.index[-1]} due to sell condition")

        # Close short position if buy condition is met
        elif self.in_short and close < lower_band:
            self.position().close()
            self.in_short = False
            print(f"Closed short position at {close} on {self.data.index[-1]} due to buy condition")

# Main code
data = load_data(data_path)
data = calculate_bollinger_bands(EURUSD, length=20, mult=2.0)
bt = Backtest(data, BollingerBandsStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
