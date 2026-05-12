# https://www.fmz.com/strategy/472252
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
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1h/btc_1h_data_2023.csv'



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

# Calculate indicators function
def calculate_indicators(data, box_length=5):
    # Calculate the 25-period moving average
    data['ma25'] = data['Close'].rolling(window=25).mean()

    # Calculate Darvas Box (Highest high and Lowest low over the box period)
    data['LL'] = data['Low'].rolling(window=box_length).min()
    data['K1'] = data['High'].rolling(window=box_length).max()

    # Darvas Box logic (We will also need previous box for calculating the new box levels)
    data['K2'] = data['High'].rolling(window=box_length-1).max()
    data['K3'] = data['High'].rolling(window=box_length-2).max()

    # New high detection logic
    data['NH'] = data['High'].where(data['High'] > data['K1'].shift(1))

    # Darvas Box logic
    data['TopBox'] = data.apply(lambda row: row['NH'] if row['K3'] < row['K2'] else np.nan, axis=1)
    data['BottomBox'] = data.apply(lambda row: row['LL'] if row['K3'] < row['K2'] else np.nan, axis=1)

    return data

# Strategy class for Darvas Box and MA25 strategy
class DarvasBoxMA25Strategy(Strategy):
    def init(self):
       pass

    def next(self):
        # Access the necessary columns
        close = self.data.Close[-1]
        ma25 = self.data.ma25[-1]
        top_box = self.data.TopBox[-1]
        bottom_box = self.data.BottomBox[-1]

        # Buy condition: Price breaks above the Darvas Box AND above MA25
        buy_condition = close > top_box and close > ma25

        # Sell condition: Price breaks below the Darvas Box
        sell_condition = close < bottom_box

        # Executing strategy
        if buy_condition and not self.position.is_long:
            self.buy()
            print(f"Long entry at {close} with top box at {top_box}")

        elif sell_condition and not self.position.is_short:
            self.sell()
            print(f"Short entry at {close} with bottom box at {bottom_box}")






# Main code
data = load_data(data_path)
data = calculate_indicators(EURUSD)
bt = Backtest(data, DarvasBoxMA25Strategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
