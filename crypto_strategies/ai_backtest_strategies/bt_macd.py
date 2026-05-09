from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import GOOG

import pandas as pd


class MACDStrategy(Strategy):
    short_ema_period = 12
    long_ema_period = 26
    signal_ema_period = 9
    buy_confirmation_periods = 2
    sell_confirmation_periods = 2
    additional_ma_filter_period = 50
    stop_loss_percent = 5
    take_profit_percent = 10

    def init(self):
        closing_prices = self.data.Close

        self.macd = self.I(self.MACD, closing_prices,
                           self.short_ema_period,
                           self.long_ema_period)

        self.signal = self.I(self.EMA, self.macd, self.signal_ema_period)

        self.histogram = self.macd - self.signal

        self.ma_filter = self.I(self.EMA, closing_prices,
                                self.additional_ma_filter_period)

    def next(self):
        if crossover(self.macd, self.signal) and all(self.histogram[-self.buy_confirmation_periods:] > 0):
            if self.data.Close[-1] > self.ma_filter[-1]:
                self.buy()
        elif crossover(self.signal, self.macd) and all(self.histogram[-self.sell_confirmation_periods:] < 0):
            self.sell()

    @staticmethod
    def MACD(prices, n_fast, n_slow):
        ema_fast = pd.Series(prices).ewm(span=n_fast, adjust=False).mean()
        ema_slow = pd.Series(prices).ewm(span=n_slow, adjust=False).mean()
        return ema_fast - ema_slow

    @staticmethod
    def EMA(prices, n):
        return pd.Series(prices).ewm(span=n, adjust=False).mean()

    def stop(self):
        # Implement Stop Loss and Take Profit
        for trade in self.trades:
            if trade.is_long:
                if self.data.Close[-1] < trade.entry_price * (1 - self.stop_loss_percent / 100):
                    self.position.close()
                elif self.data.Close[-1] > trade.entry_price * (1 + self.take_profit_percent / 100):
                    self.position.close()
            elif trade.is_short:
                if self.data.Close[-1] > trade.entry_price * (1 + self.stop_loss_percent / 100):
                    self.position.close()
                elif self.data.Close[-1] < trade.entry_price * (1 - self.take_profit_percent / 100):
                    self.position.close()


# Note: GOOG is a sample dataset included with backtesting.py.
# You need to replace it with a DataFrame on the asset you want to test.
# The DataFrame should have the following columns: ['Open', 'High', 'Low', 'Close', 'Volume']
# Example: data = pd.read_csv('path_to_your_data.csv')

bt = Backtest(GOOG, MACDStrategy, commission=.002,
              exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot()
