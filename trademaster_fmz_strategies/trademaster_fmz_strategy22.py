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




def calculate_daily_indicators(df, cumulative_period=14):
    """
    Calculate VWAP and any other required indicators on the daily timeframe.
    """
    try:
        # Calculate typical price
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        
        # Calculate typical price * volume
        df['Typical_Price_Volume'] = df['Typical_Price'] * df['Volume']
        
        # Calculate cumulative sums for typical price * volume and volume
        df['Cumulative_Typical_Price_Volume'] = df['Typical_Price_Volume'].rolling(window=cumulative_period).sum()
        df['Cumulative_Volume'] = df['Volume'].rolling(window=cumulative_period).sum()

        # Calculate VWAP
        df['VWAP'] = df['Cumulative_Typical_Price_Volume'] / df['Cumulative_Volume']

        # Drop any rows with NaN values (resulting from rolling calculations)
        df.dropna(inplace=True)

        return df

    except Exception as e:
        print(f"Error in calculate_daily_indicators: {e}")
        raise



def generate_signals(df):
    """
    Generate buy/sell signals based on VWAP crossover.
    """
    try:
        # Initialize signal column
        df['signal'] = 0

        # Generate signals based on VWAP crossover
        df['long_condition'] = (df['Close'] > df['VWAP']) & (df['Close'].shift(1) < df['VWAP'].shift(1))
        df['short_condition'] = (df['Close'] < df['VWAP']) & (df['Close'].shift(1) > df['VWAP'].shift(1))

        # Set signal = 1 for long, -1 for short
        df.loc[df['long_condition'], 'signal'] = 1
        df.loc[df['short_condition'], 'signal'] = -1

        return df

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise






class VWAPStrategy(Strategy):
    def init(self):
        """
        Initialize any strategy-related variables or calculations.
        """
        self.entry_price = None
        self.long_profit_target = None
        self.short_profit_target = None
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)


    def next(self):
        """
        Execute the strategy on each new bar (price data update).
        """
        try:
            # Long entry condition
            if self.data.signal[-1] == 1  :
                self.buy()
                if self.position():
                    if self.position().is_short:
                        self.position().close()
                self.entry_price = self.data.Close[-1]
                self.long_profit_target = self.entry_price * 1.03

            # Short entry condition
            elif self.data.signal[-1] == -1  :
                self.sell()
                if self.position():
                    if self.position().is_long:
                        self.position().close()
                self.entry_price = self.data.Close[-1]
                self.short_profit_target = self.entry_price * 0.97

            # Managing long position (take profit)
            if self.position().is_long:
                  
                if self.data.Close[-1] >= self.long_profit_target:
                    self.position().close()

             
            # Managing short position (take profit)
            elif self.position().is_short:
              
                if self.data.Close[-1] <= self.short_profit_target:
                    self.position().close()

        except Exception as e:
            print(f"Error in next function: {e}")
            raise





data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, VWAPStrategy, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()