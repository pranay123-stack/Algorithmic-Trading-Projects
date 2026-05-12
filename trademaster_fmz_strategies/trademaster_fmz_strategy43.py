# This is trademaster_fmz_strategy43.py
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
from TradeMaster.lib import crossover
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


# Helper functions for indicators
def calculate_dsl(price, length, offset):
    # Ensure price is a pandas Series
    price = pd.Series(price) if not isinstance(price, pd.Series) else price

    sma = price.rolling(window=length).mean()
    offset_value = offset * price.std()

    dsl_up = sma + offset_value
    dsl_dn = sma - offset_value

    return dsl_up.values, dsl_dn.values  # Return array-like objects


def calculate_rsi(series, period):
    # Ensure the series is a pandas Series
    series = pd.Series(series) if not isinstance(series, pd.Series) else series

    # Calculate the difference in price
    delta = series.diff()

    # Separate the gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate the average gain and loss
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # Calculate the RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.fillna(50).values  # Fill NaN with 50 (neutral RSI) and return as array


def calculate_atr(data, period):
    """Calculates ATR for given period."""
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift(1))
    low_close = np.abs(data['Low'] - data['Close'].shift(1))
    tr = high_low.combine(high_close, np.maximum).combine(low_close, np.maximum)
    return tr.rolling(window=period).mean()




class DSLStrategy(Strategy):
    # Define class-level constants for indicator parameters
    dsl_length = 34
    offset = 30
    width = 1
    atr_period = 200
    rsi_period = 10
    risk_reward = 1.5

    def init(self):
        # Assign precomputed indicators to class attributes
        self.dsl_up = self.data.DSL_UP
        self.dsl_dn = self.data.DSL_DN
        self.atr = self.data.ATR
        self.rsi = self.data.RSI
        self.dsl_up_band = self.data.DSL_UP_BAND
        self.dsl_dn_band = self.data.DSL_DN_BAND

    def next(self):
        # Conditions for Long Entry
        long_condition1 = self.dsl_up_band[-1] > self.dsl_dn[-1]
        long_condition2 = (
            self.data.Open[-1] > self.dsl_up[-1] and self.data.Close[-1] > self.dsl_up[-1] and
            self.data.Open[-2] > self.dsl_up[-2] and self.data.Close[-2] > self.dsl_up[-2]
        )
        long_signal = long_condition1 and long_condition2

        # Conditions for Short Entry
        short_condition1 = self.dsl_dn_band[-1] < self.dsl_up[-1]
        short_condition2 = (
            self.data.Open[-1] < self.dsl_dn_band[-1] and self.data.Close[-1] < self.dsl_dn_band[-1] and
            self.data.Open[-2] < self.dsl_dn_band[-2] and self.data.Close[-2] < self.dsl_dn_band[-2]
        )
        short_signal = short_condition1 and short_condition2

        # Execute Long Trade
        if long_signal and not self.position:
            stop_loss = self.dsl_up_band[-1]
            take_profit = self.data.Close[-1] + (self.data.Close[-1] - stop_loss) * self.risk_reward
            self.buy(sl=stop_loss, tp=take_profit)

        # Execute Short Trade
        if short_signal and not self.position:
            stop_loss = self.dsl_dn_band[-1]
            take_profit = self.data.Close[-1] - (stop_loss - self.data.Close[-1]) * self.risk_reward
            self.sell(sl=stop_loss, tp=take_profit)


def calculate_daily_indicators(data):
    # Use DSLStrategy constants to calculate indicators
    data['DSL_UP'], data['DSL_DN'] = calculate_dsl(data['Close'], DSLStrategy.dsl_length, DSLStrategy.offset)
    data['ATR'] = calculate_atr(data, DSLStrategy.atr_period)
    data['RSI'] = calculate_rsi(data['Close'], DSLStrategy.rsi_period)

    # Compute DSL Bands
    data['DSL_UP_BAND'] = data['DSL_UP'] - data['ATR'] * DSLStrategy.width
    data['DSL_DN_BAND'] = data['DSL_DN'] + data['ATR'] * DSLStrategy.width

    return data

file="/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1h/btc_1h_data_2023.csv"
data =load_data(file)
data = calculate_daily_indicators(data)

# Backtesting the strategy
bt = Backtest(data, DSLStrategy, cash=1000000, commission=0.002)
stats = bt.run()
bt.plot()
print(stats)
# bt.plot(superimpose=False)
# bt.tear_sheet()
