# This is trademaster_fmz_strategy34.py
# https://www.fmz.com/strategy/458176
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
# Consolidate all indicator calculations in a single function
def calculate_indicators(data, length=20, mult=2.0, macd_fast=12, macd_slow=26, macd_signal=9, rsi_length=14):
    try:
        # Bollinger Bands
        data['basis'] = data['Close'].rolling(window=length).mean()
        data['dev'] = data['Close'].rolling(window=length).std()
        data['upper'] = data['basis'] + mult * data['dev']
        data['lower'] = data['basis'] - mult * data['dev']
        
        # MACD
        macd_fast_ema = data['Close'].ewm(span=macd_fast, adjust=False).mean()
        macd_slow_ema = data['Close'].ewm(span=macd_slow, adjust=False).mean()
        data['macdLine'] = macd_fast_ema - macd_slow_ema
        data['signalLine'] = data['macdLine'].ewm(span=macd_signal, adjust=False).mean()
        data['macdHist'] = data['macdLine'] - data['signalLine']
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_length).mean()
        rs = gain / loss
        data['rsi'] = 100 - (100 / (1 + rs))
        
        # Drop NaN values after calculations
        data.dropna(inplace=True)
        print("Indicator calculation complete")
        return data
    except Exception as e:
        print(f"Error in calculate_indicators: {e}")
        raise

# Strategy class
class BollingerMACDRSIStrategy(Strategy):
    rsi_overbought = 70
    rsi_oversold = 30

    def init(self):
        print("Strategy initialization complete")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        close = self.data.Close[-1]
        lower = self.data.lower[-1]
        upper = self.data.upper[-1]
        macdLine = self.data.macdLine[-1]
        signalLine = self.data.signalLine[-1]
        rsi = self.data.rsi[-1]
        

        # Buy signal: Price < lower band, MACD Line > Signal Line, and RSI < oversold level
        if close < lower and macdLine > signalLine and rsi < self.rsi_oversold:
            self.buy()
            print(f"Entered long position at {close}")

        # Sell signal: Price > upper band, MACD Line < Signal Line, and RSI > overbought level
        elif close > upper and macdLine < signalLine and rsi > self.rsi_overbought:
            self.sell()
            print(f"Entered short position at {close} ")

# Main code
data = load_data(data_path)
data = calculate_indicators(EURUSD, length=20, mult=2.0, macd_fast=12, macd_slow=26, macd_signal=9, rsi_length=14)
bt = Backtest(data, BollingerMACDRSIStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
