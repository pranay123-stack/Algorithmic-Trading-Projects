import pandas as pd
import pandas_ta as ta
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
# from TradeMaster.risk_management.equal_weigh_rm import EqualRiskManagement
# from TradeMaster.trade_management.atr_tm import ATR_RR_TradeManagement
# from TradeMaster.trade_management.price_delta import PriceDeltaTradeManagement

import numpy as np
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


# 2. Indicator Calculation
def calculate_daily_indicators(daily_data, rsi_period=7, ema_period=50, atr_length=14):
    try:
        print("Calculating indicators")

      

          # Calculate RSI excluding the latest close at each index
        daily_data['RSI'] = ta.rsi(daily_data['Close'].shift(1), length=rsi_period)
        
        
        # Calculate EMA for the entire series
        daily_data['EMA'] = ta.ema(daily_data['Close'], length=ema_period)
        
        # Calculate ATR for the entire series
        daily_data['ATR'] = ta.atr(daily_data['High'], daily_data['Low'], daily_data['Close'], length=atr_length)
        
        daily_data.dropna(inplace=True)
        print(f"Indicator calculation complete\n{daily_data.head(20)}")
        return daily_data
    except Exception as e:
        print(f"Error in calculate_indicators: {e}")
        raise




def generate_signals(data):
    try:
        print("Generating trading signals")

        # Initialize signals
        data['signal'] = 0

        # Loop through the data to apply conditions
        for i in range(1, len(data)):
            # Define buyFlag and sellFlag
            buyFlag = data['EMA'].iloc[i] > data['Close'].iloc[i]
            sellFlag = data['EMA'].iloc[i] < data['Close'].iloc[i]
            
            # Define green and red candles
            green_candle = data['Close'].iloc[i] > data['Close'].iloc[i-1]
            red_candle = data['Close'].iloc[i] < data['Close'].iloc[i-1]

            # Define RSI conditions for buying and selling
            buyRsiFlag = data['RSI'].iloc[i] < 20
            sellRsiFlag = data['RSI'].iloc[i] > 80

            # Buy signal: EMA > Close, RSI < 20, green candle, and no open trades
            if buyFlag and buyRsiFlag and green_candle:
                data['signal'].iloc[i] = 1  # Long entry signal
            
            # Sell signal: EMA < Close, RSI > 80, red candle, and no open trades
            elif sellFlag and sellRsiFlag and red_candle:
                data['signal'].iloc[i] = -1  # Short entry signal
        
        print(f"Signal generation complete\n{data.head(20)}")
        return data

    except Exception as e:
        print(f"Error in generate_signals: {e}")
        raise

# Define the Trading Strategy
class EMARSI_Cross(Strategy):
    
    def init(self):
        print("Initializing strategy")
           #always initialize trademanagement and riskmanagement
        # self.trade_management_strategy = PriceDeltaTradeManagement(self.price_delta)
        # self.risk_management_strategy = EqualRiskManagement(initial_risk_per_trade=self.initial_risk_per_trade, initial_capital=self._broker._cash)
        # self.total_trades = len(self.closed_trades)
      
    def next(self):
        atr_value = self.data.ATR[-1]  # ATR value at the current candle
        candle_body = abs(self.data.Close[-1] - self.data.Open[-1])  # Calculate the candle body size

       

        # Long Trade Conditions
        if self.data.signal[-1] == 1:
                # Calculate stop loss distance based on ATR and candle body
            slDist = atr_value + candle_body
            # Calculate stop loss and take profit levels
            stop_loss = self.data.Close[-1] - slDist  # Stop loss for long position
            take_profit = self.data.Close[-1] + (1.2 * slDist)  # Take profit for long position
            
            print(f"Long Entry: Stop Loss = {stop_loss}, Take Profit = {take_profit}")
            if self.position():
                    if self.position().is_short:
                        self.position().close()
            
            # Execute the buy order with stop loss and take profit
            # self.buy(sl=stop_loss, tp=take_profit)
            self.buy(stop=stop_loss, limit=take_profit)

        # Short Trade Conditions
        elif self.data.signal[-1] == -1:
             # Calculate stop loss distance based on ATR and candle body
            slDist = atr_value + candle_body
            # Calculate stop loss and take profit levels
            stop_loss = self.data.High[-1] + slDist  # Stop loss for short position
            take_profit = self.data.High[-1] - (1.2 * slDist)  # Take profit for short position
            
            print(f"Short Entry: Stop Loss = {stop_loss}, Take Profit = {take_profit}")
            if self.position():
                    if self.position().is_long:
                        self.position().close()
            
            # Execute the sell order with stop loss and take profit
            # self.sell(sl=stop_loss, tp=take_profit)
            self.sell(stop=stop_loss, limit=take_profit)






data = load_data(data_path)
data= calculate_daily_indicators(EURUSD)
data = generate_signals(data)
bt = Backtest(data, EMARSI_Cross, cash=100000, commission=.002, exclusive_orders=True)
stats = bt.run()
print(stats)

bt.plot(superimpose=False)
bt.tear_sheet()