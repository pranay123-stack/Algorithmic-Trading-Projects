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


def calculate_daily_indicators(daily_data):
    try:
        print("Calculating daily indicators")

     
        # Supertrend parameters
        length1, factor1 = 7, 3
        length2, factor2 = 14, 2
        length3, factor3 = 21, 1

        # Calculate Supertrend
        supertrend1 = ta.supertrend(daily_data['High'], daily_data['Low'], daily_data['Close'], length=length1, multiplier=factor1)
        supertrend2 = ta.supertrend(daily_data['High'], daily_data['Low'], daily_data['Close'], length=length2, multiplier=factor2)
        supertrend3 = ta.supertrend(daily_data['High'], daily_data['Low'], daily_data['Close'], length=length3, multiplier=factor3)

        daily_data['Supertrend1'] = supertrend1['SUPERT_7_3.0']
        daily_data['Supertrend2'] = supertrend2['SUPERT_14_2.0']
        daily_data['Supertrend3'] = supertrend3['SUPERT_21_1.0']

        print("Daily indicators calculated successfully.")
        return daily_data

    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise



def generate_signals(daily_data):
    try:
        print("Generating trading signals")

        # Initialize 'signal' column with zeros
        daily_data['signal'] = 0

        # Iterate over rows in the DataFrame, starting from the second row
        for i in range(1, len(daily_data)):
            close_price = daily_data['Close'].iloc[i]
            prev_close = daily_data['Close'].iloc[i - 1]
            supertrend1 = daily_data['Supertrend1'].iloc[i]
            prev_supertrend1 = daily_data['Supertrend1'].iloc[i - 1]
            supertrend2 = daily_data['Supertrend2'].iloc[i]
            prev_supertrend2 = daily_data['Supertrend2'].iloc[i - 1]
            supertrend3 = daily_data['Supertrend3'].iloc[i]
            prev_supertrend3 = daily_data['Supertrend3'].iloc[i - 1]

            # Buy Signal Condition: Close price crosses above Supertrend
            if (
                (prev_close <= prev_supertrend1 and close_price > supertrend1) or
                (prev_close <= prev_supertrend2 and close_price > supertrend2) or
                (prev_close <= prev_supertrend3 and close_price > supertrend3)
            ):
                daily_data.at[daily_data.index[i], 'signal'] = 1  # Buy signal

            # Sell Signal Condition: Close price crosses below Supertrend
            elif (
                (prev_close >= prev_supertrend1 and close_price < supertrend1) or
                (prev_close >= prev_supertrend2 and close_price < supertrend2) or
                (prev_close >= prev_supertrend3 and close_price < supertrend3)
            ):
                daily_data.at[daily_data.index[i], 'signal'] = -1  # Sell signal

        print("Signals generated successfully.")
        return daily_data

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise






class SupertrendStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
           
            self.entry_price = None
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
            current_signal = self.data.signal[-1]
            current_price = self.data.Close[-1]
            
       
            # Handle buy signal
            if current_signal == 1:
                print(f"Buy signal detected, executing buy at close={current_price}")
                self.entry_price = current_price
                self.buy()
               

            # Handle sell signal
            elif current_signal == -1:
                print(f"Sell signal detected, executing sell at close={current_price}")
                self.entry_price = current_price
                if self.position().is_long:
                      self.position().close()
                
              
                

        except Exception as e:
            print(f"Error in next method: {e}")
            raise


data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, SupertrendStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()