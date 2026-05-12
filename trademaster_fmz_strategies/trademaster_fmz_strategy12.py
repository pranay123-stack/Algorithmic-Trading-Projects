import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import pandas_ta as ta
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

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


def calculate_daily_indicators(df):
    # Calculate Ichimoku components
    tenkan_period = 9
    kijun_period = 26
    senkou_b_period = 52
    displacement = 26

    df['tenkan_sen'] = (df['High'].rolling(window=tenkan_period).max() + df['Low'].rolling(window=tenkan_period).min()) / 2
    df['kijun_sen'] = (df['High'].rolling(window=kijun_period).max() + df['Low'].rolling(window=kijun_period).min()) / 2
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(displacement)
    df['senkou_span_b'] = (df['High'].rolling(window=senkou_b_period).max() + df['Low'].rolling(window=senkou_b_period).min()) / 2
    df['senkou_span_b'] = df['senkou_span_b'].shift(displacement)
    df['chikou_span'] = df['Close'].shift(-displacement)

    # Replace NaN values
    df.fillna(method='bfill', inplace=True)
    return df

def generate_signals(df):
    # Define conditions
    df['long_condition'] = (df['tenkan_sen'] > df['kijun_sen']) & (df['Close'] > df['senkou_span_a']) & (df['Close'] > df['senkou_span_b'])
    df['short_condition'] = (df['tenkan_sen'] < df['kijun_sen']) & (df['Close'] < df['senkou_span_a']) & (df['Close'] < df['senkou_span_b'])

  

    df['signal'] = 0
    df.loc[df['long_condition'], 'signal'] = 1
    df.loc[df['short_condition'], 'signal'] = -1
    
    return df

# Define the strategy class
class IchimokuStrategy(Strategy):
    def init(self):
        try:
            print("Initializing strategy")
                #always initialize trademanagement and riskmanagement
            # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
            # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
            # self.total_trades = len(self.closed_trades)
            self.entry_price = None
            self.stop_loss = None
            self.take_profit = None
            print("Strategy initialization complete")
        except Exception as e:
            print(f"Error in init method: {e}")
            raise

   

    def next(self):
        try:
            current_time = self.data.index[-1]  # Get the current timestamp of the candle

            # Initialize the stop_loss_percentage and take_profit_percentage values
            stop_loss_percentage = 0.05  # 5% Stop Loss
            take_profit_percentage = 0.10  # 10% Take Profit

            # Check for long condition
            if self.data.signal[-1]==1:
                print(f"Long condition met, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                self.stop_loss = self.entry_price * (1 - stop_loss_percentage)  # 5% Stop Loss
                self.take_profit = self.entry_price * (1 + take_profit_percentage)  # 10% Take Profit
                self.buy()
             
            # Check for short condition
            elif self.data.signal[-1]==-1:
                print(f"Short condition met, close={self.data.Close[-1]}")
                self.entry_price = self.data.Close[-1]
                self.stop_loss = self.entry_price * (1 + stop_loss_percentage)  # 5% Stop Loss
                self.take_profit = self.entry_price * (1 - take_profit_percentage)  # 10% Take Profit
                
                # If currently in a long position, close it before selling short
                if self.position().is_long:
                    self.position().close()
                    print(f"Closed Long position at {self.data.Close[-1]} due to short signal")
                
           
            # Exit strategy based on stop loss and take profit for long positions
            if self.position().is_long:
                if self.data.Close[-1] <= self.stop_loss:
                    self.position().close()
                    print(f"Closed Long position at {self.data.Close[-1]} due to hitting stop loss")
                elif self.data.Close[-1] >= self.take_profit:
                    self.position().close()
                    print(f"Closed Long position at {self.data.Close[-1]} due to hitting take profit")

        except Exception as e:
            print(f"Error in next method: {e}")
            raise




data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data,  IchimokuStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()