# https://www.fmz.com/m/copy-strategy/468333

import pandas as pd
import numpy as np
import os
import sys
from math import sqrt
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
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

# Hull Moving Average calculation
def calculate_hma(data, length):
    try:
        wma1 = data['Close'].rolling(window=length).mean()
        wma2 = data['Close'].rolling(window=length // 2).mean()
        hma_value = (2 * wma2 - wma1).rolling(window=int(sqrt(length))).mean()
        data['HMA'] = hma_value
        data.dropna(inplace=True)
        print("Hull Moving Average calculation complete")
        return data
    except Exception as e:
        print(f"Error in calculate_hma: {e}")
        raise

# Strategy class
class SHIESTDStrategy(Strategy):
    long_sl_amount = 1.25
    long_tp_amount = 37.5
    short_sl_amount = 1.25
    short_tp_amount = 37.5
    contracts = 2

    def init(self):
        self.long_entry_price = None
        self.short_entry_price = None
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        print("Strategy initialization complete")

    def next(self):
        close = self.data.Close[-1]
        hma_value = self.data.HMA[-1]

        # Long entry condition
        if crossover(self.data.Close, self.data.HMA) and self.long_entry_price is None:
            self.long_entry_price = close
            self.buy(size=self.contracts)
            print(f"Entered long position at {self.long_entry_price}")

        # Short entry condition
        elif crossover(self.data.HMA, self.data.Close) and self.short_entry_price is None:
            self.short_entry_price = close
            self.sell(size=self.contracts)
            print(f"Entered short position at {self.short_entry_price}")

        # Long exit conditions based on SL and TP
        if self.position().is_long:
            long_sl_price = self.long_entry_price - self.long_sl_amount
            long_tp_price = self.long_entry_price + self.long_tp_amount

            if close <= long_sl_price:
                self.position().close()
                print(f"Closing long position at {close} due to stop loss hit (SL={long_sl_price})")
                self.long_entry_price = None

            elif close >= long_tp_price:
                self.position().close()
                print(f"Closing long position at {close} due to take profit hit (TP={long_tp_price})")
                self.long_entry_price = None

            elif self.data.High[-1] >= hma_value:
                self.position().close()
                print(f"Closing long position at {close} as high >= HMA")
                self.long_entry_price = None

        # Short exit conditions based on SL and TP
        elif self.position().is_short:
            short_sl_price = self.short_entry_price + self.short_sl_amount
            short_tp_price = self.short_entry_price - self.short_tp_amount

            if close >= short_sl_price:
                self.position().close()
                print(f"Closing short position at {close} due to stop loss hit (SL={short_sl_price})")
                self.short_entry_price = None

            elif close <= short_tp_price:
                self.position().close()
                print(f"Closing short position at {close} due to take profit hit (TP={short_tp_price})")
                self.short_entry_price = None

            elif self.data.Low[-1] <= hma_value:
                self.position().close()
                print(f"Closing short position at {close} as low <= HMA")
                self.short_entry_price = None

# Main code
data = load_data(data_path)
data = calculate_hma(EURUSD, length=104)
bt = Backtest(data, SHIESTDStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()