import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

class PARModel:
    """
    Polynomial Autoregression Model as defined in the paper
    """
    def __init__(self, n_minutes):
        self.n_minutes = n_minutes
        self.scaler = StandardScaler()
        self.buffer = 0.015  # 1.5% as per paper
        
    def prepare_features(self, prices):
        """
        Create features according to paper's equation 7
        Xi+1 = α + α1(β1Xi + β2Xi-n) + α2(β3Xi + β4Xi-n)² + α3(β4Xi + β5Xi-n)³
        """
        # Current and lagged prices
        X = pd.DataFrame({
            'Xi': prices,
            'Xi_n': prices.shift(self.n_minutes)
        }).dropna()
        
        # Create polynomial terms
        X['term1'] = X['Xi'] + X['Xi_n']
        X['term2'] = X['term1'] ** 2
        X['term3'] = X['term1'] ** 3
        
        # Target variable is next period's price
        y = prices.shift(-1).loc[X.index].dropna()
        X = X.loc[y.index]
        
        return X, y
    
    def fit(self, prices):
        """Train the model on historical data"""
        X, y = self.prepare_features(prices)
        
        # Standardize features
        X_scaled = self.scaler.fit_transform(X)
        self.X_train = X_scaled
        self.y_train = y
        
        # Fit polynomial regression using numpy's polyfit
        self.coeffs = np.polyfit(X_scaled[:, 0], y, deg=3)
    
    def predict(self, prices):
        """Generate price predictions"""
        X, _ = self.prepare_features(prices)
        X_scaled = self.scaler.transform(X)
        return np.polyval(self.coeffs, X_scaled[:, 0])

class TradingSystem:
    """
    Implementation of the trading system described in the paper
    """
    def __init__(self, symbol, timeframe, initial_capital=100000):
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.model = PARModel(timeframe)
        
    def generate_signals(self, prices, predictions):
        """Generate trading signals based on price vs prediction line"""
        signals = pd.Series(index=predictions.index, data=0)
        
        upper_band = predictions * (1 + self.model.buffer)
        lower_band = predictions * (1 - self.model.buffer)
        
        # Long signals
        signals[prices > upper_band] = 1
        
        # Short signals
        signals[prices < lower_band] = -1
        
        return signals
    
    def backtest(self, data):
        """
        Backtest the trading strategy
        Returns performance metrics as described in paper
        """
        # Split data into training and testing periods (6 months each)
        split_idx = len(data) // 2
        train_data = data[:split_idx]
        test_data = data[split_idx:]
        
        # Train model
        self.model.fit(train_data['close'])
        
        # Generate predictions and signals for test period
        predictions = self.model.predict(test_data['close'])
        signals = self.generate_signals(test_data['close'], predictions)
        
        # Calculate returns
        position_returns = signals.shift(1) * test_data['close'].pct_change()
        cumulative_returns = (1 + position_returns).cumprod()
        
        # Calculate performance metrics
        total_return = (cumulative_returns.iloc[-1] - 1) * 100
        profitable_trades = (position_returns > 0).sum()
        total_trades = (signals != 0).sum()
        win_rate = (profitable_trades / total_trades) * 100
        
        # Calculate profit factor
        gross_profits = position_returns[position_returns > 0].sum()
        gross_losses = abs(position_returns[position_returns < 0].sum())
        profit_factor = gross_profits / gross_losses if gross_losses != 0 else float('inf')
        
        return {
            'Net_Profit_%': total_return,
            'Profit_Factor': profit_factor,
            'Win_Rate_%': win_rate,
            'Total_Trades': total_trades
        }

def load_data(symbol, start_date, end_date):
    """
    Load minute-level cryptocurrency data
    This would need to be implemented based on your data source
    """
    # Example implementation - replace with actual data loading
    import yfinance as yf
    data = yf.download(symbol, start=start_date, end=end_date, interval='1m')
    return data

def main():
    # Test configurations from paper
    configs = {
        'BTC-USD': 67,  # Bitcoin optimal timeframe
        'ETH-USD': 61,  # Ethereum optimal timeframe
        'BNB-USD': 62,  # BNB optimal timeframe
        'ADA-USD': 47   # Cardano optimal timeframe
    }
    
    # Test period from paper
    start_date = '2021-12-01'
    end_date = '2022-11-30'
    
    results = {}
    for symbol, timeframe in configs.items():
        print(f"\nTesting {symbol} with {timeframe} minute timeframe")
        
        # Initialize trading system
        system = TradingSystem(symbol, timeframe)
        
        # Load data
        data = load_data(symbol, start_date, end_date)
        
        # Run backtest
        metrics = system.backtest(data)
        results[symbol] = metrics
    
    # Display results
    results_df = pd.DataFrame(results).round(2)
    print("\nBacktest Results:")
    print(results_df)

if __name__ == "__main__":
    main()