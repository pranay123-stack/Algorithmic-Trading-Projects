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
import pandas_ta as ta
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



def calculate_daily_indicators(df):
    # Bollinger Bands calculation
    length = 20
    mult = 2.0
    df['basis'] = df['Close'].rolling(window=length).mean()
    df['stddev'] = df['Close'].rolling(window=length).std()
    df['dev'] = mult * df['stddev']
    df['upper'] = df['basis'] + df['dev']
    df['lower'] = df['basis'] - df['dev']

    # Stochastic RSI calculation
    rsi_length = 14
    stoch_length = 14
    smooth_k = 3
    smooth_d = 3
    df['rsi'] = ta.rsi(df['Close'], length=rsi_length)

  

    # Calculate Stochastic RSI using pandas_ta
    stoch_rsi_df = ta.stochrsi(df['Close'], length=rsi_length, rsi_length=stoch_length, k=smooth_k, d=smooth_d)
    print(stoch_rsi_df)
    # Add Stochastic RSI (%K and %D) to the DataFrame
    df['stoch_k'] = stoch_rsi_df['STOCHRSIk_14_14_3_3']
    df['stoch_d'] = stoch_rsi_df['STOCHRSId_14_14_3_3']
    return df



def generate_signals(df):
    upper_limit = 90
    lower_limit = 10

    # Conditions for Bearish and Bullish entries
    df['Bear'] = (df['Close'].shift(1) > df['upper'].shift(1)) & (df['Close'] < df['upper']) & \
                 (df['stoch_k'].shift(1) > upper_limit) & (df['stoch_d'].shift(1) > upper_limit)
    
    df['Bull'] = (df['Close'].shift(1) < df['lower'].shift(1)) & (df['Close'] > df['lower']) & \
                 (df['stoch_k'].shift(1) < lower_limit) & (df['stoch_d'].shift(1) < lower_limit)

    # Generating signals based on Bull and Bear conditions
    df['signal'] = 0
    df.loc[df['Bear'], 'signal'] = 1  # Enter Short
    df.loc[df['Bull'], 'signal'] = -1   # Enter Long

    return df




class BollingerBandsStochasticRSI(Strategy):
    def init(self):
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        pass

    def next(self):
        # Access the signal generated from daily data
        signal = self.data.signal[-1]
        current_price = self.data.Close[-1]
        
        if signal == 1:
            print(f"Buy signal detected, executing buy at close={current_price}")
            self.entry_price = current_price
            if self.position():
                if self.position().is_short:
                    print("Closing short position before opening long")
                    self.position().close()
                elif self.position().is_long:
                    print("Already in long position, no action needed")
                    return
            self.buy()  # Enter Long position
          
        

           
               
        elif signal == -1:  # Bearish signal
            if self.position():
                if self.position().is_long:
                    print("Closing long position before opening short")
                    self.position().close()
                elif self.position().is_short:
                    print("Already in short position, no action needed")
                    return
            self.sell()  # Enter Short position











data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, BollingerBandsStochasticRSI, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()