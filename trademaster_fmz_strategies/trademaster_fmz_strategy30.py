import pandas as pd
import numpy as np
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
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



def heikDownColor(df):
    return df.get('tradedowns', pd.Series([False] * len(df), index=df.index))

def heikUpColor(df):
    return df.get('tradeups', pd.Series([False] * len(df), index=df.index))

def heikExitColor(df):
    return df.get('tradeexitsignals', pd.Series([False] * len(df), index=df.index)) & df.get('tradeexits', pd.Series([False] * len(df), index=df.index))

def calculate_daily_indicators(df):
    """
    Calculate the indicators for the trading strategy using pandas_ta.
    
    :param df: DataFrame containing 'High', 'Low', 'Close', and 'Volume' columns.
    :return: DataFrame with calculated indicators.
    """
    try:
        # Ensure necessary columns are present
        required_columns = ['High', 'Low', 'Close', 'Open']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        # EMA calculations
        p10 = 10
        p200 = 200

        df['ema10'] = ta.ema(df['Close'], length=p10)
        df['ema200'] = ta.ema(df['Close'], length=p200)

        # ATR calculations
        lengthatr = 12
        df['atr'] = ta.atr(df['High'], df['Low'], df['Close'], length=lengthatr)
        df['ema_atr'] = ta.ema(df['Close'], length=lengthatr)

        df['ema_plus_atr'] = df['ema_atr'] + df['atr']
        df['ema_minus_atr'] = df['ema_atr'] - df['atr']

        # MACD Histogram calculation
        fastLengthHist = 12
        slowLengthHist = 26
        signalLength = 9

        macd = ta.macd(df['Close'], fast=fastLengthHist, slow=slowLengthHist, signal=signalLength)
        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        df['hist'] = df['macd'] - df['macd_signal']

        # Initialize trading signals columns if they are missing
        df['tradeups'] = False
        df['tradeexits'] = False
        df['tradedowns'] = False
        df['exitshort'] = False
        df['tradeshorts'] = False  # Added this initialization

        # Trade signals
        df['tradeups'] = (df['ema10'] > df['ema10'].shift(1)) & (df['Low'] > df['ema_minus_atr']) & (df['hist'] > df['hist'].shift(1))
        df['tradeexits'] = df['tradeups'].shift(1) & (df['ema10'] < df['ema10'].shift(1))
        df['tradedowns'] = ((df['ema10'] < df['ema10'].shift(1)) & (df['hist'] < df['hist'].shift(1))) | \
                           ((df['High'] > df['ema_plus_atr']) & (df['Close'] < df['ema_plus_atr']) & \
                            (df['Close'] < df['Open']) & (df['hist'] < df['hist'].shift(1)))
        df['exitshort'] = (df['Low'] < df['ema_minus_atr']) & (df['Close'] > df['Open']) & \
                           (df['ema10'] > df['ema10'].shift(1)) & (df['hist'] > df['hist'].shift(1))

        # Heiki Filters
        df['heikDownColor'] = heikDownColor(df)
        df['heikUpColor'] = heikUpColor(df)
        df['heikExitColor'] = heikExitColor(df)

        df['inashort_filt'] = df['heikDownColor'] & df['tradeshorts'] & ~df['heikUpColor']
        df['inalong_filt'] = df['heikUpColor'] & ~df['heikDownColor'] & ~df['tradeexits']
        df['inaexit_filt'] = df['heikExitColor'] & ~df['heikDownColor'] & ~df['heikUpColor']
        df['inasexits_filt'] = df['exitshort'] & (df['inashort_filt']) & ~df['tradeups']

        # Heiki Line Logic
        df['prev5'] = 0
        df.loc[df['inalong_filt'], 'prev5'] = 1000
        df.loc[df['inashort_filt'], 'prev5'] = -1000
        df.loc[df['inaexit_filt'], 'prev5'] = 0
        df.loc[df['inasexits_filt'], 'prev5'] = 0
        
        df['prev5'] = df['prev5'].fillna(method='ffill')

        # Generate signals
        df['shortdata2'] = (df['prev5'] == -1000) & (df['inashort_filt'])
        df['longdata2'] = (df['prev5'] == 1000) & (df['inalong_filt'])
        df['exitdata2'] = (df['prev5'] == 0) & ~df['inalong_filt'] & ~df['inashort_filt']

        # Convert boolean signals to integer codes
        df['signal'] = 0
        df.loc[df['longdata2'], 'signal'] = 1
        df.loc[df['shortdata2'], 'signal'] = -1
        df.loc[df['exitdata2'], 'signal'] = -2

        return df
    
    except Exception as e:
        print(f"Error in calculate_daily_indicators function: {e}")
        raise

def generate_signals(df):
    """
    Generate trading signals based on the 'prev5' values and add a signal column.
    
    :param df: DataFrame with 'prev5' column.
    :return: DataFrame with added 'signal' column.
    """
    try:
        # Initialize the signal column
        df['signal'] = 0
        
        # Generate long signals
        df.loc[(df['prev5'].shift(1) < 900) & (df['prev5'] > 0), 'signal'] = 1
        
        # Generate short signals
        df.loc[(df['prev5'].shift(1) > -900) & (df['prev5'] < 0), 'signal'] = -1
        
        # Generate exit signals
        df.loc[(df['prev5'] == 0) & ((df['prev5'].shift(1) > 0) | (df['prev5'].shift(1) < 0)), 'signal'] = -2
        
        return df

    except Exception as e:
        print(f"Error in generate_signals function: {e}")
        raise

class FlawlessVictoryDCA(Strategy):
    def init(self):
        print("Starting")
         #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)

    def next(self):
        signal = self.data.signal[-1]

        if signal == 1:
            self.buy()

        elif signal == -1:
            self.sell()

        elif signal == -2:
            self.position().close()






minute_data = load_data(data_path)
daily_data = calculate_daily_indicators(EURUSD)
daily_signals = generate_signals(daily_data)
bt = Backtest(daily_signals ,FlawlessVictoryDCA, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)
bt.plot(superimpose=False)
bt.tear_sheet()
