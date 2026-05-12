# Volume Profile Analysis — Bitcoin (BTCUSDT)

A comprehensive Bitcoin market microstructure analysis project that calculates **Volume Profile** (VAH, VAL, POC), **VWAP**, **Open Interest**, and **volatility metrics** from raw Bybit API data. Produces a consolidated daily backtesting dataset spanning 2020–2024.

---

## Table of Contents

- [Overview](#overview)
- [Key Concepts](#key-concepts)
- [Data Pipeline](#data-pipeline)
- [Scripts Reference](#scripts-reference)
- [Dataset Structure](#dataset-structure)
- [Installation](#installation)
- [Usage](#usage)
- [Output](#output)

---

## Overview

| Feature | Detail |
|---------|--------|
| Asset | BTCUSDT (Bybit Perpetual Futures) |
| Data Source | Bybit v5 API |
| Kline Interval | 1-minute candles |
| OI Interval | 5-minute aggregation |
| Date Range | Jan 2020 – Aug 2024 |
| Final Output | 571 daily rows with VAH, VAL, POC, VWAP, Day High/Low, Price Range |
| Total Raw CSVs | ~6,800 files |

---

## Key Concepts

### Volume Profile

Distribution of trading volume across price levels for a given period. Reveals where the market spent the most time and volume.

| Metric | Definition |
|--------|-----------|
| **POC** (Point of Control) | Price level with the highest traded volume — the "fair price" |
| **VAH** (Value Area High) | Upper boundary of the price range containing 70% of total volume |
| **VAL** (Value Area Low) | Lower boundary of the price range containing 70% of total volume |
| **Value Area** | Price range between VAH and VAL — where 70% of trading occurred |

### VWAP (Volume Weighted Average Price)

```
VWAP = Σ(Typical Price × Volume) / Σ(Volume)
Typical Price = (High + Low + Close) / 3
```

Institutional benchmark for fair value. Price above VWAP = bullish bias, below = bearish.

### Open Interest

Number of outstanding futures contracts. Rising OI + rising price = new money entering (bullish). Rising OI + falling price = new shorts (bearish).

---

## Data Pipeline

```
Step 1: Download Raw Data
   kline_download.py → 1-min candles from Bybit API → /klines/
   oi_download.py    → 5-min OI from Bybit API     → /oi/

Step 2: Process & Transform
   convert_epoch_timestamp_of_kline.py → UTC → Asia/Kolkata timezone
   price_volume_volaitility.py         → Calculate price & volume volatility
   change_in_volatility.py             → Period-over-period volatility changes
   change_in_oi.py                     → Period-over-period OI changes

Step 3: Extract Trade Data
   trade_extract.py → Decompress .gz trade files → trade1.csv, trade2.csv

Step 4: Calculate Volume Profile
   volume_profile.py → Aggregate by price level → VAH, VAL, POC per day

Step 5: Enhance
   vwap_using_klines.py         → Add VWAP column
   day_high_close_using_klines.py → Add Day High/Low columns
   price_range_vah_val.py        → Add Price_Range (VAH - VAL)

Step 6: Consolidate
   merge_all_volume_profie_single_csv.py → Single backtest CSV
   Output: final_backtest_2020_2024_with_range.csv
```

---

## Scripts Reference

### Core Volume Profile

| Script | Purpose |
|--------|---------|
| `volume_profile.py` | Calculates daily VAH, VAL, POC from trade data. Groups trades by price level, finds POC (max volume price), expands value area until 70% threshold met |
| `merge_all_volume_profie_single_csv.py` | Merges all individual daily volume profile CSVs into a single sorted file |

### Data Enhancement

| Script | Purpose |
|--------|---------|
| `vwap_using_klines.py` | Calculates cumulative VWAP from kline data and adds to volume profile |
| `day_high_close_using_klines.py` | Extracts daily high/low from kline data |
| `price_range_vah_val.py` | Computes `Price_Range = VAH - VAL` as a volatility measure |
| `convert_epoch_timestamp_of_kline.py` | Converts UNIX epoch timestamps to IST (Asia/Kolkata) |

### Data Download

| Script | Purpose |
|--------|---------|
| `kline_download.py` | Downloads 1-minute BTCUSDT candles from Bybit API (2020–2024). Paginates 1000 candles per request |
| `oi_download.py` | Downloads 5-minute open interest data from Bybit API. Paginates 1000 records per request |

### Data Processing

| Script | Purpose |
|--------|---------|
| `price_volume_volaitility.py` | Calculates `price_volatility = high - low` and `volume_volatility = abs(diff(volume))` |
| `change_in_volatility.py` | Computes period-over-period changes in price and volume volatility |
| `change_in_oi.py` | Computes `change_oi = openInterest.diff()` |

### Trade Extraction

| Script | Purpose |
|--------|---------|
| `trade-extract/trade_extract.py` | Decompresses `.gz` trade files, splits by date into `trade1.csv` / `trade2.csv` |
| `trade-extract/extract_trade_from_month_folder_and-put_in_trades_folder.py` | Organizes monthly trade folders into yearly directory structure |

### Utility

| Script | Purpose |
|--------|---------|
| `test.py` | Test script to verify Bybit API connectivity |

### Placeholder (Not Yet Implemented)

| Script | Intended Purpose |
|--------|-----------------|
| `Absorption_rate.py` | Absorption rate analysis |
| `Ai_model_training_on_final_csv.py` | ML model training on final dataset |
| `Low_volume_deviation.py` | Low volume node detection |
| `TPO.py` | Time Price Opportunity (Market Profile) |
| `value_overlap.py` | Value area overlap between sessions |

---

## Dataset Structure

### Final Output: `final_backtest_2020_2024_with_range.csv`

| Column | Description | Example |
|--------|-------------|---------|
| `Date` | Trading date | 2021-05-19 |
| `VAH` | Value Area High | 43,250.50 |
| `VAL` | Value Area Low | 38,120.00 |
| `POC` | Point of Control | 40,680.25 |
| `VWAP` | Volume Weighted Avg Price | 41,015.30 |
| `Day_High` | Session high | 43,800.00 |
| `Day_Low` | Session low | 30,000.00 |
| `Price_Range[VAH-VAL]` | Value area width | 5,130.50 |

- **Rows**: 571 daily observations
- **Period**: April 2020 – December 2021
- **Price Range**: VAH from $6,398 to $68,403

### Raw Data Folders

| Folder | Contents | Files | Period |
|--------|----------|-------|--------|
| `/klines/` | 1-min OHLCV candles (3 CSVs per day: raw, converted, volatility) | ~5,094 | 2020–2024 |
| `/oi/` | 5-min open interest snapshots | ~1,698 | 2020–2024 |
| `/volume_profile_csv/` | Daily volume profile outputs | ~571 | 2020–2021 |

---

## Installation

```bash
pip install pandas numpy requests
```

### Dependencies

| Library | Purpose |
|---------|---------|
| `pandas` | Data manipulation, CSV I/O |
| `numpy` | Numerical calculations |
| `requests` | Bybit API calls |
| `os`, `glob`, `gzip` | File operations |

No external TA libraries required — all calculations are implemented from scratch.

---

## Usage

### Full Pipeline (from scratch)

```bash
# 1. Download raw data
python kline_download.py
python oi_download.py

# 2. Convert timestamps
python convert_epoch_timestamp_of_kline.py

# 3. Calculate volatility metrics
python price_volume_volaitility.py
python change_in_volatility.py
python change_in_oi.py

# 4. Extract trade data (requires .gz trade files)
cd trade-extract
python trade_extract.py

# 5. Calculate volume profile
python volume_profile.py

# 6. Enhance with VWAP and day high/low
python vwap_using_klines.py
python day_high_close_using_klines.py
python price_range_vah_val.py

# 7. Merge into single file
python merge_all_volume_profie_single_csv.py
```

### Using the Pre-Built Dataset

The final output is ready to use:

```python
import pandas as pd

df = pd.read_csv('final_backtest_2020_2024_with_range.csv')
print(df.head())

# Example: Find days where price closed outside value area
# (potential breakout signals)
```

> **Note**: Python scripts contain hardcoded paths from the original development environment (`/Users/pranaygaurav/...`). Update paths before running.

---

## Output

### Kline Files (per day)

| File Pattern | Columns |
|-------------|---------|
| `kline_*_output.csv` | startTime (epoch), openPrice, highPrice, lowPrice, closePrice, volume, turnover |
| `converted_*_output.csv` | timestamp (IST), open, high, low, close, volume, turnover |
| `volatility_*_output.csv` | timestamp, price_volatility, volume_volatility, change_price_volatility, change_volume_volatility |

### Open Interest Files (per day)

| File Pattern | Columns |
|-------------|---------|
| `oi_*_output.csv` | timestamp, openInterest, change_oi |

---

## Disclaimer

This project is for **educational and research purposes only**. Cryptocurrency trading involves substantial risk. Past performance does not guarantee future results.
