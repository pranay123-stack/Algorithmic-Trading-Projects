import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
import logging
import pandas_ta as ta
from TradeMaster.test import EURUSD
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement



def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])  # Ensure the timestamp is in datetime format
        data.set_index('timestamp', inplace=True)  # Set the datetime column as index
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





def calculate_daily_indicators(df_daily):
   
    
    # Initialize variables
    td_length = 9
    df_daily['td_up_count'] = 0
    df_daily['td_down_count'] = 0
    td_up_count = 0
    td_down_count = 0
    
    # Calculate Tom DeMark Sequential
    for i in range(4, len(df_daily)):
        if df_daily['Close'].iloc[i] > df_daily['Close'].iloc[i - 4]:
            td_up_count = td_up_count + 1 if td_up_count != 0 else 1
            td_down_count = 0
        elif df_daily['Close'].iloc[i] < df_daily['Close'].iloc[i - 4]:
            td_down_count = td_down_count + 1 if td_down_count != 0 else 1
            td_up_count = 0
        else:
            td_up_count = 0
            td_down_count = 0
        
        df_daily.at[df_daily.index[i], 'td_up_count'] = td_up_count
        df_daily.at[df_daily.index[i], 'td_down_count'] = td_down_count

    df_daily['td_buy_setup'] = (df_daily['td_down_count'] == td_length).astype(int)
    df_daily['td_sell_setup'] = (df_daily['td_up_count'] == td_length).astype(int)

    # EMA for Elliott Wave
    wave_length = 21
    df_daily['ema'] = ta.ema(df_daily['Close'], length=wave_length)
    
    # Elliott Wave Calculation
    df_daily['wave_trend'] = np.where(df_daily['Close'] > df_daily['ema'], 1, -1)
    df_daily['wave_trend'] = df_daily['wave_trend'].replace(to_replace=-1, method='ffill')  # Forward fill

    df_daily['wave1'] = df_daily['Close'].where(df_daily['wave_trend'] == 1).ffill()
    df_daily['wave2'] = df_daily['Close'].where(df_daily['wave_trend'] == -1).ffill()
    df_daily['wave3'] = df_daily['wave1']  # Placeholder, adjust according to actual wave logic
    df_daily['wave4'] = df_daily['wave2']  # Placeholder, adjust according to actual wave logic
    df_daily['wave5'] = df_daily['wave1']  # Placeholder, adjust according to actual wave logic

    # Fibonacci Retracement Levels
    def fibonacci_retracement(level, wave_start, wave_end):
        return wave_start + (wave_end - wave_start) * level

    df_daily['wave2_fib'] = fibonacci_retracement(0.618, df_daily['wave1'], df_daily['wave2'])
    df_daily['wave4_fib'] = fibonacci_retracement(0.382, df_daily['wave3'], df_daily['wave4'])

    return df_daily





def generate_signals(df):
    df['buy_signal'] = (df['td_down_count'] == 27) & (df['wave5'].notna())
    df['sell_signal'] = (df['td_up_count'] == 27) & (df['wave5'].notna())

    df['signal'] = 0
    df.loc[df['buy_signal'], 'signal'] = 1
    df.loc[df['sell_signal'], 'signal'] = -1

    return df







# # Define the strategy class
class ElliottWaveTDStrategy(Strategy):
    def init(self):
        logging.info("Initializing strategy")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    
    def next(self):
        # logging.debug(f"Processing bar: {self.data.index[-1]} with signal {self.data.signal[-1]} at price {self.data.Close[-1]}")
         # Check for signals and execute trades based on signal value
        if self.data.signal[-1] == 1 and not self.position():
            logging.debug(f"Buy signal detected, close={self.data.Close[-1]}")
            self.buy()

        elif self.data.signal[-1] == -1 and not self.position():
            logging.debug(f"Sell signal detected, close={self.data.Close[-1]}")
            self.sell()

        # Exit strategy based on stop loss and take profit
        if self.position().is_long:
            if self.data.Close[-1] <= self.data.wave1[-1] or self.data.Close[-1] >= self.data.wave3[-1]:
                self.position().close()
                logging.info(f"Long position closed at {self.data.Close[-1]}")

        elif self.position().is_short:
            if self.data.Close[-1] >= self.data.wave1[-1] or self.data.Close[-1] <= self.data.wave3[-1]:
                self.position().close()
                logging.info(f"Short position closed at {self.data.Close[-1]}")
      
    





data_path = "/Users/pranaygaurav/Downloads/AlgoTrading/1.DATA/CRYPTO/spot/2023/BTCUSDT/btc_2023_1min/btc_1m_data_2023.csv"
data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, ElliottWaveTDStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot()