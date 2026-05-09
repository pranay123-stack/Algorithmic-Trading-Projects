"""
FINAL FORWARD TEST - Out-of-sample validation
Tests strategy_final.py on Oct-Dec 2024 (unseen data)
"""

import ccxt
import pandas as pd
import json
from strategy_final import FinalICTStrategy
from ict_indicators import ICTIndicators
from backtester import Backtester

def fetch_forward_data(symbol, timeframe, start_date='2024-10-01', end_date='2024-12-31'):
    """Fetch forward test data"""
    exchange = ccxt.binance({'enableRateLimit': True})

    start_ts = exchange.parse8601(f'{start_date}T00:00:00Z')
    end_ts = exchange.parse8601(f'{end_date}T23:59:59Z')

    all_candles = []
    current_ts = start_ts

    print(f"  Fetching {symbol} {timeframe}...", end='', flush=True)

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

def run_forward_test(symbol, timeframe, leverage=3.0):
    """Run forward test"""

    # Fetch data
    df = fetch_forward_data(symbol, timeframe)

    if len(df) < 100:
        return None

    # Calculate indicators
    ict = ICTIndicators(df.copy())
    ict.detect_fair_value_gaps(min_gap_size=0.0005, lookback=40)
    ict.detect_order_blocks(swing_length=5, min_volume_percentile=40)
    ict.detect_liquidity_sweeps(lookback=15, sweep_threshold=0.0005)
    ict.calculate_daily_bias()

    # Generate signals
    strategy = FinalICTStrategy()
    df_signals = strategy.generate_signals(ict.df.copy())

    signals = (df_signals['signal'] != 0).sum()

    if signals == 0:
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'period': 'Oct-Dec 2024',
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
    backtester = Backtester(initial_capital=10000)
    _, metrics = backtester.run_backtest(df_signals, leverage=leverage)

    return {
        'symbol': symbol,
        'timeframe': timeframe,
        'period': 'Oct-Dec 2024',
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

def main():
    print("="*100)
    print("FINAL STRATEGY - FORWARD TEST (Oct-Dec 2024)")
    print("="*100)

    symbols = ['ETH/USDT', 'BTC/USDT', 'BNB/USDT']
    timeframes = ['15m', '1h']
    leverages = [3.0, 5.0]

    all_results = []

    for symbol in symbols:
        for timeframe in timeframes:
            for leverage in leverages:
                print(f"\n{symbol} {timeframe} {leverage:.0f}x")

                try:
                    result = run_forward_test(symbol, timeframe, leverage)
                    if result:
                        all_results.append(result)
                        if result['trades'] > 0:
                            print(f"  ✅ {result['trades']} trades | Sharpe {result['sharpe']:.2f} | Return {result['return_pct']:+.1f}% | WR {result['win_rate']:.1f}%")
                        else:
                            print(f"  ⚠️ No trades")
                except Exception as e:
                    print(f"  ❌ Error: {e}")

    # Save results
    with open('FINAL_FORWARD_TEST_RESULTS.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\n{'='*100}")
    print("FORWARD TEST COMPLETE")
    print(f"{'='*100}\n")
    print(f"Total tests: {len(all_results)}")
    print(f"Results saved to: FINAL_FORWARD_TEST_RESULTS.json\n")

if __name__ == "__main__":
    main()
