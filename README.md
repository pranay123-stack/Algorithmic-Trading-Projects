# Algorithmic Trading Projects

A collection of **20+ cryptocurrency algorithmic trading strategies** spanning backtesting engines, paper-trading systems, and live-trading bots across multiple exchanges.

> **Disclaimer:** These projects are for **educational and research purposes only**. Cryptocurrency trading involves substantial risk of loss. Past performance does not guarantee future results. Use at your own risk.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Projects](#projects)
  - [1. ICT Smart Money Strategy](#1-ict-smart-money-strategy)
    - [1.1 Backtest Engine](#11-backtest-engine)
    - [1.2 Paper Trading Engine](#12-paper-trading-engine)
  - [2. Live Trading Bots — Phemex](#2-live-trading-bots--phemex)
    - [2.1 SMA Strategy](#21-sma-strategy)
    - [2.2 RSI Strategy](#22-rsi-strategy)
    - [2.3 VWAP Strategy](#23-vwap-strategy)
    - [2.4 Mean Reversion (74 Tickers)](#24-mean-reversion-74-tickers)
    - [2.5 Arbitrage Bot](#25-arbitrage-bot)
    - [2.6 Market Maker Bot](#26-market-maker-bot)
    - [2.7 Turtle Trending Algo](#27-turtle-trending-algo)
    - [2.8 Correlation Algo](#28-correlation-algo)
    - [2.9 Consolidation Pop Algo](#29-consolidation-pop-algo)
    - [2.10 Nadaraya-Watson Algo](#210-nadaraya-watson-algo)
  - [3. Live Trading Bots — HyperLiquid DEX](#3-live-trading-bots--hyperliquid-dex)
    - [3.1 Bollinger Bands Bot](#31-bollinger-bands-bot)
    - [3.2 Supply & Demand Zones Bot](#32-supply--demand-zones-bot)
    - [3.3 VWAP Bot](#33-vwap-bot)
  - [4. Backtest-Only Strategies](#4-backtest-only-strategies)
- [Getting Started](#getting-started)
- [Configuration & API Keys](#configuration--api-keys)
- [Tech Stack](#tech-stack)
- [License](#license)

---

## Overview

| Category | Count | Exchange | Mode |
|----------|-------|----------|------|
| ICT Smart Money Engines | 2 | Binance | Backtest + Paper |
| Phemex Live Bots | 10 | Phemex | Live Trading |
| HyperLiquid DEX Bots | 3 | HyperLiquid | Live Trading |
| Backtest Strategies | 13 | — | Backtest Only |

**Indicators Used:** SMA, EMA, RSI, VWAP, MACD, Bollinger Bands, ATR, Stochastic RSI, Ichimoku, Elliott Waves, Fibonacci, ADX, Pivot Points, Fair Value Gaps, Order Blocks, Liquidity Sweeps, Nadaraya-Watson Kernel Smoother

---

## Repository Structure

```
Algorithmic-Trading-Projects/
│
├── ict_smart_money_crypto_strategy/
│   ├── backtest_engine/          # ICT/SMC backtesting system
│   │   ├── strategy_final.py     # Core strategy (FVG + OB + Sweeps)
│   │   ├── ict_indicators.py     # ICT indicator calculations
│   │   ├── backtester.py         # Backtest execution engine
│   │   ├── data_fetcher.py       # CCXT data acquisition
│   │   ├── backtest_cli.py       # CLI interface
│   │   └── requirements.txt
│   │
│   └── paper_trading_engine/     # Production paper trading
│       ├── src/
│       │   └── core_trading_strategy/
│       │       ├── paper_trader.py
│       │       ├── strategy.py
│       │       ├── indicators.py
│       │       ├── risk_management.py
│       │       ├── order_management.py
│       │       ├── position_management.py
│       │       └── telegram_bot.py
│       ├── config.yaml
│       ├── run.py
│       └── requirements.txt
│
├── crypto_strategies/
│   ├── sma_strategy.py           # SMA crossover
│   ├── rsi_strategy.py           # RSI overbought/oversold
│   ├── vwap_strategy.py          # VWAP trading
│   ├── mean_reversion_74_tickers.py  # Multi-symbol mean reversion
│   ├── arbitrage_bot.py          # Funding rate arbitrage
│   ├── nice_funcs.py             # Shared utility library
│   │
│   ├── market_maker_bot/         # Spread-capturing market maker
│   ├── bollinger_bands_bot/      # BB squeeze breakout
│   ├── supply_demand_zones_bot/  # S&D zone trading
│   ├── vwap_bot/                 # Probabilistic VWAP
│   ├── turtle_trending_algo/     # 55-bar breakout
│   ├── correlation_algo/         # Cross-asset correlation
│   ├── consolidation_pop_algo/   # Volatility breakout
│   ├── nadaraya_watson_algo/     # ML kernel smoother
│   │
│   ├── ai_backtest_strategies/   # 13 backtesting strategies
│   │   ├── bt_macd.py
│   │   ├── bt_rsi_vwap.py
│   │   ├── bt_bollinger_bands.py
│   │   ├── bt_ichimoku.py
│   │   ├── bt_adx.py
│   │   ├── bt_elliot_waves.py
│   │   ├── bt_grid_fibonacci.py
│   │   ├── bt_pivot_lines.py
│   │   ├── bt_quarter_theory.py
│   │   ├── bt_ema_bollinger.py
│   │   ├── bt_sma_adx_bollinger_volume.py
│   │   ├── bt_elliot_waves_pivot_lines.py
│   │   └── Bitcoin_Trading_Strategy.py
│   │
│   └── credentials.example.py   # API key template
│
├── .gitignore
└── README.md
```

---

## Projects

### 1. ICT Smart Money Strategy

An enterprise-grade trading system based on **Inner Circle Trader (ICT) / Smart Money Concepts (SMC)** methodology.

#### 1.1 Backtest Engine

**Path:** `ict_smart_money_crypto_strategy/backtest_engine/`

Historically replays and optimizes the ICT strategy across multiple symbols and timeframes.

**Strategy Logic:**
- **Fair Value Gaps (FVG):** Detects price imbalances between candles where institutional orders may rest
- **Order Blocks (OB):** Identifies zones of institutional order flow (last opposing candle before impulsive move)
- **Liquidity Sweeps:** Detects stop-hunt events and reversal confirmations
- **Bias Filter:** EMA-50 determines trend direction
- **Entry:** Bullish/Bearish bias + any one of FVG, OB, or Sweep signal
- **Stop Loss:** Structure-based (30-bar lookback swing high/low)
- **Take Profit:** 2:1 reward-to-risk ratio
- **Quality Filters:** ATR > 0.3%, Risk < 3% of capital

**Forward Test Results (Oct–Dec 2024):**
| Metric | Value |
|--------|-------|
| Return | +25.7% |
| Sharpe Ratio | 1.30 |
| Win Rate | 42.1% |
| Profit Factor | 1.70 |
| Max Drawdown | -12.3% |

**Quick Start:**
```bash
cd ict_smart_money_crypto_strategy/backtest_engine
pip install -r requirements.txt

# Single backtest
python backtest_cli.py --symbol ETH/USDT --timeframe 15m --year 2024 --leverage 5.0

# Full optimization scan
python final_complete_backtest.py

# Forward test on recent data
python final_forward_test.py
```

---

#### 1.2 Paper Trading Engine

**Path:** `ict_smart_money_crypto_strategy/paper_trading_engine/`

Production-ready paper trading system with modular architecture, real-time data, risk management, and Telegram alerts.

**Architecture (9 modules):**

| Module | Purpose |
|--------|---------|
| `paper_trader.py` | Main orchestrator, hot-reload config |
| `indicators.py` | FVG, Order Block, Liquidity Sweep calculations |
| `strategy.py` | Signal generation with quality filters |
| `risk_management.py` | Position sizing, daily loss limits, drawdown alerts |
| `order_management.py` | Limit/market/stop order execution |
| `position_management.py` | Active position tracking and P&L |
| `entry_management.py` | Entry validation and timing |
| `exit_management.py` | TP/SL monitoring, timeout exits (80 bars max) |
| `telegram_bot.py` | Real-time trade alerts and daily summaries |

**Risk Controls:**
- Per-trade risk: 1–2% (configurable)
- Daily loss limit: 5%
- Max drawdown alert: 25%
- Configurable leverage

**Quick Start:**
```bash
cd ict_smart_money_crypto_strategy/paper_trading_engine
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python run.py
```

---

### 2. Live Trading Bots — Phemex

These bots trade perpetual futures on **Phemex** exchange via CCXT.

#### 2.1 SMA Strategy
**File:** `crypto_strategies/sma_strategy.py`

Simple Moving Average crossover bot with kill switch.

| Detail | Value |
|--------|-------|
| Indicator | SMA-20 |
| Symbol | uBTCUSD (configurable) |
| Logic | Long when price > SMA-20, Short when price < SMA-20 |
| Features | Kill switch, position tracking, scheduled execution |

---

#### 2.2 RSI Strategy
**File:** `crypto_strategies/rsi_strategy.py`

Relative Strength Index overbought/oversold trading.

| Detail | Value |
|--------|-------|
| Indicators | RSI (14), SMA |
| Symbol | uBTCUSD |
| Long Signal | RSI < 30 (oversold) |
| Short Signal | RSI > 70 (overbought) |

---

#### 2.3 VWAP Strategy
**File:** `crypto_strategies/vwap_strategy.py`

Volume-Weighted Average Price trading with PostOnly limit orders.

| Detail | Value |
|--------|-------|
| Indicators | VWAP, SMA, RSI |
| Symbol | uBTCUSD |
| Order Type | PostOnly limit orders (maker rebates) |
| Logic | Price interaction with VWAP + RSI confirmation |

---

#### 2.4 Mean Reversion (74 Tickers)
**File:** `crypto_strategies/mean_reversion_74_tickers.py`

Multi-symbol scanner that trades mean reversion across 74 cryptocurrency pairs simultaneously.

| Detail | Value |
|--------|-------|
| Indicator | SMA-20 (96-candle lookback) |
| Symbols | 74 crypto pairs (auto-scanned) |
| Timeframe | 15m |
| Leverage | 10x |
| Target Profit | +9% |
| Max Loss | -8% |
| Position Size | $30 per trade |

---

#### 2.5 Arbitrage Bot
**File:** `crypto_strategies/arbitrage_bot.py`

BTC/ETH statistical arbitrage exploiting funding rate differentials.

| Detail | Value |
|--------|-------|
| Strategy | Long low-funding, Short high-funding |
| Pairs | BTC + ETH (pair trade) |
| Position Size | $150 per leg |
| Leverage | 10x |
| Target | +0.6% |
| Stop | -0.9% |

---

#### 2.6 Market Maker Bot
**File:** `crypto_strategies/market_maker_bot/main.py`

Provides liquidity and captures bid-ask spreads with multi-layer order placement.

| Detail | Value |
|--------|-------|
| Symbol | DYDXUSD |
| Timeframe | 5m (180 bars lookback) |
| Order Layers | 3 layers (20%, 40%, 40% split) |
| Max Loss | $1,250 |
| Exit Profit | +0.4% |
| Features | Trade pause after losses, ATR stops, volume analysis |

---

#### 2.7 Turtle Trending Algo
**Path:** `crypto_strategies/turtle_trending_algo/`

Classic Turtle Trading breakout strategy adapted for crypto.

| Detail | Value |
|--------|-------|
| Indicator | 55-bar High/Low, ATR, SMA |
| Symbol | ETHUSD |
| Long Entry | 55-bar high breakout + uptrend |
| Short Entry | 55-bar low breakout + downtrend |
| Stop Loss | 2x ATR from entry |
| Take Profit | +0.2% |
| Order Type | PostOnly limit orders |

---

#### 2.8 Correlation Algo
**Path:** `crypto_strategies/correlation_algo/`

Trades lagging altcoins when ETH makes a move — exploits cross-asset correlation.

| Detail | Value |
|--------|-------|
| Lead Asset | ETH (monitored via Coinbase API for faster updates) |
| Lagging Assets | ADA, DOT, MANA, XRP, UNI, SOL on Phemex |
| Logic | ETH breaks out → find the most lagging altcoin → enter same direction |
| Timeframe | 15m |
| Stop Loss | -0.2% |
| Take Profit | +0.25% |

---

#### 2.9 Consolidation Pop Algo
**Path:** `crypto_strategies/consolidation_pop_algo/`

Detects low-volatility consolidation zones and trades the subsequent breakout.

| Detail | Value |
|--------|-------|
| Strategy | Volatility contraction → expansion breakout |
| Indicators | Volatility bands, range detection |
| Entry | Price consolidates, then breaks out ("pops") |

---

#### 2.10 Nadaraya-Watson Algo
**Path:** `crypto_strategies/nadaraya_watson_algo/`

Machine-learning-based kernel smoother combined with Stochastic RSI.

| Detail | Value |
|--------|-------|
| Indicators | Nadaraya-Watson kernel smoother, Stochastic RSI |
| Symbol | ETHUSD |
| Timeframe | 1h |
| Long Entry | NW buy signal OR Stoch RSI < 10 |
| Short Entry | NW sell signal OR Stoch RSI > 90 |
| Exit | Opposite NW signal or double Stoch RSI cross |
| Position Size | 1000 |

---

### 3. Live Trading Bots — HyperLiquid DEX

These bots trade on **HyperLiquid**, a decentralized perpetual futures exchange. They authenticate via an Ethereum wallet private key.

**Shared Library:** `crypto_strategies/nice_funcs.py` — comprehensive utility functions (order placement, L2 order book, position management, kill switch, S&D zone detection, Stoch RSI, Nadaraya-Watson calculations).

#### 3.1 Bollinger Bands Bot
**Path:** `crypto_strategies/bollinger_bands_bot/`

Trades Bollinger Band squeeze breakouts with L2 order book analysis.

| Detail | Value |
|--------|-------|
| Indicators | Bollinger Bands (band width), SMA-20 |
| Symbol | WIF (configurable) |
| Timeframe | 15m |
| Leverage | 3x |
| Entry | Band squeeze (low volatility) → breakout direction |
| Target Profit | +5% |
| Max Loss | -10% |
| Features | 10-level deep order book analysis |

---

#### 3.2 Supply & Demand Zones Bot
**Path:** `crypto_strategies/supply_demand_zones_bot/`

Identifies institutional supply/demand zones from historical swing points and trades the reactions.

| Detail | Value |
|--------|-------|
| Indicators | S&D zones, SMA |
| Logic | Price enters a zone → trade the reversal with SMA confirmation |
| Zone Detection | Historical swing highs/lows |
| Leverage | 3x |

---

#### 3.3 VWAP Bot
**Path:** `crypto_strategies/vwap_bot/`

Probabilistic VWAP entries with asymmetric long/short weighting.

| Detail | Value |
|--------|-------|
| Indicators | VWAP, probability weighting |
| Long Probability | 70% above VWAP, 30% below |
| Features | Pyramid entries, multi-level position management |

---

### 4. Backtest-Only Strategies

**Path:** `crypto_strategies/ai_backtest_strategies/`

13 backtesting strategies built with the `backtesting.py` library. These are research/educational — no live trading capability.

| # | File | Strategy | Key Indicators |
|---|------|----------|----------------|
| 1 | `bt_macd.py` | MACD Crossover | MACD (12,26), Signal (9), EMA-50 |
| 2 | `bt_rsi_vwap.py` | RSI + VWAP | RSI (14), VWAP |
| 3 | `bt_bollinger_bands.py` | Bollinger Squeeze | Bollinger Bands |
| 4 | `bt_ema_bollinger.py` | EMA + Bollinger | EMA, Bollinger Bands |
| 5 | `bt_adx.py` | ADX Trend Strength | ADX, DI+, DI- |
| 6 | `bt_ichimoku.py` | Ichimoku Cloud | Tenkan, Kijun, Senkou, Chikou |
| 7 | `bt_pivot_lines.py` | Pivot Points | Classic pivot levels |
| 8 | `bt_quarter_theory.py` | Quarter Theory | Price quarter divisions |
| 9 | `bt_elliot_waves.py` | Elliott Wave | Wave counting |
| 10 | `bt_elliot_waves_pivot_lines.py` | Elliott + Pivots | Combined wave + pivot |
| 11 | `bt_grid_fibonacci.py` | Fibonacci Grid | Fibonacci levels, grid orders |
| 12 | `bt_sma_adx_bollinger_volume.py` | Multi-Indicator | SMA, ADX, BB, Volume |
| 13 | `Bitcoin_Trading_Strategy.py` | BTC Custom | Custom BTC strategy |

**Running a backtest:**
```bash
cd crypto_strategies/ai_backtest_strategies
pip install backtesting pandas numpy ta
python bt_macd.py
```

---

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
git clone https://github.com/pranay123-stack/Algorithmic-Trading-Projects.git
cd Algorithmic-Trading-Projects

# For ICT backtest engine
cd ict_smart_money_crypto_strategy/backtest_engine
pip install -r requirements.txt

# For ICT paper trading engine
cd ../paper_trading_engine
pip install -r requirements.txt

# For crypto strategies
pip install ccxt pandas numpy ta pandas_ta schedule requests
# For HyperLiquid bots additionally:
pip install eth_account hyperliquid-python-sdk
```

---

## Configuration & API Keys

**Never commit real API keys.** See `crypto_strategies/credentials.example.py` for the template.

### Phemex Strategies

1. Create a `key_file.py` (for single-file strategies) or `config.py` (for multi-file strategies) from the template
2. Add your Phemex API key and secret
3. The `config_ex.py` files in each strategy folder show the expected format

### HyperLiquid Strategies

1. Create a `dontshare.py` file with your Ethereum wallet private key
2. Place it in the strategy folder (e.g., `bollinger_bands_bot/dontshare.py`)

### ICT Paper Trading Engine

1. Copy `.env.example` to `.env`
2. Add your Binance API keys and Telegram bot token (optional)

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| Exchange APIs | CCXT (Phemex, Binance), HyperLiquid SDK |
| Data Analysis | pandas, numpy, scipy |
| Technical Indicators | ta, pandas_ta, custom implementations |
| Backtesting | backtesting.py, vectorbt, custom engine |
| Visualization | matplotlib, seaborn, plotly |
| Notifications | Telegram Bot API |
| Scheduling | schedule, cron |
| Wallet Auth | eth_account (HyperLiquid) |

---

## License

This project is provided as-is for educational purposes. No warranty is provided. Use at your own risk.
