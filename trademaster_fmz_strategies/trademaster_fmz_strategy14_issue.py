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



def calculate_daily_indicators(df, ma_length1=200, ma_length2=13, too_deep=0.27, too_thin=0.03):
    """
    Calculate the moving averages (SMA) and conditions 'too deep' and 'too thin'.
    
    :param df: DataFrame with price data
    :param ma_length1: Length of the first SMA (default: 200)
    :param ma_length2: Length of the second SMA (default: 13)
    :param too_deep: Percentage threshold for too deep condition (default: 0.27)
    :param too_thin: Percentage threshold for too thin condition (default: 0.03)
    :return: DataFrame with calculated indicators
    """
    try:
        print("Calculating moving averages and conditions")

        # Calculate moving averages
        df['ma1'] = ta.sma(df['Close'], length=ma_length1)
        df['ma2'] = ta.sma(df['Close'], length=ma_length2)

        # Calculate the conditions 'too deep' and 'too thin'
        df['too_deep2'] = (df['ma2'] / df['ma1'] - 1) < too_deep
        df['too_thin2'] = (df['ma2'] / df['ma1'] - 1) > too_thin

        df.dropna(inplace=True)  # Drop rows with missing data

        print(f"Indicators calculated: \n{df[['ma1', 'ma2', 'too_deep2', 'too_thin2']].head()}")
        return df
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise



def generate_signals(df):
    """
    Generate buy signals based on the provided strategy buy condition.
    
    :param df: DataFrame with price data and calculated indicators
    :return: DataFrame with the 'signal' column updated (1 for buy signal)
    """
    try:
        print("Generating buy signals based on the buy condition")

        # Initialize the signal column to 0 (no signal)
        df['signal'] = 0

        # Apply the buy condition:
        # (close > ma1) and (close < ma2) and no position and too_deep2 and too_thin2
        buy_condition = (df['Close'] > df['ma1']) & \
                        (df['Close'] < df['ma2']) & \
                        (df['too_deep2']) & \
                        (df['too_thin2'])

        # If the condition is met, set the signal to 1
        df.loc[buy_condition, 'signal'] = 1

        print(f"Buy signals generated:\n{df[df['signal'] == 1][['Close', 'ma1', 'ma2', 'too_deep2', 'too_thin2', 'signal']].head()}")
        return df
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


class PullbackStrategy(Strategy):
    sl = 0.07  # Stop loss percentage

    def init(self):
        try:
            print("Initializing strategy")
            self.buy_price = None  # Store the buy price
                #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)
            print("Strategy initialization complete")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        try:
            # Buy condition is already handled by signals generated earlier
            if self.data.signal[-1] == 1 and self.position().size == 0:  # Only buy if no position is held
                print(f"Buy signal detected, close={self.data.Close[-1]}")
                self.buy_price = self.data.Open[-1]  # Capture the buy price at the time of order
                print(f"Buy executed at {self.buy_price}")

                # Place the long entry order
                self.buy()
            
            # If a position is held (long), check for exit conditions
            if self.position().size > 0:
                stop_distance = (self.buy_price - self.data.Close[-1]) / self.data.Close[-1]  # Calculate stop distance
                print(f"Stop distance: {stop_distance}, SL threshold: {self.sl}")

                # Close Condition 1: Close > MA2 and Close < Low[1]
                close_condition1 = (self.data.Close[-1] > self.data.ma2[-1]) and \
                                   (self.data.Close[-1] < self.data.Low[-2])

                # Close Condition 2: Stop loss triggered
                close_condition2 = stop_distance > self.sl

                # Exit the position if either close condition is met
                if close_condition1 or close_condition2:
                    self.position().close()
                    print(f"Position closed at {self.data.Close[-1]} due to " +
                                 ("stop loss" if close_condition2 else "Close < Low[1]"))
                    self.buy_price = None  # Reset the buy price after closing the position

        except Exception as e:
            print(f"Error in next method: {e}")
            raise





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, PullbackStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()