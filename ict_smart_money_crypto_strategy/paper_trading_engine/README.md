# ICT Smart Money Crypto Paper Trading Engine

A production-ready paper trading engine implementing ICT (Inner Circle Trader) methodology for cryptocurrency markets with institutional-grade risk management.

## Features

- **ICT Indicators**: Fair Value Gaps (FVG), Order Blocks (OB), Liquidity Sweeps
- **Risk Management**: Position sizing, daily loss limits, drawdown monitoring
- **Real-time Trading**: Live market data via CCXT (Binance/testnet support)
- **Telegram Integration**: Real-time trade notifications and alerts
- **Hot-reload Configuration**: Update strategy parameters without restart
- **Comprehensive Logging**: Structured logging with multiple output formats

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r config/requirements.txt

# Configure environment
cp config/.env.example .env
# Edit .env with your API keys and settings

# Configure strategy parameters
vim config/strategy_params.json
```

### Running

```bash
# Simple way (from project root)
python run.py

# Alternative way
python -m src.core_trading_strategy.paper_trader

# With custom config
python run.py --config config/custom_params.json

# Run tests
python tests/run_all_tests.py
```

## Project Structure

```
paper_trading_engine/
├── run.py                        # Main runner (easy start)
├── src/
│   ├── core_trading_strategy/    # All trading-related code
│   │   ├── paper_trader.py       # Main orchestrator
│   │   ├── indicators.py         # ICT indicators (FVG, OB, Sweeps)
│   │   ├── strategy.py           # Signal generation
│   │   ├── risk_management.py    # Position sizing, limits
│   │   ├── order_management.py   # Order execution
│   │   ├── position_management.py # Position tracking
│   │   ├── entry_management.py   # Entry validation
│   │   ├── exit_management.py    # Exit monitoring
│   │   ├── telegram_bot.py       # Notifications
│   │   ├── market_utils.py       # Common utilities
│   │   └── data_manager.py       # Market data fetching
│   ├── logger/                   # Logging
│   │   └── logger.py
│   └── config/                   # Configuration
│       ├── config.py
│       └── config_loader.py
├── config/                       # Configuration files
│   ├── strategy_params.json
│   ├── requirements.txt
│   └── .env.example
├── tests/                        # Unit tests
│   ├── test_*.py
│   └── run_all_tests.py
├── scripts/                      # Deployment & setup scripts
│   ├── setup.sh
│   ├── deploy.sh
│   └── paper-trader.service
├── trading_data/                 # Runtime data
│   ├── logs/
│   └── trades/
└── docs/                         # Documentation

```

## Configuration

### Strategy Parameters (`config/strategy_params.json`)

```json
{
  "atr_threshold": 0.003,
  "risk_per_trade": 0.01,
  "stop_loss_atr_multiplier": 1.5,
  "take_profit_atr_multiplier": 3.0,
  "max_holding_bars": 80
}
```

### Environment Variables (`.env`)

```bash
# Exchange API
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
USE_TESTNET=True

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading
INITIAL_CAPITAL=10000
LEVERAGE=1
```

## Risk Management

- **Position Sizing**: Automatic calculation based on stop distance
- **Daily Loss Limit**: 5% max daily drawdown
- **Max Drawdown Alert**: 25% from peak capital
- **Risk Per Trade**: Configurable (default 1%)
- **Leverage**: Configurable multiplier

## Strategy Logic

### Entry Signals
- **LONG**: Bullish bias + (FVG Bullish OR Order Block Bullish OR Liquidity Sweep Low)
- **SHORT**: Bearish bias + (FVG Bearish OR Order Block Bearish OR Liquidity Sweep High)

### Exit Conditions
1. Stop Loss hit (priority 1)
2. Take Profit hit (priority 2)
3. Timeout after max holding period (priority 3)

## Development

### Running Tests

```bash
# All tests
python tests/run_all_tests.py

# Individual test modules
python -m pytest tests/test_indicators.py
python -m pytest tests/test_strategy.py
python -m pytest tests/test_risk_management.py
```

### Adding New Features

1. Create module in appropriate `src/` subdirectory
2. Add tests in `tests/`
3. Update imports in `__init__.py` files
4. Document in code with docstrings

## Deployment

### Local Daemon (systemd)

```bash
# Install service
sudo cp scripts/paper-trader.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable paper-trader
sudo systemctl start paper-trader

# Check status
sudo systemctl status paper-trader
```

### Manual Deployment

```bash
# Run deployment script
bash scripts/deploy.sh
```

## Monitoring

### Logs
- **Location**: `trading_data/logs/`
- **Format**: Timestamped with color-coded levels
- **Rotation**: Automatic daily rotation

### Trade History
- **Location**: `trading_data/trades/`
- **Format**: JSON with full trade details
- **Frequency**: Saved after each session

## Performance Metrics

The engine tracks:
- Win rate
- Average profit/loss
- Maximum drawdown
- Sharpe ratio
- Total P&L
- Number of trades
- Average holding time

## Troubleshooting

### Common Issues

**Import Errors**: Ensure you're running from project root
```bash
python -m src.core_trading_strategy.paper_trader  # Correct
python src/core_trading_strategy/paper_trader.py  # Wrong
```

**API Connection Failed**: Check API keys in `.env` and testnet setting

**No Trades Executing**: Verify strategy parameters in `config/strategy_params.json`

**Permission Errors**: Ensure data directories are writable

## Architecture

The engine follows a modular, layered architecture:

1. **Data Layer**: Market data fetching and caching
2. **Indicator Layer**: ICT indicator calculations
3. **Strategy Layer**: Signal generation and validation
4. **Risk Layer**: Position sizing and risk checks
5. **Trading Layer**: Order and position management
6. **Integration Layer**: Orchestration and notifications

## License

Proprietary - All rights reserved

## Support

For issues or questions, contact the development team.
