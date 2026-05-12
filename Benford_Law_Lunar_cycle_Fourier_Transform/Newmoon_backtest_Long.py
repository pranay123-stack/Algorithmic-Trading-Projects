#Add adx condition and current adx > avg of prev 5 days
#ATR based exit mechanism with optimization parameters->best parameter
#Aroon indicator -apply->trend strenth in volatile market 20 period 
#vol sma fast [20 period] > vol sma slow [50 period]
#optional ->may be exiting on full moon
#btc atr < 1 % of my current close ,calm market condition->not short trade
#Hurts Experiment >0.5->trendy ,rolling optimal  window size,sliding window approach


from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import ephem
from datetime import datetime, timedelta

data_path = "/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/STRATEGY/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv"

def load_data(csv_file_path):
    try:
        data = pd.read_csv(csv_file_path)
        print("Available columns in the CSV:", data.columns.tolist())
        date_column = data.columns[0]
        print(f"Using column '{date_column}' as datetime index")
        data[date_column] = pd.to_datetime(data[date_column])
        data.set_index(date_column, inplace=True)
        data.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }, inplace=True)
        print("Final columns after renaming:", data.columns.tolist())
        return data
    except Exception as e:
        print(f"Error in load_and_prepare_data: {e}")
        print("Data head:")
        print(data.head())
        raise

class NewMoonLongStrategy(Strategy):
    trailing_stop = 0.02  # 2% trailing stop

    def init(self):
        self.lunar_dates = self.get_lunar_phases()
        self.highest_price = 0
        self.stop_price = 0
        
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
    
    def next(self):
        current_date = self.data.index[-1].to_pydatetime().date()
        current_price = self.data.Close[-1]
        
        # Check for entry signal
        upcoming_new_moons = self.lunar_dates[
            (self.lunar_dates['entry_date'] == current_date) &
            (self.lunar_dates['phase'] == 'new')
        ]
        
        if len(upcoming_new_moons) > 0 and not self.position:
            # Enter long position
            self.buy()
            self.highest_price = current_price
            self.stop_price = current_price * (1 - self.trailing_stop)
        
        # Update trailing stop if in position
        if self.position:
            if current_price > self.highest_price:
                self.highest_price = current_price
                self.stop_price = current_price * (1 - self.trailing_stop)
            
            # Check if stop loss is hit
            if current_price <= self.stop_price:
                self.position.close()

        #the day when new moon is there ,calculated daily vol if current daily vol > avg of prev 5 day vol ,only after receiving close of that new moon day
  
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