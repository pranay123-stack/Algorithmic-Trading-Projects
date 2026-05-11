# Polybot — Automated Prediction Market Trading Engine

> Config-driven trading bot for [Polymarket](https://polymarket.com) that monitors live market data, evaluates declarative rules, and executes conditional limit orders on a CLOB-based prediction market (Polygon network).

---

## What This Project Demonstrates

| Skill Area | Implementation |
|---|---|
| **Async Python** | Full `asyncio`/`aiohttp` architecture — non-blocking polling, order execution, and notifications |
| **REST API Integration** | Polymarket CLOB API client with exponential-backoff retry, rate-limit handling, and structured error logging |
| **Web3 / Blockchain** | EIP-712 typed-data signing for Polygon transaction submission via `web3.py` and `eth_account` |
| **Trading Systems** | CLOB limit orders, order book interaction, position tracking, PnL accounting, fill simulation |
| **Config-Driven Architecture** | YAML rules engine with Pydantic v2 validation — no `eval()`, fully declarative |
| **Risk Management** | 6-layer pre-trade gate: position count, size, exposure, per-market loss, daily loss, balance |
| **Observability** | structlog (JSON/console), Prometheus metrics (15+ counters/gauges/histograms), SQLite+JSONL audit trail |
| **Notifications** | Telegram Bot API via raw `aiohttp` — async queue, formatted alerts, configurable event subscriptions |
| **Containerisation** | Multi-stage Docker build, non-root user, `docker-compose` with Prometheus monitoring stack |
| **Testing** | 60 tests via `pytest-asyncio` — unit tests for every module + end-to-end integration test |
| **Type Safety** | Full PEP 484 annotations, Pydantic models at boundaries, `mypy --strict` compatible |

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│  Polymarket  │────▶│   Market    │────▶│  Strategy  │────▶│   Risk   │────▶│ Executor │
│  CLOB API    │     │   Poller    │     │   Engine   │     │  Manager │     │Paper/Live│
└─────────────┘     └─────────────┘     └───────────┘     └──────────┘     └──────────┘
                          │                    │                │                 │
                          ▼                    ▼                ▼                 ▼
                    ┌──────────────────────────────────────────────────────────────┐
                    │                    Telemetry Layer                           │
                    │          structlog  ·  Prometheus  ·  Audit Log              │
                    └──────────────────────────────────────────────────────────────┘
                                               │
                                               ▼
                                      ┌────────────────┐
                                      │    Telegram     │
                                      │  Notifications  │
                                      └────────────────┘
```

**Data Flow:** REST Poll (5-10s) → Price Snapshots → Rule Evaluation (AND logic) → Risk Gate → Order Execution → Telegram Alert

---

## Project Structure

```
polybot-prediction-market-engine/
├── polybot/                    # Main package
│   ├── config/                 #   YAML loader + Pydantic settings (env override support)
│   │   ├── loader.py           #     POLYBOT_ env prefix, deep merge, type coercion
│   │   └── settings.py         #     15+ nested config models with validators
│   ├── data/                   #   Market data layer
│   │   ├── client.py           #     Async Polymarket CLOB REST client (retry, rate-limit)
│   │   └── poller.py           #     Async iterator polling loop (configurable interval)
│   ├── strategy/               #   Rules engine
│   │   ├── models.py           #     Pure condition evaluators (lt/le/gt/ge/eq/between)
│   │   └── engine.py           #     Rule orchestrator with per-(rule, market) cooldowns
│   ├── execution/              #   Order execution
│   │   ├── base.py             #     Abstract executor (ABC + async context manager)
│   │   ├── paper.py            #     Simulated fills, balance tracking, position management
│   │   └── live.py             #     Polymarket CLOB API + EIP-712 Polygon signing
│   ├── risk/                   #   Risk management
│   │   └── manager.py          #     6 pre-trade checks, daily loss halt, reset
│   ├── notifications/          #   Alerting
│   │   └── telegram.py         #     Async queue → Telegram Bot API (raw aiohttp)
│   ├── telemetry/              #   Observability
│   │   ├── logging.py          #     structlog (JSON prod / coloured dev)
│   │   ├── metrics.py          #     Prometheus counters, gauges, histograms
│   │   └── audit.py            #     SQLite + JSONL dual-write audit trail
│   ├── types.py                #   Domain types (enums, NamedTuples, dataclasses)
│   └── main.py                 #   CLI entrypoint + async main loop
├── tests/                      # Test suite (60 tests)
│   ├── conftest.py             #   Shared fixtures (markets, snapshots, rules)
│   ├── unit/                   #   Module-level unit tests
│   │   ├── test_config.py      #     Config loading, env overrides, validation
│   │   ├── test_types.py       #     Order fills, position MTM, immutability
│   │   ├── test_strategy_engine.py  # All operators, cooldowns, market filtering
│   │   ├── test_paper_executor.py   # Fills, cancellation, balance, positions
│   │   ├── test_risk_manager.py     # Each risk check independently
│   │   └── test_telegram.py    #     Message formatting, event filtering
│   └── integration/
│       └── test_polling_loop.py #    Full cycle: snapshot → signal → risk → order → fill
├── config/
│   └── example.yaml            # Annotated example configuration
├── Dockerfile                  # Multi-stage build (python:3.12-slim, non-root)
├── docker-compose.yml          # polybot + Prometheus monitoring
├── prometheus.yml              # Scrape config
├── pyproject.toml              # Build config, dependencies, tool settings
└── requirements.txt            # Pinned dependencies
```

---

## How the Rules Engine Works

Rules are declarative YAML — no Python code in config, no `eval()`:

```yaml
rules:
  - name: "cheap_yes_buy"
    conditions:
      - field: "yes_price"       # Available: yes_price, no_price, volume_24h, liquidity
        operator: "lt"           # Available: lt, le, gt, ge, eq, between
        value: 0.15
      - field: "volume_24h"
        operator: "gt"
        value: 5000
    action: "buy_yes"            # Available: buy_yes, buy_no, sell_yes, sell_no
    size_usdc: 25.0
    cooldown_seconds: 3600       # Prevent re-triggering for 1 hour
```

**Evaluation:** All conditions use AND logic. Each rule has an independent cooldown per market. Disabled rules are skipped. Rules can target a specific `market_id` or apply to all monitored markets.

**Supported condition fields and operators:**

| Field | Description | Example |
|---|---|---|
| `yes_price` | Current YES token price (0.0–1.0) | `lt 0.20` |
| `no_price` | Current NO token price (0.0–1.0) | `gt 0.80` |
| `volume_24h` | 24-hour trading volume (USDC) | `gt 10000` |
| `liquidity` | Current order book liquidity | `ge 5000` |
| any field | Range check | `between [0.30, 0.50]` |

---

## Risk Management

Every signal passes through 6 sequential checks before an order is placed:

```
Signal → [1] Position Count → [2] Position Size → [3] Total Exposure
       → [4] Per-Market Loss → [5] Daily Loss → [6] Balance Check → Order
```

| Check | Config Key | Default | Behaviour |
|---|---|---|---|
| Max open positions | `max_positions` | 10 | Reject if at limit |
| Single position cap | `max_position_size_usdc` | $100 | Reject if signal size exceeds |
| Total exposure cap | `max_total_exposure_usdc` | $500 | Reject if aggregate would exceed |
| Per-market loss | `max_loss_per_market_usdc` | $50 | Reject if unrealised loss on market exceeds |
| Daily loss halt | `daily_loss_limit_usdc` | $100 | **Halt all trading** for the day |
| Balance check | — | — | Reject if insufficient funds |

---

## Execution Modes

### Paper Mode (Simulated)

```bash
python -m polybot.main --mode paper --config config/example.yaml
```

- Uses `DemoPoller` with random-walk price simulation (no API needed)
- `PaperExecutor` simulates fills when price crosses limit orders
- Full position tracking, PnL accounting, and audit logging
- Works completely offline — ideal for testing strategies

**Example output:**
```
polybot_starting       mode=paper, version=0.1.0
polybot_running        markets=3, rules=3
signal_generated       rule=cheap_yes_buy, market=demo-weather, price=0.1061
order_placed           order_id=648ec452..., side=BUY, size=25.0
order_filled           fill_price=0.0929, size=25.0
shutdown_complete      cancelled_orders=0
```

### Live Mode (Polygon)

```bash
export POLYBOT_PRIVATE_KEY="0x..."
python -m polybot.main --mode live --config config/example.yaml
```

- Connects to Polymarket CLOB REST API (`clob.polymarket.com`)
- Signs orders using EIP-712 typed data via Polygon wallet
- Queries on-chain USDC balance
- Graceful shutdown: cancels all resting orders on SIGTERM/SIGINT

---

## Observability Stack

### Structured Logging (structlog)
- JSON output in live mode, coloured console in paper mode
- Every log includes: filename, function, line number, ISO timestamp
- Trace context for correlating events across async boundaries

### Prometheus Metrics
- **Counters:** `polls_total`, `signals_total`, `orders_total`, `fills_total`, `risk_rejections_total`
- **Gauges:** `balance_usdc`, `total_exposure_usdc`, `positions_open`, `pnl_realized`, `pnl_unrealized`
- **Histograms:** `poll_latency_seconds`
- Exposed on port 9090, scraped by Prometheus every 15s

### Audit Trail
- **Dual persistence:** SQLite (indexed queries) + JSONL sidecar (append-only)
- **Event types:** `SIGNAL_GENERATED`, `ORDER_PLACED`, `ORDER_FILLED`, `RISK_REJECTION`, `ORDER_CANCELLED`
- Full payload and trace ID for every event

---

## Quick Start

### Local

```bash
# Install
cd polybot-prediction-market-engine
pip install -e ".[dev]"

# Run paper trading (no API key needed)
python -m polybot.main --mode paper --config config/example.yaml

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=polybot --cov-report=term-missing
```

### Docker

```bash
# Paper mode
docker compose up -d

# With Telegram notifications
TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=yyy docker compose up -d
```

### Configuration

```bash
# Copy and edit config
cp config/example.yaml config/config.yaml

# Override any setting via environment variables
export POLYBOT_RISK__MAX_POSITIONS=5
export POLYBOT_POLLING__INTERVAL_SECONDS=10
export POLYBOT_TELEGRAM__BOT_TOKEN="your-bot-token"
```

---

## Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| Language | Python 3.10+ | Full type annotations, modern syntax |
| Async I/O | `asyncio` / `aiohttp` | Non-blocking HTTP polling and execution |
| Config | `pydantic` v2 / `pyyaml` | Validated, typed configuration |
| Blockchain | `web3.py` / `eth_account` | Polygon RPC + EIP-712 order signing |
| Logging | `structlog` | Structured JSON/console logging |
| Metrics | `prometheus_client` | Counters, gauges, histograms |
| Database | `aiosqlite` | Async audit trail persistence |
| Testing | `pytest` / `pytest-asyncio` | 60 tests, async-native |
| Linting | `ruff` | Fast Python linter |
| Types | `mypy` (strict) | Static type checking |
| Container | Docker (multi-stage) | Production-ready deployment |
| Monitoring | Prometheus | Metrics collection and alerting |

---

## Test Results

```
tests/integration/test_polling_loop.py::test_full_trading_cycle      PASSED
tests/unit/test_config.py::TestConfigLoader (5 tests)                PASSED
tests/unit/test_config.py::TestConditionValidation (4 tests)         PASSED
tests/unit/test_config.py::TestRuleValidation (2 tests)              PASSED
tests/unit/test_paper_executor.py::TestPaperExecutor (9 tests)       PASSED
tests/unit/test_risk_manager.py::TestRiskManager (9 tests)           PASSED
tests/unit/test_strategy_engine.py::TestEvaluateCondition (9 tests)  PASSED
tests/unit/test_strategy_engine.py::TestEvaluateRule (2 tests)       PASSED
tests/unit/test_strategy_engine.py::TestStrategyEngine (6 tests)     PASSED
tests/unit/test_telegram.py (5 tests)                                PASSED
tests/unit/test_types.py (8 tests)                                   PASSED

60 passed in 0.52s
```

---

## Disclaimer

This project is for **educational and portfolio demonstration purposes**. It showcases software engineering patterns for real-time trading systems. Use at your own risk. Always start with paper trading mode. Never risk funds you cannot afford to lose.
