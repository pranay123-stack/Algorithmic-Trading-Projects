"""
FINAL COMPLETE BACKTEST - All Years, Symbols, Timeframes
Tests strategy_final.py comprehensively
Uses comprehensive_backtest_config.json for configuration
Generates best_settings_strategy_params.json automatically
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from strategy_final import FinalICTStrategy
from ict_indicators import ICTIndicators
from backtester import Backtester


def load_config(config_file='comprehensive_backtest_config.json'):
    """Load comprehensive backtest configuration"""
    if not os.path.exists(config_file):
        print(f"⚠️  Config file '{config_file}' not found. Using defaults.")
        return {
            'test_matrix': {
                'symbols': ['ETH/USDT', 'BTC/USDT', 'BNB/USDT'],
                'timeframes': ['15m', '1h'],
                'years': [2019, 2020, 2021, 2022, 2023, 2024],
                'leverages': [3.0, 5.0]
            },
            'ict_parameters': {
                'fvg': {'min_gap_size': 0.0005, 'lookback': 40},
                'order_blocks': {'swing_length': 5, 'min_volume_percentile': 40},
                'liquidity_sweeps': {'lookback': 15, 'sweep_threshold': 0.0005}
            },
            'backtest_settings': {'initial_capital': 10000},
            'output_files': {
                'results': 'FINAL_BACKTEST_RESULTS.json',
                'best_settings': 'best_settings_strategy_params.json'
            },
            'best_selection_criteria': {
                'primary_metric': 'sharpe_ratio',
                'min_trades': 10,
                'min_sharpe': 0.5
            }
        }

    with open(config_file, 'r') as f:
        config = json.load(f)

    print(f"✅ Loaded config from: {config_file}")
    return config


def fetch_data(symbol, timeframe, start_date, end_date):
    """Fetch market data"""
    exchange = ccxt.binance({'enableRateLimit': True})

    start_ts = exchange.parse8601(f'{start_date}T00:00:00Z')
    end_ts = exchange.parse8601(f'{end_date}T23:59:59Z')

    all_candles = []
    current_ts = start_ts

    print(f"  Fetching {symbol} {timeframe} data...", end='', flush=True)

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + 1
        except Exception as e:
            print(f" Error: {e}")
            break

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    print(f" {len(df)} candles")
    return df


def run_backtest(symbol, timeframe, year, leverage, ict_params, initial_capital):
    """Run backtest for one configuration"""

    # Fetch data
    df = fetch_data(symbol, timeframe, f'{year}-01-01', f'{year}-12-31')

    if len(df) < 100:
        return None

    # Calculate indicators with config parameters
    ict = ICTIndicators(df.copy())
    ict.detect_fair_value_gaps(
        min_gap_size=ict_params['fvg']['min_gap_size'],
        lookback=ict_params['fvg']['lookback']
    )
    ict.detect_order_blocks(
        swing_length=ict_params['order_blocks']['swing_length'],
        min_volume_percentile=ict_params['order_blocks']['min_volume_percentile']
    )
    ict.detect_liquidity_sweeps(
        lookback=ict_params['liquidity_sweeps']['lookback'],
        sweep_threshold=ict_params['liquidity_sweeps']['sweep_threshold']
    )
    ict.calculate_daily_bias()

    # Generate signals
    strategy = FinalICTStrategy()
    df_signals = strategy.generate_signals(ict.df.copy())

    signals = (df_signals['signal'] != 0).sum()

    if signals == 0:
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'year': year,
            'leverage': leverage,
            'signals': 0,
            'trades': 0,
            'sharpe': 0.0,
            'return_pct': 0.0,
            'max_dd_pct': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'expectancy': 0.0
        }

    # Backtest
    backtester = Backtester(initial_capital=initial_capital)
    _, metrics = backtester.run_backtest(df_signals, leverage=leverage)

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'year': year,
        'leverage': leverage,
        'signals': int(signals),
        'trades': int(metrics.total_trades),
        'sharpe': float(metrics.sharpe_ratio),
        'sortino': float(metrics.sortino_ratio),
        'return_pct': float(metrics.total_return_pct),
        'max_dd_pct': float(metrics.max_drawdown_pct),
        'win_rate': float(metrics.win_rate),
        'profit_factor': float(metrics.profit_factor),
        'expectancy': float(metrics.expectancy),
        'avg_win': float(metrics.avg_win),
        'avg_loss': float(metrics.avg_loss)
    }


def find_best_configuration(results, criteria):
    """Find best configuration based on criteria"""
    print(f"\n{'='*100}")
    print("FINDING BEST CONFIGURATION")
    print(f"{'='*100}")

    primary_metric = criteria.get('primary_metric', 'sharpe_ratio')
    min_trades = criteria.get('min_trades', 10)
    min_sharpe = criteria.get('min_sharpe', 0.5)

    print(f"Primary metric: {primary_metric}")
    print(f"Min trades: {min_trades}")
    print(f"Min Sharpe: {min_sharpe}")

    # Map metric names to result keys
    metric_map = {
        'sharpe_ratio': 'sharpe',
        'sharpe': 'sharpe',
        'return_pct': 'return_pct',
        'profit_factor': 'profit_factor',
        'win_rate': 'win_rate',
        'sortino': 'sortino'
    }

    metric_key = metric_map.get(primary_metric, 'sharpe')

    # Filter valid results
    valid_results = [
        r for r in results
        if r['trades'] >= min_trades and r['sharpe'] >= min_sharpe
    ]

    print(f"\nTotal results: {len(results)}")
    print(f"Valid results (>= {min_trades} trades, Sharpe >= {min_sharpe}): {len(valid_results)}")

    if not valid_results:
        print("\n⚠️  No valid results found! Using best available...")
        valid_results = [r for r in results if r['trades'] > 0]

    if not valid_results:
        print("\n❌ No results with trades found!")
        return None

    # Find best
    best = max(valid_results, key=lambda x: x[metric_key])

    print(f"\n🏆 BEST CONFIGURATION:")
    print(f"{'='*100}")
    print(f"Symbol:        {best['symbol']}")
    print(f"Timeframe:     {best['timeframe']}")
    print(f"Year:          {best['year']}")
    print(f"Leverage:      {best['leverage']}x")
    print(f"{'-'*100}")
    print(f"Sharpe:        {best['sharpe']:.3f}")
    print(f"Return:        {best['return_pct']:+.2f}%")
    print(f"Win Rate:      {best['win_rate']:.2f}%")
    print(f"Profit Factor: {best['profit_factor']:.2f}")
    print(f"Max DD:        {best['max_dd_pct']:.2f}%")
    print(f"Trades:        {best['trades']}")
    print(f"{'='*100}\n")

    return best


def generate_best_settings_file(best_config, ict_params, output_file):
    """Generate best_settings_strategy_params.json"""

    best_settings = {
        "description": "Best parameters from comprehensive backtest",
        "generated_at": datetime.now().isoformat(),
        "selection_criteria": "Highest Sharpe ratio with minimum trade count",

        "best_configuration": {
            "symbol": best_config['symbol'],
            "timeframe": best_config['timeframe'],
            "leverage": best_config['leverage'],
            "test_year": best_config['year']
        },

        "performance": {
            "sharpe_ratio": best_config['sharpe'],
            "sortino_ratio": best_config['sortino'],
            "return_pct": best_config['return_pct'],
            "max_drawdown_pct": best_config['max_dd_pct'],
            "win_rate": best_config['win_rate'],
            "profit_factor": best_config['profit_factor'],
            "trades": best_config['trades'],
            "avg_win": best_config['avg_win'],
            "avg_loss": best_config['avg_loss']
        },

        "trading": {
            "symbol": best_config['symbol'],
            "timeframe": best_config['timeframe'],
            "leverage": best_config['leverage'],
            "initial_capital": 10000,
            "exchange": "binance"
        },

        "ict_indicators": {
            "fvg": {
                "min_gap_size": ict_params['fvg']['min_gap_size'],
                "lookback": ict_params['fvg']['lookback'],
                "description": "Fair Value Gap detection"
            },
            "order_blocks": {
                "swing_length": ict_params['order_blocks']['swing_length'],
                "min_volume_percentile": ict_params['order_blocks']['min_volume_percentile'],
                "description": "Order Block detection"
            },
            "liquidity_sweeps": {
                "lookback": ict_params['liquidity_sweeps']['lookback'],
                "sweep_threshold": ict_params['liquidity_sweeps']['sweep_threshold'],
                "description": "Liquidity sweep detection"
            },
            "bias": {
                "ema_period": 50,
                "description": "Daily bias calculation"
            },
            "atr": {
                "period": 14,
                "min_atr_pct": 0.003,
                "description": "ATR volatility filter"
            }
        },

        "strategy": {
            "risk_per_trade": 0.02,
            "rr_ratio": 2.0,
            "max_position_size_pct": 0.20,
            "max_risk_pct": 0.03,
            "stop_lookback": 30,
            "max_holding_bars": 80,
            "description": "2% risk per trade, 2:1 reward:risk, structure-based stops"
        },

        "backtest": {
            "commission_rate": 0.0004,
            "slippage_pct": 0.0005,
            "description": "0.04% commission (Binance futures), 0.05% slippage"
        },

        "notes": {
            "usage": "Use these parameters for paper/live trading",
            "warning": "This is the best SINGLE configuration. Results may vary in live trading.",
            "recommendation": "Test in paper trading before live deployment"
        }
    }

    with open(output_file, 'w') as f:
        json.dump(best_settings, f, indent=2)

    print(f"✅ Best settings saved to: {output_file}\n")


def main():
    print("="*100)
    print("FINAL STRATEGY - COMPREHENSIVE BACKTEST")
    print("="*100)

    # Load configuration
    config = load_config()

    # Extract config
    test_matrix = config['test_matrix']
    ict_params = config['ict_parameters']
    backtest_settings = config.get('backtest_settings', {})
    output_files = config.get('output_files', {})
    criteria = config.get('best_selection_criteria', {})

    symbols = test_matrix['symbols']
    timeframes = test_matrix['timeframes']
    years = test_matrix['years']
    leverages = test_matrix['leverages']
    initial_capital = backtest_settings.get('initial_capital', 10000)

    print(f"\nTest Matrix:")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Timeframes: {', '.join(timeframes)}")
    print(f"  Years: {', '.join(map(str, years))}")
    print(f"  Leverages: {', '.join(map(lambda x: f'{x}x', leverages))}")
    print(f"  Initial Capital: ${initial_capital:,}")
    print(f"\nICT Parameters:")
    print(f"  FVG: gap={ict_params['fvg']['min_gap_size']}, lookback={ict_params['fvg']['lookback']}")
    print(f"  OB: swing={ict_params['order_blocks']['swing_length']}, volume={ict_params['order_blocks']['min_volume_percentile']}")
    print(f"  Sweep: lookback={ict_params['liquidity_sweeps']['lookback']}, threshold={ict_params['liquidity_sweeps']['sweep_threshold']}")

    all_results = []
    total_tests = len(symbols) * len(timeframes) * len(years) * len(leverages)
    current = 0

    print(f"\n{'='*100}")
    print(f"RUNNING {total_tests} BACKTESTS")
    print(f"{'='*100}\n")

    for symbol in symbols:
        for timeframe in timeframes:
            for year in years:
                for leverage in leverages:
                    current += 1
                    print(f"\n[{current}/{total_tests}] {symbol} {timeframe} {year} {leverage:.0f}x")

                    try:
                        result = run_backtest(symbol, timeframe, year, leverage, ict_params, initial_capital)
                        if result:
                            all_results.append(result)
                            if result['trades'] > 0:
                                print(f"  ✅ {result['trades']} trades | Sharpe {result['sharpe']:.2f} | Return {result['return_pct']:+.1f}% | WR {result['win_rate']:.1f}%")
                            else:
                                print(f"  ⚠️  No trades")
                    except Exception as e:
                        print(f"  ❌ Error: {e}")

    # Save all results
    results_file = output_files.get('results', 'FINAL_BACKTEST_RESULTS.json')
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*100}")
    print("BACKTEST COMPLETE")
    print(f"{'='*100}\n")
    print(f"Total tests: {len(all_results)}")
    print(f"Results saved to: {results_file}")

    # Find best configuration
    best_config = find_best_configuration(all_results, criteria)

    if best_config:
        # Generate best settings file
        best_settings_file = output_files.get('best_settings', 'best_settings_strategy_params.json')
        generate_best_settings_file(best_config, ict_params, best_settings_file)

        print("🎉 COMPREHENSIVE BACKTEST COMPLETE!")
        print(f"\nFiles generated:")
        print(f"  1. {results_file} - All backtest results")
        print(f"  2. {best_settings_file} - Best configuration for deployment\n")
    else:
        print("\n⚠️  Could not determine best configuration.\n")


if __name__ == "__main__":
    main()
