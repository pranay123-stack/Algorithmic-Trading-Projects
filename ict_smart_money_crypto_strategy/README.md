# ICT Smart Money Crypto Strategy

A production-grade cryptocurrency trading system implementing **Inner Circle Trader (ICT) / Smart Money Concepts (SMC)** methodology. The project includes a full backtesting engine and a real-time paper trading engine, both built for Binance Futures via CCXT.

---

## Table of Contents

- [Overview](#overview)
- [Strategy Logic](#strategy-logic)
- [Project Structure](#project-structure)
- [Backtest Engine](#backtest-engine)
- [Paper Trading Engine](#paper-trading-engine)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Performance](#performance)
- [Testing](#testing)
- [Architecture](#architecture)
- [License](#license)

---

## Overview

This system detects institutional order flow patterns — Fair Value Gaps, Order Blocks, and Liquidity Sweeps — combined with EMA-based directional bias to generate high-probability trade entries on crypto futures. It enforces strict risk management (position sizing, daily loss limits, drawdown monitoring) and supports multi-symbol, multi-timeframe backtesting across years of historical data.

### Key Features

- **ICT/SMC Indicators**: Fair Value Gaps, Order Blocks, Liquidity Sweeps, SMT Divergence, Higher-Timeframe POI
- **Dual Engines**: Historical backtesting + live paper trading
- **Multi-Asset Support**: BTC/USDT, ETH/USDT, BNB/USDT (extensible)
- **Multi-Timeframe**: 15m and 1h candles with HTF alignment
- **Risk Management**: Per-trade sizing, daily loss ceiling, max drawdown alerts
- **CLI Interface**: Configurable backtests with presets (conservative, aggressive, scalping, swing)
- **Hot-Reload Config**: Paper trader picks up config changes without restart
- **Comprehensive Logging**: Color-coded console + file-based debug logs
- **Test Suite**: Unit tests for indicators, strategy, and risk management

---

## Strategy Logic

### Entry Conditions (ALL required)

| Condition | Long | Short |
|-----------|------|-------|
| **Directional Bias** | Price > EMA-50 | Price < EMA-50 |
| **Technical Confirmation** (at least one) | Bullish FVG, Bullish OB, or Bullish Liquidity Sweep | Bearish FVG, Bearish OB, or Bearish Liquidity Sweep |
| **Volatility Filter** | ATR >= 0.3% | ATR >= 0.3% |
| **Risk Filter** | Position risk <= 3% of capital | Position risk <= 3% of capital |

### Exit Rules (Priority Order)

1. **Stop Loss** — Structure-based using 30-candle lookback + 0.3% buffer; checked intra-bar
2. **Take Profit** — 2:1 reward-to-risk ratio target
3. **Timeout** — 80 bars maximum holding period (~20 hours on 15m)

### ICT Indicators Explained

| Indicator | Description |
|-----------|-------------|
| **Fair Value Gap (FVG)** | 3-candle pattern where a gap exists between candle 1's low and candle 3's high (bullish) or candle 1's high and candle 3's low (bearish). Minimum gap size: 0.05% |
| **Order Block (OB)** | Swing high/low zones with above-average volume, representing institutional accumulation/distribution areas. Swing length: 5 bars |
| **Liquidity Sweep** | Price briefly exceeds recent highs/lows then reverses — a stop-hunt pattern. Lookback: 15 candles |
| **Daily Bias** | EMA-50 and EMA-200 crossover to determine bullish/bearish market structure |
| **SMT Divergence** | Divergence between correlated assets (e.g., BTC vs ETH) signaling potential reversals |

---

## Project Structure

```
ict_smart_money_crypto_strategy/
├── backtest_engine/
│   ├── ict_indicators.py          # ICT indicator calculations
│   ├── strategy_final.py          # Signal generation engine
│   ├── backtester.py              # Simulation framework with metrics & visualization
│   ├── data_fetcher.py            # CCXT data retrieval with pagination
│   ├── backtest_cli.py            # Command-line interface
│   ├── final_complete_backtest.py # 72-configuration automated test suite
│   ├── final_forward_test.py      # Out-of-sample validation (Oct-Dec 2024)
│   ├── strategy_params.json       # Default + preset parameters
│   ├── best_settings_strategy_params.json
│   ├── comprehensive_backtest_config.json
│   ├── BACKTEST_ARCHITECTURE.md
│   ├── FINAL_BACKTEST_RESULTS.json
│   └── requirements.txt
│
└── paper_trading_engine/
    ├── run.py                     # Entry point
    ├── config.yaml                # Trading parameters
    ├── requirements.txt
    ├── src/
    │   ├── config/
    │   │   └── config_loader.py   # YAML loader with hot-reload
    │   ├── core_trading_strategy/
    │   │   ├── paper_trader.py    # Main orchestrator (aligned scheduler)
    │   │   ├── indicators.py      # ICT technical analysis
    │   │   ├── strategy.py        # Signal generation
    │   │   ├── data_manager.py    # CCXT market data operations
    │   │   ├── risk_management.py # Position sizing & limits
    │   │   ├── order_management.py# Order lifecycle simulation
    │   │   ├── position_management.py # Trade tracking & P&L
    │   │   ├── entry_management.py# Entry validation & execution
    │   │   ├── exit_management.py # SL/TP/Timeout exit logic
    │   │   └── market_utils.py    # Shared calculations
    │   └── logger/
    │       └── logger.py          # Color-coded logging system
    ├── docs/
    │   ├── ARCHITECTURE.md
    │   ├── FINAL_STRUCTURE.md
    │   ├── QUICK_REFERENCE.md
    │   └── REFACTORING_SUMMARY.md
    └── tests/
        ├── test_indicators.py
        ├── test_strategy.py
        ├── test_risk_management.py
        └── run_all_tests.py
```

---

## Backtest Engine

### What It Does

- Fetches historical OHLCV data from Binance Futures via CCXT
- Calculates ICT indicators across multiple timeframes
- Generates entry/exit signals with quality filters
- Simulates trades with intra-bar execution, slippage, and commissions
- Produces 16 performance metrics and 6-panel visualization charts

### Metrics Computed

Sharpe Ratio, Sortino Ratio, Total Return, Win Rate, Profit Factor, Max Drawdown, Average Win/Loss, Total Trades, Monthly Returns Heatmap, Equity Curve, Drawdown Chart, and more.

### Comprehensive Test Matrix

The `final_complete_backtest.py` script runs **72 configurations** automatically:

- **3 Symbols**: BTC/USDT, ETH/USDT, BNB/USDT
- **2 Timeframes**: 15m, 1h
- **6 Years**: 2019–2024
- **2 Leverage Levels**: 3x, 5x

It then selects the optimal configuration based on Sharpe ratio.

---

## Paper Trading Engine

### What It Does

- Connects to Binance (or testnet) in real time
- Fetches live OHLCV candles aligned to minute boundaries
- Runs the full ICT strategy on each new candle
- Manages positions with simulated order fills, slippage (0.05%), and commissions (0.04%)
- Exports trade history as JSON/CSV with session timestamps

### Execution Loop

```
1. Align to next candle boundary
2. Fetch OHLCV data + calculate indicators
3. Detect new candle arrival
4. Check exit conditions (SL → TP → Timeout)
5. Generate and validate entry signals
6. Execute orders with position sizing
7. Log state and sleep until next candle
```

---

## Installation

### Prerequisites

- Python 3.10+
- pip

### Backtest Engine

```bash
cd ict_smart_money_crypto_strategy/backtest_engine
pip install -r requirements.txt
```

**Dependencies**: ccxt, pandas, numpy, matplotlib, seaborn, scipy, ta-lib, vectorbt, plotly

### Paper Trading Engine

```bash
cd ict_smart_money_crypto_strategy/paper_trading_engine
pip install -r requirements.txt
```

**Dependencies**: ccxt==4.2.25, pandas==2.2.0, numpy==1.26.3, python-dotenv, requests, pyyaml

> **Note**: TA-Lib requires a system-level installation. On Ubuntu: `sudo apt-get install ta-lib`. On macOS: `brew install ta-lib`.

---

## Usage

### Run a Backtest

```bash
# Default: ETH/USDT, 15m, 2024, 5x leverage
cd backtest_engine
python3 backtest_cli.py

# Custom parameters
python3 backtest_cli.py --symbol BTC/USDT --timeframe 1h --year 2023 --leverage 3.0

# Use a preset
python3 backtest_cli.py --preset conservative

# Export results to JSON
python3 backtest_cli.py --export results.json
```

### Run the Comprehensive Backtest (72 configs)

```bash
python3 final_complete_backtest.py
```

### Run Forward Testing

```bash
python3 final_forward_test.py
```

### Start Paper Trading

```bash
cd paper_trading_engine

# Edit config.yaml with your settings, then:
python3 run.py
```

### Run Tests

```bash
cd paper_trading_engine
python3 -m pytest tests/
# or
python3 tests/run_all_tests.py
```

---

## Configuration

### Paper Trading (`config.yaml`)

```yaml
exchange:
  name: binance
  testnet: false

trading:
  symbol: ETH/USDT
  timeframe: 15m
  leverage: 5
  initial_capital: 10000

risk:
  risk_per_trade: 0.02        # 2% per trade
  max_position_pct: 0.20      # 20% max position
  daily_loss_limit: 0.05      # 5% daily loss ceiling
  max_drawdown: 0.25          # 25% drawdown alert

indicators:
  fvg_min_size: 0.0005        # 0.05% minimum FVG
  ob_swing_length: 5
  sweep_lookback: 15
  ema_period: 50

strategy:
  min_atr_pct: 0.003          # 0.3% minimum ATR
  max_risk_pct: 0.03          # 3% max risk filter
  max_holding_bars: 80
  stop_buffer_pct: 0.003      # 0.3% stop loss buffer
```

### Backtest Presets (`strategy_params.json`)

| Preset | Risk/Trade | Leverage | Max Holding | Min ATR |
|--------|-----------|----------|-------------|---------|
| **Conservative** | 1% | 2x | 40 bars | 0.5% |
| **Aggressive** | 3% | 10x | 120 bars | 0.2% |
| **Scalping** | 1.5% | 5x | 20 bars | 0.1% |
| **Swing** | 2% | 3x | 200 bars | 0.3% |

---

## Performance

### Forward Test Results (Oct–Dec 2024, ETH/USDT 15m, 5x leverage)

| Metric | Value |
|--------|-------|
| **Total Return** | +25.7% |
| **Sharpe Ratio** | 1.30 |
| **Sortino Ratio** | 1.84 |
| **Win Rate** | 42.1% |
| **Profit Factor** | 1.70 |
| **Total Trades** | 249 |
| **Max Drawdown** | 28.2%–40.4% |

### Best Optimized Settings

| Metric | Value |
|--------|-------|
| **Sharpe Ratio** | 2.38 |
| **Sortino Ratio** | 1.84 |
| **Total Trades** | 249 |
| **Return** | +7.28% |

---

## Testing

The test suite covers three core domains:

| Test File | Coverage |
|-----------|----------|
| `test_indicators.py` | FVG detection, Order Blocks, Liquidity Sweeps, ATR, Daily Bias, edge cases |
| `test_strategy.py` | Signal generation (LONG/SHORT), risk calculations, filter validation |
| `test_risk_management.py` | Position sizing, capital tracking, drawdown monitoring, leverage, edge cases |

```bash
cd paper_trading_engine
python3 -m unittest discover tests/
```

---

## Architecture

### Design Principles

| Principle | Implementation |
|-----------|---------------|
| **Modular Design** | 8 specialized trading modules with clear boundaries |
| **Manager Pattern** | Dedicated managers for orders, positions, entries, exits, and risk |
| **Dependency Injection** | Testable, loosely coupled components |
| **Singleton Pattern** | Configuration and logging services |
| **Hot-Reload** | Config changes applied without restart |
| **Separation of Concerns** | Trading logic fully decoupled from infrastructure |

### Data Flow

```
Binance API (CCXT)
    │
    ▼
DataManager (fetch OHLCV)
    │
    ▼
Indicators (FVG, OB, Sweep, Bias)
    │
    ▼
Strategy (signal generation + filters)
    │
    ▼
EntryManager (validation + execution)
    │
    ▼
OrderManager (fill simulation)
    │
    ▼
PositionManager (P&L tracking)
    │
    ▼
ExitManager (SL / TP / Timeout)
    │
    ▼
RiskManager (sizing, limits, drawdown)
```

---

## Disclaimer

This software is for **educational and research purposes only**. Cryptocurrency trading involves substantial risk of loss. Past performance (backtested or paper-traded) does not guarantee future results. Do not trade with money you cannot afford to lose. Always do your own research before making any trading decisions.

---

## License

This project is open source. See the repository for license details.
