import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import pandas_ta as ta
from TradeMaster.test import EURUSD

# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1d/btc_day_data_2023.csv'


def load_data(csv_file_path):
    try:
        
        data = pd.read_csv(csv_file_path)
        # data['timestamp'] = pd.to_datetime(data['timestamp'])
        # data.set_index('timestamp', inplace=True)
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




def calculate_daily_indicators(df):
    try:
        # KDJ calculation (using highest, lowest, and simple moving averages)
        kdj_length = 9
        kdj_signal = 3

        kdj_highest = df['High'].rolling(window=kdj_length).max()
        kdj_lowest = df['Low'].rolling(window=kdj_length).min()
        kdj_rsv = 100 * (df['Close'] - kdj_lowest) / (kdj_highest - kdj_lowest)
        df['K'] = kdj_rsv.rolling(window=kdj_signal).mean()
        df['D'] = df['K'].rolling(window=kdj_signal).mean()
        df['J'] = 3 * df['K'] - 2 * df['D']

        # Moving Average calculation
        ma_length = 20
        df['MA'] = df['Close'].rolling(window=ma_length).mean()

        # Drop NaN rows created by rolling windows
        df.dropna(inplace=True)

        return df

    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise



def generate_signals(df):
    try:
        print("Generating signals")

        # Initialize signal column
        df['signal'] = 0

        # Define KDJ overbought and oversold levels
        kdj_overbought = 80
        kdj_oversold = 20

        # Moving Average crossovers
        df['ma_cross_up'] = (df['Close'] > df['MA']) & (df['Close'].shift(1) <= df['MA'].shift(1))
        df['ma_cross_down'] = (df['Close'] < df['MA']) & (df['Close'].shift(1) >= df['MA'].shift(1))

        # Generate Buy (Long) and Sell (Short) signals
        df.loc[(df['J'] <= kdj_oversold) & df['ma_cross_up'], 'signal'] = 1  # Buy
        df.loc[(df['J'] >= kdj_overbought) & df['ma_cross_down'], 'signal'] = -1  # Sell

        return df

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise





class KDJMAStrategy(Strategy):
    def init(self):
        self.entry_price = None
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        if self.data.signal[-1] == 1:
            if self.position():
                    if self.position().is_short:
                        self.position().close()
            self.buy()
           
                        
          
        elif self.data.signal[-1] == -1 :
            if self.position():
                    if self.position().is_long:
                        self.position().close()
                        
            self.sell()
            
  




data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, KDJMAStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()