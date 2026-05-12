import pandas as pd
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
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement



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


def calculate_daily_indicators(df, bb_length=20, bb_multiplier=2.0, macd_fast=12, macd_slow=26, macd_signal=9, rsi_length=14):
    try:
        print("Calculating Bollinger Bands, MACD, and RSI on data")

        # Bollinger Bands
        df['bb_basis'] = ta.sma(df['Close'], length=bb_length)
        df['bb_dev'] = bb_multiplier * ta.stdev(df['Close'], length=bb_length)
        df['bb_upper'] = df['bb_basis'] + df['bb_dev']
        df['bb_lower'] = df['bb_basis'] - df['bb_dev']

        # MACD
        macd = ta.macd(df['Close'], fast=macd_fast, slow=macd_slow, signal=macd_signal)
        print("macd: ", macd)
        df['macd_line']=macd['MACD_12_26_9']
        df['signal_line']=macd['MACDs_12_26_9']
        df['macd_hist'] =macd['MACDh_12_26_9']

        # RSI
        df['rsi'] = ta.rsi(df['Close'], length=rsi_length)

        # Drop NaN values
        df.dropna(inplace=True)
        print("Indicator calculation complete")
        return df
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise


# Function to generate buy/sell signals
def generate_signals(df, rsi_oversold=30, rsi_overbought=70):
    try:
        print("Generating buy/sell signals")

        # Buy signal: price below lower Bollinger band, MACD line > signal line, RSI < oversold level
        df['buy_signal'] = (df['Close'] < df['bb_lower']) & (df['macd_line'] > df['signal_line']) & (df['rsi'] < rsi_oversold)

        # Sell signal: price above upper Bollinger band, MACD line < signal line, RSI > overbought level
        df['sell_signal'] = (df['Close'] > df['bb_upper']) & (df['macd_line'] < df['signal_line']) & (df['rsi'] > rsi_overbought)

        # Create the 'signal' column
        # 1 for buy, -1 for sell, and 0 for no signal
        df['signal'] = 0  # Default to no signal
        df.loc[df['buy_signal'], 'signal'] = 1  # Buy signal
        df.loc[df['sell_signal'], 'signal'] = -1  # Sell signal

        print("Signal generation complete")
        return df
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


# Define the strategy class
class BollingerMacdRsiStrategy(Strategy):
    def init(self):
        self.entry_price = None
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        # Buy signal
        if self.data.signal[-1] == 1:
            if self.position():
                    if self.position().is_short:
                        self.position().close()
            self.buy()

        # Sell signal
        elif self.data.signal[-1] == -1:
            if self.position():
                    if self.position().is_long:
                        self.position().close()
            self.sell()





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data,BollingerMacdRsiStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()