"""
Paper Trading Engine - Modular Architecture
Complete standalone implementation with no backtest folder dependencies
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
import json
from pathlib import Path
import shutil

# Import all standalone modules (NO imports from backtest folder)
from src.core_trading_strategy.indicators import ICTIndicators
from src.core_trading_strategy.strategy import TradingStrategy
from src.core_trading_strategy.risk_management import RiskManager
from src.core_trading_strategy.order_management import OrderManager, OrderType
from src.core_trading_strategy.position_management import PositionManager
from src.core_trading_strategy.entry_management import EntryManager
from src.core_trading_strategy.exit_management import ExitManager
from src.core_trading_strategy.data_manager import DataManager
from src.config.config_loader import get_config

# Setup centralized logging with colors
from src.logger.logger import get_logger, safe_execution, log_exceptions, move_log_to_folder

logger = get_logger(__name__)

# Load configuration
config = get_config('config.yaml')

# Get project root (3 levels up from this file: src/core_trading_strategy/paper_trader.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PaperTrader:
    """
    Modular Paper Trading Engine

    Architecture:
    - Data Manager: Market data fetching and caching
    - Indicators: ICT indicator calculations
    - Strategy: Signal generation
    - Entry Manager: Entry validation and execution
    - Exit Manager: Exit monitoring and execution
    - Position Manager: Position tracking
    - Order Manager: Order creation and execution
    - Risk Manager: Risk limits and position sizing
    """

    def __init__(self):
        """Initialize paper trading engine with modular components"""
        logger.info("Initializing Modular Paper Trading Engine...")

        # Initialize data manager
        self.data_manager = DataManager(
            exchange_name=config.exchange.name,
            testnet=config.exchange.use_testnet,
            lookback_candles=config.data.lookback_candles
        )

        # Initialize ICT indicators
        self.indicators = None  # Will be created when data is available

        # Initialize trading strategy
        self.strategy = TradingStrategy(
            timeframe=config.trading.timeframe,
            rr_ratio=config.strategy.rr_ratio,
            stop_lookback=config.strategy.stop_lookback,
            min_atr_pct=config.indicators.atr.min_atr_pct,
            max_risk_pct=config.risk.max_risk_pct
        )

        # Initialize risk manager
        self.risk_manager = RiskManager(
            initial_capital=config.trading.initial_capital,
            risk_per_trade_pct=config.risk.risk_per_trade,
            max_daily_loss_pct=config.risk.max_daily_loss_pct / 100,
            max_drawdown_pct=config.risk.max_drawdown_pct / 100,
            max_position_size_pct=config.strategy.max_position_size_pct,
            leverage=config.trading.leverage
        )

        # Initialize position manager
        self.position_manager = PositionManager(max_positions=config.trading.max_positions)

        # Initialize entry manager
        self.entry_manager = EntryManager(
            min_atr_pct=config.indicators.atr.min_atr_pct,
            max_risk_pct=config.risk.max_risk_pct,
            slippage_pct=config.execution.slippage_pct
        )

        # Initialize exit manager
        self.exit_manager = ExitManager(
            max_holding_bars=config.strategy.max_holding_bars,
            slippage_pct=config.execution.slippage_pct
        )

        # Initialize order manager
        self.order_manager = OrderManager(
            commission_rate=config.execution.commission_rate,
            slippage_pct=config.execution.slippage_pct
        )

        # Trading state
        self.is_running = False
        self.start_time = None
        self.daily_reset_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.entry_bar_index = None

        # Create timestamp for this session (used for filenames)
        self.session_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.json_filename = f'paper_trading_history_{self.session_timestamp}.json'
        self.csv_filename = f'trades_{self.session_timestamp}.csv'

        # Create trades folder if it doesn't exist
        self.trades_dir = PROJECT_ROOT / 'trading_data' / 'trades'
        self.trades_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Configuration: {config.trading.symbol} {config.trading.timeframe} {config.trading.leverage}x leverage")
        logger.info(f"Session files: {self.json_filename}, {self.csv_filename}")
        logger.info("All modules initialized successfully")

    def fetch_and_process_data(self) -> pd.DataFrame:
        """
        Fetch latest data and calculate indicators

        Returns:
            DataFrame with OHLCV + indicators
        """
        try:
            # Fetch fresh data (aligned scheduler ensures we only fetch on candle close)
            df = self.data_manager.update_data(
                symbol=config.trading.symbol,
                timeframe=config.trading.timeframe
            )

            if df is None or len(df) < 100:
                logger.warning("Insufficient data")
                return None

            # Calculate indicators
            self.indicators = ICTIndicators(df.copy())
            df_with_indicators = self.indicators.calculate_all(
                fvg_min_gap=config.indicators.fvg.min_gap_size,
                fvg_lookback=config.indicators.fvg.lookback,
                ob_swing=config.indicators.order_blocks.swing_length,
                ob_volume_pct=config.indicators.order_blocks.min_volume_percentile,
                sweep_lookback=config.indicators.liquidity_sweeps.lookback,
                sweep_threshold=config.indicators.liquidity_sweeps.sweep_threshold
            )

            return df_with_indicators

        except Exception as e:
            logger.error(f"Error fetching/processing data: {e}", exc_info=True)
            return None

    def check_entry(self, df: pd.DataFrame) -> bool:
        """
        Check for entry signal and execute if valid

        Args:
            df: DataFrame with indicators

        Returns:
            True if entry executed, False otherwise
        """
        # Don't enter if already in position
        if self.position_manager.has_open_position():
            return False

        # Generate signals
        df_signals = self.strategy.generate_signals(
            df.copy(),
            use_fvg=config.indicators.fvg.enabled,
            use_ob=config.indicators.order_blocks.enabled,
            use_sweep=config.indicators.liquidity_sweeps.enabled
        )

        # Get latest signal
        signal = self.strategy.get_latest_signal(df_signals)

        if signal is None:
            return False

        # Get current price and ATR
        current_price = df['close'].iloc[-1]
        current_atr_pct = df['atr_pct'].iloc[-1] if 'atr_pct' in df.columns else None

        # Prepare entry
        entry_details = self.entry_manager.prepare_entry(
            signal=signal,
            current_price=current_price,
            capital=self.risk_manager.current_capital,
            risk_per_trade_pct=config.risk.risk_per_trade,
            leverage=config.trading.leverage,
            atr_pct=current_atr_pct
        )

        if entry_details is None:
            return False

        # Create entry order
        order = self.order_manager.create_order(
            symbol=config.trading.symbol,
            side=entry_details['action'],
            size=entry_details['position_size'],
            order_type=OrderType.MARKET,
            stop_price=entry_details['stop_loss'],
            take_profit_price=entry_details['take_profit']
        )

        # Execute order
        success = self.order_manager.execute_order(
            order=order,
            current_price=current_price,
            timestamp=entry_details['timestamp']
        )

        if not success:
            self.entry_manager.log_entry(entry_details, False, "Order execution failed")
            return False

        # Open position
        position = self.position_manager.open_position(
            symbol=config.trading.symbol,
            side=entry_details['action'],
            entry_price=order.filled_price,
            size=entry_details['position_size'],
            stop_loss=entry_details['stop_loss'],
            take_profit=entry_details['take_profit'],
            leverage=config.trading.leverage,
            entry_time=entry_details['timestamp']
        )

        # Log successful entry
        self.entry_manager.log_entry(entry_details, True)

        # Store entry bar index
        self.entry_bar_index = len(df) - 1

        return True

    def check_exit(self, df: pd.DataFrame) -> bool:
        """
        Check for exit conditions and execute if triggered

        Args:
            df: DataFrame with current bar

        Returns:
            True if exit executed, False otherwise
        """
        # No position to exit
        if not self.position_manager.has_open_position():
            return False

        current_position = self.position_manager.get_current_position()
        current_bar = {
            'high': df['high'].iloc[-1],
            'low': df['low'].iloc[-1],
            'close': df['close'].iloc[-1]
        }
        current_bar_index = len(df) - 1

        # Check exit conditions
        should_exit, exit_price, exit_reason = self.exit_manager.check_exit_conditions(
            position=current_position.to_dict(),
            current_bar=current_bar,
            current_bar_index=current_bar_index,
            entry_bar_index=self.entry_bar_index
        )

        if not should_exit:
            return False

        # Prepare exit
        exit_details = self.exit_manager.prepare_exit(
            position=current_position.to_dict(),
            exit_price=exit_price,
            exit_reason=exit_reason,
            timestamp=df.index[-1]
        )

        # Create exit order
        exit_order = self.order_manager.create_order(
            symbol=config.trading.symbol,
            side='SHORT' if current_position.side == 'LONG' else 'LONG',  # Opposite side to close
            size=current_position.size,
            order_type=OrderType.MARKET
        )

        # Execute exit order
        success = self.order_manager.execute_order(
            order=exit_order,
            current_price=exit_price,
            timestamp=exit_details['timestamp']
        )

        if not success:
            self.exit_manager.log_exit(current_position.to_dict(), exit_details, False, "Order execution failed")
            return False

        # Close position
        closed_position = self.position_manager.close_position(
            exit_price=exit_order.filled_price,
            exit_reason=exit_reason,
            exit_time=exit_details['timestamp']
        )

        # Update risk manager capital
        self.risk_manager.update_capital(closed_position.pnl)

        # Log successful exit
        self.exit_manager.log_exit(current_position.to_dict(), exit_details, True)

        # Reset entry bar index
        self.entry_bar_index = None

        # Save trade history
        self._save_trades()

        return True

    def check_risk_limits(self) -> bool:
        """
        Check if risk limits are breached

        Returns:
            True if all clear, False if limits breached
        """
        limits = self.risk_manager.check_risk_limits()

        if limits['daily_limit_breached']:
            logger.warning(f"Daily loss limit breached: {limits['daily_loss_pct']:.2f}%")
            return False

        if limits['dd_limit_breached']:
            logger.error(f"Max drawdown limit breached: {limits['current_dd_pct']:.2f}%")
            return False

        return True

    def send_daily_report(self):
        """Send daily performance report"""
        # Reset daily metrics
        self.risk_manager.reset_daily_metrics()

    def _save_trades(self, move_to_folder=False):
        """
        Save trade history to session files

        Args:
            move_to_folder: If True, move files to trades/ folder (when stopping)
        """
        position_stats = self.position_manager.get_stats()
        risk_stats = self.risk_manager.get_stats()
        order_stats = self.order_manager.get_stats()
        entry_stats = self.entry_manager.get_entry_stats()
        exit_stats = self.exit_manager.get_exit_stats()

        # Prepare data structure
        data = {
            'strategy': 'FinalICTStrategy',
            'symbol': config.trading.symbol,
            'timeframe': config.trading.timeframe,
            'leverage': config.trading.leverage,
            'session_start': str(self.start_time),
            'session_end': str(datetime.now()),
            'initial_capital': config.trading.initial_capital,
            'current_capital': risk_stats['current_capital'],
            'total_return_pct': risk_stats['total_return_pct'],
            'max_drawdown_pct': risk_stats['max_dd_reached'],
            'performance': position_stats,
            'orders': order_stats,
            'entry_stats': entry_stats,
            'exit_stats': exit_stats,
            'trade_history': self.position_manager.get_position_history()
        }

        # Save to session JSON file (in current directory during run)
        json_path = Path(self.json_filename)
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        # Save trades to CSV
        trade_history = self.position_manager.get_position_history()
        if trade_history:
            self._save_trades_csv(trade_history, self.csv_filename)

        # If stopping (Ctrl+C), move files to trading_data/trades/ folder
        if move_to_folder:
            try:
                json_dest = self.trades_dir / self.json_filename
                csv_dest = self.trades_dir / self.csv_filename

                shutil.move(str(json_path), str(json_dest))
                csv_path = Path(self.csv_filename)
                if csv_path.exists():
                    shutil.move(str(csv_path), str(csv_dest))

                logger.info(f"✅ Session files moved to trading_data/trades/ folder:")
                logger.info(f"   - {json_dest}")
                if csv_dest.exists():
                    logger.info(f"   - {csv_dest}")
            except Exception as e:
                logger.error(f"Error moving files to trading_data/trades/ folder: {e}")
        else:
            logger.info(f"Session data saved to {self.json_filename} and {self.csv_filename}")

    def _save_trades_csv(self, trades, filename):
        """Save trades to CSV file"""
        import csv

        if not trades:
            return

        # Define CSV headers
        headers = [
            'entry_time', 'exit_time', 'symbol', 'direction', 'leverage',
            'entry_price', 'exit_price', 'position_size', 'stop_loss', 'take_profit',
            'pnl', 'pnl_pct', 'exit_reason', 'holding_time', 'entry_reasons'
        ]

        with open(filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction='ignore')
            writer.writeheader()

            for trade in trades:
                # Format entry_reasons if it's a list
                if isinstance(trade.get('entry_reasons'), list):
                    trade['entry_reasons'] = '; '.join(trade['entry_reasons'])
                writer.writerow(trade)

    def _log_market_analysis(self, df: pd.DataFrame):
        """Log ICT indicator values and market analysis"""
        latest = df.iloc[-1]

        # Check bias
        bias_long = latest.get('bullish_bias', False)
        bias_short = latest.get('bearish_bias', False)
        bias_str = "🟢 BULLISH" if bias_long else ("🔴 BEARISH" if bias_short else "⚪ NEUTRAL")

        logger.info(f"🎯 Market Bias: {bias_str}")

        # ATR
        atr = latest.get('atr', 0)
        atr_pct = (atr / latest['close']) * 100 if latest['close'] > 0 else 0
        logger.info(f"📈 ATR: {atr:.2f} ({atr_pct:.2f}%)")

        # FVG
        fvg_bullish = latest.get('fvg_bullish', False)
        fvg_bearish = latest.get('fvg_bearish', False)
        if fvg_bullish or fvg_bearish:
            fvg_str = "🟢 Bullish FVG" if fvg_bullish else "🔴 Bearish FVG"
            logger.info(f"💎 FVG: {fvg_str}")
        else:
            logger.info(f"💎 FVG: None")

        # Order Blocks
        ob_bullish = latest.get('ob_bullish', False)
        ob_bearish = latest.get('ob_bearish', False)
        if ob_bullish or ob_bearish:
            ob_str = "🟢 Bullish OB" if ob_bullish else "🔴 Bearish OB"
            logger.info(f"🧱 Order Block: {ob_str}")
        else:
            logger.info(f"🧱 Order Block: None")

        # Liquidity Sweeps
        sweep_high = latest.get('sweep_high', False)
        sweep_low = latest.get('sweep_low', False)
        if sweep_high or sweep_low:
            sweep_str = "🔼 High Sweep" if sweep_high else "🔽 Low Sweep"
            logger.info(f"🌊 Liquidity Sweep: {sweep_str}")
        else:
            logger.info(f"🌊 Liquidity Sweep: None")

        # Position status
        if self.position_manager.has_open_position():
            pos = self.position_manager.get_current_position()
            pnl_pct = ((latest['close'] - pos.entry_price) / pos.entry_price * 100) * (1 if pos.side == 'LONG' else -1)
            logger.info(f"💼 Position: {pos.side} @ {pos.entry_price:.2f} | PnL: {pnl_pct:+.2f}%")
        else:
            logger.info(f"💼 Position: None (Looking for entry)")

        # Log last 20 candles to file (DEBUG level - file only)
        logger.debug("\n" + "="*80)
        logger.debug("📊 LAST 20 CANDLES WITH INDICATORS")
        logger.debug("="*80)

        # Get last 20 rows
        recent_data = df.tail(20)

        for idx, row in recent_data.iterrows():
            bias = "BULL" if row.get('bullish_bias', False) else ("BEAR" if row.get('bearish_bias', False) else "NEUT")
            fvg = "FVG_B" if row.get('fvg_bullish', False) else ("FVG_S" if row.get('fvg_bearish', False) else "     ")
            ob = "OB_B" if row.get('ob_bullish', False) else ("OB_S" if row.get('ob_bearish', False) else "    ")
            sweep = "SW_H" if row.get('sweep_high', False) else ("SW_L" if row.get('sweep_low', False) else "    ")
            atr_val = row.get('atr', 0)

            logger.debug(
                f"{idx} | O:{row['open']:7.2f} H:{row['high']:7.2f} L:{row['low']:7.2f} C:{row['close']:7.2f} "
                f"| {bias} | ATR:{atr_val:6.2f} | {fvg} | {ob} | {sweep}"
            )

        logger.debug("="*80 + "\n")

    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes"""
        mapping = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '6h': 360, '12h': 720,
            '1d': 1440
        }
        return mapping.get(timeframe, 15)  # Default to 15m

    def _wait_for_next_minute_boundary(self):
        """Wait until the next exact minute (HH:MM:00)"""
        now = datetime.now()
        current_second = now.second
        microseconds = now.microsecond

        if current_second == 0 and microseconds < 100000:
            # Already at minute boundary
            return

        # Calculate seconds to wait until next minute
        wait_seconds = 60 - current_second

        logger.info(f"⏳ Aligning to next minute boundary (waiting {wait_seconds} seconds)")
        logger.info(f"   Current time: {now.strftime('%H:%M:%S')}")
        logger.info(f"   Will align to: {(now + timedelta(seconds=wait_seconds)).strftime('%H:%M:00')}")

        time.sleep(wait_seconds)

    def _get_seconds_until_next_candle_close(self, timeframe_minutes: int) -> int:
        """
        Calculate seconds until next candle boundary aligned to timeframe

        Args:
            timeframe_minutes: Candle timeframe in minutes (e.g., 15 for 15m)

        Returns:
            Seconds to wait until next candle closes
        """
        now = datetime.now()
        current_minute = now.minute
        current_second = now.second

        # Find next timeframe boundary
        # For 15m: boundaries are at :00, :15, :30, :45
        next_boundary = ((current_minute // timeframe_minutes) + 1) * timeframe_minutes

        # Handle hour overflow
        if next_boundary >= 60:
            next_boundary = 0
            minutes_to_wait = 60 - current_minute
        else:
            minutes_to_wait = next_boundary - current_minute

        # Total seconds to wait (subtract current seconds)
        seconds_to_wait = (minutes_to_wait * 60) - current_second

        return seconds_to_wait

    def run(self):
        """Main trading loop with aligned scheduler"""
        logger.info("=" * 60)
        logger.info("Starting Modular Paper Trading Engine")
        logger.info("=" * 60)
        logger.info(f"Strategy: FinalICTStrategy (Independent OR logic)")
        logger.info(f"Configuration: {config.trading.symbol} {config.trading.timeframe} {config.trading.leverage}x")
        logger.info(f"Expected: {config.performance.expected_win_rate*100:.1f}% WR, Sharpe {config.performance.expected_sharpe:.2f}, PF {config.performance.expected_profit_factor:.2f}")
        logger.info("=" * 60)

        self.is_running = True
        self.start_time = datetime.now()

        # Get timeframe in minutes
        timeframe_minutes = self._get_timeframe_minutes(config.trading.timeframe)
        logger.info(f"📊 Timeframe: {config.trading.timeframe} ({timeframe_minutes} minutes)")

        # Step 1: Align to next minute boundary first
        self._wait_for_next_minute_boundary()
        logger.info(f"✅ Aligned to minute boundary: {datetime.now().strftime('%H:%M:%S')}")

        try:
            last_candle_time = None  # Track last processed candle

            while self.is_running:
                # Fetch and process data
                df = self.fetch_and_process_data()
                if df is None:
                    logger.warning("Failed to fetch/process data, retrying in 60 seconds...")
                    time.sleep(60)
                    continue

                # Get timestamp of last completed candle
                current_candle_time = df.iloc[-2].name if len(df) > 1 else df.iloc[-1].name

                # Check for configuration updates (hot-reload)
                config_loader = get_config_loader()
                if config_loader.check_for_updates():
                    logger.info("🔄 Configuration updated - changes will apply on next signal")

                # Only process if this is a NEW candle
                if current_candle_time != last_candle_time:
                    logger.info("=" * 60)
                    logger.info(f"🕐 New {config.trading.timeframe} candle at {datetime.now().strftime('%H:%M:%S')}")
                    logger.info(f"   Timestamp: {current_candle_time}")

                    # Log market data
                    latest_candle = df.iloc[-1]
                    logger.info(f"📊 Market Data:")
                    logger.info(f"   Open:   {latest_candle['open']:.2f}")
                    logger.info(f"   High:   {latest_candle['high']:.2f}")
                    logger.info(f"   Low:    {latest_candle['low']:.2f}")
                    logger.info(f"   Close:  {latest_candle['close']:.2f}")
                    logger.info(f"   Volume: {latest_candle['volume']:,.0f}")

                    # Log indicator values
                    self._log_market_analysis(df)

                    # Check risk limits
                    if not self.check_risk_limits():
                        logger.error("Risk limits breached, stopping trading")
                        break

                    # Check exit first (if in position)
                    self.check_exit(df)

                    # Check entry (if not in position)
                    self.check_entry(df)

                    logger.info("=" * 60)

                    # Update last processed candle
                    last_candle_time = current_candle_time

                    # Check if it's time for daily report
                    now = datetime.now()
                    if now.date() > self.daily_reset_time.date():
                        self.send_daily_report()
                        self.daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

                else:
                    logger.info(f"⏳ No new candle yet (last: {current_candle_time})")

                # Step 2: Sleep until next candle boundary + buffer
                sleep_seconds = self._get_seconds_until_next_candle_close(timeframe_minutes)
                buffer_seconds = 5  # Wait 5 extra seconds to ensure candle is closed
                total_sleep = sleep_seconds + buffer_seconds

                next_check_time = datetime.now() + timedelta(seconds=sleep_seconds)
                logger.info(f"💤 Sleeping {total_sleep} seconds until next {config.trading.timeframe} candle")
                logger.info(f"   Next check at: {next_check_time.strftime('%H:%M:%S')} (+ {buffer_seconds}s buffer)")

                time.sleep(total_sleep)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping...")
        except Exception as e:
            logger.error(f"Error in trading loop: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop the trading engine"""
        logger.info("=" * 60)
        logger.info("Stopping Modular Paper Trading Engine")
        logger.info("=" * 60)
        self.is_running = False

        # Close any open position
        if self.position_manager.has_open_position():
            logger.warning("Closing open position on shutdown")
            df = self.data_manager.update_data(config.trading.symbol, config.trading.timeframe)
            if df is not None:
                self.check_exit(df)

        # Calculate summary
        runtime = datetime.now() - self.start_time if self.start_time else timedelta(0)
        position_stats = self.position_manager.get_stats()
        risk_stats = self.risk_manager.get_stats()

        logger.info(f"Runtime: {runtime}")
        logger.info(f"Total Trades: {position_stats['total_trades']}")
        logger.info(f"Win Rate: {position_stats['win_rate']:.1f}%")
        logger.info(f"Profit Factor: {position_stats['profit_factor']:.2f}")
        logger.info(f"Total Return: {risk_stats['total_return_pct']:+.2f}%")
        logger.info(f"Max Drawdown: {risk_stats['max_dd_reached']:.2f}%")
        logger.info("=" * 60)

        # Save final session data and move to trades/ folder
        logger.info("Saving session data...")
        self._save_trades(move_to_folder=True)
        logger.info("✅ Session complete!")

        # Move log file to logs/ folder
        move_log_to_folder()


if __name__ == "__main__":
    from src.config.config_loader import get_config_loader

    # Load configuration from config.yaml
    config_loader = get_config_loader('config.yaml')

    # Print configuration summary
    print(config_loader.summary())

    # Start trading
    trader = PaperTrader()
    trader.run()
