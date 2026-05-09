# Architecture Documentation

## Overview

The ICT Smart Money Crypto Paper Trading Engine follows a modular, layered architecture designed for maintainability, testability, and scalability.

## Directory Structure

```
paper_trading_engine/
├── src/                    # Source code
│   ├── core/              # Core infrastructure
│   ├── indicators/        # ICT indicators & strategy
│   ├── trading/           # Order & position management
│   ├── risk/              # Risk management
│   ├── notifications/     # External notifications
│   └── utils/             # Common utilities
├── config/                # Configuration files
├── tests/                 # Unit tests
├── scripts/               # Deployment scripts
├── data/                  # Runtime data
│   ├── logs/             # Application logs
│   └── trades/           # Trade history
└── docs/                 # Documentation
```

## Module Organization

### 1. Core Infrastructure (`src/core/`)

**Purpose**: Foundational components used across the system

**Modules**:
- `config.py`: Static configuration constants
- `config_loader.py`: Hot-reload configuration management
- `data_manager.py`: Market data fetching and caching
- `logger.py`: Centralized logging with formatters
- `paper_trader.py`: Main orchestrator

**Dependencies**: None (except external libraries)

**Used By**: All other modules

### 2. Indicators (`src/indicators/`)

**Purpose**: ICT indicator calculations and signal generation

**Modules**:
- `indicators.py`: Fair Value Gaps, Order Blocks, Liquidity Sweeps
- `strategy.py`: Trading signal generation and validation

**Dependencies**:
- `src.core.logger`

**Used By**:
- `src.core.paper_trader`

### 3. Trading (`src/trading/`)

**Purpose**: Order execution and position lifecycle management

**Modules**:
- `order_management.py`: Order creation, validation, and execution
- `position_management.py`: Position tracking and P&L calculation
- `entry_management.py`: Entry signal validation and execution
- `exit_management.py`: Exit monitoring and execution

**Dependencies**:
- `src.core.logger`
- `src.utils.market_utils`

**Used By**:
- `src.core.paper_trader`

### 4. Risk (`src/risk/`)

**Purpose**: Position sizing and risk limit enforcement

**Modules**:
- `risk_management.py`: Position sizing, daily loss limits, drawdown tracking

**Dependencies**:
- `src.core.logger`
- `src.utils.market_utils`

**Used By**:
- `src.core.paper_trader`
- `src.trading.entry_management`

### 5. Notifications (`src/notifications/`)

**Purpose**: External notifications and alerts

**Modules**:
- `telegram_bot.py`: Telegram integration for trade alerts

**Dependencies**:
- `src.core.logger`

**Used By**:
- `src.core.paper_trader`

### 6. Utils (`src/utils/`)

**Purpose**: Common utility functions to eliminate code duplication

**Modules**:
- `market_utils.py`: Slippage, position sizing, P&L calculations

**Dependencies**: None

**Used By**:
- `src.trading.*`
- `src.risk.*`

## Data Flow

```
Market Data → Indicators → Strategy → Risk Manager → Entry Manager → Order Manager
                                                                          ↓
Exit Manager ← Position Manager ← Order Execution ← Order Manager
    ↓
Telegram Bot (notifications)
```

### Detailed Flow

1. **Data Acquisition**
   - `DataManager` fetches OHLCV data from exchange
   - Caches data to reduce API calls

2. **Indicator Calculation**
   - `ICTIndicators` processes market data
   - Calculates FVG, OB, Liquidity Sweeps, Bias

3. **Signal Generation**
   - `TradingStrategy` evaluates indicator conditions
   - Generates LONG/SHORT signals with entry/stop/target levels

4. **Risk Validation**
   - `RiskManager` checks daily loss limits
   - Calculates position size based on risk parameters
   - Validates risk/reward ratios

5. **Entry Execution**
   - `EntryManager` validates signal quality
   - `OrderManager` executes entry orders
   - `PositionManager` tracks new position

6. **Exit Monitoring**
   - `ExitManager` monitors stop loss, take profit, timeout
   - `OrderManager` executes exit orders
   - `PositionManager` closes position and records P&L

7. **Notification**
   - `TelegramBot` sends alerts for entries, exits, and errors

## Configuration Management

### Static Configuration (`src/core/config.py`)
- Initial capital
- Leverage
- Commission rates
- Directory paths

### Dynamic Configuration (`config/strategy_params.json`)
- ATR threshold
- Risk per trade
- Stop loss multiplier
- Take profit multiplier
- Max holding period

### Environment Variables (`.env`)
- API keys
- Telegram credentials
- Testnet flag

## Design Patterns

### 1. Singleton Pattern
- `ConfigLoader`: Single instance manages hot-reload
- `Logger`: Single instance manages all logging

### 2. Strategy Pattern
- `TradingStrategy`: Encapsulates signal generation logic

### 3. Manager Pattern
- `RiskManager`, `OrderManager`, `PositionManager`, etc.
- Each manager handles specific domain

### 4. Facade Pattern
- `PaperTrader`: Provides simplified interface to complex subsystem

## Dependency Injection

Modules receive dependencies through constructor injection:

```python
class PaperTrader:
    def __init__(self):
        self.data_manager = DataManager()
        self.indicators = ICTIndicators()
        self.strategy = TradingStrategy()
        # ... etc
```

Benefits:
- Testability (can mock dependencies)
- Flexibility (can swap implementations)
- Clear dependency graph

## Error Handling

### Layered Error Handling

1. **Component Level**: Catch and log specific errors
2. **Manager Level**: Handle component failures gracefully
3. **Orchestrator Level**: Coordinate recovery or shutdown

### Logging Strategy

- **DEBUG**: Detailed diagnostic information
- **INFO**: Confirmation of normal operation
- **WARNING**: Unexpected but recoverable events
- **ERROR**: Serious problems that prevent functionality
- **CRITICAL**: System failure requiring immediate attention

## Testing Strategy

### Unit Tests
- Each module has corresponding test file
- Tests use mock data, no live API calls
- Focus on business logic validation

### Test Organization
```
tests/
├── test_indicators.py      # ICT indicator calculations
├── test_strategy.py        # Signal generation logic
├── test_risk_management.py # Risk calculations
├── test_logger.py          # Logging functionality
└── run_all_tests.py        # Test runner
```

## Scalability Considerations

### Current Architecture Supports

1. **Multiple Symbols**: Easy to extend DataManager for multiple pairs
2. **Multiple Strategies**: Strategy pattern allows multiple implementations
3. **Multiple Exchanges**: CCXT abstraction supports 100+ exchanges
4. **Backtesting**: Modular design allows historical data replay

### Future Enhancements

1. **Database Integration**: Replace JSON files with PostgreSQL/TimescaleDB
2. **Multi-threading**: Parallel processing of multiple symbols
3. **REST API**: Expose functionality via API endpoints
4. **Web Dashboard**: Real-time monitoring and control
5. **Machine Learning**: Integrate ML models for signal filtering

## Performance Optimizations

1. **Data Caching**: Reduce redundant API calls
2. **Lazy Loading**: Load data only when needed
3. **Efficient Calculations**: Vectorized operations with pandas/numpy
4. **Log Rotation**: Prevent log files from growing indefinitely

## Security Best Practices

1. **Environment Variables**: API keys stored in `.env`, not in code
2. **API Key Validation**: Check keys before trading
3. **Input Validation**: Validate all user inputs and signals
4. **Error Isolation**: Exceptions don't expose sensitive data
5. **Testnet First**: Always test on testnet before production

## Deployment

### Development
```bash
python -m src.core.paper_trader
```

### Production (systemd)
```bash
sudo systemctl start paper-trader
```

### Monitoring
- Logs: `trading_data/logs/`
- Trade history: `trading_data/trades/`
- System status: `systemctl status paper-trader`

## Maintenance Guidelines

### Adding New Features

1. Identify appropriate module/package
2. Create new module if needed
3. Update `__init__.py` with exports
4. Add unit tests
5. Update documentation

### Modifying Existing Features

1. Update module code
2. Update corresponding tests
3. Run full test suite
4. Update documentation if API changes

### Code Style

- Follow PEP 8
- Use type hints where beneficial
- Add docstrings to all public functions
- Keep functions focused (single responsibility)
- Prefer composition over inheritance
