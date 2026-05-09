from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from talib import RSI, SMA
import numpy as np

class RSIVWAPStrategy(Strategy):
    rsi_period = 14
    oversold_threshold = 30
    overbought_threshold = 70
    
    def init(self):
        # Calculate the RSI
        self.rsi = self.I(RSI, self.data.Close, self.rsi_period)
        
        # Calculate VWAP (manually since it's not natively supported by backtesting.py)
        self.vwap = self.I(self.compute_vwap)

    def compute_vwap(self, opens, highs, lows, closes, volumes):
        typical_price = (highs + lows + closes) / 3
        cumulative_vwap = (typical_price * volumes).cumsum() / volumes.cumsum()
        return cumulative_vwap

    def next(self):
        # If RSI crosses above oversold and price is below VWAP, and we're not already in a long position
        if (self.rsi[-1] > self.oversold_threshold) and (self.data.Close[-1] < self.vwap[-1]) and (not self.position.is_long):
            # Buy when price crosses above VWAP
            if self.data.Close[-2] < self.vwap[-2] and self.data.Close[-1] > self.vwap[-1]:
                self.buy()
        
        # If RSI crosses below overbought and price is above VWAP, and we're not already in a short position
        if (self.rsi[-1] < self.overbought_threshold) and (self.data.Close[-1] > self.vwap[-1]) and (not self.position.is_short):
            # Sell/short when price crosses below VWAP
            if self.data.Close[-2] > self.vwap[-2] and self.data.Close[-1] < self.vwap[-1]:
                self.sell()
        
        # Close long position when RSI crosses overbought or price crosses below VWAP
        if self.position.is_long:
            if (self.rsi[-1] > self.overbought_threshold) or (self.data.Close[-1] < self.vwap[-1]):
                self.position.close()
        
        # Close short position when RSI crosses oversold or price crosses above VWAP
        if self.position.is_short:
            if (self.rsi[-1] < self.oversold_threshold) or (self.data.Close[-1] > self.vwap[-1]):
                self.position.close()

# Note: Users must provide their own 'data' DataFrame with columns: Open, High, Low, Close, Volume
# This data should be intraday data with the desired timeframe (5 minutes to 1 hour).
# Example: data = pd.read_csv('intraday_data.csv', index_col=0, parse_dates=True)

# bt = Backtest(data, RSIVWAPStrategy, cash=10000, commission=.002)
# stats = bt.run()
# bt.plot()
