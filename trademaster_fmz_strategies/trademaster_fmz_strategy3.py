import pandas as pd
import numpy as np
import os
import sys
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import pandas_ta as ta
from TradeMaster.test import EURUSD
data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'

def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return data
    except Exception as e:
        print(f"Error in load_and_prepare_data: {e}")
        raise

def calculate_daily_indicators(daily_data):
    try:
        print("Calculating EMA, MACD, RSI, and Volume indicators on daily data")
        daily_data['ema_short'] = ta.ema(daily_data['Close'], length=9)
        daily_data['ema_long'] = ta.ema(daily_data['Close'], length=20)
        macd = ta.macd(daily_data['Close'], fast=12, slow=26, signal=9)
        daily_data['macd_line'] = macd['MACD_12_26_9']
        daily_data['signal_line'] = macd['MACDs_12_26_9']
        daily_data['rsi'] = ta.rsi(daily_data['Close'], length=14)
        daily_data['volume_ma'] = ta.sma(daily_data['Volume'], length=20)
        daily_data.dropna(inplace=True)
        return daily_data
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise

class BONKTradingStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
               #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)
            self.entry_price = None
            print("Strategy initialization complete")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        try:
            # Skip if there’s not enough data to calculate the signals
            if len(self.data) < 2:
                return
            
            # Access the current and previous indicators for generating signals
            prev_ema_short = self.data.ema_short[-2]
            prev_ema_long = self.data.ema_long[-2]
            current_ema_short = self.data.ema_short[-1]
            current_ema_long = self.data.ema_long[-1]
            current_macd_line = self.data.macd_line[-1]
            current_signal_line = self.data.signal_line[-1]
            current_rsi = self.data.rsi[-1]
            current_volume = self.data.Volume[-1]
            volume_ma = self.data.volume_ma[-1]

            # Define buy and sell conditions
            buy_condition = (
                prev_ema_short <= prev_ema_long and
                current_ema_short > current_ema_long and
                current_macd_line > current_signal_line and
                current_rsi < 70 and
                current_volume > volume_ma
            )
            
            sell_condition = (
                prev_ema_long <= prev_ema_short and
                current_ema_long > current_ema_short and
                current_macd_line < current_signal_line and
                current_rsi > 30 and
                current_volume > volume_ma
            )

            # Execute buy logic
            if buy_condition:
                print(f"Buy signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                long_stop_loss = self.entry_price * 0.95
                long_take_profit = self.entry_price * 1.05

                if self.position():
                    if self.position().is_short:
                        print("Closing short position before opening long")
                        self.position().close()
                    elif self.position().is_long:
                        print("Already in long position, no action needed")
                        return
                self.buy(stop=long_stop_loss, limit=long_take_profit)

            # Execute sell logic
            elif sell_condition:
                print(f"Sell signal detected, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                short_stop_loss = self.entry_price * 1.05
                short_take_profit = self.entry_price * 0.95

                if self.position():
                    if self.position().is_long:
                        print("Closing long position before opening short")
                        self.position().close()
                    elif self.position().is_short:
                        print("Already in short position, no action needed")
                        return
                self.sell(stop=short_stop_loss, limit=short_take_profit)

        except Exception as e:
            print(f"Error in next method: {e}")
            raise

# Load data and calculate indicators
data = load_data(data_path)
data = calculate_daily_indicators(EURUSD)

# Run the backtest
bt = Backtest(data, BONKTradingStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
