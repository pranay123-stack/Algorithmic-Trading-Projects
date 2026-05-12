import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import pandas_ta as ta
from TradeMaster.lib import crossover
from datetime import time
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

from TradeMaster.test import EURUSD

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

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
        print(f"Error in load_and_prepare_data: {e}")
        raise

def calculate_daily_indicators(daily_data):
    try:
        # Calculate EMAs, HMA, and SMA using pandas_ta
        daily_data['fast_ema'] = ta.ema(daily_data['Close'], length=9)
        daily_data['slow_ema'] = ta.ema(daily_data['Close'], length=21)
        daily_data['ema_200'] = ta.ema(daily_data['Close'], length=200)
        daily_data['hma_300'] = ta.hma(daily_data['Close'], length=300)
        daily_data['ma_18'] = ta.sma(daily_data['Close'], length=18)

        # Initialize columns for Fibonacci levels
        daily_data['fib_618'] = np.nan
        daily_data['fib_65'] = np.nan

        return daily_data

    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise

class GoldenHarmonyBreakoutStrategy(Strategy):
   

      # Strategy parameters
    initial_risk_per_trade = 0.01
    price_delta = 0.004
    def init(self):
           #always initialize trademanagement and riskmanagement
        self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        self.total_trades = len(self.closed_trades)
        self.low = np.nan
        self.high = np.nan
        self.first_crossover = False

    def next(self):
        # Ensure there are at least two data points to avoid IndexError
        if len(self.data) < 2:
            return  # Skip this iteration if there's not enough data

        # Calculate current and previous fast and slow EMA values
        prev_fast_ema = self.data.fast_ema[-2]
        curr_fast_ema = self.data.fast_ema[-1]
        prev_slow_ema = self.data.slow_ema[-2]
        curr_slow_ema = self.data.slow_ema[-1]

        # Check for crossover and update low and high
        if prev_fast_ema < prev_slow_ema and curr_fast_ema > curr_slow_ema:
            if not self.first_crossover:
                self.low = self.data.Close[-1]
                self.high = self.data.Close[-1]
                self.first_crossover = True
            else:
                self.low = min(self.low, self.data.Close[-1])
                self.high = max(self.high, self.data.Close[-1])

        elif prev_fast_ema > prev_slow_ema and curr_fast_ema < curr_slow_ema:
            self.low = np.nan
            self.high = np.nan
            self.first_crossover = False

        # Calculate Fibonacci levels if low and high are set
        fib_618 = self.high - (self.high - self.low) * 0.618 if not np.isnan(self.low) and not np.isnan(self.high) else np.nan

        # Generate buy or sell signals
        current_close = self.data.Close[-1]
        previous_close = self.data.Close[-2]

        if not np.isnan(fib_618):
            # Check for Buy Signal
            if previous_close < fib_618 and current_close > fib_618:
                if self.position().is_short:
                    self.position().close()
                self.buy()

            # Check for Sell Signal
            elif previous_close > fib_618 and current_close < fib_618:
                if self.position().is_long:
                    self.position().close()
                self.sell()


    def add_buy_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df, direction="buy")
            stop_loss_perc = (entry - stop_loss) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            self.buy(size=qty, sl=stop_loss, tp=take_profit)
   

    
    def add_sell_trade(self):
        risk_per_trade = self.risk_management_strategy.get_risk_per_trade(self._broker._cash)
        entry = self.data.Close[-1]
        if risk_per_trade > 0:
            stop_loss, take_profit = self.trade_management_strategy.calculate_tp_sl(df=self.data.df, direction="sell")
            stop_loss_perc = (stop_loss - entry) / entry
            trade_size = risk_per_trade / stop_loss_perc
            qty = math.ceil(trade_size / self.data.Close[-1])
            # self.sell(size=qty, sl=stop_loss, tp=take_profit)
            self.add_sell_trade()

    
    def on_trade_close(self):
        num_of_trades_closed = len(self.closed_trades) - self.total_trades
        if num_of_trades_closed > 0:
            for trade in self.closed_trades[-num_of_trades_closed:]:
                if trade.pl < 0:
                    self.risk_management_strategy.update_after_loss()
                else:
                    self.risk_management_strategy.update_after_win()
        self.total_trades = len(self.closed_trades)

      
data = load_data(data_path)
data = calculate_daily_indicators(EURUSD)
print(data)
bt = Backtest(data, GoldenHarmonyBreakoutStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()


