import pandas as pd
import pandas as pd
import numpy as np
import pandas_ta as ta
import pandas as pd
import numpy as np
import pandas_ta as ta
import logging

import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

from TradeMaster.test import EURUSD



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
    # RSI Calculation
    rsiLength = 14
    src = daily_data['Close']
    
    # Calculate change
    change = src.diff()

    # Calculate up and down components
    up = ta.rma(change.clip(lower=0), length=rsiLength)
    down = ta.rma(-change.clip(upper=0), length=rsiLength)

    # Compute RSI based on the Pine Script logic
    daily_data['RSI'] = 100 - 100 / (1 + up / down)
    daily_data['RSI'] = daily_data['RSI'].fillna(0)

    # Bollinger Bands Calculation
    bbLength = 20
    bbMultiplier = 1.0
    
    # Calculate the basis (SMA) and deviation (standard deviation)
    basis = ta.sma(src, length=bbLength)
    deviation = bbMultiplier * ta.stdev(src, length=bbLength)
    
    # Calculate upper and lower bands
    daily_data['UpperBand'] = basis + deviation
    daily_data['LowerBand'] = basis - deviation

    return daily_data


def generate_signals(daily_data, dca_enabled=False, dca_interval=1):
    # Strategy Parameters
    RSILowerLevel = 42
    RSIUpperLevel = 70

    # Initialize the signal column with 0 (no action)
    daily_data['signal'] = 0

    # Loop through each row in the DataFrame
    for i in range(1, len(daily_data)):
        # Define the BBBuyTrigger and BBSellTrigger based on Bollinger Bands
        BBBuyTrigger = daily_data['Close'].iloc[i] < daily_data['LowerBand'].iloc[i]
        BBSellTrigger = daily_data['Close'].iloc[i] > daily_data['UpperBand'].iloc[i]

        # Define the RSI Guards
        rsiBuyGuard = daily_data['RSI'].iloc[i] > RSILowerLevel
        rsiSellGuard = daily_data['RSI'].iloc[i] > RSIUpperLevel

        # Combine conditions to form buy and sell conditions
        buy_condition = BBBuyTrigger and rsiBuyGuard
        sell_condition = BBSellTrigger and rsiSellGuard

        # Determine the current hour (assuming the index is a datetime index)
        current_hour = daily_data.index[i].hour

        # Apply the DCA Logic if enabled
        if dca_enabled and (current_hour % dca_interval == 0):
            if buy_condition:
                daily_data.at[daily_data.index[i], 'signal'] = 1  # DCA Buy Signal
                print("DCA - Buy Signal!")  # Replace with logging or another action
        else:
            if buy_condition:
                daily_data.at[daily_data.index[i], 'signal'] = 1  # Regular Buy Signal
                print("Buy Signal!")  # Replace with logging or another action

        # Handle Sell Condition
        if sell_condition:
            daily_data.at[daily_data.index[i], 'signal'] = -1  # Sell Signal
            print("Sell Signal!")  # Replace with logging or another action

    return daily_data






class DCA_Trading_Strategy(Strategy):
    stoploss_input = 0.06604
    takeprofit_input = 0.02328
 
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
            if current_signal==1:
                print(f"Buy signal detected, executing long at close={current_price}")
                self.entry_price = current_price
                self.buy()  # DCA or regular long position based on dca_enabled

            if current_signal==-1:
                    # Handle stop loss and take profit
                if self.position().is_long:
                    stop_loss_level = self.entry_price * (1 - self.stoploss_input)
                    take_profit_level = self.entry_price * (1 + self.takeprofit_input)
                    if current_price < stop_loss_level or current_price > take_profit_level:
                        print(f"Price reached stop loss or take profit level. Closing position.")
                        self.position().close()
            

            print("Next method processing complete")

        except Exception as e:
            print(f"Error in next method: {e}")
            raise





# Function to load data from CSV
def load_data(csv_file_path):

        data = pd.read_csv(csv_file_path)

        # Ensure that the 'timestamp' column is in datetime format
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            data.set_index('timestamp', inplace=True)  # Set as DatetimeIndex
        else:
            raise ValueError("CSV data must contain a 'timestamp' column.")

        # Rename columns to match backtesting library expectations
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)

        # Handle missing values by forward filling
        data.fillna(method='ffill', inplace=True)

        return data






data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, DCA_Trading_Strategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()