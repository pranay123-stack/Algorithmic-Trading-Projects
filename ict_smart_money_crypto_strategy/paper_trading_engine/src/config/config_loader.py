"""
Configuration Loader with Hot-Reload Support
Loads config.yaml and provides a simple namespace-based Config class
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from src.logger.logger import get_logger

logger = get_logger(__name__)

# Get project root (3 levels up from this file: src/config/config_loader.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Config:
    """
    Simple configuration namespace with attribute-style access.

    Supports nested config access:
        config.exchange.name
        config.risk.risk_per_trade
        config.trading.symbol

    Also supports dictionary-style access:
        config['exchange']['name']
    """

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize Config from dictionary

        Args:
            data: Configuration dictionary
        """
        self._data = data
        self._nested_configs = {}

        # Convert nested dicts to Config objects
        for key, value in data.items():
            if isinstance(value, dict):
                self._nested_configs[key] = Config(value)

    def __getattr__(self, name: str) -> Any:
        """
        Get configuration value using attribute access

        Args:
            name: Configuration key

        Returns:
            Configuration value or nested Config object
        """
        if name.startswith('_'):
            # Access private attributes normally
            return object.__getattribute__(self, name)

        if name in self._nested_configs:
            return self._nested_configs[name]

        if name in self._data:
            return self._data[name]

        raise AttributeError(f"Config has no attribute '{name}'")

    def __getitem__(self, key: str) -> Any:
        """
        Get configuration value using dictionary access

        Args:
            key: Configuration key

        Returns:
            Configuration value or nested Config object
        """
        if key in self._nested_configs:
            return self._nested_configs[key]
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value with default fallback

        Args:
            key: Configuration key (supports nested keys with '.')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            get('trading.symbol')  → 'ETH/USDT'
            get('risk.risk_per_trade') → 0.02
        """
        # Handle nested keys with dot notation
        if '.' in key:
            keys = key.split('.')
            value = self

            for k in keys:
                if isinstance(value, Config):
                    try:
                        value = getattr(value, k)
                    except AttributeError:
                        return default
                elif isinstance(value, dict):
                    value = value.get(k)
                    if value is None:
                        return default
                else:
                    return default

            return value

        # Direct key access
        if key in self._nested_configs:
            return self._nested_configs[key]
        return self._data.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Config back to dictionary

        Returns:
            Dictionary representation
        """
        result = {}
        for key, value in self._data.items():
            if key in self._nested_configs:
                result[key] = self._nested_configs[key].to_dict()
            else:
                result[key] = value
        return result

    def __repr__(self) -> str:
        """String representation of Config"""
        return f"Config({self._data})"


class ConfigLoader:
    """
    Loads and monitors config.yaml for live updates

    Features:
    - Loads from YAML file
    - Hot-reload: Detects file changes without restart
    - Provides Config class with attribute access
    - Validates configuration structure
    """

    def __init__(self, config_file: str = 'config.yaml'):
        """
        Initialize config loader

        Args:
            config_file: Path to YAML configuration file (relative to project root)
        """
        # Convert to Path object, resolve relative to project root
        if not Path(config_file).is_absolute():
            self.config_file = PROJECT_ROOT / config_file
        else:
            self.config_file = Path(config_file)

        self.last_modified = 0
        self.config: Optional[Config] = None
        self._raw_config: Dict = {}

        # Load initial configuration
        self.reload()

    def reload(self) -> bool:
        """
        Reload configuration from file if modified

        Returns:
            True if config was reloaded, False if no changes
        """
        try:
            # Check if file exists
            if not self.config_file.exists():
                logger.warning(f"Config file not found: {self.config_file}")
                return False

            # Check modification time
            current_mtime = self.config_file.stat().st_mtime

            if current_mtime <= self.last_modified and self.config is not None:
                return False  # No changes

            # Load YAML
            with open(self.config_file, 'r') as f:
                new_config = yaml.safe_load(f)

            # Validate config
            if not self._validate_config(new_config):
                logger.error("Invalid configuration, keeping previous config")
                return False

            # Detect changes
            old_config = self._raw_config.copy()

            # Update config
            self._raw_config = new_config
            self.config = Config(new_config)
            self.last_modified = current_mtime

            # Log changes
            if old_config:
                changes = self._detect_changes(old_config, new_config)
                if changes:
                    logger.info("Configuration reloaded with changes:")
                    for change in changes:
                        logger.info(f"   {change}")
            else:
                logger.info(f"Configuration loaded from {self.config_file}")

            return True

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False

    def check_for_updates(self) -> bool:
        """
        Check if config file has been modified and reload if needed

        Returns:
            True if config was updated, False otherwise
        """
        return self.reload()

    def get_config(self) -> Config:
        """
        Get the Config object

        Returns:
            Config instance with attribute-style access
        """
        if self.config is None:
            raise RuntimeError("Configuration not loaded")
        return self.config

    def _validate_config(self, config: Dict) -> bool:
        """
        Validate configuration structure

        Args:
            config: Configuration dictionary

        Returns:
            True if valid, False otherwise
        """
        # Check for required top-level sections
        required_sections = ['exchange', 'trading', 'risk', 'indicators', 'strategy']

        for section in required_sections:
            if section not in config:
                logger.error(f"Missing required section: {section}")
                return False

        # Validate exchange section
        exchange = config.get('exchange', {})
        if 'name' not in exchange:
            logger.error("Missing required key: exchange.name")
            return False

        # Validate trading section
        trading = config.get('trading', {})
        required_trading_keys = ['symbol', 'timeframe', 'leverage', 'initial_capital']

        for key in required_trading_keys:
            if key not in trading:
                logger.error(f"Missing required trading key: {key}")
                return False

        return True

    def _detect_changes(self, old_config: Dict, new_config: Dict, prefix: str = '') -> list:
        """
        Detect differences between old and new configuration

        Args:
            old_config: Previous configuration
            new_config: New configuration
            prefix: Key prefix for nested detection

        Returns:
            List of change descriptions
        """
        changes = []

        # Check all keys in new config
        for key, new_value in new_config.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if key not in old_config:
                changes.append(f"Added: {full_key} = {new_value}")
            elif isinstance(new_value, dict) and isinstance(old_config[key], dict):
                # Recursively check nested dictionaries
                changes.extend(self._detect_changes(old_config[key], new_value, full_key))
            elif new_value != old_config[key]:
                changes.append(f"Changed: {full_key}: {old_config[key]} -> {new_value}")

        # Check for removed keys
        for key in old_config:
            if key not in new_config:
                full_key = f"{prefix}.{key}" if prefix else key
                changes.append(f"Removed: {full_key}")

        return changes

    def summary(self) -> str:
        """
        Get configuration summary

        Returns:
            Human-readable configuration summary
        """
        if self.config is None:
            return "Configuration not loaded"

        cfg = self.config

        summary = f"""
Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Trading Setup:
   Symbol:          {cfg.trading.symbol}
   Timeframe:       {cfg.trading.timeframe}
   Leverage:        {cfg.trading.leverage}x
   Initial Capital: ${cfg.trading.initial_capital:,}
   Exchange:        {cfg.exchange.name}

Risk Management:
   Risk Per Trade:  {cfg.risk.risk_per_trade * 100:.1f}%
   Max Risk:        {cfg.risk.max_risk_pct * 100:.1f}%
   Max Daily Loss:  {cfg.risk.max_daily_loss_pct:.1f}%
   Max Drawdown:    {cfg.risk.max_drawdown_pct:.1f}%

Strategy Parameters:
   R:R Ratio:       {cfg.strategy.rr_ratio}:1
   Stop Lookback:   {cfg.strategy.stop_lookback} bars
   Max Holding:     {cfg.strategy.max_holding_bars} bars
   Max Position:    {cfg.strategy.max_position_size_pct * 100:.1f}%

Config File:     {self.config_file}
Last Modified:   {time.ctime(self.last_modified)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return summary


# Global instance for easy access
_config_loader: Optional[ConfigLoader] = None


def get_config_loader(config_file: str = 'config.yaml') -> ConfigLoader:
    """
    Get global ConfigLoader instance (singleton pattern)

    Args:
        config_file: Path to configuration file

    Returns:
        ConfigLoader instance
    """
    global _config_loader

    if _config_loader is None:
        _config_loader = ConfigLoader(config_file)

    return _config_loader


def get_config(config_file: str = 'config.yaml') -> Config:
    """
    Get global Config instance

    Args:
        config_file: Path to configuration file

    Returns:
        Config instance with attribute-style access
    """
    loader = get_config_loader(config_file)
    return loader.get_config()
