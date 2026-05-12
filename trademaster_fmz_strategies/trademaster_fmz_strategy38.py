# This is trademaster_fmz_strategy38.py
# https://www.fmz.com/strategy/446986
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
from TradeMaster.test import EURUSD
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

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


# Calculate Bollinger Bands and RSI indicators
def calculate_indicators(data, rsi_length=14, bb_length=20, bb_mult=2.0):
    # RSI Calculation
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_length).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    
    # Bollinger Bands Calculation
    data['BBbasis'] = data['Close'].rolling(window=bb_length).mean()
    data['BBdev'] = data['Close'].rolling(window=bb_length).std()
    data['BBupper'] = data['BBbasis'] + bb_mult * data['BBdev']
    data['BBlower'] = data['BBbasis'] - bb_mult * data['BBdev']
    
    data.dropna(inplace=True)
    print("Indicator calculation complete")
    return data

# Strategy class
class BollingerRSIStrategy(Strategy):
    RSIoverSold = 30
    RSIoverBought = 70

    def init(self):
        print("Strategy initialization complete")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        close = self.data.Close[-1]
        rsi = self.data.RSI[-1]
        upper_band = self.data.BBupper[-1]
        lower_band = self.data.BBlower[-1]

        # Long condition: RSI crosses above oversold and price crosses above lower Bollinger band
        if rsi < self.RSIoverSold and crossover(self.data.Close, self.data.BBlower):
            self.buy()
            print(f"Entered long at {close} on {self.data.index[-1]}")

        # Short condition: RSI crosses below overbought and price crosses below upper Bollinger band
        elif rsi > self.RSIoverBought and crossover(self.data.BBupper,self.data.Close):
            self.sell()
            print(f"Entered short at {close} on {self.data.index[-1]}")

# Main code
data = load_data(data_path)
data = calculate_indicators(EURUSD, rsi_length=14, bb_length=20, bb_mult=2.0)
bt = Backtest(data, BollingerRSIStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()