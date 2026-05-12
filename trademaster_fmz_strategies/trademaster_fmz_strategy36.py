# This is trademaster_fmz_strategy36.py
# https://www.fmz.com/strategy/453232
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.test import EURUSD
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

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

# Calculate Bollinger Bands indicators
def calculate_bollinger_bands(data, length=34, mult=2.0):
    data['basis'] = data['Close'].rolling(window=length).mean()
    data['dev'] = data['Close'].rolling(window=length).std()
    data['upper1'] = data['basis'] + data['dev']
    data['lower1'] = data['basis'] - data['dev']
    data['upper2'] = data['basis'] + mult * data['dev']
    data['lower2'] = data['basis'] - mult * data['dev']
    data.dropna(inplace=True)
    print("Bollinger Bands calculation complete")
    return data

# Strategy class
class BollingerBandsStrategy(Strategy):
    def init(self):
        print("Strategy initialization complete")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        close = self.data.Close[-1]
        upper1 = self.data.upper1[-1]
        lower1 = self.data.lower1[-1]

        # Long condition: Close above upper Bollinger band
        if close > upper1 and not self.position().is_long:
            self.buy()
            print(f"Entered long position at {close} on {self.data.index[-1]}")

        # Short condition: Close below lower Bollinger band
        elif close < lower1 and not self.position().is_short:
            self.sell()
            print(f"Entered short position at {close} on {self.data.index[-1]}")

        # Close long position if short condition is met
        if self.position().is_long and close < lower1:
            self.position().close()
            print(f"Closed long position at {close} on {self.data.index[-1]} due to short condition")

        # Close short position if long condition is met
        elif self.position().is_short and close > upper1:
            self.position().close()
            print(f"Closed short position at {close} on {self.data.index[-1]} due to long condition")

# Main code
data = load_data(data_path)
data = calculate_bollinger_bands(EURUSD, length=34, mult=2.0)
bt = Backtest(data, BollingerBandsStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()