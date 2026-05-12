import pandas as pd
import numpy as np
import ephem
from datetime import datetime
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt

def analyze_and_compare_phases(df):
    """
    Analyze percentage changes and compare phases based on multiple metrics
    """
    def get_moon_phase(date):
        moon = ephem.Moon()
        moon.compute(date)
        phase_pct = moon.phase
        
        if phase_pct < 6.25:
            return 'New Moon'
        elif phase_pct < 18.75:
            return 'Waxing Crescent'
        elif phase_pct < 31.25:
            return 'First Quarter'
        elif phase_pct < 43.75:
            return 'Waxing Gibbous'
        elif phase_pct < 56.25:
            return 'Full Moon'
        elif phase_pct < 68.75:
            return 'Waning Gibbous'
        elif phase_pct < 81.25:
            return 'Last Quarter'
        elif phase_pct < 93.75:
            return 'Waning Crescent'
        else:
            return 'New Moon'
    
    # Calculate volatility
    df['volatility'] = df['close'].rolling(window=24).std()
    
    # Get moon phases
    df.index = pd.to_datetime(df.index)
    df['moon_phase'] = df.index.map(get_moon_phase)
    
    # Detect phase changes
    df['phase_change'] = df['moon_phase'] != df['moon_phase'].shift(1)
    phase_changes = df[df['phase_change']].index
    
    # Calculate changes for each phase
    phase_changes_list = []
    
    for i in range(len(phase_changes)-1):
        start_date = phase_changes[i]
        end_date = phase_changes[i+1]
        phase = df.loc[start_date, 'moon_phase']
        
        # Calculate percentage changes
        price_change = ((df.loc[end_date, 'close'] - df.loc[start_date, 'close']) / df.loc[start_date, 'close']) * 100
        volume_change = ((df.loc[end_date, 'volume'] - df.loc[start_date, 'volume']) / df.loc[start_date, 'volume']) * 100
        volatility_change = ((df.loc[end_date, 'volatility'] - df.loc[start_date, 'volatility']) / df.loc[start_date, 'volatility']) * 100
        
        phase_changes_list.append({
            'phase': phase,
            'start_date': start_date,
            'end_date': end_date,
            'price_change': price_change,
            'volume_change': volume_change,
            'volatility_change': volatility_change
        })
    
    changes_df = pd.DataFrame(phase_changes_list)
    
    # Calculate phase metrics
    phase_analysis = changes_df.groupby('phase').agg({
        'price_change': ['mean', 'std', 'count'],
        'volume_change': ['mean', 'std', 'count'],
        'volatility_change': ['mean', 'std', 'count']
    })
    
    # Create comparison metrics
    comparison = pd.DataFrame(index=phase_analysis.index)
    
    # Price metrics
    comparison['avg_price_change'] = phase_analysis[('price_change', 'mean')]
    comparison['price_consistency'] = abs(phase_analysis[('price_change', 'mean')]) / phase_analysis[('price_change', 'std')]
    
    # Volume metrics
    comparison['avg_volume_change'] = phase_analysis[('volume_change', 'mean')]
    comparison['volume_consistency'] = abs(phase_analysis[('volume_change', 'mean')]) / phase_analysis[('volume_change', 'std')]
    
    # Volatility metrics
    comparison['avg_volatility_change'] = phase_analysis[('volatility_change', 'mean')]
    comparison['volatility_consistency'] = abs(phase_analysis[('volatility_change', 'mean')]) / phase_analysis[('volatility_change', 'std')]
    
    # Calculate rankings
    rankings = pd.DataFrame(index=phase_analysis.index)
    
    # Rank by price performance
    rankings['price_rank'] = comparison['avg_price_change'].rank(ascending=False)
    rankings['price_consistency_rank'] = comparison['price_consistency'].rank(ascending=False)
    
    # Rank by volume
    rankings['volume_rank'] = comparison['avg_volume_change'].rank(ascending=False)
    rankings['volume_consistency_rank'] = comparison['volume_consistency'].rank(ascending=False)
    
    # Rank by volatility
    rankings['volatility_rank'] = comparison['avg_volatility_change'].rank(ascending=False)
    rankings['volatility_consistency_rank'] = comparison['volatility_consistency'].rank(ascending=False)
    
    # Calculate overall scores
    rankings['overall_score'] = (
        rankings['price_rank'] * 0.4 +  # Price weighted more heavily
        rankings['price_consistency_rank'] * 0.2 +
        rankings['volume_consistency_rank'] * 0.2 +
        rankings['volatility_consistency_rank'] * 0.2
    )
    
    return changes_df, phase_analysis, comparison, rankings

def analyze_fourier_transform(df, column='close', sampling_rate=24):
    """
    Perform Fourier Transform analysis on time series data.
    
    Parameters:
    -----------
    df : pandas.DataFrame
        Input DataFrame with time series data
    column : str, default='close'
        Column name to analyze
    sampling_rate : int, default=24
        Number of samples per day (24 for hourly data)
    """
    # Prepare the data
    data = df[column].values
    n_samples = len(data)
    
    # Remove trend using first difference
    detrended_data = np.diff(data)
    
    # Apply FFT
    fft_result = fft(detrended_data)
    frequencies = fftfreq(n_samples-1, 1/sampling_rate)
    
    # Calculate amplitudes
    amplitudes = np.abs(fft_result)
    
    # Consider only positive frequencies up to Nyquist frequency
    positive_freq_mask = frequencies > 0
    frequencies = frequencies[positive_freq_mask]
    amplitudes = amplitudes[positive_freq_mask]
    
    # Convert frequencies to periods (in days)
    periods = sampling_rate / frequencies
    
    # Find dominant periods
    n_peaks = 5  # Number of dominant periods to identify
    peak_indices = np.argsort(amplitudes)[-n_peaks:][::-1]
    dominant_periods = periods[peak_indices]
    dominant_amplitudes = amplitudes[peak_indices]
    
    return frequencies, amplitudes, dominant_periods, dominant_amplitudes, periods

def print_comprehensive_analysis(phase_analysis, comparison, rankings, dominant_periods, dominant_amplitudes):
    """Print detailed analysis combining lunar phases and Fourier analysis"""
    print("\nCombined Analysis Report")
    print("=" * 80)
    
    # Print lunar phase analysis
    print("\n1. Lunar Phase Analysis")
    print("-" * 40)
    for phase in phase_analysis.index:
        print(f"\n{phase}:")
        print(f"Price Change:      {phase_analysis.loc[phase, ('price_change', 'mean')]:>7.2f}% ± {phase_analysis.loc[phase, ('price_change', 'std')]:>6.2f}%")
        print(f"Volume Change:     {phase_analysis.loc[phase, ('volume_change', 'mean')]:>7.2f}% ± {phase_analysis.loc[phase, ('volume_change', 'std')]:>6.2f}%")
        print(f"Volatility Change: {phase_analysis.loc[phase, ('volatility_change', 'mean')]:>7.2f}% ± {phase_analysis.loc[phase, ('volatility_change', 'std')]:>6.2f}%")
    
    # Print phase rankings
    print("\n2. Phase Rankings (1 = Best, 8 = Worst)")
    print("-" * 60)
    print(f"{'Phase':<20} {'Price':>8} {'Price Cons':>12} {'Vol Cons':>12} {'Vol Change':>12} {'Overall':>8}")
    print("-" * 60)
    
    # Sort by overall score
    rankings_sorted = rankings.sort_values('overall_score')
    for phase in rankings_sorted.index:
        print(f"{phase:<20} {rankings.loc[phase, 'price_rank']:>8.0f} "
              f"{rankings.loc[phase, 'price_consistency_rank']:>12.0f} "
              f"{rankings.loc[phase, 'volume_consistency_rank']:>12.0f} "
              f"{rankings.loc[phase, 'volume_rank']:>12.0f} "
              f"{rankings.loc[phase, 'overall_score']:>8.1f}")
    
    # Print Fourier analysis results
    print("\n3. Fourier Analysis Results")
    print("-" * 40)
    print("\nDominant Cycles Found:")
    
    for i, (period, amplitude) in enumerate(zip(dominant_periods, dominant_amplitudes), 1):
        print(f"\nCycle {i}:")
        print(f"Period: {period:.1f} days")
        print(f"Amplitude: {amplitude:.2f}")
        
        # Interpret the cycle
        if 27 <= period <= 31:
            print("Interpretation: Lunar cycle (≈29.5 days)")
        elif 350 <= period <= 380:
            print("Interpretation: Annual cycle (≈365 days)")
        elif period <= 7:
            print("Interpretation: Weekly pattern")
        elif period <= 1:
            print("Interpretation: Intraday pattern")
        else:
            print("Interpretation: No standard cycle match")
    
    # Print trading implications
    print("\n4. Trading Implications:")
    print("-" * 40)
    
    # Best phases for different strategies
    best_price = comparison['avg_price_change'].idxmax()
    most_consistent = comparison['price_consistency'].idxmax()
    highest_volume = comparison['avg_volume_change'].idxmax()
    most_volatile = comparison['avg_volatility_change'].idxmax()
    
    print(f"Best Phase for Returns: {best_price} ({comparison['avg_price_change'][best_price]:.2f}%)")
    print(f"Most Consistent Phase: {most_consistent}")
    print(f"Highest Volume Phase: {highest_volume}")
    print(f"Most Volatile Phase: {most_volatile}")

def plot_analysis(df, periods, amplitudes, peak_indices):
    """Create visualizations for both lunar and Fourier analysis"""
    plt.figure(figsize=(15, 10))
    
    # Plot 1: Price and Moon Phases
    plt.subplot(2, 1, 1)
    plt.plot(df.index, df['close'], label='Price', alpha=0.7)
    plt.title('Price Movement and Moon Phases')
    plt.scatter(df[df['moon_phase'] == 'Full Moon'].index, 
               df[df['moon_phase'] == 'Full Moon']['close'],
               color='yellow', label='Full Moon', alpha=0.5)
    plt.scatter(df[df['moon_phase'] == 'New Moon'].index,
               df[df['moon_phase'] == 'New Moon']['close'],
               color='black', label='New Moon', alpha=0.5)
    plt.legend()
    
    # Plot 2: Frequency Domain Analysis
    plt.subplot(2, 1, 2)
    plt.plot(periods, amplitudes)
    plt.title('Frequency Domain Analysis')
    plt.xlabel('Period (days)')
    plt.ylabel('Amplitude')
    
    # Add markers for dominant periods
    for idx in peak_indices:
        plt.scatter(periods[idx], amplitudes[idx], color='red')
        plt.annotate(f'{periods[idx]:.1f} days', 
                    xy=(periods[idx], amplitudes[idx]),
                    xytext=(10, 10),
                    textcoords='offset points')
    
    plt.tight_layout()
    plt.show()

# Example usage
if __name__ == "__main__":
    # Read your data
    df = pd.read_csv('/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/STRATEGY/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv', 
                     index_col='datetime', 
                     parse_dates=True)
    
    # Run lunar phase analysis
    changes_df, phase_analysis, comparison, rankings = analyze_and_compare_phases(df)
    
    # Run Fourier analysis
    frequencies, amplitudes, dominant_periods, dominant_amplitudes, periods = analyze_fourier_transform(df)
    
    # Find peak indices for plotting
    n_peaks = 5
    peak_indices = np.argsort(amplitudes)[-n_peaks:][::-1]
    
    # Create visualizations
    plot_analysis(df, periods, amplitudes, peak_indices)
    
    # Print comprehensive analysis
    print_comprehensive_analysis(phase_analysis, comparison, rankings, dominant_periods, dominant_amplitudes)