#trix -TRIPLE SMOOTH EMA
#WHENEVER trix below 0 -> cant take long trade ,but we will take long trade against signal
#Reverse condition for taking  short trade also means when trux suggest donot take short trade but we take short trade

#zscore to use how far trix from o level
#momentum oscillator








from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import ephem
import numpy as np
from datetime import datetime, timedelta
import talib

data_path = "/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv"


def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        date_column = data.columns[0]
        data[date_column] = pd.to_datetime(data[date_column])
        data.set_index(date_column, inplace=True)
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

def calculate_adx(high, low, close, period=14):
    return talib.ADX(high, low, close, timeperiod=period)

def calculate_aroon(high, low, period=14):
    aroon_up, aroon_down = talib.AROON(high, low, timeperiod=period)
    return aroon_up, aroon_down

class NewMoonLongStrategy(Strategy):
    # Parameters
    atr_periods = 14
    atr_multiplier = 2.0
    adx_period = 14
    aroon_period = 14
    vol_sma_fast = 20
    vol_sma_slow = 50
    
    def init(self):
        # Lunar phases
        self.lunar_dates = self.get_lunar_phases()
        
        # Technical indicators
        self.adx = self.I(calculate_adx, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        aroon_up, aroon_down = calculate_aroon(self.data.High, self.data.Low, self.aroon_period)
        self.aroon_up = self.I(lambda x: x, aroon_up)
        self.aroon_down = self.I(lambda x: x, aroon_down)
        
        # Volume SMAs
        self.vol_sma_fast_line = self.I(lambda x: pd.Series(x).rolling(self.vol_sma_fast).mean(), self.data.Volume)
        self.vol_sma_slow_line = self.I(lambda x: pd.Series(x).rolling(self.vol_sma_slow).mean(), self.data.Volume)
        
        # ATR for exit
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_periods)
        
    def get_lunar_phases(self):
        lunar_dates = []
        start_date = self.data.index[0].to_pydatetime().date()
        end_date = self.data.index[-1].to_pydatetime().date()
        
        moon = ephem.Moon()
        date = start_date
        while date <= end_date:
            moon.compute(date)
            next_new = ephem.next_new_moon(date).datetime().date()
            lunar_dates.append({
                'date': next_new,
                'phase': 'new',
                'entry_date': next_new - timedelta(days=3)
            })
            date = next_new + timedelta(days=1)
            
        return pd.DataFrame(lunar_dates)
    
    def check_volume_condition(self):
        current_vol = self.data.Volume[-1]
        prev_5_day_avg = np.mean(self.data.Volume[-6:-1])
        return current_vol > prev_5_day_avg
    
    def check_adx_condition(self):
        current_adx = self.adx[-1]
        prev_5_day_avg_adx = np.mean(self.adx[-6:-1])
        return current_adx > prev_5_day_avg_adx
    
    def check_aroon_condition(self):
        return self.aroon_up[-1] > self.aroon_down[-1]
    
    def check_volume_sma_condition(self):
        return self.vol_sma_fast_line[-1] > self.vol_sma_slow_line[-1]
    
    def next(self):
        current_date = self.data.index[-1].to_pydatetime().date()
        current_price = self.data.Close[-1]
        
        # Entry conditions
        upcoming_new_moons = self.lunar_dates[
            (self.lunar_dates['entry_date'] == current_date) &
            (self.lunar_dates['phase'] == 'new')
        ]
        
        # Check all entry conditions
        if (len(upcoming_new_moons) > 0 and 
            not self.position and 
            self.check_volume_condition() and
            self.check_adx_condition() and
            self.check_aroon_condition() and
            self.check_volume_sma_condition()):
            
            # Calculate stop loss based on ATR
            stop_price = current_price - self.atr[-1] * self.atr_multiplier
            
            # Enter long position
            self.buy(sl=stop_price)
       
   

# Load and prepare data
try:
    print("Loading data from:", data_path)
    data = load_data(data_path)
    print("Data shape:", data.shape)

    # Initialize and run backtest
    bt = Backtest(
        data,
        NewMoonLongStrategy,
        cash=100000,
        commission=.002,
        exclusive_orders=True
    )

    stats = bt.run()
    print("\nBacktest Statistics:")
    print(stats)
    bt.plot()
    
except Exception as e:
    print(f"Error during execution: {e}")
    import traceback
    traceback.print_exc()
