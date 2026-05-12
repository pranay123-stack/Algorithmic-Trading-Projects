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







def calculate_daily_indicators(daily_data, p=10, x=1, q=9, adxlen=14, dilen=14):
    """
    Calculate the Chande Kroll Stop and ADX indicators on a 10-minute timeframe.
    """

  
    daily_data['ATR'] = ta.atr(daily_data['High'], daily_data['Low'], daily_data['Close'], length=p)
    
    # Initial High and Low Stops
    daily_data['first_high_stop'] = daily_data['High'].rolling(window=p).max() - x * daily_data['ATR']
    daily_data['first_low_stop'] = daily_data['Low'].rolling(window=p).min() + x * daily_data['ATR']
    
    # Final Stop Levels
    daily_data['stop_short'] = daily_data['first_high_stop'].rolling(window=q).max()
    daily_data['stop_long'] = daily_data['first_low_stop'].rolling(window=q).min()
    
    # ADX Calculation
    daily_data['ADX'] = ta.adx(daily_data['High'], daily_data['Low'], daily_data['Close'], length=dilen)['ADX_14']
    daily_data['plus_DI'] = ta.adx(daily_data['High'], daily_data['Low'], daily_data['Close'], length=dilen)['DMP_14']
    daily_data['minus_DI'] = ta.adx(daily_data['High'], daily_data['Low'], daily_data['Close'], length=dilen)['DMN_14']
    
    return daily_data

def generate_signals(daily_data, ADX_sig=20):
    """
    Generate trading signals based on the Chande Kroll Stop strategy logic.
    """
    daily_data['signal'] = 0
    
    # Long Entry
    daily_data.loc[(daily_data['Close'] < daily_data['stop_long']) & (daily_data['ADX'] > ADX_sig), 'signal'] = 1
    
    # Short Entry
    daily_data.loc[(daily_data['Close'] > daily_data['stop_short']) & (daily_data['ADX'] > ADX_sig), 'signal'] = -1
    
    return daily_data

class ChandeKrollStopStrategy(Strategy):

    def init(self):
        try:
            print("Initializing Rainbow Oscillator Strategy")
            self.entry_price = None
               #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)
            print("Initialization complete")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

    def next(self):
        try:
            current_signal = self.data.signal[-1]
            current_price = self.data.Close[-1]
            print(f"Processing bar: {self.data.index[-1]} with signal {current_signal} at price {current_price}")

                
                    # Handle buy signal
            if current_signal == 1:
                print(f"Buy signal detected, executing long at close={current_price}")
                self.entry_price = current_price
                if self.position():
                    if self.position().is_short:
                        print("Closing short position before opening long")
                        self.position().close()
                    elif self.position().is_long:
                        print("Already in long position, no action needed")
                        return
                self.buy()  # Execute long position

            # Handle sell signal
            if current_signal == -1:
                print(f"Sell signal detected, executing short at close={current_price}")
                self.entry_price = current_price
                if self.position():
                    if self.position().is_long:
                        print("Closing long position before opening short")
                        self.position().close()
                    elif self.position().is_short:
                        print("Already in short position, no action needed")
                        return
                self.sell()  # Execute short position

                    
            
                    
                    
        except Exception as e:
            print(f"Error in next method: {e}")
            raise






data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, ChandeKrollStopStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()

