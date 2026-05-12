# Polynomial Regression Trading Strategy

An intraday cryptocurrency trading strategy using **Polynomial Autoregression (PAR)** to predict short-term price movements and generate band-based entry/exit signals. Based on published IEEE research on polynomial regression for investment forecasting.

---

## Table of Contents

- [Overview](#overview)
- [Strategy Logic](#strategy-logic)
- [Model Architecture](#model-architecture)
- [Optimal Parameters](#optimal-parameters)
- [Installation](#installation)
- [Usage](#usage)
- [File Reference](#file-reference)
- [Research Papers](#research-papers)

---

## Overview

The strategy fits a **3rd-degree polynomial** to recent price data, generates 1-period-ahead predictions, and creates upper/lower bands (±1.5%) around the prediction. Trades are triggered when price breaks outside these bands.

| Feature | Detail |
|---------|--------|
| Model Type | 3rd-degree Polynomial Autoregression |
| Asset Class | Cryptocurrencies (BTC, ETH, BNB, ADA) |
| Timeframe | 1-minute bars with optimized lookback windows |
| Prediction Horizon | 1 period ahead |
| Band Width | ±1.5% (empirically determined from research) |
| Test Period | Dec 2021 – Nov 2022 (12 months) |

---

## Strategy Logic

### Signal Generation

```
Upper Band = Predicted Price × 1.015
Lower Band = Predicted Price × 0.985
```

| Signal | Condition | Action |
|--------|-----------|--------|
| LONG (+1) | Price > Upper Band | Price exceeding expected upside |
| SHORT (-1) | Price < Lower Band | Price falling below expected downside |
| NEUTRAL (0) | Lower Band ≤ Price ≤ Upper Band | No trade |

### Feature Engineering

Based on **Equation 7** from the research paper:

```
Xi+1 = α + α1(β1·Xi + β2·Xi-n) + α2(β3·Xi + β4·Xi-n)² + α3(β4·Xi + β5·Xi-n)³
```

| Feature | Calculation | Purpose |
|---------|-------------|---------|
| `Xi` | Current price | Present state |
| `Xi_n` | Price n-minutes ago | Lagged state |
| `term1` | Xi + Xi_n | Linear component |
| `term2` | (Xi + Xi_n)² | Quadratic curvature |
| `term3` | (Xi + Xi_n)³ | Cubic inflection capture |

---

## Model Architecture

### Training Phase
1. Split historical data 50/50 (training / testing)
2. Extract polynomial features from training set
3. Standardize features using `StandardScaler`
4. Fit 3rd-degree polynomial via `np.polyfit()`

### Prediction Phase
1. Transform test data features using trained scaler
2. Evaluate polynomial using `np.polyval()`
3. Generate upper/lower bands at ±1.5%

### Signal Generation
1. Compare actual prices to band thresholds
2. Generate signals: +1 (long), -1 (short), 0 (neutral)
3. Calculate position returns and cumulative performance

---

## Optimal Parameters

Each asset has an empirically optimized lookback window (in minutes):

| Asset | Optimal Lookback (n) | Timeframe |
|-------|----------------------|-----------|
| BTC-USD | 67 minutes | 1-minute bars |
| ETH-USD | 61 minutes | 1-minute bars |
| BNB-USD | 62 minutes | 1-minute bars |
| ADA-USD | 47 minutes | 1-minute bars |

### Performance Metrics Calculated
- Net Profit (%)
- Profit Factor (Gross Profits / Gross Losses)
- Win Rate (%)
- Total Trades

---

## Installation

```bash
pip install numpy pandas scikit-learn yfinance
```

### Dependencies

| Library | Purpose |
|---------|---------|
| `numpy` | Polynomial fitting (`polyfit`, `polyval`) |
| `pandas` | Data manipulation and time series |
| `scikit-learn` | `StandardScaler` for feature normalization |
| `yfinance` | Market data download (optional) |

---

## Usage

```bash
python code.py
```

The script will:
1. Load/download minute-level crypto data
2. Create polynomial features with optimal lookback per asset
3. Train the PAR model on the first 50% of data
4. Generate predictions and bands on the remaining 50%
5. Output performance metrics (Net Profit, Profit Factor, Win Rate, Total Trades)

---

## File Reference

| File | Description |
|------|-------------|
| `code.py` | Main strategy implementation — feature engineering, model training, signal generation, backtesting |
| `Intraday_trading_of_cryptocurrencies_using_polynom.pdf` | Primary research paper — cryptocurrency intraday trading with polynomial regression |
| `Polynomial_Moving_Regression_Band_Stocks_Trading_S.pdf` | Regression band methodology for stocks trading |
| `strategy13_polynomial_regression.pdf` | Baseline polynomial regression strategy reference |
| `ArtIssykKul8.pdf` | Additional polynomial regression research |
| `IEEE_research.txt` | Link to IEEE publication: https://ieeexplore.ieee.org/abstract/document/9988398 |
| `amazon.in.txt` | Additional reference links (books, FMZ strategy, tutorials) |

---

## Research Papers

1. **Intraday Trading of Cryptocurrencies Using Polynomial Regression** — Direct basis for BTC/ETH/BNB/ADA configurations
2. **Polynomial Moving Regression Band Stocks Trading Strategy** — Origin of the ±1.5% band methodology
3. **IEEE Publication** ([link](https://ieeexplore.ieee.org/abstract/document/9988398)) — Peer-reviewed polynomial regression trading research

### Additional References
- [Trading with Regression Channel](https://www.amazon.com/Trading-Regression-Channel-Defining-Predicting/dp/1885439016) — Book on regression channel trading
- [FMZ Strategy #426323](https://www.fmz.com/lang/en/strategy/426323) — FMZ platform implementation
- [Polynomial Regression for Investment Forecasting](https://fastercapital.com/content/Polynomial-Regression--How-to-Use-Polynomial-Regression-for-Investment-Forecasting.html) — Tutorial

---

## Disclaimer

This project is for **educational and research purposes only**. Cryptocurrency trading involves substantial risk. Past backtest performance does not guarantee future results.
