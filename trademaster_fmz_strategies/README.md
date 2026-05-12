# TradeMaster FMZ Strategies Collection

A collection of **43 algorithmic trading strategies** built on the TradeMaster backtesting framework, covering a wide range of technical analysis methodologies — from simple moving average crossovers to complex multi-indicator systems with order flow concepts. All strategies are designed for cryptocurrency trading (primarily BTC/USDT).

---

## Table of Contents

- [Overview](#overview)
- [Strategy Categories](#strategy-categories)
- [Strategy Index](#strategy-index)
- [Framework & Infrastructure](#framework--infrastructure)
- [Common Indicators](#common-indicators)
- [Risk Management](#risk-management)
- [Installation](#installation)
- [Usage](#usage)
- [Tasksheet Documentation](#tasksheet-documentation)

---

## Overview

| Feature | Detail |
|---------|--------|
| Total Strategies | 43 Python scripts |
| Framework | TradeMaster (Backtrader-like) |
| Primary Asset | BTC/USDT |
| Timeframes | Daily (1D) and Hourly (1H) |
| Initial Capital | $100K–$1M |
| Commission | 0.2% per trade |
| Indicator Library | pandas_ta |
| Documentation | 37 HTML tasksheets |

---

## Strategy Categories

### By Methodology

| Category | Count | Complexity | Strategies |
|----------|-------|------------|------------|
| **EMA/SMA Crossover** | 15+ | Low–Medium | 1, 3, 8, 10, 17 |
| **Bollinger Bands** | 8+ | Low | 5, 25, 40 |
| **RSI-Based** | 10+ | Low–Medium | 7, 25 (as guard) |
| **MACD-Based** | 8+ | Medium | 3, 7 (confirmation) |
| **Supertrend** | 4+ | Medium | 13, 23 |
| **ATR/Volatility** | 12+ | Medium | 17, 20 |
| **Structure/Breakout** | 4+ | High | 20 |
| **Multi-Indicator** | 8+ | High | 7, 17, 21 |
| **DCA/Grid** | 3+ | Medium | 25, 30 |
| **Candle Pattern** | 2+ | Low–Medium | 35 |

### By Signal Type

| Type | Description | Example |
|------|-------------|---------|
| **Trend Following** | Ride momentum after confirmation | EMA crossovers, Supertrend |
| **Mean Reversion** | Fade extremes back to mean | Bollinger Band bounces, RSI oversold/overbought |
| **Breakout** | Enter on structure breaks | Order block + FVG, Red candle breakout |
| **Accumulation** | DCA into positions on weakness | Bollinger + RSI DCA strategies |
| **Volatility** | Enter on squeeze breakouts | BB + Keltner Channel squeeze |

---

## Strategy Index

| # | Strategy Name | Key Indicators | Approach |
|---|--------------|----------------|----------|
| 1 | Golden Harmony Breakout | EMA, Fibonacci, Order Blocks | Trend + Structure |
| 2 | EMA Crossover Basic | EMA fast/slow | Trend Following |
| 3 | MACD + EMA Confirmation | MACD, EMA | Multi-Indicator |
| 4 | RSI + SMA | RSI, SMA | Mean Reversion |
| 5 | Bollinger Bands | BB(20, 2.0) | Mean Reversion |
| 6 | *Issue flagged* | — | — |
| 7 | Scalping/Swing Combo | BB, Keltner, RSI, MACD, LinReg | Multi-Indicator |
| 8 | Dual EMA Crossover | EMA 9/21 | Trend Following |
| 9 | SMA + Volume | SMA, Volume MA | Trend + Volume |
| 10 | Triple EMA | EMA 5/10/50 | Trend Following |
| 11 | *Issue flagged* | — | — |
| 12 | Ichimoku Cloud | Tenkan, Kijun, Senkou, Chikou | Cloud Trading |
| 13 | Supertrend | Supertrend(7, 3.0) | Trend Following |
| 14 | *Issue flagged* | — | — |
| 15 | VWAP + EMA | VWAP, EMA | Intraday |
| 16 | HMA Crossover | Hull MA | Trend Following |
| 17 | Multi-Indicator Trend | EMA, ATR, MACD, RSI | Multi-Indicator |
| 18 | Stochastic RSI | StochRSI, SMA | Mean Reversion |
| 19 | EMA + ADX Filter | EMA, ADX | Trend Strength |
| 20 | Trend Structure Break | Order Block, FVG, BoS | Structure |
| 21 | MACD + BB + RSI | MACD, BB, RSI | Multi-Indicator |
| 22 | SMA Ribbon | SMA 8/18/50 | Trend Following |
| 23 | Multi-Supertrend | Supertrend(10,14,21) | Trend Following |
| 24 | WMA + EMA Crossover | WMA 30, EMA 9 | Trend Following |
| 25 | DCA + Bollinger + RSI | BB, RSI < 42 | Accumulation |
| 26 | Chande Kroll Stop | CKS, ATR | Volatility Stop |
| 27 | KDJ Stochastic | KDJ, EMA | Mean Reversion |
| 28 | *Issue flagged* | — | — |
| 29 | EMA + MACD Trend | EMA 50/200, MACD | Trend Following |
| 30 | Flawless Victory DCA | BB, RSI, DCA grid | Accumulation |
| 31 | Supertrend + EMA | Supertrend, EMA | Trend Following |
| 32 | ATR Trailing Stop | ATR, EMA | Volatility |
| 33 | RSI Divergence | RSI, Price action | Divergence |
| 34 | Multi-Timeframe EMA | EMA on multiple TFs | Trend Following |
| 35 | Red Candle Breakout (*issue*) | Candle pattern, volume | Breakout |
| 36 | BONK Strategy | EMA, BB, RSI | Multi-Indicator |
| 37 | Fukuiz Trading | EMA, MACD, volume | Trend Following |
| 38 | BB + Stochastic RSI | BB, StochRSI | Mean Reversion |
| 39 | SMA + MACD + RSI | SMA, MACD, RSI | Multi-Indicator |
| 40 | BB Squeeze Breakout | BB narrow bands | Volatility |
| 41 | *Issue flagged* | — | — |
| 42 | Multi-EMA Strategy | EMA 8/21/50/200 | Trend Following |
| 43 | DSL Strategy | Donchian bands, ATR | Channel Trading |

> Strategies marked *issue* have known bugs or incomplete implementations.

---

## Framework & Infrastructure

### TradeMaster Backtesting Framework

All strategies follow a standard structure:

```python
from TradeMaster.backtesting import Backtest, Strategy
from TradeMaster.lib import crossover
import pandas_ta as ta

# 1. Load data
data = pd.read_csv("data.csv")

# 2. Calculate indicators
def calculate_daily_indicators(df):
    df['EMA_fast'] = ta.ema(df['Close'], length=9)
    df['EMA_slow'] = ta.ema(df['Close'], length=21)
    return df

# 3. Define strategy
class MyStrategy(Strategy):
    def init(self):
        pass
    
    def next(self):
        if crossover(self.data.EMA_fast, self.data.EMA_slow):
            self.buy()
        elif crossover(self.data.EMA_slow, self.data.EMA_fast):
            self.sell()

# 4. Run backtest
bt = Backtest(data, MyStrategy, cash=100000, commission=0.002)
stats = bt.run()
bt.plot()
bt.tear_sheet()
```

### Risk Management Modules

| Module | Description |
|--------|-------------|
| `EqualRiskManagement` | Position sizing based on account risk % and stop distance |
| `ATR_RR_TradeManagement` | Dynamic stops/targets based on ATR with risk-reward ratio |
| `PriceDeltaTradeManagement` | Fixed percentage moves for stop loss and take profit |

> Note: Most strategies have risk management commented out. Uncomment for production use.

---

## Common Indicators

**Most frequently used across all 43 strategies**:

| Indicator | Library Call | Typical Params | Usage Count |
|-----------|-------------|----------------|-------------|
| EMA | `ta.ema()` | 5, 9, 21, 50, 200 | 20+ strategies |
| Bollinger Bands | `ta.bbands()` | length=20, std=2.0 | 8+ |
| RSI | `ta.rsi()` | 7, 10, 14 | 10+ |
| MACD | `ta.macd()` | 12/26/9 | 8+ |
| ATR | `ta.atr()` | 10, 14 | 12+ |
| SMA | `ta.sma()` | 8, 20, 50, 200 | 12+ |
| Supertrend | `ta.supertrend()` | 7/3.0, 10/2.0 | 4+ |
| VWAP | `ta.vwap()` | — | 3+ |
| ADX | `ta.adx()` | 14 | 5+ |
| Stochastic RSI | `ta.stochrsi()` | 14 | 3+ |

---

## Risk Management

### Typical Stop/Target Configuration

| Style | Stop Loss | Take Profit | Risk:Reward |
|-------|-----------|-------------|-------------|
| Scalping | 2–5% | 4–10% | 1:2 |
| Swing | 5–10% | 10–20% | 1:1.5 to 1:2 |
| DCA | Based on grid levels | 5–15% | Varies |

### Position Management
- One position at a time (`exclusive_orders=True`)
- Position tracking via `self.position().is_long` / `.is_short`
- Exit on opposite signal or stop/target hit

---

## Installation

```bash
pip install TradeMaster pandas pandas_ta numpy
```

> **Note**: TradeMaster is a proprietary framework. Ensure you have access to the `TradeMaster` package.

### Data Requirements

- CSV files with columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`
- Columns are renamed to: `Open`, `High`, `Low`, `Close`, `Volume` by each script
- Primary dataset: BTC/USDT daily candles (2023)

---

## Usage

```bash
# Run any individual strategy
python trademaster_fmz_strategy1.py
python trademaster_fmz_strategy7.py
python trademaster_fmz_strategy25.py

# Each script will:
# 1. Load BTC data from CSV
# 2. Calculate indicators
# 3. Run backtest
# 4. Display performance stats
# 5. Plot equity curve
# 6. Generate tear sheet
```

### Modifying Parameters

Most strategies have configurable parameters at the top of the file:

```python
# Example: adjust EMA periods
ema_fast_period = 9    # Change to desired fast period
ema_slow_period = 21   # Change to desired slow period
```

---

## Tasksheet Documentation

The `Tasksheet/` folder contains **37 HTML documents** with strategy documentation and backtest results:

<details>
<summary>Click to expand full list</summary>

- AKMACDBBStrategy.html
- BBStrategy.html
- BONKTradingStrategy.html
- BollingerBandsStochasticRSI.html
- BollingerBandsStrategy.html
- BollingerMacdRsiStrategy.html
- BollingerRSIStrategy.html
- DCA_Trading_Strategy.html
- EMA9WMA30Strategy.html
- EMASMACrossoverStrategy.html
- FlawlessVictoryDCA.html
- Fukuiz_Trading_Strategy.html
- IchimokuStrategy.html
- MACDStrategy.html
- MultiEMAStrategy.html
- RedCandleBreakoutBuyStrategy.html
- SupertrendStrategy.html
- VWAPStrategy.html
- *(and more...)*

</details>

Open any HTML file in a browser to view the strategy documentation and results.

---

## Disclaimer

This project is for **educational and research purposes only**. Cryptocurrency trading involves substantial risk. Past backtest performance does not guarantee future results.
