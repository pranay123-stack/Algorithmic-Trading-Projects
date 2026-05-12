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



def calculate_daily_indicators(daily_data, factor=5, atr_period=10):
    try:
        # Calculate Supertrend
        supertrend = ta.supertrend(daily_data['High'], daily_data['Low'], daily_data['Close'], length=10, multiplier=5)
        print("supertrend", supertrend)
        daily_data['Supertrend'] =   supertrend['SUPERT_10_5.0']
        daily_data['Direction'] =   supertrend['SUPERTd_10_5.0']
              # Drop rows where 'Supertrend' or 'Direction' are NaN
   
        return daily_data
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise




def generate_signals(daily_data):
    try:
        print("Generating signals based on Supertrend")

        # Initialize signal column
        daily_data['signal'] = 0
        daily_data['signal_direction'] = 0
      

        for i in range(3, len(daily_data)):
            # Get current and previous values
            current_supertrend = daily_data['Supertrend'].iloc[i]
            previous_supertrend_2 = daily_data['Supertrend'].iloc[i - 2]
            previous_supertrend_3 = daily_data['Supertrend'].iloc[i - 3]
            current_direction = daily_data['Direction'].iloc[i]

            if current_direction < 0:
                if current_supertrend > previous_supertrend_2:
                    daily_data.at[daily_data.index[i], 'signal'] = 1  # Buy signal (long)
                    daily_data.at[daily_data.index[i], 'signal_direction'] = 1
              
            elif current_direction > 0:
                if current_supertrend < previous_supertrend_3:
                    daily_data.at[daily_data.index[i], 'signal'] = -1  # Sell signal (short)
                    daily_data.at[daily_data.index[i], 'signal_direction'] = -1
                
        print("Signal generation complete")
        return daily_data
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise






class SupertrendStrategy(Strategy):
    def init(self):
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        pass

    def next(self):
        # Access the last row of the data
        current_signal = self.data.signal[-1]
        current_signaldirection = self.data.signal_direction[-1]

        if  current_signal ==1:
               self.buy()

        if  current_signal ==-1:
               self.sell()
        
        if current_signaldirection <0 :
            if self.position().is_short :
                self.position().close()

        
        if current_signaldirection >0 : 
            if self.position().is_long :
                self.position().close()

        





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, SupertrendStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()


  


  

       






      
                    
