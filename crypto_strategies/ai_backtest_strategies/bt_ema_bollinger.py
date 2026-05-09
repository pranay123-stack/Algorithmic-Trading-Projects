from backtesting import Backtest, Strategy
from backtesting.lib import crossover

import pandas as pd
from backtesting.test import GOOG

class EMABollingerStrategy(Strategy):
    short_ema_period = 50
    long_ema_period = 200
    bb_period = 20
    bb_std_num = 2

    def init(self):
        # Initialize the indicators
        self.short_ema = self.I(pd.Series.ewm, self.data.Close, span=self.short_ema_period, min_periods=self.short_ema_period)
        self.long_ema = self.I(pd.Series.ewm, self.data.Close, span=self.long_ema_period, min_periods=self.long_ema_period)

        self.bb_mid = self.I(pd.Series.rolling, self.data.Close, self.bb_period).mean()
        self.bb_upper = self.bb_mid + self.data.Close.rolling(self.bb_period).std() * self.bb_std_num
        self.bb_lower = self.bb_mid - self.data.Close.rolling(self.bb_period).std() * self.bb_std_num

    def next(self):
        # Check for long entry
        if crossover(self.short_ema, self.long_ema) and self.data.Close[-1] < self.bb_lower[-1]:
            self.buy()

        # Check for short entry
        elif crossover(self.long_ema, self.short_ema) and self.data.Close[-1] > self.bb_upper[-1]:
            self.sell()

        # Check for long exit
        for trade in self.trades:
            if trade.is_long:
                if self.data.Close[-1] > self.bb_upper[-1]:
                    trade.close()
                elif crossover(self.long_ema, self.short_ema):
                    trade.close()
            elif trade.is_short:
                if self.data.Close[-1] < self.bb_lower[-1]:
                    trade.close()
                elif crossover(self.short_ema, self.long_ema):
                    trade.close()

# Load historical data
data = GOOG  # Replace with your data source

# Instantiate the backtest with the strategy
bt = Backtest(data, EMABollingerStrategy,
              cash=10000, commission=.002,
              exclusive_orders=True)

# Run the backtest
output = bt.run()

# Print the output
print(output)

# Output plots if needed
# bt.plot()
