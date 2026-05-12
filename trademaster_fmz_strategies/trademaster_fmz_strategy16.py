import pandas as pd
import pandas_ta as ta
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import numpy as np
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


# 2. Indicator Calculation
def calculate_daily_indicators(daily_data, fast_len=14, slow_len=100, atr_length=10):
    try:
        print("Resampling data to daily timeframe for indicator calculation")
      
        print("Calculating SMAs and ATR on daily data")

        # Calculate SMAs
        daily_data['fast_sma'] = ta.sma(daily_data['Close'], length=fast_len)
        daily_data['slow_sma'] = ta.sma(daily_data['Close'], length=slow_len)
        
        # True Range calculation
        tr = pd.concat([
            daily_data['High'] - daily_data['Low'],
            (daily_data['High'] - daily_data['Close'].shift(1)).abs(),
            (daily_data['Low'] - daily_data['Close'].shift(1)).abs()
        ], axis=1).max(axis=1)

        # Calculate ATR as the SMA of the True Range
        daily_data['atr'] = ta.sma(tr, length=atr_length)

        print("Indicator calculation complete")
        return daily_data
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise


# 3. Generate Signals
def generate_signals(daily_data, risk_per_trade=2.0):
    try:
        print("Generating trading signals")

        # Initialize signals and stop loss columns
        daily_data['signal'] = 0


        # Loop through the data to generate signals
        for i in range(1, len(daily_data)):
            # Check for a buy signal
            if (daily_data['Close'].iloc[i] > daily_data['slow_sma'].iloc[i]) and \
               (daily_data['Close'].iloc[i-1] <= daily_data['slow_sma'].iloc[i-1]):
                daily_data.at[daily_data.index[i], 'signal'] = 1

            # Check for a sell signal
            elif (daily_data['Close'].iloc[i] < daily_data['fast_sma'].iloc[i]) and \
                 (daily_data['Close'].iloc[i-1] >= daily_data['fast_sma'].iloc[i-1]):
                daily_data.at[daily_data.index[i], 'signal'] = -1

      
        print(f"Signal generation complete\n{daily_data.head(20)}")
        return daily_data
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


# Define the Trading Strategy
class TAMMY_V2(Strategy):
 
  

    def init(self):
        print("Initializing strategy")
        self.stop_loss = None
        self.risk_per_trade = 2.0
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
      

    def next(self):
        # Calculate stop loss dynamically
        atr_value = self.data.atr[-1]  # Use ATR from the latest available data
        
        # Check if we need to enter a long position
        if self.data.signal[-1] == 1:
            # Calculate and set the stop loss for the new long position
            self.stop_loss = self.data.Close[-1] - atr_value * (self.risk_per_trade / 100)
            self.buy()

        # Manage the existing position
        if self.position().is_long:
            # Check if the stop loss condition is met
            if self.data.Close[-1] <= self.stop_loss:
                self.position().close()
            
            # Alternatively, check for a sell signal to close the position
            elif self.data.signal[-1] == -1:
                self.position().close()





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data,TAMMY_V2, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()