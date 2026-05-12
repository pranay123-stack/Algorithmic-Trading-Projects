import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

import pandas_ta as ta
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
  
    # Parameters for indicators
    lengthBB = 20
    multBB = 2.0
    lengthKC = 20
    multKC = 1.5
    use_true_range = True 

    daily_data['ShortScalpMA'] = ta.ema(daily_data['Close'], 5)
    daily_data['LongScalpMA'] = ta.ema(daily_data['Close'], 15)
    daily_data['ShortSwingMA'] = ta.sma(daily_data['Close'], 20)
    daily_data['LongSwingMA'] = ta.sma(daily_data['Close'], 50)
    

    #Calculate MACD
    macd = ta.macd(daily_data['Close'])
    daily_data['MACDLine'] = macd['MACD_12_26_9']
    daily_data['SignalLine'] = macd['MACDs_12_26_9']
    daily_data['MACDHist'] = macd['MACDh_12_26_9']





    # Calculate Bollinger Bands
    basis = ta.sma(daily_data['Close'], lengthBB)
    dev = multBB * ta.stdev(daily_data['Close'], lengthBB)
    daily_data['BollingerUpper'] = basis + dev
    daily_data['BollingerLower'] = basis - dev







    # Calculate Keltner Channels
    tr = pd.concat([
        daily_data['High'] - daily_data['Low'],
        (daily_data['High'] - daily_data['Close'].shift(1)).abs(),
        (daily_data['Low'] - daily_data['Close'].shift(1)).abs()
    ], axis=1).max(axis=1)

    maKC = ta.sma(daily_data['Close'], lengthKC)
    rangeKC = tr if use_true_range else (daily_data['High'] - daily_data['Low'])
    rangeKCMA = rangeKC.rolling(window=lengthKC).mean()
    daily_data['KeltnerUpper'] = maKC + rangeKCMA * multKC
    daily_data['KeltnerLower'] = maKC - rangeKCMA * multKC



    # Calculate Momentum Value
    highest_high = daily_data['High'].rolling(lengthKC).max()
    lowest_low = daily_data['Low'].rolling(lengthKC).min()
    avgPrice = (highest_high + lowest_low) / 2
    daily_data['MomentumValue'] = ta.linreg(daily_data['Close'] - avgPrice, lengthKC, 0)



    #squeeze condition
    daily_data['SqueezeOn'] = (daily_data['BollingerLower'] > daily_data['KeltnerLower']) & (daily_data['BollingerUpper'] < daily_data['KeltnerUpper'])
    daily_data['SqueezeOff'] = (daily_data['BollingerLower'] < daily_data['KeltnerLower']) & (daily_data['BollingerUpper'] > daily_data['KeltnerUpper'])
 

 
    return daily_data


# def generate_signals(daily_data):

#     #// Buy and Sell Signals for Scalping
#     # scalpBuySignal = ta.crossover(shortScalpMA, longScalpMA)
#     # scalpSellSignal = ta.crossunder(shortScalpMA, longScalpMA)

#     #// Buy and Sell Signals for Swing Trading
#     # swingBuySignal = ta.crossover(shortSwingMA, longSwingMA)
#     # swingSellSignal = ta.crossunder(shortSwingMA, longSwingMA)



#     # // Strategy Logic
#     # if (scalpBuySignal and not noSqz and momentum val > 0)
#     #     strategy.entry("Scalp Buy", strategy.long)


#     # if (swingBuySignal and not noSqz and val > 0)
#     #     strategy.entry("Swing Buy", strategy.long)

#    pass



def generate_signals(daily_data):
    try:
        print("Generating signals based on strategy logic")

        # Initialize signal columns
        daily_data['scalpBuySignal'] = 0
        daily_data['scalpSellSignal'] = 0
        daily_data['swingBuySignal'] = 0
        daily_data['swingSellSignal'] = 0
        daily_data['signal'] = 0

        # Loop through the daily data to check for crossovers
        for i in range(1, len(daily_data)):
            # Scalp Buy Signal: ShortScalpMA crosses above LongScalpMA
            if daily_data['ShortScalpMA'].iloc[i-1] < daily_data['LongScalpMA'].iloc[i-1] and \
               daily_data['ShortScalpMA'].iloc[i] > daily_data['LongScalpMA'].iloc[i]:
                daily_data['scalpBuySignal'].iloc[i] = 1

            # Scalp Sell Signal: ShortScalpMA crosses below LongScalpMA
            if daily_data['ShortScalpMA'].iloc[i-1] > daily_data['LongScalpMA'].iloc[i-1] and \
               daily_data['ShortScalpMA'].iloc[i] < daily_data['LongScalpMA'].iloc[i]:
                daily_data['scalpSellSignal'].iloc[i] = 1

            # Swing Buy Signal: ShortSwingMA crosses above LongSwingMA
            if daily_data['ShortSwingMA'].iloc[i-1] < daily_data['LongSwingMA'].iloc[i-1] and \
               daily_data['ShortSwingMA'].iloc[i] > daily_data['LongSwingMA'].iloc[i]:
                daily_data['swingBuySignal'].iloc[i] = 1

            # Swing Sell Signal: ShortSwingMA crosses below LongSwingMA
            if daily_data['ShortSwingMA'].iloc[i-1] > daily_data['LongSwingMA'].iloc[i-1] and \
               daily_data['ShortSwingMA'].iloc[i] < daily_data['LongSwingMA'].iloc[i]:
                daily_data['swingSellSignal'].iloc[i] = 1

            # Determine the squeeze condition
            noSqz = not daily_data['SqueezeOn'].iloc[i] and not daily_data['SqueezeOff'].iloc[i]

            # Apply the strategy logic
            if daily_data['scalpBuySignal'].iloc[i] == 1 and not noSqz and daily_data['MomentumValue'].iloc[i] > 0:
                daily_data['signal'].iloc[i] = 1  # Scalp Buy

            elif daily_data['scalpSellSignal'].iloc[i] == 1 and not noSqz and daily_data['MomentumValue'].iloc[i] < 0:
                daily_data['signal'].iloc[i] = -1  # Scalp Sell

            elif daily_data['swingBuySignal'].iloc[i] == 1 and not noSqz and daily_data['MomentumValue'].iloc[i] > 0:
                daily_data['signal'].iloc[i] = 2  # Swing Buy

            elif daily_data['swingSellSignal'].iloc[i] == 1 and not noSqz and daily_data['MomentumValue'].iloc[i] < 0:
                daily_data['signal'].iloc[i] = -2  # Swing Sell

        print("Signal generation complete")
        return daily_data

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise


# Define the strategy class
class CombinedScalpingSwingStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
            self.last_position_type = None
               #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)
        except Exception as e:
            print(f"Error in init method: {e}")
            raise


    def next(self):
        try:
           
     

            if self.data.signal[-1] == 1:  # Scalp Buy
                print(f"Scalp Buy signal detected, close={self.data.Close[-1]}")
                self.buy()
                self.last_position_type = 'scalp'

            elif self.data.signal[-1] == -1:  # Scalp Sell
               
                if self.position() and self.last_position_type == 'scalp':
                    print("last position type", self.last_position_type)
                    self.position().close()
                    self.last_position_type = None  # Reset after closing

            elif self.data.signal[-1] == 2:  # Swing Buy
                print(f"Swing Buy signal detected, close={self.data.Close[-1]}")
                self.buy()
                self.last_position_type = 'swing'

            elif self.data.signal[-1] == -2:  # Swing Sell
               
                if self.position() and self.last_position_type == 'swing':
                    print("last position type", self.last_position_type)
                    self.position().close()
                    self.last_position_type = None  # Reset after closing

        except Exception as e:
            print(f"Error in next method: {e}")
            raise




data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, CombinedScalpingSwingStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()