# Benford's Law, Lunar Cycle & Fourier Transform Trading Strategies

Three independent algorithmic trading approaches exploiting market anomalies and cyclical patterns in Bitcoin, built on the hypothesis that volume distributions, lunar phases, and spectral cycles contain actionable trading signals.

---

## Table of Contents

- [Overview](#overview)
- [Strategies](#strategies)
  - [1. Benford's Law Volume Strategy](#1-benfords-law-volume-strategy)
  - [2. Lunar Cycle Strategies](#2-lunar-cycle-strategies)
  - [3. Fourier Transform Analysis](#3-fourier-transform-analysis)
- [File Reference](#file-reference)
- [Installation](#installation)
- [Usage](#usage)
- [Data](#data)
- [Research Hypotheses](#research-hypotheses)

---

## Overview

| Strategy | Approach | Timeframe | Key Indicator |
|----------|----------|-----------|---------------|
| Benford's Law v1 | Volume anomaly detection + EMA crossover | 30m | Benford Score + OBV |
| Benford's Law v2 | v1 + ADX trend strength filtering | 30m | Benford Score + ADX |
| Full Moon Long/Short | Lunar phase directional bias | 30m | Ephemeris calculation |
| New Moon Long/Short | Lunar phase directional bias | 30m | Ephemeris calculation |
| Combined New Moon | Lunar + multi-indicator confirmation | 30m | ADX + Aroon + Volume SMA |
| Fourier Transform | Spectral cycle identification | 30m | FFT dominant periods |

---

## Strategies

### 1. Benford's Law Volume Strategy

**Hypothesis**: Legitimate trading volume follows Benford's Law (first-digit distribution: 30.1% for 1, 17.6% for 2, etc.). Deviations indicate synthetic or anomalous activity.

#### Version 1 (`benford_law_volume_based_strategy_version_1.py`)

**Indicators**: EMA-5, EMA-900, ATR(14), OBV, Benford Score

**Entry Rules**:
| Signal | Conditions |
|--------|-----------|
| LONG | EMA5 crosses above EMA900 + OBV trending up + Benford Score > 0.1 |
| SHORT | EMA5 crosses below EMA900 + OBV not trending up + Benford Score > 0.1 |

**Risk Management**:
- Dynamic ATR-based stops: 4x–6x ATR for stop loss, 8x–12x ATR for take profit
- Volatility adjustment: multipliers shift when ATR/Close > 2%
- Position sizing: 99.9% capital, 2x leverage, 1/5 margin
- Commission: 0.2%

#### Version 2 (`benford_law_volume_based_strategy_ADX_version_2.py`)

Adds **ADX(14)** trend strength confirmation with rolling 10-period average comparison:

| ADX State | Price Trend | Interpretation | Signal |
|-----------|-------------|----------------|--------|
| ADX > 25 | Current avg > Previous avg | Strong trend, continuation | BUY |
| ADX > 25 | Current avg < Previous avg | Strong trend, reversal | SELL |
| ADX < 25 | Current avg > Previous avg | Weak trend, fading move | SELL |
| ADX < 25 | Current avg < Previous avg | Weak trend, reversal expected | BUY |

---

### 2. Lunar Cycle Strategies

**Hypothesis**: Market behavior correlates with lunar phases. A 3-day pre-event window shows exploitable directional bias.

#### Variants

| Script | Moon Phase | Direction | Exit |
|--------|-----------|-----------|------|
| `Full_moon_backtest_Long.py` | Full Moon | LONG | 2% trailing stop |
| `Full_moon_backtest_Short.py` | Full Moon | SHORT | 2% trailing stop |
| `Newmoon_backtest_Long.py` | New Moon | LONG | 2% trailing stop |
| `Newmoon_backtest_short.py` | New Moon | SHORT | 2% trailing stop |

**Entry Logic** (all variants):
- Calculate next full/new moon date using `ephem` library
- Enter position **3 days before** the lunar event
- Exit on 2% trailing stop loss

**Backtest Parameters**: $100k initial capital, 0.2% commission, exclusive orders

#### Combined Strategy (`combined_newmoon_long_short.py`)

Adds technical confirmation filters to new moon signals:

**Long Entry** (all conditions required):
1. New moon lunar signal triggered
2. Current volume > 5-day average volume
3. Current ADX > 5-day average ADX
4. Aroon Up > Aroon Down
5. Fast Volume SMA(20) > Slow Volume SMA(50)

**Short Entry**: Lunar signal triggered but long conditions not met

**Stop Loss**: ATR × 2.0

---

### 3. Fourier Transform Analysis

**Hypothesis**: Bitcoin price contains cyclical components detectable via spectral analysis, including a ~29.5-day lunar cycle.

#### `fourier_transform.py`

- Removes trend via first differencing
- Applies FFT to detrended close prices
- Identifies top 5 dominant periods
- Classifies cycles: 27–31 days = lunar, 350–380 days = annual, <7 days = weekly
- Maps candles to moon phases and scores each phase by:
  - Price performance (40%)
  - Price consistency (20%)
  - Volume consistency (20%)
  - Volatility consistency (20%)

#### `lunar_test.py`

- Extends Fourier analysis with Gaussian correlation distributions
- Computes Pearson correlations (price-volume, price-volatility, volume-volatility) per lunar phase
- Generates per-phase Gaussian distribution PNG plots

---

## File Reference

| File | Purpose |
|------|---------|
| `benford_law_volume_based_strategy_version_1.py` | Benford's Law + EMA crossover strategy |
| `benford_law_volume_based_strategy_ADX_version_2.py` | Enhanced with ADX trend filtering |
| `Full_moon_backtest_Long.py` | Full moon long-only backtest |
| `Full_moon_backtest_Short.py` | Full moon short-only backtest |
| `Newmoon_backtest_Long.py` | New moon long-only backtest |
| `Newmoon_backtest_short.py` | New moon short-only backtest |
| `combined_newmoon_long_short.py` | New moon + ADX/Aroon/Volume filters |
| `fourier_transform.py` | FFT spectral analysis + lunar phase scoring |
| `lunar_test.py` | Gaussian correlation analysis per moon phase |
| `formatting_zelta_lab_data.py` | Data preparation (reformat CSV) |
| `append_time_00_00_00_to_signals_csv.py` | Timestamp normalization utility |
| `BTC_2019_2023_30m.csv` | Bitcoin 30m OHLCV data (2019–2023) |
| `output_file.csv` | Reformatted data for backtesting |
| `trades.csv` | Sample trade output (48 trades) |
| `moon_phases.txt` | Research reference link |

---

## Installation

```bash
pip install pandas numpy pandas_ta backtesting ephem scipy matplotlib coloredlogs talib
```

### Dependencies

| Library | Purpose |
|---------|---------|
| `pandas`, `numpy` | Data manipulation |
| `pandas_ta` / `talib` | Technical indicators (EMA, ATR, OBV, ADX, Aroon) |
| `backtesting` | Backtest framework |
| `ephem` (PyEphem) | Lunar phase calculations |
| `scipy.fft` | Fast Fourier Transform |
| `matplotlib` | Visualization |
| `coloredlogs` | Colored console logging |

---

## Usage

### Run Benford's Law Strategy

```bash
# Version 1 - Basic
python benford_law_volume_based_strategy_version_1.py

# Version 2 - With ADX
python benford_law_volume_based_strategy_ADX_version_2.py
```

### Run Lunar Backtests

```bash
# Individual variants
python Full_moon_backtest_Long.py
python Newmoon_backtest_short.py

# Combined with technical filters
python combined_newmoon_long_short.py
```

### Run Fourier Analysis

```bash
# Spectral analysis + lunar phase scoring
python fourier_transform.py

# Gaussian correlation analysis (generates PNGs)
python lunar_test.py
```

### Data Preparation

```bash
# Format raw data first
python formatting_zelta_lab_data.py
python append_time_00_00_00_to_signals_csv.py
```

---

## Data

- **Asset**: Bitcoin (BTC)
- **Timeframe**: 30-minute candles
- **Period**: September 2019 – 2023
- **Source**: `BTC_2019_2023_30m.csv` (4.9 MB, ~87,000 candles)
- **Columns**: datetime, open, high, low, close, volume

### Sample Trade Results (from `trades.csv`)

- **Total Trades**: 48 (Oct 2019 – Oct 2023)
- **Position Sizes**: 1–30 BTC per trade
- **Return Range**: -7% to +5% per trade
- **Average Hold Time**: ~8–9 hours

---

## Research Hypotheses

1. **Benford's Law**: Volume first-digit distributions deviating from Benford's expected frequencies indicate synthetic/manipulated activity. Legitimate trends respect this distribution.

2. **Lunar Cycles**: Market sentiment and behavior correlate with full/new moon phases. A 3-day anticipatory window provides edge for directional trades.

3. **Fourier Spectral Analysis**: Bitcoin price contains a ~29.5-day cyclical component matching the lunar period, alongside annual (~365 day) and weekly (<7 day) cycles.

4. **Technical Confirmation**: Lunar signals filtered through ADX, Aroon, and volume SMA alignment significantly reduce false signals.

---

## Disclaimer

This project is for **educational and research purposes only**. Cryptocurrency trading involves substantial risk. Past backtest performance does not guarantee future results.
