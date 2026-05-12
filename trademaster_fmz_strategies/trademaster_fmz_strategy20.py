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





def calculate_daily_indicators(daily_data, fast_length=9, slow_length=21, order_block_threshold=0.1, fvg_threshold=0.5, atr_length=14):
    print("Calculating daily indicators")

   
    # Calculate moving averages using pandas_ta
    daily_data['Fast_MA'] = ta.sma(daily_data['Close'], length=fast_length)
    daily_data['Slow_MA'] = ta.sma(daily_data['Close'], length=slow_length)
    
    # Determine trend
    daily_data['Bullish_Trend'] = daily_data['Fast_MA'] > daily_data['Slow_MA']
    daily_data['Bearish_Trend'] = daily_data['Fast_MA'] < daily_data['Slow_MA']

    # Break of Structure (BOS)
    daily_data['Highest_High'] = daily_data['High'].rolling(window=10).max()
    daily_data['Lowest_Low'] = daily_data['Low'].rolling(window=10).min()
    daily_data['Bullish_BOS'] = (daily_data['Bullish_Trend']) & (daily_data['Close'] > daily_data['Highest_High'])
    daily_data['Bearish_BOS'] = (daily_data['Bearish_Trend']) & (daily_data['Close'] < daily_data['Lowest_Low'])

    # Order Block Identification
    daily_data['Order_Block_High'] = np.where(daily_data['Bullish_BOS'], daily_data['Highest_High'], np.nan)
    daily_data['Order_Block_Low'] = np.where(daily_data['Bullish_BOS'], daily_data['Close'] * (1 - order_block_threshold / 100), np.nan)
    daily_data['Order_Block_High'] = np.where(daily_data['Bearish_BOS'], daily_data['Close'] * (1 + order_block_threshold / 100), daily_data['Order_Block_High'])
    daily_data['Order_Block_Low'] = np.where(daily_data['Bearish_BOS'], daily_data['Lowest_Low'], daily_data['Order_Block_Low'])

    # Fair Value Gap (FVG)
    daily_data['FVG_High'] = np.where(daily_data['Bullish_BOS'], daily_data['High'], np.nan)
    daily_data['FVG_Low1'] = np.where(daily_data['Bullish_BOS'], daily_data['High'] * (1 - fvg_threshold / 100), np.nan)
    daily_data['FVG_Low2'] = np.where(daily_data['Bullish_BOS'], daily_data['High'] * (1 - fvg_threshold / 100 * 2), np.nan)
    daily_data['FVG_Low1'] = np.where(daily_data['Bearish_BOS'], daily_data['Low'] * (1 + fvg_threshold / 100), daily_data['FVG_Low1'])
    daily_data['FVG_Low2'] = np.where(daily_data['Bearish_BOS'], daily_data['Low'] * (1 + fvg_threshold / 100 * 2), daily_data['FVG_Low2'])

    # Calculate ATR using pandas_ta
    daily_data['ATR'] = ta.atr(daily_data['High'], daily_data['Low'], daily_data['Close'], length=atr_length)

    print("Daily indicators calculated successfully")
    return daily_data


def generate_signals(daily_data):
    print("Generating signals based on strategy logic")

    # Initialize 'Signal' column with NaNs
    daily_data['signal'] = 0

    # Loop through each row of the DataFrame
    for i in range(1, len(daily_data)):
        # Check long entry condition
        if (daily_data['Fast_MA'].iloc[i] > daily_data['Slow_MA'].iloc[i] and
            daily_data['Fast_MA'].iloc[i-1] <= daily_data['Slow_MA'].iloc[i-1]):
            daily_data['signal'].iloc[i] = 1
        
        # Check short entry condition
        elif (daily_data['Fast_MA'].iloc[i] < daily_data['Slow_MA'].iloc[i] and
              daily_data['Fast_MA'].iloc[i-1] >= daily_data['Slow_MA'].iloc[i-1]):
            daily_data['signal'].iloc[i] = -1

    print("Signals generated successfully")
    return daily_data







# Define the strategy class
class TrendStructureBreakStrategy(Strategy):
    def init(self):
     
        self.atr_multiplier = 5.5
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        if self.data.signal[-1] == 1:
            if self.position().is_short:
                self.position().close()
            self.buy()

            if self.position().is_long:
                self.position().close()
            self.sell()
        





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, TrendStructureBreakStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()