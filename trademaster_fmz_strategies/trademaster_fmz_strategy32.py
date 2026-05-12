# https://www.fmz.com/strategy/458268

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

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
# Consolidate all indicator calculations in a single function
def calculate_indicators(data, length=20, mult=2.0):
    try:
        # Calculate Bollinger Bands
        data['basis'] = data['Close'].rolling(window=length).mean()
        data['dev'] = data['Close'].rolling(window=length).std()
        data['upper'] = data['basis'] + mult * data['dev']
        data['lower'] = data['basis'] - mult * data['dev']
        
        # Drop rows with NaN values
        data.dropna(inplace=True)
        print("Indicator calculation complete")
        return data
    except Exception as e:
        print(f"Error in calculate_indicators: {e}")
        raise

# Strategy class
class MeanReversionBollingerStrategy(Strategy):
    def init(self):
        # Tracking variables for entry price and entry date
        self.entry_price = None
        self.entry_date = None
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        print("Strategy initialization complete")

    def next(self):
        close = self.data.Close[-1]
        basis = self.data.basis[-1]
        upper = self.data.upper[-1]
        lower = self.data.lower[-1]
    
        
        # Long entry condition: Price crosses above the middle band
        if crossover(self.data.Close, self.data.basis) and (self.entry_date is None or self.entry_date != current_date):
            self.entry_price = close
            self.buy()
            print(f"Entered long position at {close}")

        # Exit conditions: price crosses below middle band or drops 2% below entry price
        if self.position().is_long:
            drop_price = self.entry_price * 0.98  # 2% below entry
            if close <= drop_price:
                self.position().close()
                print(f"Emergency stop triggered at {close} due to 2% drop from entry price {self.entry_price}")
                self.entry_date = None  # Allow new entry
            elif crossover(self.data.basis,self.data.Close):
                self.position().close()
                print(f"Exited long position at {close} due to cross under middle band")
                self.entry_date = None  # Allow new entry

# Main code
data = load_data(data_path)
data = calculate_indicators(EURUSD, length=20, mult=2.0)
bt = Backtest(data, MeanReversionBollingerStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
