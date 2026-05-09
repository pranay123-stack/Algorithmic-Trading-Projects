# Quick Reference Guide

## Common Commands

### Running the Engine

```bash
# From project root
python -m src.core.paper_trader

# With custom config
python -m src.core.paper_trader --config config/custom_params.json

# Run tests
python tests/run_all_tests.py
```

### File Locations

| Item | Location |
|------|----------|
| Source code | `src/` |
| Configuration | `config/` |
| Logs | `trading_data/logs/` |
| Trade history | `trading_data/trades/` |
| Tests | `tests/` |
| Scripts | `scripts/` |
| Documentation | `docs/` |

## Module Import Reference

```python
# Core modules
from src.core.config import Config
from src.core.config_loader import ConfigLoader, get_config_loader
from src.core.data_manager import DataManager
from src.core.logger import get_logger

# Indicators
from src.indicators.indicators import ICTIndicators
from src.indicators.strategy import TradingStrategy

# Trading
from src.trading.order_management import OrderManager, OrderType
from src.trading.position_management import PositionManager
from src.trading.entry_management import EntryManager
from src.trading.exit_management import ExitManager

# Risk
from src.risk.risk_management import RiskManager

# Notifications
from src.notifications.telegram_bot import TelegramBot

# Utils
from src.utils.market_utils import MarketUtils
```

## Configuration Quick Reference

### Strategy Parameters (`config/strategy_params.json`)

```json
{
  "atr_threshold": 0.003,           // Min volatility for trade (0.3%)
  "risk_per_trade": 0.01,           // Risk per trade (1%)
  "stop_loss_atr_multiplier": 1.5,  // Stop distance in ATR units
  "take_profit_atr_multiplier": 3.0, // Target distance in ATR units
  "max_holding_bars": 80            // Max candles to hold position
}
```

### Environment Variables (`.env`)

```bash
# Exchange
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
USE_TESTNET=True

# Telegram
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading
INITIAL_CAPITAL=10000
LEVERAGE=1
```

## Key Functions Reference

### DataManager

```python
dm = DataManager()
df = dm.fetch_ohlcv(symbol='BTC/USDT', timeframe='15m', limit=500)
```

### ICTIndicators

```python
indicators = ICTIndicators()
df = indicators.calculate_fvg(df)
df = indicators.calculate_order_blocks(df)
df = indicators.calculate_liquidity_sweeps(df)
df = indicators.calculate_daily_bias(df)
```

### TradingStrategy

```python
strategy = TradingStrategy(atr_threshold=0.003, risk_per_trade=0.01)
signal = strategy.generate_signal(df)
# Returns: {'type': 'LONG/SHORT', 'entry': float, 'stop': float, 'target': float, ...}
```

### RiskManager

```python
rm = RiskManager(initial_capital=10000, max_daily_loss_pct=0.05)
size = rm.calculate_position_size(entry=50000, stop=49000, direction='long')
limits = rm.check_risk_limits()
```

### OrderManager

```python
om = OrderManager()
order = om.create_order(
    symbol='BTC/USDT',
    order_type=OrderType.MARKET,
    side='buy',
    quantity=0.1,
    price=50000
)
filled = om.execute_order(order, current_price=50000)
```

### MarketUtils

```python
from src.utils.market_utils import MarketUtils

# Slippage
price = MarketUtils.calculate_slippage(50000, 'buy', 0.0005)

# Position sizing
size = MarketUtils.calculate_position_size(10000, 0.01, 50000, 49000, 1)

# P&L
pnl = MarketUtils.calculate_pnl('long', 50000, 51000, 0.1)

# Commission
comm = MarketUtils.calculate_commission(0.1, 50000, 0.0004)
```

## Logging Reference

```python
from src.core.logger import get_logger

logger = get_logger(__name__)

logger.debug("Detailed diagnostic info")
logger.info("Normal operation confirmation")
logger.warning("Unexpected but recoverable")
logger.error("Serious problem")
logger.critical("System failure")
```

## Directory Commands

```bash
# Create data directories
mkdir -p trading_data/logs trading_data/trades

# View recent logs
tail -f trading_data/logs/paper_trading_$(date +%Y%m%d)*.log

# View trade history
ls -lh trading_data/trades/

# Clean old logs (keep last 7 days)
find trading_data/logs -name "*.log" -mtime +7 -delete
```

## Systemd Service

```bash
# Install
sudo cp scripts/paper-trader.service /etc/systemd/system/
sudo systemctl daemon-reload

# Start/Stop
sudo systemctl start paper-trader
sudo systemctl stop paper-trader

# Enable on boot
sudo systemctl enable paper-trader

# Check status
sudo systemctl status paper-trader

# View logs
sudo journalctl -u paper-trader -f
```

## Testing Commands

```bash
# Run all tests
python tests/run_all_tests.py

# Run specific test
python -m pytest tests/test_indicators.py -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

## Troubleshooting

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**: Run from project root
```bash
cd /path/to/paper_trading_engine
python -m src.core.paper_trader
```

### API Connection Failed
**Problem**: Cannot connect to exchange

**Solution**:
1. Check `.env` file exists and has correct keys
2. Verify `USE_TESTNET=True` for testing
3. Check network connectivity

### No Trades Executing
**Problem**: Engine runs but no trades

**Solution**:
1. Check `atr_threshold` not too high
2. Verify market volatility sufficient
3. Check logs for signal rejections
4. Ensure sufficient capital

### Permission Errors
**Problem**: Cannot write to data directories

**Solution**:
```bash
chmod -R 755 data/
```

## Performance Tips

1. **Reduce API calls**: Increase cache duration in DataManager
2. **Optimize indicator lookback**: Use smaller window sizes
3. **Limit log verbosity**: Set log level to WARNING in production
4. **Archive old data**: Move old trade files to archive folder

## Security Checklist

- [ ] `.env` file not committed to git
- [ ] API keys have appropriate permissions
- [ ] Testnet enabled for initial testing
- [ ] Log files don't contain sensitive data
- [ ] File permissions properly set (755 for dirs, 644 for files)
