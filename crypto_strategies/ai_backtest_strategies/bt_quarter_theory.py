from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd

class QuarterTheoryStrategy(Strategy):
    def init(self):
        # Here you can precalculate any indicators or any heavy computations
        # Since the theory is based on price levels divisible by 0.25,
        # we do not need to precalculate any technical indicators.
        pass

    def next(self):
        price = self.data.Close[-1]  # Current closing price
        quarter_levels = [round(price - (price % 0.25)), round(price - (price % 0.25) + 0.25, 2)]

        # Long Entry
        if price > quarter_levels[1] and not self.position.is_long:
            self.buy(sl=quarter_levels[0], tp=quarter_levels[1] + 0.25)

        # Short Entry
        elif price < quarter_levels[0] and not self.position.is_short:
            self.sell(sl=quarter_levels[1], tp=quarter_levels[0] - 0.25)

        # Here you might add additional logic to handle trailing stop loss, etc.

# Assume `data` is a pandas DataFrame with OHLC 'Open', 'High', 'Low', 'Close'
# data columns, indexed by datetime. It can be obtained, for example, by
# reading a CSV file with `pd.read_csv()` or by fetching from a database.

# Here we might load historical data, like so:
# data = pd.read_csv('historical_data.csv', index_col=0, parse_dates=True)

# Generate some example data
date_range = pd.date_range('2010-01-01', '2020-01-01', freq='D')
price_range = pd.Series(range(len(date_range))) * 0.25
data = pd.DataFrame({
    'Open': price_range,
    'High': price_range + 0.1,
    'Low': price_range - 0.1,
    'Close': price_range
}, index=date_range)

bt = Backtest(data, QuarterTheoryStrategy, cash=100000, commission=.002,
              exclusive_orders=True)

output = bt.run()
print(output)

# Uncomment to plot the trades over the price plot
# bt.plot()
