# https://www.fmz.com/strategy/458026

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
# Strategy class
class RedCandleBreakoutBuyStrategy(Strategy):
    big_red_candle_points = 20
    stop_loss_points = 20
    target_points = 50
    default_quantity = 1
    max_quantity = 5  # Limit maximum quantity

    def init(self):
        # Tracking the first big red candle's low and whether it has been detected
        self.first_red_candle_low = None
        self.first_red_candle_detected = False
        # Tracking variables for dynamic quantity adjustment based on profits
        self.last_equity = self.equity
        self.current_quantity = self.default_quantity
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        print("Strategy initialization complete")

    def next(self):
        high = self.data.High[-1]
        low = self.data.Low[-1]
        open_price = self.data.Open[-1]
        close = self.data.Close[-1]

        # Detect a big red candle
        big_red_candle = (high - low >= self.big_red_candle_points) and (close < open_price)

        # Track the first big red candle low
        if big_red_candle:
            self.first_red_candle_low = low
            self.first_red_candle_detected = True

        # Reset if a new big red candle is detected
        if big_red_candle and self.first_red_candle_detected:
            self.first_red_candle_low = low

        # Buy signal: second candle breaking the first red candle's low
        buy_signal = (
            self.first_red_candle_detected
            and low < self.first_red_candle_low
            and close > open_price
        )

        # Quantity adjustment based on profit
        if self.equity >= self.last_equity * 1.5:
            self.current_quantity = min(self.current_quantity + 1, self.max_quantity)
            self.last_equity = self.equity

        # Execute buy strategy only if enough equity is available
        if buy_signal:
            entry_price = close
            cost = entry_price * self.current_quantity
            if self.equity >= cost:
                stop_loss = entry_price - self.stop_loss_points
                target = entry_price + self.target_points
                self.buy(size=self.current_quantity)
                self.set_sl(entry_price=entry_price, stop_loss=stop_loss, target=target)
                print(f"Entered long position at {entry_price} with SL={stop_loss} and TP={target} on {self.data.index[-1]}")
            else:
                print(f"Skipping trade due to insufficient equity: needs {cost}, available {self.equity}")

    def set_sl(self, entry_price, stop_loss, target):
        """
        Helper function to implement stop loss and target profit.
        """
        # Implement stop loss and take profit
        if self.position().is_long:
            if self.data.Low[-1] <= stop_loss:
                self.position().close()
                print(f"Stopped out at {self.data.Close[-1]}")
            elif self.data.High[-1] >= target:
                self.position().close()
                print(f"Target reached at {self.data.Close[-1]}")

# Main code
data = load_data(data_path)
bt = Backtest(EURUSD, RedCandleBreakoutBuyStrategy, cash=24000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()