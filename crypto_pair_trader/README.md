# Crypto Intraday Pair Trading System

A production-grade, modular intraday pair trading system for cryptocurrency markets. Trades statistically cointegrated crypto pairs using mean-reversion signals on minute-level candles. All positions are intraday — no overnight risk.

---

## Strategy Overview

**Core idea:** When two highly correlated/cointegrated crypto assets temporarily diverge from their historical spread relationship, bet on convergence.

```
1. Select cointegrated pairs   →  Engle-Granger + ADF + correlation + half-life
2. Compute spread              →  spread = price_A - β × price_B  (OLS hedge ratio)
3. Track z-score               →  z = (spread - μ) / σ  (rolling window)
4. Enter on divergence         →  |z| > 2.0 → go long cheap leg, short expensive leg
5. Exit on convergence         →  |z| < 0.5 → close both legs
6. Risk controls               →  stop loss, time exit, spread-widen protection, session close
```

**This is NOT:**
- HFT (holds minutes to hours, not microseconds)
- Arbitrage (statistical relationship, not guaranteed convergence)
- Directional (dollar-neutral, profits from spread mean-reversion)

---

## Architecture

```
crypto_pair_trader/
│
├── config/
│   ├── settings.yaml           # Master config — exchange, strategy, risk params
│   └── loader.py               # Frozen dataclass config with env-var overrides
│
├── pair_selection/
│   ├── selector.py             # Correlation, cointegration, ADF, half-life, ranking
│   └── spread.py               # Rolling spread, z-score, hedge ratio tracking
│
├── strategies/
│   └── mean_reversion.py       # Entry/exit logic, vol/trend filters, session mgmt
│
├── exchanges/
│   ├── base.py                 # Async CCXT wrapper (Binance/Bybit/OKX)
│   ├── factory.py              # Exchange factory
│   └── ws_stream.py            # WebSocket streaming (multi-exchange)
│
├── execution/
│   ├── paper.py                # Paper executor with slippage simulation
│   ├── live.py                 # Live executor with retry + partial fill handling
│   └── tracker.py              # Position lifecycle (open/close, PnL calculation)
│
├── risk/
│   └── manager.py              # Dollar-neutral sizing, daily loss cap, exposure limits
│
├── backtesting/
│   └── engine.py               # Event-driven backtester with full trade simulation
│
├── analytics/
│   └── metrics.py              # Sharpe, win rate, PF, drawdown, expectancy
│
├── database/
│   └── store.py                # SQLite/PostgreSQL — trades, signals, market data, PnL
│
├── dashboard/
│   └── app.py                  # Streamlit dashboard with live charts
│
├── utils/
│   ├── log.py                  # Rotating file + console structured logging
│   └── types.py                # Signal, TradeRecord, PairScore, Side, OrderStatus
│
├── main.py                     # Live/paper trading orchestrator
├── run_backtest.py             # Standalone backtest runner
├── run_paper_test.py           # Paper trading integration test
└── requirements.txt
```

---

## Quick Start

### 1. Install

```bash
cd crypto_pair_trader
pip install -r requirements.txt
```

### 2. Configure

Edit `config/settings.yaml`:

```yaml
mode: "paper"          # "paper" or "live"

exchange:
  name: "binance"      # binance | bybit | okx
  testnet: true
  api_key: ""          # or set EXCHANGE_API_KEY env var
  api_secret: ""       # or set EXCHANGE_API_SECRET env var
```

### 3. Run Backtest

```bash
python run_backtest.py
```

### 4. Run Paper Trading

```bash
# Live polling against Binance (no real orders)
python main.py

# Or replay historical data through paper engine
python run_paper_test.py
```

### 5. Run Live Trading

```bash
# In settings.yaml: mode: "live", testnet: false, add API keys
python main.py
```

### 6. Launch Dashboard

```bash
streamlit run dashboard/app.py
```

---

## Pair Selection Engine

The system automatically selects tradeable pairs from a configurable universe:

| Filter | Purpose | Default |
|---|---|---|
| Rolling correlation | Minimum co-movement | > 0.75 |
| Max correlation | Avoid near-identical pairs | < 0.995 |
| Engle-Granger cointegration | Long-run equilibrium | p < 0.05 |
| ADF stationarity on spread | Spread mean-reverts | p < 0.05 |
| Half-life (Ornstein-Uhlenbeck) | Speed of reversion | 5–200 candles |
| Daily volume | Liquidity floor | > $5M |
| Composite scoring | Weighted rank | Top N pairs selected |

Pairs are rescored every 60 minutes (configurable).

---

## Strategy Logic

### Entry Conditions (all must pass)
- `|z-score| > 2.0` (spread diverged from mean)
- Volatility filter: short-term spread vol < 3× long-term vol
- Trend filter: spread not trending too strongly (linear regression slope check)
- Not near session end
- Open pairs < max (default 3)

### Exit Conditions (any triggers)
| Exit Type | Condition | Avg PnL (backtest) |
|---|---|---|
| **Mean reversion** | `\|z\| < 0.5` | +$6.71 |
| **Stop loss** | `\|z\| > 4.0` | -$79.44 |
| **Time exit** | Held > 240 min | -$90.99 |
| **Spread widen** | Current std > 2× entry std | -$61.35 |
| **Session close** | UTC 23:45 | -$1.39 |

### Position Sizing
- Dollar-neutral: notional_A ≈ notional_B
- Max $10,000 per leg (configurable)
- Max 20% of capital per pair
- Max 60% total portfolio exposure

---

## Backtest Results

**7-day backtest on LINK/AVAX (best cointegrated pair):**

| Metric | Value |
|---|---|
| Total Trades | 55 |
| Win Rate | 72.7% |
| Total PnL | +$91.17 |
| Profit Factor | 1.191 |
| Max Drawdown | -0.81% |
| Avg Trade Duration | 60 min |
| Max Win Streak | 11 |
| Max Loss Streak | 2 |

**Paper trading replay (55 trades, full pipeline with slippage):**

| Metric | Value |
|---|---|
| Total Trades | 55 |
| Win Rate | 56.4% |
| Total PnL | -$85.94 |
| Profit Factor | 0.845 |
| Gross Profit | $468.45 |
| Gross Loss | $554.40 |
| DB Integrity | 55/55 trades persisted |

*Note: Paper replay includes realistic slippage and commissions. The mean-reversion signal is profitable on clean exits (+$6.71 avg), but stop-loss and spread-widen exits dominate losses. See "Tuning" section below.*

---

## Dashboard

The Streamlit dashboard provides:

- **Live spread & z-score charts** per active pair
- **Open positions** table with real-time PnL
- **Trade history** with color-coded PnL
- **Equity curve** with drawdown overlay
- **PnL distribution** histogram
- **Exit reason breakdown** pie chart
- **Risk metrics** sidebar (capital, daily loss, open pairs)

Auto-refreshes every 5 seconds.

---

## Configuration Reference

All parameters in `config/settings.yaml`:

<details>
<summary>Click to expand full config reference</summary>

```yaml
# ── Mode ───────────────────────────────────
mode: "paper"                    # paper | live

# ── Exchange ───────────────────────────────
exchange:
  name: "binance"                # binance | bybit | okx
  testnet: true
  api_key: ""                    # env: EXCHANGE_API_KEY
  api_secret: ""                 # env: EXCHANGE_API_SECRET
  passphrase: ""                 # OKX only, env: EXCHANGE_PASSPHRASE

# ── Data ───────────────────────────────────
data:
  timeframe: "5m"                # 1m | 3m | 5m | 15m
  history_days: 7
  use_websocket: true

# ── Pair Selection ─────────────────────────
pair_selection:
  universe: [...]                # List of symbols to consider
  min_correlation: 0.75
  cointegration_pvalue: 0.05
  adf_pvalue: 0.05
  min_half_life: 5               # candles
  max_half_life: 200
  hedge_ratio_window: 120
  min_daily_volume_usd: 5000000
  rescore_interval_minutes: 60
  max_pairs: 5

# ── Strategy ───────────────────────────────
strategy:
  zscore_entry: 2.0
  zscore_exit: 0.5
  zscore_stop: 4.0
  lookback: 60
  max_holding_minutes: 240
  spread_widening_mult: 2.0
  vol_filter_max_ratio: 3.0
  trend_filter_adx_thresh: 35

# ── Risk ───────────────────────────────────
risk:
  max_position_usd: 10000
  max_pair_exposure_pct: 0.20
  max_portfolio_exposure_pct: 0.6
  max_daily_loss_usd: 500
  max_open_pairs: 3
  dollar_neutral_tolerance: 0.05
  session_end_utc: "23:45"
  capital: 50000

# ── Backtest ───────────────────────────────
backtest:
  initial_capital: 50000
  commission_bps: 4
  slippage_bps: 3

# ── Database ───────────────────────────────
database:
  engine: "sqlite"               # sqlite | postgresql
  sqlite_path: "data/trades.db"
```

</details>

---

## Tuning Guide

### Parameters That Matter Most

| Parameter | Impact | Recommendation |
|---|---|---|
| `zscore_entry` | Trade frequency vs conviction | 2.0–2.5 (higher = fewer but better trades) |
| `zscore_stop` | Tail risk | 3.0–3.5 (tighter cuts losers faster) |
| `lookback` | Spread mean sensitivity | 40–80 (shorter = more reactive) |
| `cointegration_pvalue` | Pair quality filter | Keep ≤ 0.05 (strict = profitable) |
| `max_holding_minutes` | Stale trade cleanup | 120–180 (shorter = less time-exit bleed) |

### Walk-Forward Optimization

```
1. Split data: 5 days train / 2 days validate
2. Grid search over zscore_entry × zscore_stop × lookback
3. Rank by Sharpe ratio on validation set
4. Roll forward and repeat
5. Only deploy params stable across multiple windows
```

### Key Insight from Backtests

The system correctly identifies that **only strongly cointegrated pairs produce edge**:
- LINK/AVAX (coint_p = 0.0000): **+$91 profit, 72.7% WR**
- Pairs with coint_p > 0.05: **all lost money**

The strict `cointegration_pvalue: 0.05` filter is the most important parameter.

---

## Common Pitfalls in Intraday Pair Trading

1. **Overfitting lookback/thresholds** to a specific regime — use walk-forward, not single backtest
2. **Spread regime breaks** — cointegration can break during news; the spread-widen filter handles this
3. **Commission bleed** — 4bps round-trip on 50+ trades/week adds up fast; target maker rebates
4. **Hedge ratio drift** — β changes intraday; the system rescores every 60 min
5. **Survivorship bias** — only test on pairs that exist today, not delisted ones
6. **Correlation ≠ cointegration** — high correlation doesn't guarantee mean-reversion
7. **Overnight gap risk** — system auto-squares-off at session end to avoid this

---

## Future Improvements

- **Regime detection (HMM/clustering)** — adjust thresholds per market regime
- **ML spread prediction** — LSTM/Transformer to predict spread direction before z-score threshold
- **Reinforcement learning** — optimal entry/exit timing
- **Order book features** — bid-ask imbalance, depth as additional signals
- **Funding rate integration** — perp funding as mean-reversion catalyst
- **Multi-exchange execution** — arb the same pair across venues
- **Spectral clustering** — replace brute-force pair search with graph-based selection

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Exchange connectivity | CCXT (async) |
| Real-time data | WebSockets (native) |
| Statistics | statsmodels, scipy, numpy |
| Data handling | pandas |
| Database | SQLite (default) / PostgreSQL |
| Dashboard | Streamlit + Plotly |
| Logging | Python stdlib (rotating files) |
| Config | YAML + frozen dataclasses |

---

## License

For educational and research purposes. Use at your own risk. Not financial advice.
