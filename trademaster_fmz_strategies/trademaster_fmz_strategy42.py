  #https://www.fmz.com/strategy/439741
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
import logging

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



# Calculate daily indicators
def calculate_daily_indicators(df):
    try:
        # Momentum = src - src[len]
        df['Momentum'] = df['Close'] - df['Close'].shift(50)
        
        # ATR with a length of 14
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        # VIX Fix = (highest(close,VIXFixLength)-low)/(highest(close,VIXFixLength))*100
        VIXFixLength = 22
        df['VIXFix'] = ((df['Close'].rolling(window=VIXFixLength).max() - df['Low']) / 
                        (df['Close'].rolling(window=VIXFixLength).max())) * 100
        
        # Band upper and lower for momentum comparison
        df['BandUpper'] = 5
        df['BandLower'] = -5
        
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Error calculating daily indicators: {e}")
        return None

def generate_signals(df):
    try:
        # Long1: Momentum > BandUpper
        df['Long1'] = df['Momentum'] > df['BandUpper']
        
        # Short1: Momentum < BandLower
        df['Short1'] = df['Momentum'] < df['BandLower']
        
        # VIX crossover and crossunder conditions
        df['Long2'] = (df['Momentum'] > df['VIXFix']) & (df['Momentum'].shift(1) <= df['VIXFix'].shift(1))  # Crossover
        df['Short2'] = (df['Momentum'] < df['VIXFix']) & (df['Momentum'].shift(1) >= df['VIXFix'].shift(1))  # Crossunder
        
        # Sell signal: when Short1 condition is met
        df['SellSignal'] = df['Short1']
        
        # Buy signal: when Long2 condition is met (to close short positions)
        df['BuySignal'] = df['Long2']
        
        return df
    except Exception as e:
        print(f"Error generating signals: {e}")
        return None




class FearAndGreedIndex(Strategy):
    def init(self):
        # This method is used to initialize the strategy; no complex indicators are needed here
        pass
    
    def next(self):
        try:
            # Check for sell signals and enter short positions
            if self.data.SellSignal[-1] and not self.position.is_short:
                self.sell()
            
            # Check for buy signals (to close the short positions)
            if self.data.BuySignal[-1] and self.position.is_short:
                self.position.close()
                
        except Exception as e:
            print(f"Error in next function: {e}")






data = calculate_daily_indicators(EURUSD)
bt = Backtest(data, FearAndGreedIndex, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
