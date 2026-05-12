import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import pandas_ta as ta
from TradeMaster.test import EURUSD
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_and_prepare_data: {e}")
        raise

def calculate_daily_indicators(df):
    # Calculate the required indicators
    df['SMA01'] = ta.sma(df['Close'], length=3)
    df['SMA02'] = ta.sma(df['Close'], length=8)
    df['SMA03'] = ta.sma(df['Close'], length=10)
    df['EMA01'] = ta.ema(df['Close'], length=5)
    df['EMA02'] = ta.ema(df['Close'], length=3)
    df['OHLC'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4.0

    # Ensure no NaN values from indicator calculations
    df.dropna(inplace=True)

    return df

class ComboStrategy(Strategy):
    def init(self):
        # Initialize variables
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        self.BarsSinceEntry = None
        self.MaxProfitCount = 0  # Initialize MaxProfitCount as 0
        self.MaxBars = 10  # Maximum bars to hold position
        self.position_avg_price = None  # Track average price of the position

    def next(self):
        # Initialize BarsSinceEntry if it's the first bar of the strategy
        if self.BarsSinceEntry is None:
            self.BarsSinceEntry = 0

        if len(self.data) < 2:
            return  # Skip this iteration if there's not enough data

        # Signal generation conditions
        cond01 = self.data.Close[-1] < self.data.SMA03[-1]
        cond02 = self.data.Close[-1] <= self.data.SMA01[-1]
        cond03 = self.data.Close[-2] > self.data.SMA01[-2]
        cond04 = self.data.Open[-1] > self.data.EMA01[-1]
        cond05 = self.data.SMA02[-1] < self.data.SMA02[-2]
        entry01 = cond01 & cond02 & cond03 & cond04 & cond05

        cond06 = self.data.Close[-1] < self.data.EMA02[-1]
        cond07 = self.data.Open[-1] > self.data.OHLC[-1]
        cond08 = self.data.Volume[-1] <= self.data.Volume[-2]
        shifted_open = self.data.Open[-2]
        shifted_close = self.data.Close[-2]
        cond09 = (self.data.Close[-1] < min(shifted_open, shifted_close)) | (self.data.Close[-1] > max(shifted_open, shifted_close))
        entry02 = cond06 & cond07 & cond08 & cond09

        # Buy condition based on either Entry01 or Entry02
        buy_condition = entry01 | entry02

        # Check if no position is open
        cond00 = self.position().size == 0

        # Update BarsSinceEntry
        if cond00:
            self.BarsSinceEntry = 0  # Reset BarsSinceEntry if no position
            self.MaxProfitCount = 0  # Reset MaxProfitCount if no position
        else:
            # Increment BarsSinceEntry if there is an open position
            self.BarsSinceEntry += 1
            # If the current close price is greater than the average entry price and BarsSinceEntry > 1
            if self.data.Close[-1] > self.position_avg_price and self.BarsSinceEntry > 1:
                self.MaxProfitCount += 1  # Increment MaxProfitCount
                print(f"MaxProfitCount incremented: {self.MaxProfitCount}")

        # Execute a buy if the buy condition is met and no position is open
        if buy_condition and cond00:
            self.buy(size=1)
            self.position_avg_price = self.data.Close[-1]  # Store the entry price
            print(f"Position opened at {self.data.Close[-1]}")

        # Exit the position if BarsSinceEntry exceeds MaxBars or MaxProfitCount exceeds threshold
        if (self.BarsSinceEntry - 1) >= self.MaxBars or self.MaxProfitCount >= 5:
            self.position().close()
            print(f"Position closed at {self.data.Close[-1]}")

# Load data and apply indicators
data = load_data(data_path)
data = calculate_daily_indicators(EURUSD)

# Run backtest
bt = Backtest(data, ComboStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
