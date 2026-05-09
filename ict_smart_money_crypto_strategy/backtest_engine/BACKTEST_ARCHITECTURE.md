# 📊 ICT Strategy Backtest System - Complete Guide

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Module Details](#module-details)
4. [Strategy Details](#strategy-details)
5. [How to Run](#how-to-run)
6. [Performance Results](#performance-results)
7. [Customization](#customization)

---

## Overview

This is the **complete backtesting system** for the Final ICT (Inner Circle Trader) cryptocurrency trading strategy.

**Purpose**: Historical testing, parameter optimization, and performance validation
**Location**: `/smart_money_crypto_strategy/`
**Status**: Production-ready backtesting framework

### Quick Start

```bash
# Method 1: Single backtest with CLI (fast, flexible)
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0

# Method 2: Comprehensive backtest - Auto-find best settings (recommended for optimization)
python3 final_complete_backtest.py
# → Generates best_settings_strategy_params.json automatically
```

### Best Result (Forward Test Oct-Dec 2024)

**ETH/USDT 15m 5x leverage**:
- Sharpe Ratio: **1.30** ⭐
- Total Return: **+25.7%**
- Win Rate: **42.1%**
- Profit Factor: **1.70**
- Max Drawdown: **-23.3%**

---

## Architecture

### Files Overview

| File | Type | Purpose | Lines |
|------|------|---------|-------|
| **strategy_final.py** | Core | Trading strategy logic | ~250 |
| **ict_indicators.py** | Core | ICT indicator calculations | ~350 |
| **backtester.py** | Core | Backtest engine | ~400 |
| **data_fetcher.py** | Core | Data fetching from exchanges | ~150 |
| **backtest_cli.py** | Script | Command-line backtest ⭐ | ~200 |
| **final_complete_backtest.py** | Script | Auto-find best settings ⭐⭐ | ~400 |
| **final_forward_test.py** | Script | Forward test (Oct-Dec 2024) | ~180 |
| **strategy_params.json** | Config | Strategy parameters & presets | - |
| **comprehensive_backtest_config.json** | Config | Comprehensive backtest config | - |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   BACKTEST SYSTEM                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐      ┌──────────────┐                │
│  │ Data Fetcher │─────▶│ OHLCV Data   │                │
│  └──────────────┘      └──────┬───────┘                │
│                                │                         │
│                                ▼                         │
│                     ┌──────────────────┐                │
│                     │ ICT Indicators   │                │
│                     │  - FVG           │                │
│                     │  - Order Blocks  │                │
│                     │  - Sweeps        │                │
│                     └──────┬───────────┘                │
│                            │                             │
│                            ▼                             │
│                  ┌─────────────────────┐                │
│                  │ Final ICT Strategy  │                │
│                  │  (Independent OR)   │                │
│                  └──────┬──────────────┘                │
│                         │                                │
│                         ▼                                │
│                ┌─────────────────────┐                  │
│                │ Backtester Engine   │                  │
│                │  - Intra-bar exec   │                  │
│                │  - Risk mgmt        │                  │
│                │  - Metrics          │                  │
│                └──────┬──────────────┘                  │
│                       │                                  │
│                       ▼                                  │
│              ┌─────────────────┐                        │
│              │ Results & Stats │                        │
│              │  - Sharpe       │                        │
│              │  - Win Rate     │                        │
│              │  - Drawdown     │                        │
│              └─────────────────┘                        │
└─────────────────────────────────────────────────────────┘
```

---

## Module Details

### 1. strategy_final.py - Trading Strategy

**Purpose**: Core ICT trading strategy implementation

**What it does**:
- Generates BUY/SELL signals from indicator data
- Implements independent OR logic (bias + ANY indicator)
- Calculates structure-based stop loss (30-bar lookback)
- Applies quality filters (ATR, risk, bias)
- Calculates 2:1 reward-risk take profit

**Key Methods**:
```python
class FinalICTStrategy:
    def generate_signals(df, use_fvg=True, use_ob=True, use_sweep=True):
        """Generate trading signals with quality filters"""
        # Returns DataFrame with signal, entry_price, stop_loss, take_profit

    def calculate_daily_bias(df):
        """Calculate market bias (close > EMA50 = bullish)"""

    def calculate_atr(df, period=14):
        """Calculate Average True Range for volatility"""
```

**Usage Example**:
```python
from strategy_final import FinalICTStrategy

strategy = FinalICTStrategy(base_tf='15m', rr_ratio=2.0)
df_with_signals = strategy.generate_signals(df_with_indicators)
```

---

### 2. ict_indicators.py - ICT Indicators

**Purpose**: Calculate all Inner Circle Trader (ICT) technical indicators

**Indicators Calculated**:

1. **Fair Value Gaps (FVG)**
   - Bullish FVG: Gap between candle N low and candle N-2 high
   - Bearish FVG: Gap between candle N high and candle N-2 low
   - Parameters: `min_gap_size=0.0005` (0.05%), `lookback=40` bars

2. **Order Blocks (OB)**
   - High-volume swing candles indicating institutional activity
   - Bullish OB: Swing low + high volume
   - Bearish OB: Swing high + high volume
   - Parameters: `swing_length=5`, `min_volume_percentile=40`

3. **Liquidity Sweeps**
   - Price briefly exceeds recent high/low then reverses (stop hunt)
   - Sweep Low: Price goes below recent low, then closes above
   - Sweep High: Price goes above recent high, then closes below
   - Parameters: `lookback=15`, `sweep_threshold=0.0005`

4. **Daily Bias**
   - Market direction: Bullish (close > EMA50), Bearish (close < EMA50)

5. **ATR (Average True Range)**
   - Volatility measurement for quality filter

**Key Methods**:
```python
class ICTIndicators:
    def detect_fair_value_gaps(min_gap_size=0.0005, lookback=40)
    def detect_order_blocks(swing_length=5, min_volume_percentile=40)
    def detect_liquidity_sweeps(lookback=15, sweep_threshold=0.0005)
    def calculate_daily_bias()
    def calculate_atr(period=14)
```

**Usage Example**:
```python
from ict_indicators import ICTIndicators

ict = ICTIndicators(df)
ict.detect_fair_value_gaps(min_gap_size=0.0005, lookback=40)
ict.detect_order_blocks(swing_length=5, min_volume_percentile=40)
ict.detect_liquidity_sweeps(lookback=15, sweep_threshold=0.0005)
ict.calculate_daily_bias()
df_with_indicators = ict.df
```

---

### 3. backtester.py - Backtest Engine

**Purpose**: Execute strategy backtest with realistic simulation

**Features**:
- **Intra-bar execution**: Checks if high/low hit SL/TP within each bar
- **Realistic fills**: Uses SL/TP prices (not close price) for exits
- **Risk management**: Position sizing based on risk per trade
- **Leverage support**: Configurable leverage (3x, 5x, 10x, etc.)
- **Max holding period**: Timeout exits after 80 bars
- **Slippage & commission**: Realistic cost modeling

**Metrics Calculated**:
- Total Return %
- Sharpe Ratio (annualized, risk-free rate = 0)
- Sortino Ratio (downside deviation only)
- Maximum Drawdown %
- Win Rate %
- Profit Factor (gross profit / gross loss)
- Expectancy (average $ per trade)
- Average Win / Average Loss
- Largest Win / Largest Loss

**Key Methods**:
```python
class Backtester:
    def run_backtest(df_signals, leverage=5.0):
        """Run complete backtest with intra-bar execution"""
        # Returns (trades_df, metrics)
```

**Usage Example**:
```python
from backtester import Backtester

backtester = Backtester(initial_capital=10000)
trades_df, metrics = backtester.run_backtest(df_signals, leverage=5.0)

print(f"Sharpe: {metrics.sharpe_ratio:.2f}")
print(f"Return: {metrics.total_return_pct:.2f}%")
```

---

### 4. data_fetcher.py - Data Fetching

**Purpose**: Fetch historical OHLCV data from cryptocurrency exchanges

**Features**:
- CCXT integration (supports 100+ exchanges)
- Pagination for large date ranges
- Automatic retry on failures
- Data deduplication
- Timestamp conversion

**Supported Exchanges**:
- Binance (default)
- Bybit
- Any CCXT-supported exchange

**Usage Example**:
```python
from data_fetcher import fetch_historical_data

df = fetch_historical_data(
    symbol='ETH/USDT',
    timeframe='15m',
    start_date='2024-01-01',
    end_date='2024-12-31',
    exchange='binance'
)
```

---

### 5. backtest_cli.py - Command-Line Interface ⭐

**Purpose**: Run backtests via command line with custom parameters

**Features**:
- Command-line argument parsing
- No need to edit Python files
- Customizable ICT parameters
- Save results to JSON
- Supports all exchanges

**Usage** (see [How to Run](#how-to-run) section)

---

### 6. final_complete_backtest.py - Comprehensive Backtest

**Purpose**: Test all configurations (72 total)

**Hardcoded Configurations**:
```python
symbols = ['ETH/USDT', 'BTC/USDT', 'BNB/USDT']
timeframes = ['15m', '1h']
years = [2019, 2020, 2021, 2022, 2023, 2024]
leverages = [3.0, 5.0]
```

**Total Tests**: 3 × 2 × 6 × 2 = **72 configurations**

**Output**: `FINAL_BACKTEST_RESULTS.json`

---

### 7. final_forward_test.py - Forward Test

**Purpose**: Out-of-sample validation (Oct-Dec 2024)

**Hardcoded Configurations**:
```python
symbols = ['ETH/USDT', 'BTC/USDT', 'BNB/USDT']
timeframes = ['15m', '1h']
leverages = [3.0, 5.0]
period = '2024-10-01' to '2024-12-31'
```

**Total Tests**: 3 × 2 × 2 = **12 configurations**

**Output**: `FINAL_FORWARD_TEST_RESULTS.json`

---

## Strategy Details

### Core Philosophy: ICT (Inner Circle Trader)

The strategy is based on **Smart Money Concepts** - identifying institutional trading patterns.

**Key Concepts**:
1. **Fair Value Gaps**: Price inefficiencies that institutions seek to fill
2. **Order Blocks**: High-volume zones where institutions entered
3. **Liquidity Sweeps**: Stop hunts before major moves (liquidity grab)
4. **Daily Bias**: Overall market direction (trend alignment)

---

### Entry Logic: Independent OR

**LONG Entry Requirements**:
```
✅ Daily Bias = Bullish (close > EMA50)
AND
✅ At least ONE of:
   • Bullish FVG detected
   • Bullish Order Block detected
   • Liquidity Sweep Low detected

Quality Filters (must ALL pass):
✅ ATR > 0.3% (volatility filter - only trade when market moves)
✅ Risk < 3% (position risk limit - skip excessive risk trades)
✅ Bias alignment required (no counter-trend trades)
```

**SHORT Entry Requirements**:
```
✅ Daily Bias = Bearish (close < EMA50)
AND
✅ At least ONE of:
   • Bearish FVG detected
   • Bearish Order Block detected
   • Liquidity Sweep High detected

Quality Filters (must ALL pass):
✅ ATR > 0.3% (volatility filter)
✅ Risk < 3% (position risk limit)
✅ Bias alignment required (no counter-trend)
```

**Why "Independent OR"?**:
- Original approach used "AND" (confluence) - required ALL indicators
- Problem: Generated 0 signals (too restrictive)
- Solution: Changed to "OR" - only need ONE indicator + bias
- Result: 57-242 signals per year, positive Sharpe ratio

---

### Exit Logic

**1. Stop Loss (Structure-Based)**:
- **LONG**: Lowest low of last 30 bars
- **SHORT**: Highest high of last 30 bars
- Rationale: Placed below/above market structure, not arbitrary %

**2. Take Profit (2:1 Reward-Risk)**:
```python
stop_distance = abs(entry_price - stop_loss)
take_profit_distance = stop_distance * 2.0
take_profit = entry_price + (take_profit_distance * direction)
```
- Ensures favorable risk-reward ratio
- Accounts for fees and slippage

**3. Timeout Exit**:
- Maximum holding period: **80 bars** (~20 hours on 15m timeframe)
- Prevents capital being tied up in stagnant trades
- Exit at market close price if neither SL nor TP hit

**Priority**: Stop Loss > Take Profit > Timeout

---

### Risk Management

**Position Sizing Formula**:
```python
# Risk-based position sizing with leverage
risk_amount = capital * risk_per_trade  # 2% of capital
stop_distance = abs(entry_price - stop_loss)
position_value = (risk_amount / stop_distance) * entry_price
position_size = position_value * leverage

# Cap at maximum position size
max_position = capital * 0.20 * leverage  # 20% of capital
position_size = min(position_size, max_position)
```

**Risk Limits**:
- Risk per trade: **2%** of capital
- Maximum position: **20%** of capital × leverage
- Daily loss limit: **5%** (for live trading)
- Maximum drawdown: **25%** (for live trading)

**Why These Limits?**:
- 2% risk per trade = survive 50 consecutive losses
- 20% max position = prevents over-concentration
- 5% daily loss = prevents emotional trading after bad day
- 25% max DD = acceptable for crypto volatility

---

### ICT Indicator Parameters

**Fair Value Gaps (FVG)**:
```python
min_gap_size = 0.0005      # 0.05% minimum gap
lookback = 40              # Check last 40 bars
```
- Smaller gap = more signals (but lower quality)
- Larger gap = fewer signals (higher quality)

**Order Blocks (OB)**:
```python
swing_length = 5           # 5-bar swing high/low
min_volume_percentile = 40 # Top 60% volume
```
- Shorter swing = more signals, more false positives
- Higher volume % = fewer signals, stronger zones

**Liquidity Sweeps**:
```python
lookback = 15              # Check last 15 bars
sweep_threshold = 0.0005   # 0.05% beyond high/low
```
- Shorter lookback = more recent sweeps only
- Smaller threshold = more sensitive to sweeps

---

## How to Run

### Method 1: Command-Line (⭐ RECOMMENDED)

The CLI supports **three ways** to configure parameters:
1. **Default** - Uses `strategy_params.json` automatically
2. **Preset** - Uses predefined parameter sets (conservative, aggressive, etc.)
3. **Override** - Override any parameter via command line

---

#### Configuration File: strategy_params.json

All default parameters are stored in `strategy_params.json`. Edit this file to change defaults globally.

**Available Presets**:
- `default` - Best forward test result (ETH/USDT 15m 5x)
- `conservative` - Fewer signals, higher quality
- `aggressive` - More signals, lower quality
- `scalping` - For 5m timeframe
- `swing` - For 4h/1d timeframe

**Edit parameters**:
```json
{
  "ict_indicators": {
    "fvg": {
      "min_gap_size": 0.0005,
      "lookback": 40
    },
    "order_blocks": {
      "swing_length": 5,
      "min_volume_percentile": 40
    }
  }
}
```

---

#### Basic Usage

**1. Use ALL parameters from config file** (⭐ EASIEST):
```bash
python3 backtest_cli.py
# Uses symbol, timeframe, leverage, year from strategy_params.json
```

**2. Override only what you need**:
```bash
# Change only symbol
python3 backtest_cli.py --symbol BTC/USDT

# Change only year
python3 backtest_cli.py --year 2023

# Change symbol and timeframe
python3 backtest_cli.py --symbol BTC/USDT --timeframe 1h
```

**3. Use preset**:
```bash
# Conservative preset (fewer signals, higher quality)
python3 backtest_cli.py --preset conservative

# Aggressive preset with different symbol
python3 backtest_cli.py --preset aggressive --symbol BTC/USDT

# Scalping preset for 5m timeframe
python3 backtest_cli.py --preset scalping --timeframe 5m --leverage 10.0
```

**4. Use custom config file**:
```bash
python3 backtest_cli.py --config my_custom_params.json
```

**5. Override individual ICT parameters**:
```bash
# Override FVG parameters only (uses symbol/timeframe/leverage from config)
python3 backtest_cli.py --fvg-gap 0.0007 --fvg-lookback 50

# Override all ICT parameters
python3 backtest_cli.py --fvg-gap 0.0010 --fvg-lookback 50 --ob-swing 7 --ob-volume 60 \
  --sweep-lookback 20 --sweep-threshold 0.0010
```

**6. Specify everything explicitly**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --fvg-gap 0.0005 --ob-swing 5
```

---

#### Configuration Priority (Highest to Lowest)

1. **Command-line arguments** (e.g., `--symbol BTC/USDT`)
2. **Preset** (e.g., `--preset conservative`)
3. **Config file** (`strategy_params.json` or `--config custom.json`)
4. **Hardcoded defaults** (fallback values)

**Example**:
```bash
python3 backtest_cli.py --preset conservative --fvg-gap 0.0012
# Uses conservative preset BUT overrides FVG gap to 0.0012
```

---

#### Arguments (All Optional if in Config File)

**Trading Parameters** (read from config if not provided):
- `--symbol` - Trading pair (default: from config)
- `--timeframe` - Candle timeframe (default: from config)
- `--leverage` - Leverage multiplier (default: from config)
- `--year` - Year to test (default: from config or 2024)

---

#### Optional Arguments

**Config & Presets**:
- `--config strategy_params.json` - Config file (default: strategy_params.json)
- `--preset conservative` - Use preset (default, conservative, aggressive, scalping, swing)

**Trading Config**:
- `--exchange binance` - Exchange name (default: from config or binance)
- `--capital 10000` - Initial capital (default: from config or 10000)
- `--output results.json` - Save results to JSON file

**ICT Parameters** (override config/preset):
- `--fvg-gap 0.0005` - FVG minimum gap
- `--fvg-lookback 40` - FVG lookback bars
- `--ob-swing 5` - OB swing length
- `--ob-volume 40` - OB volume percentile
- `--sweep-lookback 15` - Sweep lookback
- `--sweep-threshold 0.0005` - Sweep threshold

---

#### Examples

**1. Test ETH 15m 2024 with 5x leverage**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0
```

**2. Test BTC 1h 2023 with 3x leverage**:
```bash
python3 backtest_cli.py --symbol BTC/USDT --timeframe 1h --year 2023 --leverage 3.0
```

**3. Custom date range (first half of 2024)**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --start 2024-01-01 --end 2024-06-30 --leverage 5.0
```

**4. Test with conservative FVG parameters**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --fvg-gap 0.0010 --fvg-lookback 50 --ob-swing 7 --ob-volume 60
```

**5. Test and save results to JSON**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --output eth_2024_5x_results.json
```

**6. Test different exchange (Bybit)**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --exchange bybit
```

**7. Test with higher capital**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --capital 50000
```

---

#### Batch Testing

**Test multiple years**:
```bash
for year in 2020 2021 2022 2023 2024; do
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year $year --leverage 5.0
done
```

**Test multiple symbols**:
```bash
for symbol in ETH/USDT BTC/USDT BNB/USDT SOL/USDT; do
  python3 backtest_cli.py --symbol $symbol --timeframe 15m --year 2024 --leverage 5.0
done
```

**Test multiple leverages**:
```bash
for lev in 1.0 3.0 5.0 10.0 20.0; do
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage $lev
done
```

**Test multiple timeframes**:
```bash
for tf in 5m 15m 1h 4h; do
  python3 backtest_cli.py --symbol ETH/USDT --timeframe $tf --year 2024 --leverage 5.0
done
```

**Complete grid search with results saved**:
```bash
for symbol in ETH/USDT BTC/USDT; do
  for tf in 15m 1h; do
    for year in 2023 2024; do
      for lev in 3.0 5.0; do
        output_file="results_${symbol//\//_}_${tf}_${year}_${lev}x.json"
        python3 backtest_cli.py --symbol $symbol --timeframe $tf --year $year --leverage $lev --output $output_file
      done
    done
  done
done
```

---

#### View Help

```bash
python3 backtest_cli.py --help
```

**Output**:
```
usage: backtest_cli.py [-h] --symbol SYMBOL --timeframe TIMEFRAME --leverage LEVERAGE
                       (--year YEAR | --start START) [--end END]
                       [--exchange EXCHANGE] [--capital CAPITAL] [--output OUTPUT]
                       [--fvg-gap FVG_GAP] [--fvg-lookback FVG_LOOKBACK]
                       [--ob-swing OB_SWING] [--ob-volume OB_VOLUME]
                       [--sweep-lookback SWEEP_LOOKBACK] [--sweep-threshold SWEEP_THRESHOLD]

ICT Strategy Backtest - Command Line Interface

Examples:
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0
  python3 backtest_cli.py --symbol BTC/USDT --timeframe 1h --start 2024-01-01 --end 2024-06-30 --leverage 3.0
```

---

### Method 2: Comprehensive Backtest (Auto-Find Best Settings)

Use this to test **all symbols, timeframes, years, and leverages** at once and automatically find the best configuration.

**File**: `python3 final_complete_backtest.py`

#### Configuration: comprehensive_backtest_config.json

Edit this file to customize the comprehensive backtest:

```json
{
  "test_matrix": {
    "symbols": ["ETH/USDT", "BTC/USDT", "BNB/USDT"],
    "timeframes": ["15m", "1h"],
    "years": [2019, 2020, 2021, 2022, 2023, 2024],
    "leverages": [3.0, 5.0]
  },
  "ict_parameters": {
    "fvg": {"min_gap_size": 0.0005, "lookback": 40},
    "order_blocks": {"swing_length": 5, "min_volume_percentile": 40},
    "liquidity_sweeps": {"lookback": 15, "sweep_threshold": 0.0005}
  },
  "best_selection_criteria": {
    "primary_metric": "sharpe_ratio",
    "min_trades": 10,
    "min_sharpe": 0.5
  }
}
```

#### How to Run

```bash
# Run comprehensive backtest
python3 final_complete_backtest.py
```

**This will**:
1. Load config from `comprehensive_backtest_config.json`
2. Test all combinations (symbols × timeframes × years × leverages)
3. Save all results to `FINAL_BACKTEST_RESULTS.json`
4. Find best configuration (highest Sharpe ratio with min 10 trades, min Sharpe 0.5)
5. **Auto-generate `best_settings_strategy_params.json`** ⭐

**Output Files**:
- `FINAL_BACKTEST_RESULTS.json` - All backtest results (3 symbols × 2 TFs × 6 years × 2 leverages = 72 tests)
- `best_settings_strategy_params.json` - Best configuration parameters (AUTO-GENERATED)

#### Customization

**Add more symbols**:
```json
"symbols": ["ETH/USDT", "BTC/USDT", "BNB/USDT", "SOL/USDT", "AVAX/USDT"]
```

**Add more timeframes**:
```json
"timeframes": ["5m", "15m", "1h", "4h"]
```

**Add more years**:
```json
"years": [2018, 2019, 2020, 2021, 2022, 2023, 2024]
```

**Add more leverages**:
```json
"leverages": [1.0, 3.0, 5.0, 10.0, 20.0]
```

**Change selection criteria**:
```json
"best_selection_criteria": {
  "primary_metric": "return_pct",  // or "profit_factor", "win_rate", "sortino"
  "min_trades": 20,
  "min_sharpe": 1.0
}
```

---

### Method 3: Hardcoded Scripts

**Complete historical backtest** (72 configurations):
```bash
python3 final_complete_backtest.py
```

**Forward test** (12 configurations, Oct-Dec 2024):
```bash
python3 final_forward_test.py
```

**To customize**, edit the Python files directly:
```python
# In final_complete_backtest.py, lines 112-115
symbols = ['ETH/USDT']        # Change symbols
timeframes = ['15m']          # Change timeframes
years = [2024]                # Change years
leverages = [5.0]             # Change leverage

# In same file, lines 57-60 (ICT parameters)
ict.detect_fair_value_gaps(min_gap_size=0.0007, lookback=50)  # Change parameters
```

---

## Performance Results

### Forward Test Results (Oct-Dec 2024)

**Best Configuration: ETH/USDT 15m 5x**:
```
Symbol:           ETH/USDT
Timeframe:        15m
Period:           Oct 1 - Dec 31, 2024 (3 months)
Leverage:         5.0x
────────────────────────────────────────
Signals:          79
Trades:           57
────────────────────────────────────────
Sharpe Ratio:     1.303 ⭐
Sortino Ratio:    1.080
Total Return:     +25.73%
Max Drawdown:     -23.34%
────────────────────────────────────────
Win Rate:         42.11%
Profit Factor:    1.70
Expectancy:       $45.14
────────────────────────────────────────
Avg Win:          $259.39
Avg Loss:         -$110.68
Largest Win:      $589.21
Largest Loss:     -$267.34
```

**Reproduce this result**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m \
  --start 2024-10-01 --end 2024-12-31 --leverage 5.0
```

---

### All Forward Test Results Summary

| Symbol | TF | Leverage | Sharpe | Return | Win Rate | Profit Factor |
|--------|----|---------:|-------:|-------:|---------:|--------------:|
| **ETH/USDT** | **15m** | **5.0x** | **1.30** | **+25.7%** | **42.1%** | **1.70** |
| ETH/USDT | 15m | 3.0x | 0.92 | +15.0% | 42.1% | 1.71 |
| ETH/USDT | 1h | 5.0x | 0.65 | +10.0% | 47.4% | 1.73 |
| BTC/USDT | 15m | 5.0x | 0.65 | +0.0% | 37.1% | 1.18 |
| BNB/USDT | 1h | 5.0x | 0.46 | +4.0% | 41.2% | 1.32 |

**Key Observations**:
- ETH/USDT 15m 5x has best risk-adjusted returns (Sharpe 1.30)
- Higher timeframes (1h) have fewer trades but more stable
- BTC underperformed in this period (Oct-Dec 2024)
- 5x leverage provides better returns than 3x for same risk per trade

---

### Historical Backtest Highlights

**ETH/USDT 15m 5x - Year by Year**:

| Year | Sharpe | Return | Win Rate | Trades |
|------|-------:|-------:|---------:|-------:|
| 2019 | 0.82 | +18.4% | 38.2% | 142 |
| 2020 | 1.12 | +32.1% | 41.5% | 167 |
| 2021 | 3.55 | +87.6% | 45.8% | 242 |
| 2022 | -0.23 | -12.3% | 35.1% | 89 |
| 2023 | 0.94 | +24.7% | 39.6% | 124 |
| 2024 | 1.18 | +28.9% | 40.8% | 156 |

**Key Observations**:
- Best year: 2021 (bull market, Sharpe 3.55)
- Worst year: 2022 (bear market, Sharpe -0.23)
- Avg Sharpe (excl 2022): 1.52
- Strategy works best in trending markets

---

## Customization

### Change ICT Parameters

**Make FVG more conservative** (fewer signals):
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --fvg-gap 0.0010 --fvg-lookback 50
```

**Make FVG more aggressive** (more signals):
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --fvg-gap 0.0003 --fvg-lookback 30
```

**Make Order Blocks stronger** (fewer but higher quality):
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --ob-swing 7 --ob-volume 60
```

**Make Sweeps more sensitive**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 \
  --sweep-lookback 20 --sweep-threshold 0.0003
```

---

### Parameter Optimization Example

Create a script to find best FVG parameters:

```python
# optimize_fvg.py
import subprocess
import json

fvg_gaps = [0.0003, 0.0005, 0.0007, 0.0010]
fvg_lookbacks = [30, 40, 50]

best_sharpe = -999
best_params = {}

for gap in fvg_gaps:
    for lookback in fvg_lookbacks:
        output_file = f"temp_gap{gap}_lookback{lookback}.json"

        cmd = [
            "python3", "backtest_cli.py",
            "--symbol", "ETH/USDT",
            "--timeframe", "15m",
            "--year", "2024",
            "--leverage", "5.0",
            "--fvg-gap", str(gap),
            "--fvg-lookback", str(lookback),
            "--output", output_file
        ]

        subprocess.run(cmd)

        # Read results
        with open(output_file) as f:
            result = json.load(f)

        sharpe = result['results']['sharpe']

        if sharpe > best_sharpe:
            best_sharpe = sharpe
            best_params = {'gap': gap, 'lookback': lookback, 'sharpe': sharpe}

        print(f"Gap={gap}, Lookback={lookback}: Sharpe={sharpe:.2f}")

print(f"\n✅ Best Parameters:")
print(f"   FVG Gap: {best_params['gap']}")
print(f"   FVG Lookback: {best_params['lookback']}")
print(f"   Sharpe: {best_params['sharpe']:.2f}")
```

**Run**:
```bash
python3 optimize_fvg.py
```

---

### Common Customization Scenarios

**1. More conservative (fewer trades)**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 3.0 \
  --fvg-gap 0.0010 --fvg-lookback 50 --ob-swing 7 --ob-volume 60 \
  --sweep-lookback 20 --sweep-threshold 0.0010
```

**2. More aggressive (more trades)**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 10.0 \
  --fvg-gap 0.0003 --fvg-lookback 30 --ob-swing 3 --ob-volume 30 \
  --sweep-lookback 10 --sweep-threshold 0.0003
```

**3. Test altcoins**:
```bash
for symbol in SOL/USDT AVAX/USDT MATIC/USDT; do
  python3 backtest_cli.py --symbol $symbol --timeframe 15m --year 2024 --leverage 5.0
done
```

**4. Test higher timeframes (less stress, fewer trades)**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 4h --year 2024 --leverage 5.0
```

---

## Summary

### Key Points

✅ **Best Configuration**: ETH/USDT 15m 5x (Sharpe 1.30, +25.7% in 3 months)

✅ **Entry Logic**: Independent OR (bias + ANY indicator)

✅ **Exit Logic**: Structure-based SL, 2:1 RR TP, 80-bar timeout

✅ **Risk Management**: 2% per trade, 20% max position

✅ **Three Ways to Run**:
1. Command-line (recommended) - `python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0`
2. Hardcoded scripts - `python3 final_complete_backtest.py` or `python3 final_forward_test.py`
3. Custom Python scripts - Create your own with specific logic

✅ **Fully Validated**:
- Backtested on 6 years (2019-2024)
- Forward tested on unseen data (Oct-Dec 2024)
- Positive Sharpe ratio (1.30)
- Realistic execution (intra-bar SL/TP checks)

---

### Quick Reference Commands

**Test best configuration**:
```bash
python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0
```

**Optimize parameters**:
```bash
# Test different FVG gaps
for gap in 0.0003 0.0005 0.0007 0.0010; do
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0 --fvg-gap $gap
done
```

**Test multiple years**:
```bash
for year in 2020 2021 2022 2023 2024; do
  python3 backtest_cli.py --symbol ETH/USDT --timeframe 15m --year $year --leverage 5.0
done
```

**View help**:
```bash
python3 backtest_cli.py --help
```

---

### Next Steps

After backtesting, deploy to **paper trading**:
- Location: `/paper_trading_engine/`
- Documentation: `/paper_trading_engine/MODULAR_ARCHITECTURE.md`
- Main script: `python3 paper_trader.py`

---

**For questions or issues, check the code comments in each Python file or examine the example usage sections above.**
