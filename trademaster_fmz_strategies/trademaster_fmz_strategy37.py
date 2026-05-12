# https://www.fmz.com/strategy/449446

import pandas as pd
import numpy as np
import os
import sys
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

# Calculate MACD and Bollinger Bands on MACD
def calculate_macd_bb(data, fast_length=12, slow_length=26, signal_length=9, bb_length=10, bb_dev=1):
    # MACD calculation
    fast_ma = data['Close'].ewm(span=fast_length, adjust=False).mean()
    slow_ma = data['Close'].ewm(span=slow_length, adjust=False).mean()
    data['macd'] = fast_ma - slow_ma
    data['signal'] = data['macd'].ewm(span=signal_length, adjust=False).mean()
    
    # Bollinger Bands on MACD
    data['macd_sma'] = data['macd'].rolling(window=bb_length).mean()
    data['macd_std'] = data['macd'].rolling(window=bb_length).std()
    data['Upper'] = data['macd_sma'] + (bb_dev * data['macd_std'])
    data['Lower'] = data['macd_sma'] - (bb_dev * data['macd_std'])
    
    data.dropna(inplace=True)
    print("MACD and Bollinger Bands calculation complete")
    return data

# Strategy class
class AKMACDBBStrategy(Strategy):
    tp_percent = 1.0 / 100  # Take Profit percentage
    sl_percent = 1.0 / 100  # Stop Loss percentage

    def init(self):
        print("Strategy initialization complete")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        close = self.data.Close[-1]
        macd = self.data.macd[-1]
        upper = self.data.Upper[-1]
        lower = self.data.Lower[-1]

        # Buy condition: MACD crosses above the Upper Bollinger Band
        if macd > upper and not self.position().is_long:
            self.buy()
            entry_price = close
            tp_price = entry_price * (1 + self.tp_percent)
            sl_price = entry_price * (1 - self.sl_percent)
            print(f"Entered long at {entry_price} with TP at {tp_price} and SL at {sl_price}")
            self.set_tp_sl(tp_price, sl_price)

        # Sell condition: MACD crosses below the Lower Bollinger Band
        elif macd < lower and not self.position().is_short:
            self.sell()
            entry_price = close
            tp_price = entry_price * (1 - self.tp_percent)
            sl_price = entry_price * (1 + self.sl_percent)
            print(f"Entered short at {entry_price} with TP at {tp_price} and SL at {sl_price}")
            self.set_tp_sl(tp_price, sl_price)

    def set_tp_sl(self, tp_price, sl_price):
        """
        Helper function to implement take profit and stop loss.
        """
        if self.position().is_long:
            if self.data.High[-1] >= tp_price:
                self.position().close()
                print(f"Long TP reached at {tp_price}")
            elif self.data.Low[-1] <= sl_price:
                self.position().close()
                print(f"Long SL hit at {sl_price}")
        elif self.position().is_short:
            if self.data.Low[-1] <= tp_price:
                self.position().close()
                print(f"Short TP reached at {tp_price}")
            elif self.data.High[-1] >= sl_price:
                self.position().close()
                print(f"Short SL hit at {sl_price}")

# Main code
data = load_data(data_path)
data = calculate_macd_bb(EURUSD, fast_length=12, slow_length=26, signal_length=9, bb_length=10, bb_dev=1)
bt = Backtest(data, AKMACDBBStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()