from backtesting import Backtest, Strategy
from backtesting.lib import crossover

import talib

import pandas as pd


class ADXStrategy(Strategy):
    adx_period = 14
    di_period = 14
    adx_threshold = 25
    exit_threshold = 20

    def init(self):
        high = self.data.High
        low = self.data.Low
        close = self.data.Close

        self.adx = self.I(talib.ADX, high, low, close, self.adx_period)
        self.plus_di = self.I(talib.PLUS_DI, high, low, close, self.di_period)
        self.minus_di = self.I(talib.MINUS_DI, high, low, close, self.di_period)

    def next(self):
        if crossover(self.plus_di, self.minus_di) and self.adx[-1] > self.adx_threshold:
            self.buy()
        elif crossover(self.minus_di, self.plus_di) and self.adx[-1] > self.adx_threshold:
            self.sell()

        for trade in self.trades:
            if trade.is_long and (
                crossover(self.minus_di, self.plus_di)
                or self.adx[-1] < self.exit_threshold
            ):
                trade.close()
            elif trade.is_short and (
                crossover(self.plus_di, self.minus_di)
                or self.adx[-1] < self.exit_threshold
            ):
                trade.close()


# Note: 'data' must be a DataFrame with columns: 'Open', 'High', 'Low', 'Close', 'Volume'
data = pd.DataFrame()  # replace with your actual data

bt = Backtest(data, ADXStrategy, cash=10000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot()
