
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import pandas_ta as ta
import pandas as pd
import numpy as np
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



def calculate_daily_indicators(df):
    # ATR calculation
    df['tr'] = np.maximum(df['High'] - df['Low'], 
                          np.maximum(abs(df['High'] - df['Close'].shift()), 
                                     abs(df['Low'] - df['Close'].shift())))
        # ATR Calculation using pandas_ta
    atrLength = 14
    df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=atrLength)


    # Bollinger Bands calculation
    df['basis'] = df['Close'].rolling(window=20).mean()
    df['deviation'] = df['Close'].rolling(window=20).std()
    df['upper_band'] = df['basis'] + (2 * df['deviation'])
    df['lower_band'] = df['basis'] - (2 * df['deviation'])

        # RSI Calculation using pandas_ta
    rsiLength = 14
    df['rsi'] = ta.rsi(df['Close'], length=rsiLength)


    # MACD Calculation using pandas_ta
    macdShortLength = 12
    macdLongLength = 26
    macdSignalSmoothing = 9
    macd = ta.macd(df['Close'], fast=macdShortLength, slow=macdLongLength, signal=macdSignalSmoothing)
    df['macd_line'] = macd['MACD_12_26_9']
    df['signal_line'] = macd['MACDs_12_26_9']


    return df






def generate_signals(df):
    df['long_condition'] = (df['Close'].shift(1) > df['upper_band'].shift(1)) & (df['rsi'] > 50) & (df['macd_line'] > df['signal_line'])
    df['short_condition'] = (df['Close'].shift(1) < df['lower_band'].shift(1)) & (df['rsi'] < 50) & (df['macd_line'] < df['signal_line'])

    # Reversed strategy logic
    df['signal'] = 0
    df.loc[df['long_condition'], 'signal'] = -1  # Sell (short) signal
    df.loc[df['short_condition'], 'signal'] = 1   # Buy (long) signal

    return df




class VolatilityBreakoutStrategy(Strategy):
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
            if current_signal == -1:
                print(f"Buy signal detected, executing sell at close={current_price}")
                self.entry_price = current_price
                if self.position().is_long:
                     self.position().close()
                self.sell()  
                

            # Handle sell signal
            elif current_signal == 1:
                print(f"Sell signal detected, executing buy at close={current_price}")
                self.entry_price = current_price
                if self.position().is_short:
                     self.position().close()
                self.buy()  
               


            
        except Exception as e:
            print(f"Error in next method: {e}")
            raise





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, VolatilityBreakoutStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()