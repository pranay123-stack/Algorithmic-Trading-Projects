# Prediction Market Arbitrage Bot

An AI-powered cross-platform arbitrage detection system that monitors **Kalshi** and **Polymarket** prediction markets in real time, identifies matching markets using NLP, detects pricing inefficiencies, and sends instant alerts via Telegram or Discord.

---

## Table of Contents

- [Overview](#overview)
- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Intelligent Market Matching](#intelligent-market-matching)
- [Arbitrage Detection Logic](#arbitrage-detection-logic)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Example Output](#example-output)
- [API Reference](#api-reference)
- [Extending the Bot](#extending-the-bot)
- [Disclaimer](#disclaimer)

---

## Overview

Prediction markets like Kalshi and Polymarket allow users to trade on the outcomes of real-world events. Because these platforms operate independently with separate order books, price discrepancies can arise for the same event — creating arbitrage opportunities.

This bot automates the entire pipeline:

1. **Ingests** live market data from both platforms via their public REST APIs
2. **Matches** equivalent markets across platforms using sentence embeddings (NLP)
3. **Detects** arbitrage where buying YES on one platform + NO on the other costs less than $1 (guaranteed profit)
4. **Alerts** you in real time via Telegram or Discord
5. **Displays** a live terminal dashboard using Rich

---

## How It Works

### The Arbitrage Principle

Binary prediction markets sell YES and NO contracts. If an event occurs, YES pays $1; if not, NO pays $1. On a single platform, YES + NO prices always sum to ~$1. But across platforms, they don't have to:

```
Platform A:  YES = $0.42
Platform B:  NO  = $0.52  (equivalent to YES = $0.48)

Cost to buy both:  $0.42 + $0.52 = $0.94
Guaranteed payout: $1.00
Profit:            $0.06 per dollar pair (6.4% return)
```

The bot scans for exactly these situations across hundreds of markets simultaneously.

### The Matching Challenge

The hard problem isn't the math — it's figuring out which markets on Kalshi correspond to which markets on Polymarket. The same event can be worded very differently:

| Kalshi | Polymarket |
|--------|------------|
| "Will Argentina win the 2026 FIFA World Cup?" | "Will Argentina become 2026 World Cup champions?" |
| "Will Bitcoin be above $100k on Dec 31?" | "BTC price over $100,000 end of year?" |
| "Will the Fed cut rates in June?" | "Federal Reserve interest rate cut at June FOMC meeting?" |

This bot uses **sentence embeddings** to solve this — see [Intelligent Market Matching](#intelligent-market-matching).

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Main Orchestrator                     │
│                  (async polling loop)                    │
├───────────┬───────────┬──────────────┬──────────────────┤
│           │           │              │                  │
│  Kalshi   │ Polymarket│   Market     │   Arbitrage      │
│  Client   │  Client   │   Matcher    │   Detector       │
│           │           │   (NLP)      │                  │
│ REST API  │ Gamma API │  Sentence    │  Cross-platform  │
│ /markets  │ /markets  │  Transformers│  spread calc     │
│ /orderbook│ CLOB /book│  + Heuristic │                  │
│           │           │  Filters     │                  │
├───────────┴───────────┴──────────────┴──────────────────┤
│                                                         │
│                    Alert System                          │
│              Telegram + Discord Webhooks                 │
│                                                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│                  Rich Terminal Dashboard                 │
│          (live-updating tables with matches & arbs)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Data Flow Per Cycle

```
1. Fetch all open markets from Kalshi (/trade-api/v2/markets)
2. Fetch all active markets from Polymarket (Gamma API)
3. Normalize titles → compute sentence embeddings → cosine similarity matrix
4. Filter matches above threshold + heuristic cross-checks
5. Fetch order books for matched markets (concurrent)
6. Calculate arb spreads for both directions
7. Filter opportunities above minimum spread
8. Send alerts + update dashboard
9. Sleep → repeat
```

---

## Intelligent Market Matching

The market matching layer is the core intelligence of the bot. It uses a three-stage pipeline:

### Stage 1: Title Normalization

Before comparing, titles are cleaned and standardized:

- Lowercased, question marks stripped
- **Synonym normalization**: "champion/championship/victory/triumphant" → "win", "elected/election/vote" → "election", "exceed/above/over/greater than" → "above"
- **Filler word removal**: "will", "the", "a", "be", "in", "on", etc.
- **Date normalization**: various date formats → standardized form

```python
# Before normalization
"Will Argentina become the 2026 World Cup champions?"
# After normalization
"argentina 2026 world cup win"
```

### Stage 2: Semantic Embedding Similarity

Uses the `all-MiniLM-L6-v2` model from sentence-transformers (384-dimensional embeddings, ~80MB model):

- Encodes all normalized titles into dense vectors
- Computes full cosine similarity matrix (Kalshi × Polymarket)
- Filters pairs above the configurable threshold (default: 0.82)

This catches semantic equivalence that keyword matching would miss:
- "Fed rate cut" ↔ "Federal Reserve reduces interest rates" → similarity: 0.91

### Stage 3: Heuristic Cross-Checks

Embedding similarity alone can produce false positives. The heuristic layer catches these:

- **Number mismatch filter**: If both titles contain numbers but none overlap, reject the match. This prevents matching "BTC above $70k" with "BTC above $100k" (same topic, different markets).
- **Greedy deduplication**: Each market appears in at most one match (the highest-similarity one), preventing one popular event from consuming multiple match slots.

---

## Arbitrage Detection Logic

For each matched market pair, the detector checks **two directions**:

### Direction 1: Buy YES on Kalshi + Buy NO on Polymarket
```
cost = kalshi_yes_ask + polymarket_no_ask
spread = (1.0 - cost) × 100%
profit_per_dollar = (1.0 - cost) / cost
```

### Direction 2: Buy YES on Polymarket + Buy NO on Kalshi
```
cost = polymarket_yes_ask + kalshi_no_ask
spread = (1.0 - cost) × 100%
profit_per_dollar = (1.0 - cost) / cost
```

**Price sources** (in priority order):
1. **Order book best ask** — actual price you'd pay to fill
2. **Mid price** — (best bid + best ask) / 2
3. **Last/indicative price** — from the market listing

Only opportunities with `spread >= MIN_ARB_SPREAD` (default 1%) are surfaced.

---

## Project Structure

```
prediction-market-arbitrage-bot/
│
├── run.py                              # Entry point script
├── pyproject.toml                      # Package metadata + CLI entry point
├── requirements.txt                    # Python dependencies
├── .env.example                        # Configuration template
├── .gitignore
│
└── prediction_arb/                     # Main package
    ├── __init__.py
    ├── config.py                       # Environment-based configuration
    ├── models.py                       # Data models
    │   ├── Platform                    #   Enum: kalshi | polymarket
    │   ├── OrderBookLevel              #   Single price/size level
    │   ├── OrderBook                   #   Bids + asks with best price helpers
    │   ├── Market                      #   Platform-agnostic market representation
    │   ├── MarketMatch                 #   Paired markets + similarity score
    │   └── ArbOpportunity              #   Detected arb with full details
    │
    ├── kalshi_client.py                # Kalshi REST API client
    │   ├── fetch_markets()             #   Paginated market listing
    │   ├── fetch_all_markets()         #   Auto-paginate all open markets
    │   └── fetch_orderbook()           #   Order book for a ticker
    │
    ├── polymarket_client.py            # Polymarket Gamma + CLOB client
    │   ├── fetch_markets()             #   Paginated market listing (Gamma)
    │   ├── fetch_all_markets()         #   Auto-paginate all active markets
    │   └── fetch_orderbook()           #   Order book for a token (CLOB)
    │
    ├── market_matcher.py               # NLP-based market matching
    │   ├── normalize_title()           #   Title cleaning + synonym replacement
    │   ├── compute_embeddings()        #   Sentence transformer encoding
    │   ├── cosine_similarity_matrix()  #   Batch similarity computation
    │   └── find_matches()              #   Full matching pipeline
    │
    ├── arbitrage.py                    # Arbitrage detection engine
    │   └── detect_arbitrage()          #   Cross-platform spread analysis
    │
    ├── alerter.py                      # Alert dispatch system
    │   ├── send_telegram()             #   Telegram Bot API
    │   ├── send_discord()              #   Discord webhook
    │   └── send_alerts()               #   Dispatch to all channels
    │
    └── main.py                         # Async orchestrator
        ├── run_cycle()                 #   Single scan cycle
        ├── main()                      #   Polling loop with graceful shutdown
        └── cli()                       #   CLI entry point with logging
```

---

## Installation

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# Clone the repo
git clone https://github.com/pranay123-stack/Algorithmic-Trading-Projects.git
cd Algorithmic-Trading-Projects/prediction-market-arbitrage-bot

# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your Telegram/Discord credentials
```

### Install as Package (optional)

```bash
pip install -e .
# Now you can run: arb-bot
```

---

## Configuration

All configuration is via environment variables (`.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token (get from [@BotFather](https://t.me/BotFather)) |
| `TELEGRAM_CHAT_ID` | — | Telegram chat/group ID to send alerts to |
| `DISCORD_WEBHOOK_URL` | — | Discord channel webhook URL |
| `ALERT_CHANNELS` | `telegram` | Comma-separated: `telegram`, `discord`, or both |
| `MIN_ARB_SPREAD` | `1.0` | Minimum spread (%) to trigger an alert |
| `MATCH_THRESHOLD` | `0.82` | Cosine similarity threshold for market matching (0.0–1.0) |
| `POLL_INTERVAL` | `30` | Seconds between scan cycles |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model name |

### Setting Up Telegram Alerts

1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → follow prompts
2. Copy the bot token → paste into `TELEGRAM_BOT_TOKEN`
3. Add the bot to a group or start a DM with it
4. Get your chat ID: visit `https://api.telegram.org/bot<TOKEN>/getUpdates` after sending a message
5. Paste the chat ID into `TELEGRAM_CHAT_ID`

### Setting Up Discord Alerts

1. Open Discord → Server Settings → Integrations → Webhooks → New Webhook
2. Copy the webhook URL → paste into `DISCORD_WEBHOOK_URL`
3. Add `discord` to `ALERT_CHANNELS`

---

## Usage

### Run the Bot

```bash
# Using the script
python run.py

# Or if installed as a package
arb-bot
```

The bot will:
- Load the sentence transformer model on first run (~80MB download)
- Begin polling both platforms every `POLL_INTERVAL` seconds
- Display a live Rich dashboard in the terminal
- Send alerts when arbitrage opportunities are found
- Log all activity to `arb_bot.log`

### Stop the Bot

Press `Ctrl+C` for graceful shutdown.

---

## Example Output

### Terminal Dashboard

```
Prediction Market Arbitrage Bot | Cycle 5 | 14:32:18 UTC
Poll interval: 30s | Min spread: 1.0%

              Matched Markets (12)
┌───────┬──────────────────────────┬──────────────────────────┬───────┬───────┐
│ Sim   │ Kalshi                   │ Polymarket               │ K.Yes │ P.Yes │
├───────┼──────────────────────────┼──────────────────────────┼───────┼───────┤
│ 0.952 │ Will Bitcoin be above    │ BTC price over $100k     │ 0.62  │ 0.65  │
│       │ $100k on Dec 31?         │ end of year?             │       │       │
├───────┼──────────────────────────┼──────────────────────────┼───────┼───────┤
│ 0.941 │ Will the Fed cut rates   │ Federal Reserve rate cut │ 0.45  │ 0.42  │
│       │ in June?                 │ at June FOMC?            │       │       │
├───────┼──────────────────────────┼──────────────────────────┼───────┼───────┤
│ 0.897 │ Will Argentina win the   │ Argentina 2026 World Cup │ 0.18  │ 0.20  │
│       │ 2026 FIFA World Cup?     │ champions?               │       │       │
└───────┴──────────────────────────┴──────────────────────────┴───────┴───────┘

              Arbitrage Opportunities (1)
┌─────────┬──────────────────────────────┬────────┬────────┬────────┬────────┐
│ Spread  │ Direction                    │ K.Price│ P.Price│ $/$    │ Market │
├─────────┼──────────────────────────────┼────────┼────────┼────────┼────────┤
│ +2.10%  │ BUY YES on Kalshi + BUY NO   │ 0.420  │ 0.560  │ 0.0214 │ Will   │
│         │ on Polymarket                │        │        │        │ BTC... │
└─────────┴──────────────────────────────┴────────┴────────┴────────┴────────┘
```

### Telegram/Discord Alert

```
========================================
ARBITRAGE ALERT | +2.10%
========================================
Direction: BUY YES on Kalshi + BUY NO on Polymarket
Kalshi price: 0.420
Polymarket price: 0.560
Profit per $1: $0.0214

Kalshi: Will Bitcoin be above $100k on Dec 31?
  ID: BTC-100K-DEC31
Polymarket: BTC price over $100k end of year?
  ID: 0x3f2a...

Match similarity: 0.952
Detected at: 2026-05-13 14:32 UTC
========================================
```

---

## API Reference

### Kalshi (Public, No Auth Required)

| Endpoint | Purpose |
|----------|---------|
| `GET /trade-api/v2/markets` | List all markets (paginated) |
| `GET /trade-api/v2/markets/{ticker}/orderbook` | Order book for a market |

Rate limit: 30 requests/second for public data.

### Polymarket

| Endpoint | Purpose |
|----------|---------|
| `GET gamma-api.polymarket.com/markets` | List all markets (Gamma API) |
| `GET clob.polymarket.com/book?token_id=X` | Order book for a token (CLOB API) |

No authentication required for market data.

---

## Extending the Bot

### Adding a New Platform

1. Create `prediction_arb/newplatform_client.py` with `fetch_all_markets()` and `fetch_orderbook()`
2. Return `Market` objects with `Platform.NEW_PLATFORM`
3. Add the fetch call in `main.py:run_cycle()`
4. The matcher and arb detector work with any `Market` objects

### Using a Different Embedding Model

Change `EMBEDDING_MODEL` in `.env`. Any model supported by `sentence-transformers` works:

- `all-MiniLM-L6-v2` — fast, 80MB (default)
- `all-mpnet-base-v2` — more accurate, 420MB
- `paraphrase-multilingual-MiniLM-L12-v2` — multilingual support

### Adding More Alert Channels

1. Add a `send_X()` function in `alerter.py`
2. Add the channel name to the dispatch logic in `send_alerts()`
3. Add config variables in `config.py`

---

## Disclaimer

This tool is for **educational and research purposes only**. Prediction market trading involves financial risk. This bot detects opportunities but does **not** execute trades automatically. Always verify opportunities manually before acting. The authors are not responsible for any financial losses. Check your local regulations regarding prediction market trading.
