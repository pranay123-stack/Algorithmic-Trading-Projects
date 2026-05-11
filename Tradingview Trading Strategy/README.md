# TradingView Futures Trading Strategies

A comprehensive collection of Pine Script strategies and indicators for futures trading on TradingView, designed for multiple asset classes including Forex, Crypto, Commodities, and Index Futures.

## Overview

This repository contains professional-grade trading tools developed for futures markets:

| Script | Type | Purpose |
|--------|------|---------|
| `universal_futures_strategy_optimized.pine` | Strategy | Multi-asset futures trading with adaptive parameters |
| `future_pinescript_strategy.pine` | Strategy | COT-based strategy for commodities & index futures |
| `ATAS_RangeXV.pine` | Indicator | ATAS-style range bar visualization |
| `ATAS_SpeedOfTape.pine` | Indicator | Transaction speed indicator (ATAS-style) |

---

## Strategies

### 1. Universal Futures Strategy - Multi-Asset Optimized

**File:** `universal_futures_strategy_optimized.pine`

A sophisticated multi-asset trading strategy that works across all futures markets with adaptive parameters.

#### Key Features

- **Auto Asset Detection**: Automatically detects and optimizes parameters for:
  - Forex (EUR/USD, GBP/JPY, etc.)
  - Crypto (BTC, ETH, etc.)
  - Commodities (Gold, Oil, Agriculture)
  - Index Futures (ES, NQ, DAX, etc.)

- **Composite Sentiment Index**: Replaces traditional COT data with universal indicators:
  - Money Flow Index (MFI) - Volume-weighted momentum (40% weight)
  - Stochastic RSI - Dual momentum oscillator (30% weight)
  - Price Position Index - Percentile ranking (30% weight)

- **Adaptive Thresholds**: Automatically adjusts entry thresholds based on market volatility

- **Multi-Timeframe Analysis**: Confirms signals across fast (1H), medium (4H), and slow (Daily) timeframes

- **Market Regime Filter**: Uses ADX to filter trades based on trending/ranging conditions

- **Advanced Risk Management**:
  - ATR-based stop loss and take profit
  - Trailing stops
  - Fixed risk alternative
  - Configurable position sizing

#### Parameters

| Category | Parameter | Default | Description |
|----------|-----------|---------|-------------|
| Asset | Asset Class | Auto | Auto-detect or manual selection |
| Sentiment | MFI Length | 14 | Money Flow Index period |
| Sentiment | Stochastic RSI Length | 14 | Dual momentum lookback |
| Adaptive | Base Long Threshold | 85 | Entry threshold for longs |
| Adaptive | Base Short Threshold | 15 | Entry threshold for shorts |
| Risk | ATR Stop Loss Multiplier | 2.0 | ATR multiple for stops |
| Risk | ATR Take Profit Multiplier | 3.0 | ATR multiple for targets |

---

### 2. COT Strategy - Commodities & Index Futures

**File:** `future_pinescript_strategy.pine`

A Commitment of Traders (COT) based strategy specifically designed for traditional commodities and major US index futures.

#### Supported Instruments

- **US Index Futures**: ES, NQ, YM, RTY
- **Energy**: CL, NG, RB, HO
- **Metals**: GC, SI, HG, PL, PA
- **Agriculture**: ZC, ZW, ZS, ZL, ZM, CT, KC, CC, SB, OJ
- **Livestock**: LE, GF, HE

> **Note**: This strategy does NOT support crypto futures (BTC, ETH) or non-US indices (DAX, Nikkei, FTSE)

#### Key Features

- **Commercial Index Calculation**: Tracks smart money (commercial hedgers) positioning
- **RSI Confirmation**: Uses RSI(8) to time entries
- **COT Data Integration**: Leverages TradingView's official COT library

#### Entry Logic

**Long Entry:**
- Commercial Index > 90 (commercials are heavily long)
- Previous RSI was in oversold zone (0-30)
- Current RSI crosses above 30

**Short Entry:**
- Commercial Index < 10 (commercials are heavily short)
- Previous RSI was in overbought zone (70-100)
- Current RSI crosses below 70

---

## Indicators

### 3. Range XV [ATAS Style]

**File:** `ATAS_RangeXV.pine`

A professional range bar visualization indicator inspired by ATAS platform.

#### Features

- **Range Bar Formation**: Creates visual range boxes based on price movement
- **Volume Confirmation**: Requires volume above average to confirm range completion
- **Direction Detection**: Identifies bullish/bearish range bars
- **High Volume Highlighting**: Colors candles with exceptional volume (>2x average)
- **Info Panel**: Real-time display of range progress and status

#### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Range Size | 10 points | Price range to form one bar |
| Volume Confirm | 1.0x | Min volume vs average |
| Volume Lookback | 20 | Bars for average calculation |

---

### 4. Speed of Tape [ATAS Style]

**File:** `ATAS_SpeedOfTape.pine`

Measures transaction speed and highlights candles when trading activity exceeds normal levels.

#### Features

- **Speed Calculation Types**:
  - Tick Count (approximated via volume)
  - Volume-based
  - Delta-based (price movement)

- **Auto Filter**: Automatically calculates threshold using mean + standard deviation
- **Visual Alerts**: Paints candles yellow when high speed is detected
- **Optional Histogram**: View speed as histogram with SMA overlay

#### Use Cases

- Identify institutional activity
- Spot unusual market interest
- Time entries during high-activity periods

---

## Installation

1. Open TradingView and go to Pine Editor
2. Copy the contents of the desired `.pine` file
3. Paste into Pine Editor
4. Click "Add to Chart"

## Usage Tips

### For Universal Futures Strategy

1. **Asset Selection**: Start with "Auto" mode to let the strategy detect your asset class
2. **Backtest First**: Run strategy tester on historical data before live trading
3. **Adjust Thresholds**: In choppy markets, increase base thresholds for fewer signals
4. **Use Regime Filter**: Enable "Only Trade in Trends" for trend-following approach

### For COT Strategy

1. **Check Symbol Support**: Ensure you're trading a supported instrument
2. **Weekly Timeframe**: COT data is released weekly, works best on daily+ charts
3. **Combine with Technicals**: Use COT for bias, technicals for timing

### For ATAS Indicators

1. **Range XV**: Adjust range size based on instrument volatility
2. **Speed of Tape**: Use Auto Filter for dynamic thresholds

## Risk Disclaimer

These tools are for educational and research purposes. Past performance does not guarantee future results. Always:

- Backtest thoroughly before live trading
- Use proper position sizing
- Never risk more than you can afford to lose
- Understand the strategy logic before deploying capital

## License

This code is subject to the Mozilla Public License 2.0. See [LICENSE](https://mozilla.org/MPL/2.0/) for details.

## Author

Developed for professional futures trading applications.

---

*For questions or customizations, please open an issue in this repository.*
