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




def calculate_daily_indicators(daily_data):
    try:
        # Parameters
        maLength = 50
        lengthATR = 14
        multiplier = 1.5
        length = 20

        # Calculate Simple Moving Average (SMA)
        daily_data['ma'] = daily_data['Close'].rolling(window=maLength).mean()

        # Calculate ATR using pandas_ta
        daily_data['atr'] = ta.atr(daily_data['High'], daily_data['Low'], daily_data['Close'], length=lengthATR)

        # Calculate Alpha Trend levels
        daily_data['upperLevel'] = daily_data['Close'] + (multiplier * daily_data['atr'])
        daily_data['lowerLevel'] = daily_data['Close'] - (multiplier * daily_data['atr'])

        # Initialize Alpha Trend with NaN
        daily_data['alphaTrend'] = np.nan

 
        # Calculate Alpha Trend
        for i in range(1, len(daily_data)):
            current_close = daily_data['Close'].iloc[i]
            current_upper = daily_data['upperLevel'].iloc[i]
            current_lower = daily_data['lowerLevel'].iloc[i]
            prev_alpha_trend = daily_data['alphaTrend'].iloc[i - 1]

            if pd.isna(prev_alpha_trend):
                daily_data.at[daily_data.index[i], 'alphaTrend'] = current_close
            elif current_close > daily_data['lowerLevel'].iloc[i - 1]:
                daily_data.at[daily_data.index[i], 'alphaTrend'] = max(prev_alpha_trend, current_lower)
            elif current_close < daily_data['upperLevel'].iloc[i - 1]:
                daily_data.at[daily_data.index[i], 'alphaTrend'] = min(prev_alpha_trend, current_upper)
            else:
                daily_data.at[daily_data.index[i], 'alphaTrend'] = prev_alpha_trend

        # Calculate highest and lowest close over the specified window
        daily_data['highestClose'] = daily_data['Close'].rolling(window=length).max()
        daily_data['lowestClose'] = daily_data['Close'].rolling(window=length).min()

        return daily_data

    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise


def generate_signals(daily_data):
    try:
        # Initialize the 'signal' column with zeros
        daily_data['signal'] = 0

        # Loop through each row of the DataFrame
        for i in range(1, len(daily_data)):
            # Calculate the buy signal
            if (daily_data['Close'].iloc[i] > daily_data['highestClose'].iloc[i-1] and
                daily_data['Close'].iloc[i-1] <= daily_data['highestClose'].iloc[i-1] and
                daily_data['Close'].iloc[i] > daily_data['ma'].iloc[i] and
                daily_data['Close'].iloc[i] > daily_data['alphaTrend'].iloc[i]):
                daily_data['signal'].iloc[i] = 1
            
            # Calculate the sell signal
            elif (daily_data['Close'].iloc[i] < daily_data['lowestClose'].iloc[i-1] and
                  daily_data['Close'].iloc[i-1] >= daily_data['lowestClose'].iloc[i-1] and
                  daily_data['Close'].iloc[i] < daily_data['ma'].iloc[i] and
                  daily_data['Close'].iloc[i] < daily_data['alphaTrend'].iloc[i]):
                daily_data['signal'].iloc[i] = -1

        return daily_data
    
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


class TRMUSStrategy(Strategy):
    stop_loss_perc = 0.02
    take_profit_perc = 0.04

    def init(self):
        print("Initializing strategy")
            #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        try:
            if self.data.signal[-1] == 1:

                if self.position():
                        if self.position().is_short:
                            print("Closing short position before opening long")
                            self.position().close()
                        elif self.position().is_long:
                            print("Already in long position, no action needed")
                            return
                self.buy(
                    stop=self.data['Close'][-1] * (1 - self.stop_loss_perc),
                    limit=self.data['Close'][-1] * (1 + self.take_profit_perc)
                )
            elif self.data.signal[-1] == -1:
                if self.position():
                    if self.position().is_long:
                        print("Closing long position before opening short")
                        self.position().close()
                    elif self.position().is_short:
                        print("Already in short position, no action needed")
                        return
                self.sell(
                    stop=self.data['Close'][-1] * (1 + self.stop_loss_perc),
                    limit=self.data['Close'][-1] * (1 - self.take_profit_perc)
                )
        except Exception as e:
            print(f"Error in TRMUSStrategy next: {e}")
            raise








data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data,TRMUSStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()