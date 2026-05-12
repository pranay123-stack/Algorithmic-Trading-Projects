import pandas_ta as ta
import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import logging
import coloredlogs
import pandas_ta as ta
import pandas as pd
import pandas_ta as ta
from backtesting import Strategy, Backtest
import logging



# Declare global variable
current_data ={}

# Set up logging
log_file_path = "/Users/pranaygaurav/Downloads/AlgoTrading/2.ALGO_TRADING_COMPANIES/CRYPTO/ZELTA_LABS/tradebook/log.log"

logging.basicConfig(level=logging.DEBUG, filename=log_file_path, filemode='a',
                    format='%(asctime)s - %(levelname)s - %(message)s')

coloredlogs.install(level='DEBUG',
                    fmt='%(asctime)s - %(levelname)s - %(message)s',
                    level_styles={
                        'info': {'color': 'green'},
                        'debug': {'color': 'white'},
                        'error': {'color': 'red'},
                    })




def load_and_prepare_data(csv_file_path):
    try:
        logging.info("Loading data from CSV")
        data = pd.read_csv(csv_file_path)
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        data.set_index('timestamp', inplace=True)
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        logging.info("Data loading and preparation complete")
        return data
    except Exception as e:
        logging.error(f"Error in load_and_prepare_data: {e}")
        raise



def calculate_daily_indicators(df):
    try:
        logging.info("Calculating EMA5, EMA900, ATR, OBV, and volume-based Benford's Law")

        # Calculate EMA5 and EMA900
        df['EMA5'] = ta.ema(df['Close'], length=5)
        df['EMA900'] = ta.ema(df['Close'], length=900)

        # Calculate ATR for risk management
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        # Calculate OBV (On-Balance Volume)
        df['OBV'] = ta.obv(df['Close'], df['Volume'])

        # Calculate volume analysis based on Benford's Law
        df['Volume_First_Digit'] = df['Volume'].astype(str).str[0].astype(int)
        benford_distribution = [0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046]

        # Calculate how closely volume follows Benford's Law
        df['Benford_Score'] = df['Volume_First_Digit'].map(lambda x: benford_distribution[x - 1] if 1 <= x <= 9 else 0)

        logging.info("Indicator calculation complete")
        return df.dropna()  # Drop rows with NaN values (due to indicator calculations)

    except Exception as e:
        logging.error(f"Error in calculate_daily_indicators: {e}")
        raise

# Function to generate buy/sell signals based on EMA crossover, OBV, and Benford's Law
def generate_signals(df):
    try:
        logging.info("Generating buy/sell signals based on EMA crossover, OBV analysis, and Benford's Law")

        # Initialize signal column
        df['signal'] = 0

        for i in range(1, len(df)):
            # Conditions for EMA crossover
            crossover_up = df['EMA5'].iloc[i] > df['EMA900'].iloc[i] and df['EMA5'].iloc[i - 1] <= df['EMA900'].iloc[i - 1]
            crossover_down = df['EMA5'].iloc[i] < df['EMA900'].iloc[i] and df['EMA5'].iloc[i - 1] >= df['EMA900'].iloc[i - 1]

            # Filter crossover signals based on OBV trend and Benford's Law score
            obv_trend_up = df['OBV'].iloc[i] > df['OBV'].iloc[i - 1]  # Signal if OBV is trending up
            benford_ok = df['Benford_Score'].iloc[i] > 0.1  # Example threshold for Benford's score

            if crossover_up and obv_trend_up and benford_ok:
                df.at[df.index[i], 'signal'] = 1  # Buy signal

            elif crossover_down and not obv_trend_up and benford_ok:
                df.at[df.index[i], 'signal'] = -1  # Sell signal

        logging.info("Signal generation complete")
        return df

    except Exception as e:
        logging.error(f"Error in generate_signals: {e}")
        raise





class EMACrossoverStrategy(Strategy):
    initsize=0.999
    mysize=initsize
    leverage = 2.0  # Example leverage factor (2x)
    margin= 0
    

    def init(self):
        self.entry_price = None
        self.atr = self.data['ATR']
        self.long_sl=None
        self.long_tp=None
        self.short_sl=None
        self.short_tp=None
       

    def calculate_dynamic_atr_multipliers(self):
        """
        Example logic to adjust ATR multipliers dynamically.
        You can base this on volatility, price levels, or any custom logic.
        """
        volatility = self.atr[-1] / self.data.Close[-1]  # ATR as a percentage of current price

        if volatility > 0.02:  # Example threshold for high volatility
            # Higher multipliers in volatile conditions
            atr_multiplier_long_sl = 6.0
            atr_multiplier_long_tp = 12.0
            atr_multiplier_short_sl = 6.0
            atr_multiplier_short_tp = 6.0
        else:
            # Lower multipliers in less volatile conditions
            atr_multiplier_long_sl = 4.0
            atr_multiplier_long_tp = 8.0
            atr_multiplier_short_sl = 4.0
            atr_multiplier_short_tp = 4.0

        return atr_multiplier_long_sl, atr_multiplier_long_tp, atr_multiplier_short_sl, atr_multiplier_short_tp

   

    def next(self):
        global current_data
        price = self.data.Close[-1]
        signal = self.data.signal[-1]

        # Get dynamic ATR multipliers
        atr_multiplier_long_sl, atr_multiplier_long_tp, atr_multiplier_short_sl, atr_multiplier_short_tp = self.calculate_dynamic_atr_multipliers()

        # Add current row's data to the global dictionary
        current_data = {
            'timestamp': self.data.index[-1],  # Assuming the index is timestamp
            'Open': self.data.Open[-1],
            'High': self.data.High[-1],
            'Low': self.data.Low[-1],
            'Close': price,
            'Volume': self.data.Volume[-1],
            'extra': 'none',
            'signal': 0,  # Default no position
            'TP': 0,  # Stop loss price
            'SL': 0 , # Take profit price
            'after ': 'none', #
        }

             # Managing open long positions
        if self.position.is_long:
           
            # Close long position if stop loss or take profit is hit
            if price <= self.long_sl :
                self.position.close()
                current_data['signal'] = 0  # Taking short position
                logging.info(f"Closing long position at SL {price}")
                self.long_sl = None

               # Close long position if stop loss or take profit is hit
            if  price >= self.long_tp:
                self.position.close()
                current_data['signal'] = 0  # Taking short position
                logging.info(f"Closing long position at  TP{price}")
                self.long_tp=None


        # Managing open short positions
        elif self.position.is_short:
          
            # Close short position if stop loss or take profit is hit
            if price >= self.short_sl:
                self.position.close()
                current_data['signal'] = 0  # Taking short position
                logging.info(f"Closing short position at SL {price}")
                self.short_sl =None

            if price <= self.short_tp:
                self.position.close()
                current_data['signal'] = 0 # Taking short position
                logging.info(f"Closing short position at  TP{price}")
                self.short_tp =None



        # Long entry condition
        if signal == 1 and not self.position:
            self.entry_price = price
            self.buy(size=self.mysize)
            current_data['signal'] = 1  # Taking long position
            logging.info(f"Long entry at {self.entry_price}")
            stop_loss = self.entry_price - atr_multiplier_long_sl * self.atr[-1]  # Long stop loss using dynamic ATR
            take_profit = self.entry_price + atr_multiplier_long_tp * self.atr[-1]  # Long take profit using dynamic ATR
            current_data['TP'] =  round(take_profit,2) # Taking long position
            current_data['SL'] =  round(stop_loss,2) # Taking long position
            self.long_sl = stop_loss # Taking long
            self.long_tp = take_profit # Taking long position


        # Short entry condition
        elif signal == -1 and not self.position :
            self.entry_price = price
            self.sell(size=self.mysize)
            current_data['signal'] = -1  # Taking short position
            logging.info(f"Short entry at {self.entry_price}")
            stop_loss = self.entry_price + atr_multiplier_short_sl * self.atr[-1]  # Short stop loss using dynamic ATR
            take_profit = self.entry_price - atr_multiplier_short_tp * self.atr[-1]  # Short take profit using dynamic ATR
            current_data['TP'] =  round(take_profit,2) # Taking long position
            current_data['SL'] =  round(stop_loss,2) # Taking long position
            self.short_sl = stop_loss # Taking long
            self.short_tp = take_profit # Taking long position

  


   
        
        current_df = pd.DataFrame([current_data])

        # Define the path where the CSV file will be saved
        csv_file_path = '/Users/pranaygaurav/Downloads/AlgoTrading/2.ALGO_TRADING_COMPANIES/CRYPTO/ZELTA_LABS/2020_30min_signals.csv'  # Change this to your desired path

        # Append the current row of data to the CSV file
        if not hasattr(self, 'is_csv_initialized'):  # Ensure CSV is initialized once
            current_df.to_csv(csv_file_path, mode='w', index=False, header=True)
            self.is_csv_initialized = True
        else:
            current_df.to_csv(csv_file_path, mode='a', index=False, header=False)

 


try:
    data_path = '/Users/pranaygaurav/Downloads/AlgoTrading/0.DATA/CRYPTO/spot/2020/BTCUSDT/btc_2020_30min/btc_2020_30min.csv'
    minute_data = load_and_prepare_data(data_path)
    daily_data = calculate_daily_indicators(minute_data)
    daily_signals = generate_signals(daily_data)
    bt = Backtest(daily_signals, EMACrossoverStrategy, cash=1000000, margin =1/5,commission=.002)
    stats = bt.run()
    logging.info(stats)
    logging.info("Backtest complete")
  

except Exception as e:
    logging.error(f"Error during strategy execution: {e}")
    raise