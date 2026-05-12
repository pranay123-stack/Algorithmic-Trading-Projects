# This is trademaster_fmz_strategy39.py
# https://www.fmz.com/strategy/458031
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

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


# Calculate Support, Resistance, and Bollinger Bands
def calculate_indicators(data, period=20):
    # Support and Resistance Levels
    data['highMax'] = data['High'].rolling(window=period).max()
    data['lowMin'] = data['Low'].rolling(window=period).min()

    # Bollinger Bands Calculation
    data['basis'] = data['Close'].rolling(window=period).mean()
    data['dev'] = data['Close'].rolling(window=period).std()
    data['upperBB'] = data['basis'] + 2 * data['dev']
    data['lowerBB'] = data['basis'] - 2 * data['dev']

    data.dropna(inplace=True)
    print("Support, Resistance, and Bollinger Bands calculation complete")
    return data

# Strategy class
class MarsSignalsPrecisionTrading(Strategy):
    def init(self):
        print("Strategy initialization complete")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        close = self.data.Close[-1]
        open_price = self.data.Open[-1]
        highMax = self.data.highMax[-1]
        lowMin = self.data.lowMin[-1]

          # Ensure there are at least two data points to avoid IndexError
        if len(self.data) < 2:
            return  # Skip this iteration if there's not enough data

        # Buy signal: Close > Open and Close > previous highMax
        buy_signal = (close > open_price) and (close > self.data.highMax[-2])
        
        # Sell signal: Close < Open and Close < previous lowMin
        sell_signal = (close < open_price) and (close < self.data.lowMin[-2])

        # Execute buy or sell based on signals
        if buy_signal and not self.position().is_long:
            self.buy()
            print(f"Entered long position at {close} on {self.data.index[-1]}")
        
        if sell_signal and not self.position().is_short:
            self.sell()
            print(f"Entered short position at {close} on {self.data.index[-1]}")

# Main code
data = load_data(data_path)
data = calculate_indicators(EURUSD, period=20)
bt = Backtest(data, MarsSignalsPrecisionTrading, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()