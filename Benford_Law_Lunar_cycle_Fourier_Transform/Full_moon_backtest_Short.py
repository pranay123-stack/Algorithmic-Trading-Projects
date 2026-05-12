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

class FullMoonShortStrategy(Strategy):
    trailing_stop = 0.02  # 2% trailing stop

    def init(self):
        self.lunar_dates = self.get_lunar_phases()
        self.lowest_price = float('inf')
        self.stop_price = float('inf')
        
    def get_lunar_phases(self):
        lunar_dates = []
        start_date = self.data.index[0].to_pydatetime().date()
        end_date = self.data.index[-1].to_pydatetime().date()
        
        moon = ephem.Moon()
        date = start_date
        while date <= end_date:
            moon.compute(date)
            next_full = ephem.next_full_moon(date).datetime().date()
            lunar_dates.append({
                'date': next_full,
                'phase': 'full',
                'entry_date': next_full - timedelta(days=3)
            })
            date = next_full + timedelta(days=1)
            
        return pd.DataFrame(lunar_dates)
    
    def next(self):
        current_date = self.data.index[-1].to_pydatetime().date()
        current_price = self.data.Close[-1]
        
        # Check for entry signal
        upcoming_full_moons = self.lunar_dates[
            (self.lunar_dates['entry_date'] == current_date) &
            (self.lunar_dates['phase'] == 'full')
        ]
        
        if len(upcoming_full_moons) > 0 and not self.position:
            # Enter short position
            self.sell()
            self.lowest_price = current_price
            self.stop_price = current_price * (1 + self.trailing_stop)
        
        # Update trailing stop if in position
        if self.position:
            if current_price < self.lowest_price:
                self.lowest_price = current_price
                self.stop_price = current_price * (1 + self.trailing_stop)
            
            # Check if stop loss is hit
            if current_price >= self.stop_price:
                self.position.close()

# Load and prepare data
try:
    print("Loading data from:", data_path)
    data = load_data(data_path)
    print("Data shape:", data.shape)

    # Initialize and run backtest
    bt = Backtest(
        data,
        FullMoonShortStrategy,
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