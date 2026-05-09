"""
Command-Line Backtest Script
Run backtests with custom parameters via command line

Usage Examples:
  # Use ALL parameters from strategy_params.json
  python3 backtest_cli.py

  # Use config file defaults but override symbol/timeframe
  python3 backtest_cli.py --symbol BTC/USDT --timeframe 1h

  # Using preset from strategy_params.json
  python3 backtest_cli.py --preset conservative

  # Override everything from command line
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0

  # Override specific ICT parameters
  python3 backtest_cli.py --fvg-gap 0.0007 --ob-swing 7

  # Load custom config file
  python3 backtest_cli.py --config my_params.json
"""

import argparse
import ccxt
import pandas as pd
from datetime import datetime
from ict_indicators import ICTIndicators
from strategy_final import FinalICTStrategy
from backtester import Backtester
import json
import os


def load_config(config_file='strategy_params.json'):
    """Load configuration from JSON file"""
    if not os.path.exists(config_file):
        print(f"Warning: Config file '{config_file}' not found. Using defaults.")
        return {}

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print(f"✅ Loaded config from: {config_file}")
        return config
    except Exception as e:
        print(f"Warning: Failed to load config: {e}. Using defaults.")
        return {}


def get_params_from_config(config, preset=None):
    """Extract parameters from config, optionally using a preset"""
    params = {}

    # Use preset if specified
    if preset and 'presets' in config and preset in config['presets']:
        preset_params = config['presets'][preset]
        print(f"📋 Using preset: {preset} - {preset_params.get('description', '')}")
        params.update({
            'fvg_gap': preset_params.get('fvg_gap'),
            'fvg_lookback': preset_params.get('fvg_lookback'),
            'ob_swing': preset_params.get('ob_swing'),
            'ob_volume': preset_params.get('ob_volume'),
            'sweep_lookback': preset_params.get('sweep_lookback'),
            'sweep_threshold': preset_params.get('sweep_threshold')
        })
    else:
        # Use default parameters from config
        if 'ict_indicators' in config:
            ict = config['ict_indicators']
            params.update({
                'fvg_gap': ict.get('fvg', {}).get('min_gap_size'),
                'fvg_lookback': ict.get('fvg', {}).get('lookback'),
                'ob_swing': ict.get('order_blocks', {}).get('swing_length'),
                'ob_volume': ict.get('order_blocks', {}).get('min_volume_percentile'),
                'sweep_lookback': ict.get('liquidity_sweeps', {}).get('lookback'),
                'sweep_threshold': ict.get('liquidity_sweeps', {}).get('sweep_threshold')
            })

    # Add other config values
    if 'trading' in config:
        params.update({
            'exchange': config['trading'].get('exchange'),
            'capital': config['trading'].get('initial_capital')
        })

    return {k: v for k, v in params.items() if v is not None}


def fetch_data(symbol, timeframe, start_date, end_date, exchange_name='binance'):
    """Fetch historical data"""
    print(f"Fetching {symbol} {timeframe} from {start_date} to {end_date}...")

    exchange = getattr(ccxt, exchange_name)({'enableRateLimit': True})

    start_ts = exchange.parse8601(f'{start_date}T00:00:00Z')
    end_ts = exchange.parse8601(f'{end_date}T23:59:59Z')

    all_candles = []
    current_ts = start_ts

    while current_ts < end_ts:
        try:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=current_ts, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            current_ts = candles[-1][0] + 1
        except Exception as e:
            print(f"Error fetching data: {e}")
            break

    df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df = df[~df.index.duplicated(keep='first')]

    print(f"Fetched {len(df)} candles")
    return df


def run_backtest(args):
    """Run backtest with provided arguments"""

    # Determine date range
    if args.year:
        start_date = f'{args.year}-01-01'
        end_date = f'{args.year}-12-31'
    else:
        start_date = args.start
        end_date = args.end

    # Fetch data
    df = fetch_data(args.symbol, args.timeframe, start_date, end_date, args.exchange)

    if len(df) < 100:
        print("❌ Insufficient data (< 100 candles)")
        return

    # Calculate ICT indicators
    print(f"\nCalculating ICT indicators...")
    print(f"  FVG: gap={args.fvg_gap}, lookback={args.fvg_lookback}")
    print(f"  OB: swing={args.ob_swing}, volume_pct={args.ob_volume}")
    print(f"  Sweep: lookback={args.sweep_lookback}, threshold={args.sweep_threshold}")

    ict = ICTIndicators(df.copy())
    ict.detect_fair_value_gaps(min_gap_size=args.fvg_gap, lookback=args.fvg_lookback)
    ict.detect_order_blocks(swing_length=args.ob_swing, min_volume_percentile=args.ob_volume)
    ict.detect_liquidity_sweeps(lookback=args.sweep_lookback, sweep_threshold=args.sweep_threshold)
    ict.calculate_daily_bias()

    # Generate signals
    print(f"\nGenerating signals...")
    strategy = FinalICTStrategy()
    df_signals = strategy.generate_signals(ict.df.copy())

    signals = (df_signals['signal'] != 0).sum()
    print(f"  Signals generated: {signals}")

    if signals == 0:
        print("❌ No signals generated")
        return

    # Run backtest
    print(f"\nRunning backtest with {args.leverage}x leverage...")
    backtester = Backtester(initial_capital=args.capital)
    _, metrics = backtester.run_backtest(df_signals, leverage=args.leverage)

    # Display results
    print(f"\n{'='*70}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*70}")
    print(f"Symbol:           {args.symbol}")
    print(f"Timeframe:        {args.timeframe}")
    print(f"Period:           {start_date} to {end_date}")
    print(f"Leverage:         {args.leverage}x")
    print(f"Initial Capital:  ${args.capital:,.0f}")
    print(f"{'-'*70}")
    print(f"Signals:          {signals}")
    print(f"Trades:           {metrics.total_trades}")
    print(f"{'-'*70}")
    print(f"Sharpe Ratio:     {metrics.sharpe_ratio:.3f}")
    print(f"Sortino Ratio:    {metrics.sortino_ratio:.3f}")
    print(f"Total Return:     {metrics.total_return_pct:+.2f}%")
    print(f"Max Drawdown:     {metrics.max_drawdown_pct:.2f}%")
    print(f"{'-'*70}")
    print(f"Win Rate:         {metrics.win_rate:.2f}%")
    print(f"Profit Factor:    {metrics.profit_factor:.2f}")
    print(f"Expectancy:       ${metrics.expectancy:.2f}")
    print(f"{'-'*70}")
    print(f"Avg Win:          ${metrics.avg_win:.2f}")
    print(f"Avg Loss:         ${metrics.avg_loss:.2f}")
    print(f"Largest Win:      ${metrics.largest_win:.2f}")
    print(f"Largest Loss:     ${metrics.largest_loss:.2f}")
    print(f"{'='*70}\n")

    # Save results if requested
    if args.output:
        result = {
            'symbol': args.symbol,
            'timeframe': args.timeframe,
            'start_date': start_date,
            'end_date': end_date,
            'leverage': args.leverage,
            'initial_capital': args.capital,
            'parameters': {
                'fvg_gap': args.fvg_gap,
                'fvg_lookback': args.fvg_lookback,
                'ob_swing': args.ob_swing,
                'ob_volume': args.ob_volume,
                'sweep_lookback': args.sweep_lookback,
                'sweep_threshold': args.sweep_threshold
            },
            'results': {
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
        }

        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)

        print(f"✅ Results saved to: {args.output}\n")


def main():
    parser = argparse.ArgumentParser(
        description='ICT Strategy Backtest - Command Line Interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use ALL parameters from strategy_params.json
  python3 backtest_cli.py

  # Use config defaults but override symbol and year
  python3 backtest_cli.py --symbol BTC/USDT --year 2023

  # Use preset from strategy_params.json
  python3 backtest_cli.py --preset conservative

  # Override everything from command line
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0

  # Override specific ICT parameters only
  python3 backtest_cli.py --fvg-gap 0.0007 --ob-swing 7

  # Load custom config file
  python3 backtest_cli.py --config my_params.json

  # Save results to JSON
  python3 backtest_cli.py --output results.json
        """
    )

    # Trading parameters (now optional - can be loaded from config)
    parser.add_argument('--symbol', type=str,
                        help='Trading symbol (e.g., ETH/USDT, BTC/USDT) - default: from config')
    parser.add_argument('--timeframe', type=str,
                        help='Timeframe (e.g., 5m, 15m, 1h, 4h, 1d) - default: from config')
    parser.add_argument('--leverage', type=float,
                        help='Leverage multiplier (e.g., 3.0, 5.0, 10.0) - default: from config')

    # Date range (either year OR start/end)
    parser.add_argument('--year', type=int,
                           help='Year to test (e.g., 2024)')
    parser.add_argument('--start', type=str,
                           help='Start date (YYYY-MM-DD)')

    parser.add_argument('--end', type=str,
                        help='End date (YYYY-MM-DD) - required if --start is used')

    # Optional arguments
    parser.add_argument('--config', type=str, default='strategy_params.json',
                        help='Config file path (default: strategy_params.json)')
    parser.add_argument('--preset', type=str,
                        help='Use preset from config (default, conservative, aggressive, scalping, swing)')
    parser.add_argument('--exchange', type=str,
                        help='Exchange name (default: from config or binance)')
    parser.add_argument('--capital', type=float,
                        help='Initial capital (default: from config or 10000)')
    parser.add_argument('--output', type=str,
                        help='Output JSON file path (optional)')

    # ICT indicator parameters (override config)
    parser.add_argument('--fvg-gap', type=float,
                        help='FVG minimum gap size (default: from config or 0.0005)')
    parser.add_argument('--fvg-lookback', type=int,
                        help='FVG lookback period (default: from config or 40)')
    parser.add_argument('--ob-swing', type=int,
                        help='Order Block swing length (default: from config or 5)')
    parser.add_argument('--ob-volume', type=int,
                        help='Order Block volume percentile (default: from config or 40)')
    parser.add_argument('--sweep-lookback', type=int,
                        help='Liquidity sweep lookback (default: from config or 15)')
    parser.add_argument('--sweep-threshold', type=float,
                        help='Liquidity sweep threshold (default: from config or 0.0005)')

    args = parser.parse_args()

    # Load config file
    config = load_config(args.config)

    # Get parameters from config (with preset if specified)
    config_params = get_params_from_config(config, args.preset)

    # Load trading parameters from config if not provided via command line
    if args.symbol is None:
        args.symbol = config.get('trading', {}).get('symbol')
    if args.timeframe is None:
        args.timeframe = config.get('trading', {}).get('timeframe')
    if args.leverage is None:
        args.leverage = config.get('trading', {}).get('leverage')
    if args.year is None and args.start is None:
        # Try to get default year from config (if exists)
        args.year = config.get('trading', {}).get('default_year', 2024)

    # Validate required trading parameters
    if not args.symbol:
        parser.error("--symbol is required (either via command line or in config file)")
    if not args.timeframe:
        parser.error("--timeframe is required (either via command line or in config file)")
    if not args.leverage:
        parser.error("--leverage is required (either via command line or in config file)")
    if not args.year and not args.start:
        parser.error("Either --year or --start/--end is required")

    # Override ICT parameters with command-line arguments (if provided)
    if args.exchange is None:
        args.exchange = config_params.get('exchange', 'binance')
    if args.capital is None:
        args.capital = config_params.get('capital', 10000)
    if args.fvg_gap is None:
        args.fvg_gap = config_params.get('fvg_gap', 0.0005)
    if args.fvg_lookback is None:
        args.fvg_lookback = config_params.get('fvg_lookback', 40)
    if args.ob_swing is None:
        args.ob_swing = config_params.get('ob_swing', 5)
    if args.ob_volume is None:
        args.ob_volume = config_params.get('ob_volume', 40)
    if args.sweep_lookback is None:
        args.sweep_lookback = config_params.get('sweep_lookback', 15)
    if args.sweep_threshold is None:
        args.sweep_threshold = config_params.get('sweep_threshold', 0.0005)

    # Validate date arguments
    if args.start and not args.end:
        parser.error("--end is required when using --start")

    # Run backtest
    run_backtest(args)


if __name__ == "__main__":
    main()
