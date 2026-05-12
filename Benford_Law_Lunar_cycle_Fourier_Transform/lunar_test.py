# import pandas as pd
# import numpy as np
# import ephem
# from datetime import datetime

# def analyze_and_compare_phases(df):
#     """
#     Analyze percentage changes and compare phases based on multiple metrics
#     """
#     # [Previous phase calculation code remains same until phase_analysis]
    
#     def get_moon_phase(date):
#         moon = ephem.Moon()
#         moon.compute(date)
#         phase_pct = moon.phase
        
#         if phase_pct < 6.25:
#             return 'New Moon'
#         elif phase_pct < 18.75:
#             return 'Waxing Crescent'
#         elif phase_pct < 31.25:
#             return 'First Quarter'
#         elif phase_pct < 43.75:
#             return 'Waxing Gibbous'
#         elif phase_pct < 56.25:
#             return 'Full Moon'
#         elif phase_pct < 68.75:
#             return 'Waning Gibbous'
#         elif phase_pct < 81.25:
#             return 'Last Quarter'
#         elif phase_pct < 93.75:
#             return 'Waning Crescent'
#         else:
#             return 'New Moon'
    
#     # Calculate volatility
#     df['volatility'] = df['close'].rolling(window=24).std()
    
#     # Get moon phases
#     df.index = pd.to_datetime(df.index)
#     df['moon_phase'] = df.index.map(get_moon_phase)
    
#     # Detect phase changes
#     df['phase_change'] = df['moon_phase'] != df['moon_phase'].shift(1)
#     phase_changes = df[df['phase_change']].index
    
#     # Calculate changes for each phase
#     phase_changes_list = []
    
#     for i in range(len(phase_changes)-1):
#         start_date = phase_changes[i]
#         end_date = phase_changes[i+1]
#         phase = df.loc[start_date, 'moon_phase']
        
#         # Calculate percentage changes
#         price_change = ((df.loc[end_date, 'close'] - df.loc[start_date, 'close']) / df.loc[start_date, 'close']) * 100
#         volume_change = ((df.loc[end_date, 'volume'] - df.loc[start_date, 'volume']) / df.loc[start_date, 'volume']) * 100
#         volatility_change = ((df.loc[end_date, 'volatility'] - df.loc[start_date, 'volatility']) / df.loc[start_date, 'volatility']) * 100
        
#         phase_changes_list.append({
#             'phase': phase,
#             'start_date': start_date,
#             'end_date': end_date,
#             'price_change': price_change,
#             'volume_change': volume_change,
#             'volatility_change': volatility_change
#         })
    
#     changes_df = pd.DataFrame(phase_changes_list)
    
#     # Calculate phase metrics
#     phase_analysis = changes_df.groupby('phase').agg({
#         'price_change': ['mean', 'std', 'count'],
#         'volume_change': ['mean', 'std', 'count'],
#         'volatility_change': ['mean', 'std', 'count']
#     })
    
#     # Create comparison metrics
#     comparison = pd.DataFrame(index=phase_analysis.index)
    
#     # Price metrics
#     comparison['avg_price_change'] = phase_analysis[('price_change', 'mean')]
#     comparison['price_consistency'] = abs(phase_analysis[('price_change', 'mean')]) / phase_analysis[('price_change', 'std')]
    
#     # Volume metrics
#     comparison['avg_volume_change'] = phase_analysis[('volume_change', 'mean')]
#     comparison['volume_consistency'] = abs(phase_analysis[('volume_change', 'mean')]) / phase_analysis[('volume_change', 'std')]
    
#     # Volatility metrics
#     comparison['avg_volatility_change'] = phase_analysis[('volatility_change', 'mean')]
#     comparison['volatility_consistency'] = abs(phase_analysis[('volatility_change', 'mean')]) / phase_analysis[('volatility_change', 'std')]
    
#     # Calculate rankings
#     rankings = pd.DataFrame(index=phase_analysis.index)
    
#     # Rank by price performance
#     rankings['price_rank'] = comparison['avg_price_change'].rank(ascending=False)
#     rankings['price_consistency_rank'] = comparison['price_consistency'].rank(ascending=False)
    
#     # Rank by volume
#     rankings['volume_rank'] = comparison['avg_volume_change'].rank(ascending=False)
#     rankings['volume_consistency_rank'] = comparison['volume_consistency'].rank(ascending=False)
    
#     # Rank by volatility
#     rankings['volatility_rank'] = comparison['avg_volatility_change'].rank(ascending=False)
#     rankings['volatility_consistency_rank'] = comparison['volatility_consistency'].rank(ascending=False)
    
#     # Calculate overall scores
#     rankings['overall_score'] = (
#         rankings['price_rank'] * 0.4 +  # Price weighted more heavily
#         rankings['price_consistency_rank'] * 0.2 +
#         rankings['volume_consistency_rank'] * 0.2 +
#         rankings['volatility_consistency_rank'] * 0.2
#     )
    
#     return changes_df, phase_analysis, comparison, rankings

# def print_comprehensive_analysis(phase_analysis, comparison, rankings):
#     """Print detailed analysis with comparisons"""
#     print("\nPhase Performance Rankings")
#     print("=" * 80)
    
#     # Print basic changes
#     print("\n1. Basic Phase Changes:")
#     print("-" * 40)
#     for phase in phase_analysis.index:
#         print(f"\n{phase}:")
#         print(f"Price Change:      {phase_analysis.loc[phase, ('price_change', 'mean')]:>7.2f}% ± {phase_analysis.loc[phase, ('price_change', 'std')]:>6.2f}%")
#         print(f"Volume Change:     {phase_analysis.loc[phase, ('volume_change', 'mean')]:>7.2f}% ± {phase_analysis.loc[phase, ('volume_change', 'std')]:>6.2f}%")
#         print(f"Volatility Change: {phase_analysis.loc[phase, ('volatility_change', 'mean')]:>7.2f}% ± {phase_analysis.loc[phase, ('volatility_change', 'std')]:>6.2f}%")
    
#     # Print phase rankings
#     print("\n2. Phase Rankings (1 = Best, 8 = Worst)")
#     print("-" * 60)
#     print(f"{'Phase':<20} {'Price':>8} {'Price Cons':>12} {'Vol Cons':>12} {'Vol Change':>12} {'Overall':>8}")
#     print("-" * 60)
    
#     # Sort by overall score
#     rankings_sorted = rankings.sort_values('overall_score')
#     for phase in rankings_sorted.index:
#         print(f"{phase:<20} {rankings.loc[phase, 'price_rank']:>8.0f} "
#               f"{rankings.loc[phase, 'price_consistency_rank']:>12.0f} "
#               f"{rankings.loc[phase, 'volume_consistency_rank']:>12.0f} "
#               f"{rankings.loc[phase, 'volume_rank']:>12.0f} "
#               f"{rankings.loc[phase, 'overall_score']:>8.1f}")
    
#     # Print trading implications
#     print("\n3. Trading Implications:")
#     print("-" * 40)
    
#     # Best phases for different strategies
#     best_price = comparison['avg_price_change'].idxmax()
#     most_consistent = comparison['price_consistency'].idxmax()
#     highest_volume = comparison['avg_volume_change'].idxmax()
#     most_volatile = comparison['avg_volatility_change'].idxmax()
    
#     print(f"Best Phase for Returns: {best_price} ({comparison['avg_price_change'][best_price]:.2f}%)")
#     print(f"Most Consistent Phase: {most_consistent}")
#     print(f"Highest Volume Phase: {highest_volume}")
#     print(f"Most Volatile Phase: {most_volatile}")

# # Example usage
# if __name__ == "__main__":
#     # Read your data
#     df = pd.read_csv('/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/STRATEGY/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv', index_col='datetime', parse_dates=True)
    
#     # Run analysis
#     changes_df, phase_analysis, comparison, rankings = analyze_and_compare_phases(df)
    
#     # Print comprehensive analysis
#     print_comprehensive_analysis(phase_analysis, comparison, rankings)








# #gaussian curve of  correlation between vol and price , etc during each phase
# #whole data probability picture,market behavior


import pandas as pd
import numpy as np
import ephem
from datetime import datetime
from scipy import stats
import matplotlib.pyplot as plt

def generate_gaussian_data(mean, std, points=100):
    """Generate data for Gaussian curve"""
    x = np.linspace(mean - 4*std, mean + 4*std, points)
    y = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x - mean) / std)**2)
    return x, y

def calculate_correlations(phase_data):
    """Calculate correlations for a phase with proper NaN and inf handling"""
    try:
        # Remove NaN and inf values
        clean_data = phase_data.replace([np.inf, -np.inf], np.nan).dropna()
        
        if len(clean_data) < 2:  # Need at least 2 points for correlation
            return {
                'price_volume': 0.0,
                'price_volatility': 0.0,
                'volume_volatility': 0.0
            }
        
        # Calculate correlations with error handling
        try:
            price_vol_corr = stats.pearsonr(clean_data['price_change'], clean_data['volume_change'])
            price_vol = price_vol_corr[0] if not np.isnan(price_vol_corr[0]) else 0.0
        except:
            price_vol = 0.0
            
        try:
            price_volatility_corr = stats.pearsonr(clean_data['price_change'], clean_data['volatility_change'])
            price_volatility = price_volatility_corr[0] if not np.isnan(price_volatility_corr[0]) else 0.0
        except:
            price_volatility = 0.0
            
        try:
            vol_volatility_corr = stats.pearsonr(clean_data['volume_change'], clean_data['volatility_change'])
            vol_volatility = vol_volatility_corr[0] if not np.isnan(vol_volatility_corr[0]) else 0.0
        except:
            vol_volatility = 0.0
        
        return {
            'price_volume': price_vol,
            'price_volatility': price_volatility,
            'volume_volatility': vol_volatility
        }
        
    except Exception as e:
        print(f"Error in correlation calculation: {str(e)}")
        return {
            'price_volume': 0.0,
            'price_volatility': 0.0,
            'volume_volatility': 0.0
        }

def plot_gaussian_correlations(changes_df, phase):
    """Plot Gaussian curves for correlations in a phase"""
    try:
        phase_data = changes_df[changes_df['phase'] == phase]
        correlations = calculate_correlations(phase_data)
        
        plt.figure(figsize=(12, 6))
        plt.title(f'Correlation Distribution for {phase}')
        
        # Standard deviation for Gaussian curves
        std = 0.2
        colors = ['blue', 'green', 'red']
        
        for (corr_type, corr_value), color in zip(correlations.items(), colors):
            if not np.isnan(corr_value):  # Only plot if correlation is valid
                x, y = generate_gaussian_data(corr_value, std)
                plt.plot(x, y, label=f'{corr_type}: {corr_value:.3f}', color=color)
        
        plt.xlabel('Correlation Coefficient')
        plt.ylabel('Probability Density')
        plt.legend()
        plt.grid(True)
        plt.axvline(x=0, color='black', linestyle='--', alpha=0.3)
        plt.savefig(f'correlation_gaussian_{phase.replace(" ", "_")}.png')
        plt.close()
        
    except Exception as e:
        print(f"Error in plotting for phase {phase}: {str(e)}")
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
    
    # Add correlation analysis
    correlations_by_phase = {}
    for phase in changes_df['phase'].unique():
        phase_data = changes_df[changes_df['phase'] == phase]
        correlations_by_phase[phase] = calculate_correlations(phase_data)
        
        # Generate Gaussian plots
        plot_gaussian_correlations(changes_df, phase)
    
    return changes_df, phase_analysis, comparison, rankings, correlations_by_phase

def print_comprehensive_analysis(phase_analysis, comparison, rankings, correlations_by_phase):
    """Print detailed analysis with comparisons"""
    print("\nPhase Performance Rankings")
    print("=" * 80)
    
    # Print basic changes
    print("\n1. Basic Phase Changes:")
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
    
    # Print trading implications
    print("\n3. Trading Implications:")
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
    
    # Print correlation analysis
    print("\n4. Correlation Analysis by Phase:")
    print("-" * 60)
    
    for phase, correlations in correlations_by_phase.items():
        print(f"\n{phase}:")
        print(f"Price-Volume Correlation:      {correlations['price_volume']:.3f}")
        print(f"Price-Volatility Correlation:  {correlations['price_volatility']:.3f}")
        print(f"Volume-Volatility Correlation: {correlations['volume_volatility']:.3f}")

# Example usage
if __name__ == "__main__":
    # Read your data
    df = pd.read_csv('/Users/pranaygaurav/Downloads/AlgoTrading/ZELTA_LABS/STRATEGY/Benford_Law_Lunar_cycle_Fourier_Transform/output_file.csv', index_col='datetime', parse_dates=True)
    
    # Run analysis
    changes_df, phase_analysis, comparison, rankings, correlations_by_phase = analyze_and_compare_phases(df)
    
    # Print comprehensive analysis
    print_comprehensive_analysis(phase_analysis, comparison, rankings, correlations_by_phase)