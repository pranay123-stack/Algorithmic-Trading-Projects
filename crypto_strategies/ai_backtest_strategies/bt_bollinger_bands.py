from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from backtesting.test import SMA, GOOG
import pandas as pd

class BollingerBandsStrategy(Strategy):
    n1 = 20  # period for the SMA
    n2 = 50  # period for the trend filter SMA
    n_std_dev = 2

    def init(self):
        self.sma = self.I(SMA, self.data.Close, self.n1)
        self.upper_band = self.I(lambda data: SMA(data, self.n1) + self.n_std_dev * pd.Series(data).rolling(self.n1).std(), self.data.Close)
        self.lower_band = self.I(lambda data: SMA(data, self.n1) - self.n_std_dev * pd.Series(data).rolling(self.n1).std(), self.data.Close)
        self.trend_sma = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        if crossover(self.data.Close, self.lower_band) and self.data.Close[-1] > self.trend_sma[-1]:
            self.buy()

        if crossover(self.upper_band, self.data.Close) and self.data.Close[-1] < self.trend_sma[-1]:
            self.sell()

        for trade in self.trades:
            if trade.is_long and crossover(self.sma, self.data.Close):
                self.position.close()
            elif trade.is_short and crossover(self.data.Close, self.sma):
                self.position.close()

# Example usage with Google stock data
bt = Backtest(GOOG, BollingerBandsStrategy, cash=10000, commission=.002)
stats = bt.run()
bt.plot()
