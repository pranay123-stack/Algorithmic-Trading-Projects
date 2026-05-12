import pandas as pd
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import numpy as np
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



def calculate_daily_indicators(df):
    # Calculate VWAP
    df['ohlc4'] = (df['Open'] + df['High'] + df['Low'] + df['Close']) / 4
    df['sumSrc'] = (df['ohlc4'] * df['Volume']).cumsum()
    df['sumVol'] = df['Volume'].cumsum()
    df['vwapW'] = df['sumSrc'] / df['sumVol']
    
    # Custom calculation of source
    df['h'] = np.power(df['High'], 2) / 2
    df['l'] = np.power(df['Low'], 2) / 2
    df['o'] = np.power(df['Open'], 2) / 2
    df['c'] = np.power(df['Close'], 2) / 2
    df['source'] = np.sqrt((df['h'] + df['l'] + df['o'] + df['c']) / 4)
    
    # Moving Average and Range calculation
    length = 27
    mult = 0
    df['ma'] = df['source'].rolling(window=length).mean()
    df['range'] = df['High'] - df['Low']
    df['rangema'] = df['range'].rolling(window=length).mean()
    df['upper'] = df['ma'] + df['rangema'] * mult
    df['lower'] = df['ma'] - df['rangema'] * mult
    
    return df




def generate_signals(df):
    # Signal conditions based on indicator crossovers and VWAP conditions
    df['crossUpper'] = (df['source'] > df['upper']) & (df['source'].shift(1) <= df['upper'].shift(1))
    df['crossLower'] = (df['source'] < df['lower']) & (df['source'].shift(1) >= df['lower'].shift(1))
    
    df['bprice'] = np.where(df['crossUpper'], df['High'] + 0.01, np.nan)
    df['bprice'] = df['bprice'].fillna(method='ffill')
    
    df['sprice'] = np.where(df['crossLower'], df['Low'] - 0.01, np.nan)
    df['sprice'] = df['sprice'].fillna(method='ffill')
    
    df['crossBcond'] = df['crossUpper']
    df['crossBcond'] = np.where(df['crossBcond'].isna(), False, df['crossBcond'])
    
    df['crossScond'] = df['crossLower']
    df['crossScond'] = np.where(df['crossScond'].isna(), False, df['crossScond'])
    
    df['cancelBcond'] = df['crossBcond'] & ((df['source'] < df['ma']) | (df['High'] >= df['bprice']))
    df['cancelScond'] = df['crossScond'] & ((df['source'] > df['ma']) | (df['Low'] <= df['sprice']))
    
    # Long and short conditions based on VWAP
    df['longCondition'] = (df['Close'] > df['vwapW'])
    df['shortCondition'] = (df['Close'] < df['vwapW'])
    
    df['signal'] = 0
    df.loc[df['crossUpper'], 'signal'] = 1
    df.loc[df['crossLower'], 'signal'] = -1
    
    return df





class VWAPMTFStockStrategy(Strategy):
    def init(self):
       # Initialize the strategy with a 27-day moving average and a 10-day range multiplier
        self.entry_price = None
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
        
     
    def next(self):
     
        # Long entry logic
        if self.data.signal[-1] == 1 :
            self.buy(stop=self.data.bprice[-1])

            # Long entry logic
        if self.data.signal[-1] == -1:
            if self.position().is_long:
                self.position().close()
              


           







data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, VWAPMTFStockStrategy, cash=100000, commission=.002)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()