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





def calculate_daily_indicators(df):
    try:
        print("Calculating RSI, Stochastic RSI, and price change")

        lookback_period = 24  # Lookback period in bars for 30min timeframe
        rsi_length = 14  # RSI Length
        stoch_length = 14  # Stochastic RSI Length
        k = 3  # Stochastic %K
        d = 3  # Stochastic %D
        big_move_threshold = 2.5 / 100  # Big Move Threshold as percentage

        # Calculate RSI
        df['RSI'] = ta.rsi(df['Close'], length=rsi_length)

        # Calculate Stochastic RSI
        stoch_rsi = ta.stochrsi(df['RSI'], length=stoch_length)

    
      
    
        df['StochRSI_K'] = ta.sma(stoch_rsi['STOCHRSIk_14_14_3_3'], length=k)
        df['StochRSI_D'] = ta.sma(df['StochRSI_K'], length=d)

        # Calculate percent price change from 12 hours ago (lookback period)
        df['Price_12hrs_Ago'] = df['Close'].shift(lookback_period - 1)
        df['Percent_Change'] = abs(df['Close'] - df['Price_12hrs_Ago']) / df['Price_12hrs_Ago']

        # # Drop NaN rows
        # df.dropna(inplace=True)

        print("Indicator calculation complete")
        return df
    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise


def generate_signals(df):
    try:
        print("Generating signals based on Stoch RSI and price moves")

        # Initialize signal column
        df['signal'] = 0

        big_move_threshold = 2.5 / 100  # Big Move Threshold as percentage

        for i in range(len(df)):
            # Check conditions for entering long or short
            if (df['Percent_Change'].iloc[i] >= big_move_threshold) and (df['StochRSI_K'].iloc[i] < 3 or df['StochRSI_D'].iloc[i] < 3):
                df.at[df.index[i], 'signal'] = 1  # Long signal
            elif (df['Percent_Change'].iloc[i] >= big_move_threshold) and (df['StochRSI_K'].iloc[i] > 97 or df['StochRSI_D'].iloc[i] > 97):
                df.at[df.index[i], 'signal'] = -1  # Short signal

        print("Signal generation complete")
        return df.dropna()
    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise





class StochRSIMoveStrategy(Strategy):
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
            # Buy signal
            if self.data.signal[-1] == 1 :
                print(f"Long entry signal at close price {self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                if self.position():
                    if self.position().is_short:
                        self.position().close()
                        
                self.buy()

            # Sell/Short signal
            if self.data.signal[-1] == -1 :
                print(f"Short entry signal at close price {self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                if self.position():
                    if self.position().is_long:
                        self.position().close()
                        
                self.sell()

        except Exception as e:
            print(f"Error in next method: {e}")
            raise




data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, StochRSIMoveStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()