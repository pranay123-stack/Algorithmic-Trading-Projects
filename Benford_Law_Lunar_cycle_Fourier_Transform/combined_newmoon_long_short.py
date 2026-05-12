#==============WITH TRIX================

# from backtesting import Backtest, Strategy
# from backtesting.lib import crossover
# import pandas as pd
# import ephem
# import numpy as np
# from datetime import datetime, timedelta
# import talib


# trade_path =  "/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/Benford_Law_Lunar_cycle_Fourier_Transform/trades.csv"
# def calculate_trix(close_prices, period=14):
#     """
#     Calculate TRIX (Triple Exponential Average) indicator for contrarian signals.
#     When TRIX suggests bullish movement, we'll look for short opportunities,
#     and vice versa.
#     """
#     # Calculate triple smoothed EMA
#     ema1 = pd.Series(talib.EMA(close_prices, timeperiod=period))
#     ema2 = pd.Series(talib.EMA(ema1, timeperiod=period))
#     ema3 = pd.Series(talib.EMA(ema2, timeperiod=period))
    
#     # Calculate TRIX line (percent change of triple-smoothed EMA)
#     trix = 100 * (ema3 - ema3.shift(1)) / ema3.shift(1)
    
#     # Calculate signal line (9-period EMA of TRIX)
#     signal = pd.Series(talib.EMA(trix, timeperiod=9))
    
#     return trix, signal

# class ContrarianLunarTrixStrategy(Strategy):
#     """
#     A contrarian trading strategy that takes positions opposite to TRIX signals,
#     combined with lunar cycle analysis.
#     """
    
#     # Strategy Parameters
#     atr_periods = 10
#     atr_multiplier = 3
#     trix_period = 20
#     min_holding_bars = 10
#     max_holding_bars = 30
#     risk_per_trade = 0.02
    
#     def init(self):
#         """Initialize strategy components and indicators"""
#         # Lunar phases
#         self.lunar_dates = self.get_lunar_phases()
        
#         # TRIX indicator for contrarian signals
#         trix, trix_signal = calculate_trix(self.data.Close, self.trix_period)
#         self.trix = self.I(lambda x: x, trix)
#         self.trix_signal = self.I(lambda x: x, trix_signal)
        
#         # ATR for position sizing
#         self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_periods)
        
#         # RSI for additional confirmation
#         self.rsi = self.I(talib.RSI, self.data.Close, timeperiod=14)
        
#         # Position tracking
#         self.entry_bar = 0
#         self.position_type = None
#         self.initial_stop = 0
    
#     def get_lunar_phases(self):
#         """Calculate lunar phases for the entire trading period"""
#         lunar_dates = []
#         start_date = self.data.index[0].to_pydatetime().date()
#         end_date = self.data.index[-1].to_pydatetime().date()
        
#         moon = ephem.Moon()
#         date = start_date
#         while date <= end_date:
#             moon.compute(date)
#             next_new = ephem.next_new_moon(date).datetime().date()
#             entry_start = next_new - timedelta(days=3)
#             exit_date = next_new
            
#             lunar_dates.append({
#                 'date': next_new,
#                 'entry_date': entry_start,
#                 'exit_date': exit_date,
#                 'phase': 'new'
#             })
#             date = next_new + timedelta(days=1)
            
#         return pd.DataFrame(lunar_dates)
    
#     def check_contrarian_trix_signal(self):
#         """
#         Analyze TRIX indicator for contrarian signals.
#         When TRIX shows bullish signals, we look for short entries,
#         and when TRIX shows bearish signals, we look for long entries.
#         """
#         # Get current and previous values
#         curr_trix = self.trix[-1]
#         prev_trix = self.trix[-2]
#         curr_signal = self.trix_signal[-1]
#         prev_signal = self.trix_signal[-2]
        
#         # Detect traditional crossovers
#         traditional_bullish = prev_trix <= prev_signal and curr_trix > curr_signal
#         traditional_bearish = prev_trix >= prev_signal and curr_trix < curr_signal
        
#         # Check traditional momentum
#         traditional_bullish_momentum = curr_trix > 0 and curr_trix > prev_trix
#         traditional_bearish_momentum = curr_trix < 0 and curr_trix < prev_trix
        
#         # Return contrarian signals (opposite of traditional)
#         return {
#             # When TRIX shows bullish signals, we go short
#             'short': traditional_bullish or traditional_bullish_momentum,
#             # When TRIX shows bearish signals, we go long
#             'long': traditional_bearish or traditional_bearish_momentum
#         }
    
#     def check_confirmation_signals(self):
#         """
#         Additional confirmation signals for contrarian trades.
#         Uses RSI and price action to confirm reversal potential.
#         """
#         current_rsi = self.rsi[-1]
        
#         # Oversold/Overbought conditions support contrarian moves
#         oversold = current_rsi < 30  # Supports going long
#         overbought = current_rsi > 70  # Supports going short
        
#         return {
#             'long': oversold,
#             'short': overbought
#         }
    
#     def calculate_position_size(self, entry_price, stop_price, direction='long'):
#         """Calculate position size based on risk parameters"""
#         if entry_price == 0 or stop_price == 0:
#             return 0
            
#         risk_per_share = abs(entry_price - stop_price)
#         if risk_per_share == 0:
#             return 0
            
#         account_value = self.equity
#         risk_amount = account_value * self.risk_per_trade
#         position_value = (risk_amount / risk_per_share) * entry_price
        
#         return min(position_value / account_value, 1.0)
    
#     def should_exit_trade(self):
#         """Determine if current position should be exited"""
#         if not self.position or self.entry_bar == 0:
#             return False
        
#         current_bar = len(self.data)-1
#         bars_held = current_bar - self.entry_bar
        
#         # Time-based exits
#         if bars_held < self.min_holding_bars:
#             return False
#         if bars_held >= self.max_holding_bars:
#             return True
        
#         # Reversal of contrarian signals
#         trix_signals = self.check_contrarian_trix_signal()
#         if self.position.is_long and trix_signals['short']:
#             return True
#         if self.position.is_short and trix_signals['long']:
#             return True
        
#         # Regular trailing stop
#         current_price = self.data.Close[-1]
#         atr_value = self.atr[-1]
        
#         if self.position.is_long:
#             stop_level = current_price - (atr_value * self.atr_multiplier)
#             return current_price < stop_level
#         elif self.position.is_short:
#             stop_level = current_price + (atr_value * self.atr_multiplier)
#             return current_price > stop_level
        
#         return False
    
#     def next(self):
#         """Main strategy logic"""
#         current_date = self.data.index[-1].to_pydatetime().date()
#         current_price = self.data.Close[-1]
        
#         # Check exit conditions
#         if self.position:
#             if self.should_exit_trade():
#                 self.position.close()
#                 self.entry_bar = 0
#                 self.position_type = None
#                 return
        
#         # Entry logic
#         if not self.position:
#             lunar_signal = self.lunar_dates[
#                 (self.lunar_dates['entry_date'] == current_date) &
#                 (self.lunar_dates['phase'] == 'new')
#             ]
            
#             if len(lunar_signal) > 0:
#                 # Get contrarian TRIX signals
#                 trix_signals = self.check_contrarian_trix_signal()
#                 # Get confirmation signals
#                 confirm_signals = self.check_confirmation_signals()
                
#                 atr_value = self.atr[-1]
                
#                 # Long entry (when TRIX is bearish)
#                 if trix_signals['long'] and confirm_signals['long']:
#                     stop_price = current_price - (atr_value * self.atr_multiplier)
#                     size = self.calculate_position_size(current_price, stop_price, 'long')
                    
#                     if size > 0:
#                         self.buy(size=size, sl=stop_price)
#                         self.entry_bar = len(self.data)-1
#                         self.position_type = 'long'
                
#                 # Short entry (when TRIX is bullish)
#                 elif trix_signals['short'] and confirm_signals['short']:
#                     stop_price = current_price + (atr_value * self.atr_multiplier)
#                     size = self.calculate_position_size(current_price, stop_price, 'short')
                    
#                     if size > 0:
#                         self.sell(size=size, sl=stop_price)
#                         self.entry_bar = len(self.data)-1
#                         self.position_type = 'short'

# def run_backtest(data_path):
#     """Execute backtest with the contrarian lunar-TRIX strategy"""
#     try:
#         print(f"Loading data from: {data_path}")
#         data = pd.read_csv(data_path)
#         date_column = data.columns[0]
#         data[date_column] = pd.to_datetime(data[date_column])
#         data.set_index(date_column, inplace=True)
#         data.rename(columns={
#             'open': 'Open', 'high': 'High',
#             'low': 'Low', 'close': 'Close',
#             'volume': 'Volume'
#         }, inplace=True)
        
#         bt = Backtest(
#             data,
#             ContrarianLunarTrixStrategy,
#             cash=100000,
#             commission=.002,
#             margin=1/3,
#             exclusive_orders=True
#         )
        
#         stats = bt.run()
#         print("\nBacktest Statistics:")
#         print(stats)
#         trades = stats['_trades']  
#         trades.to_csv(trade_path)
       
#         return stats, bt
        
#     except Exception as e:
#         print(f"Error during execution: {e}")
#         import traceback
#         traceback.print_exc()
#         return None, None

# if __name__ == "__main__":
#     data_path = "/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv"
#     stats, bt = run_backtest(data_path)







#######==================WITHOUT TRIX===============================
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
import pandas as pd
import ephem
import numpy as np
from datetime import datetime, timedelta
import talib

def load_data(csv_file_path):
    """
    Load and prepare data from CSV file, ensuring proper datetime indexing and column naming.
    Prints diagnostic information about the data loading process.
    """
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

def calculate_adx(high, low, close, period=14):
    """Calculate Average Directional Index (ADX)"""
    return talib.ADX(high, low, close, timeperiod=period)

def calculate_aroon(high, low, period=14):
    """Calculate Aroon indicators"""
    aroon_up, aroon_down = talib.AROON(high, low, timeperiod=period)
    return aroon_up, aroon_down

class CombinedLunarStrategy(Strategy):
    """
    A trading strategy that combines long and short positions based on lunar cycles
    and technical indicators. Long positions use multiple technical indicators,
    while short positions use a trailing stop mechanism.
    """
    # Parameters for long strategy
    atr_periods = 14
    atr_multiplier = 2.0
    adx_period = 14
    aroon_period = 14
    vol_sma_fast = 20
    vol_sma_slow = 50
    
    # Parameters for short strategy
    trailing_stop = 0.02  # 2% trailing stop
    
    def init(self):
        # Lunar phases
        self.lunar_dates = self.get_lunar_phases()
        
        # Technical indicators for long strategy
        self.adx = self.I(calculate_adx, self.data.High, self.data.Low, self.data.Close, self.adx_period)
        aroon_up, aroon_down = calculate_aroon(self.data.High, self.data.Low, self.aroon_period)
        self.aroon_up = self.I(lambda x: x, aroon_up)
        self.aroon_down = self.I(lambda x: x, aroon_down)
        
        # Volume SMAs
        self.vol_sma_fast_line = self.I(lambda x: pd.Series(x).rolling(self.vol_sma_fast).mean(), self.data.Volume)
        self.vol_sma_slow_line = self.I(lambda x: pd.Series(x).rolling(self.vol_sma_slow).mean(), self.data.Volume)
        
        # ATR for long strategy exit
        self.atr = self.I(talib.ATR, self.data.High, self.data.Low, self.data.Close, self.atr_periods)
        
        # Variables for short strategy
        self.lowest_price = float('inf')
        self.stop_price = float('inf')
        
    def get_lunar_phases(self):
        """Calculate lunar phases for the entire data period"""
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
    
    def check_long_conditions(self):
        """Check all conditions required for long entry"""
        return (self.check_volume_condition() and
                self.check_adx_condition() and
                self.check_aroon_condition() and
                self.check_volume_sma_condition())
    
    def check_volume_condition(self):
        """Check if current volume is above 5-day average"""
        current_vol = self.data.Volume[-1]
        prev_5_day_avg = np.mean(self.data.Volume[-6:-1])
        return current_vol > prev_5_day_avg
    
    def check_adx_condition(self):
        """Check if ADX is showing strengthening trend"""
        current_adx = self.adx[-1]
        prev_5_day_avg_adx = np.mean(self.adx[-6:-1])
        return current_adx > prev_5_day_avg_adx
    
    def check_aroon_condition(self):
        """Check if Aroon indicates upward trend"""
        return self.aroon_up[-1] > self.aroon_down[-1]
    
    def check_volume_sma_condition(self):
        """Check if faster volume SMA is above slower SMA"""
        return self.vol_sma_fast_line[-1] > self.vol_sma_slow_line[-1]
    
    def update_short_position(self, current_price):
        """Update trailing stop for short positions"""
        if current_price < self.lowest_price:
            self.lowest_price = current_price
            self.stop_price = current_price * (1 + self.trailing_stop)
        
        # Check if stop loss is hit
        if current_price >= self.stop_price:
            self.position.close()
    
    def next(self):
        """
        Main strategy logic executed for each candle.
        Handles both long and short position entry/exit based on lunar phases
        and technical conditions.
        """
        current_date = self.data.index[-1].to_pydatetime().date()
        current_price = self.data.Close[-1]
        
        # Check for lunar phase signal
        upcoming_new_moons = self.lunar_dates[
            (self.lunar_dates['entry_date'] == current_date) &
            (self.lunar_dates['phase'] == 'new')
        ]
        
        # If we're not in a position and we have a lunar signal
        if len(upcoming_new_moons) > 0 and not self.position:
            if self.check_long_conditions():
                # Enter long position with ATR-based stop loss
                stop_price = current_price - self.atr[-1] * self.atr_multiplier
                self.buy(sl=stop_price)
            else:
                # Enter short position with trailing stop
                self.sell()
                self.lowest_price = current_price
                self.stop_price = current_price * (1 + self.trailing_stop)
        
        # Update trailing stop for short positions
        elif self.position and self.position.is_short:
            self.update_short_position(current_price)

def run_backtest(data_path):
    """
    Run the backtest with the combined strategy and display results
    """
    try:
        print("Loading data from:", data_path)
        data = load_data(data_path)
        print("Data shape:", data.shape)

        # Initialize and run backtest
        bt = Backtest(
            data,
            CombinedLunarStrategy,
            cash=100000,
            commission=.002,
            margin=1/3,  # Allowing for short positions
            exclusive_orders=True
        )

        stats = bt.run()
        print("\nBacktest Statistics:")
        print(stats)
        bt.plot()
        return stats, bt
        
    except Exception as e:
        print(f"Error during execution: {e}")
        import traceback
        traceback.print_exc()
        return None, None

if __name__ == "__main__":
    data_path = "/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv"  # Replace with your data path
    stats, bt = run_backtest(data_path)