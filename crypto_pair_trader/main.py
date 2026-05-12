"""Main orchestrator — ties all modules together for live/paper trading."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

# Ensure project root on path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config
from database.store import DatabaseStore
from exchanges.factory import create_exchange
from exchanges.base import ExchangeClient
from exchanges.ws_stream import WebSocketStream
from execution.paper import PaperExecutor
from execution.live import LiveExecutor
from execution.tracker import PositionTracker
from pair_selection.selector import PairSelector
from pair_selection.spread import SpreadEngine
from risk.manager import RiskManager
from strategies.mean_reversion import Action, MeanReversionStrategy
from utils.log import setup_logging, get_logger
from utils.types import PairScore, Side

log = get_logger(__name__)


class TradingOrchestrator:
    """
    Core loop that:
      1. Selects pairs periodically
      2. Streams / polls price data
      3. Computes spreads and z-scores
      4. Generates signals via strategy
      5. Manages risk and sizing
      6. Executes orders (paper or live)
      7. Tracks positions and persists to DB
    """

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db = DatabaseStore(cfg)
        self.exchange = create_exchange(cfg)
        self.pair_selector = PairSelector(cfg)
        self.spread_engine = SpreadEngine(cfg)
        self.strategy = MeanReversionStrategy(cfg)
        self.risk = RiskManager(cfg, self.db)
        self.tracker = PositionTracker(self.db)

        if cfg.mode == "paper":
            self.executor = PaperExecutor(cfg)
        else:
            self.executor = LiveExecutor(cfg, self.exchange)

        self._active_pairs: List[PairScore] = []
        self._price_cache: Dict[str, pd.DataFrame] = {}
        self._last_rescore = datetime.min
        self._running = False

    async def run(self) -> None:
        """Main async loop."""
        self._running = True
        log.info("=== TRADING ORCHESTRATOR STARTING ===")
        log.info("Mode: %s | Exchange: %s | Timeframe: %s",
                 self.cfg.mode, self.cfg.exchange.name, self.cfg.data.timeframe)

        try:
            # Initial pair selection
            await self._rescore_pairs()

            if self.cfg.data.use_websocket and self._active_pairs:
                await self._run_websocket_loop()
            else:
                await self._run_polling_loop()
        except KeyboardInterrupt:
            log.info("Shutting down (KeyboardInterrupt)")
        except Exception as e:
            log.exception("Fatal error: %s", e)
        finally:
            await self._shutdown()

    # ── Polling mode ───────────────────────────────────────

    async def _run_polling_loop(self) -> None:
        tf_seconds = self._timeframe_seconds()
        while self._running:
            now = datetime.utcnow()

            # Periodic rescore
            elapsed = (now - self._last_rescore).total_seconds()
            if elapsed > self.cfg.pair_selection.rescore_interval_minutes * 60:
                await self._rescore_pairs()

            # Session end square-off
            if self.risk.should_square_off(now):
                await self._square_off_all("session_close")
                # Sleep until next session
                await asyncio.sleep(60)
                self.risk.reset_daily()
                continue

            # Update prices and evaluate each active pair
            for pair in self._active_pairs:
                try:
                    await self._update_and_evaluate(pair, now)
                except Exception as e:
                    log.error("Error evaluating %s/%s: %s", pair.leg_a, pair.leg_b, e)

            await asyncio.sleep(tf_seconds)

    # ── WebSocket mode ─────────────────────────────────────

    async def _run_websocket_loop(self) -> None:
        symbols = set()
        for p in self._active_pairs:
            symbols.add(p.leg_a)
            symbols.add(p.leg_b)

        ws = WebSocketStream(
            self.cfg.exchange.name,
            list(symbols),
            self.cfg.data.timeframe,
            on_candle=self._on_ws_candle,
        )

        # Run WS + periodic tasks concurrently
        await asyncio.gather(
            ws.start(),
            self._periodic_tasks(),
        )

    async def _on_ws_candle(self, symbol_raw: str, candle: Dict) -> None:
        """Callback from WS stream on each closed candle."""
        now = datetime.utcnow()

        # Map raw symbol back to CCXT format
        # (simple heuristic — works for major pairs)
        for pair in self._active_pairs:
            leg_a_raw = pair.leg_a.replace("/", "").upper()
            leg_b_raw = pair.leg_b.replace("/", "").upper()
            sr = symbol_raw.upper()

            if sr == leg_a_raw:
                price_a = candle["close"]
                # Need price_b — fetch from cache or ticker
                state = self.spread_engine.get_state(pair.leg_a, pair.leg_b)
                if state is None:
                    continue
                price_b = state.last_price_b
                await self._process_tick(pair, price_a, price_b, now)

            elif sr == leg_b_raw:
                price_b = candle["close"]
                state = self.spread_engine.get_state(pair.leg_a, pair.leg_b)
                if state is None:
                    continue
                price_a = state.last_price_a
                await self._process_tick(pair, price_a, price_b, now)

    async def _periodic_tasks(self) -> None:
        """Runs alongside WS — periodic rescore, session management."""
        while self._running:
            now = datetime.utcnow()

            # Rescore
            elapsed = (now - self._last_rescore).total_seconds()
            if elapsed > self.cfg.pair_selection.rescore_interval_minutes * 60:
                await self._rescore_pairs()

            # Session end
            if self.risk.should_square_off(now):
                await self._square_off_all("session_close")
                self.risk.reset_daily()

            await asyncio.sleep(30)

    # ── Core logic ─────────────────────────────────────────

    async def _update_and_evaluate(self, pair: PairScore, now: datetime) -> None:
        """Fetch latest prices and run strategy for one pair."""
        try:
            ticker_a = await self.exchange.fetch_ticker(pair.leg_a)
            ticker_b = await self.exchange.fetch_ticker(pair.leg_b)
        except Exception as e:
            log.warning("Ticker fetch failed for %s/%s: %s", pair.leg_a, pair.leg_b, e)
            return

        price_a = ticker_a["last"]
        price_b = ticker_b["last"]
        await self._process_tick(pair, price_a, price_b, now)

    async def _process_tick(
        self, pair: PairScore, price_a: float, price_b: float, now: datetime
    ) -> None:
        """Update spread, evaluate strategy, execute if needed."""
        state = self.spread_engine.update(pair.leg_a, pair.leg_b, price_a, price_b)
        if state is None:
            return

        # Store signal
        from utils.types import Signal
        sig_record = Signal(
            timestamp=now, pair_leg_a=pair.leg_a, pair_leg_b=pair.leg_b,
            zscore=state.zscore, spread=float(state.spread_series.iloc[-1]),
            hedge_ratio=state.hedge_ratio,
            side_a=Side.LONG, side_b=Side.SHORT, strength=abs(state.zscore),
        )
        self.db.insert_signal(sig_record)

        action = self.strategy.evaluate(state, now)
        if action == Action.HOLD:
            return

        signal = self.strategy.generate_signal(state, action, now)
        if signal is None:
            return

        if action in (Action.ENTER_LONG_SPREAD, Action.ENTER_SHORT_SPREAD):
            await self._handle_entry(pair, signal, price_a, price_b, action, now)
        else:
            await self._handle_exit(pair, signal, price_a, price_b, action, now)

    async def _handle_entry(
        self, pair: PairScore, signal, price_a: float, price_b: float,
        action: Action, now: datetime,
    ) -> None:
        sizes = self.risk.compute_sizes(signal, price_a, price_b)
        if sizes is None:
            return

        # Execute both legs
        order_a = await self.executor.execute_order(
            pair.leg_a, signal.side_a, sizes["qty_a"], price_a
        )
        order_b = await self.executor.execute_order(
            pair.leg_b, signal.side_b, sizes["qty_b"], price_b
        )

        fill_a = order_a.get("fill_price", price_a)
        fill_b = order_b.get("fill_price", price_b)

        self.tracker.open_trade(
            pair.leg_a, pair.leg_b,
            signal.side_a, signal.side_b,
            sizes["qty_a"], sizes["qty_b"],
            fill_a, fill_b,
            signal.hedge_ratio, signal.zscore,
        )
        self.strategy.register_entry(
            self.spread_engine.get_state(pair.leg_a, pair.leg_b),
            action, now,
        )

    async def _handle_exit(
        self, pair: PairScore, signal, price_a: float, price_b: float,
        action: Action, now: datetime,
    ) -> None:
        # Reverse the entry legs
        order_a = await self.executor.execute_order(
            pair.leg_a, signal.side_a, 0, price_a  # qty from tracker
        )
        order_b = await self.executor.execute_order(
            pair.leg_b, signal.side_b, 0, price_b
        )

        fill_a = order_a.get("fill_price", price_a)
        fill_b = order_b.get("fill_price", price_b)

        # Commission estimate
        open_trade = self.tracker.get_open_trades().get(
            self.tracker.pair_key(pair.leg_a, pair.leg_b)
        )
        commission = 0.0
        if open_trade:
            notional = (open_trade.qty_a * fill_a + open_trade.qty_b * fill_b)
            commission = notional * (self.cfg.backtest.commission_bps / 10000)

        trade = self.tracker.close_trade(
            pair.leg_a, pair.leg_b,
            fill_a, fill_b,
            signal.zscore, action.value, commission,
        )
        if trade:
            self.risk.record_pnl(trade.pnl)
            self.db.insert_pnl_snapshot(
                self.cfg.risk.capital + trade.pnl,
                trade.pnl,
                len(self.tracker.get_open_trades()),
            )

        self.strategy.register_exit(pair.leg_a, pair.leg_b, action.value)

    # ── Pair selection ─────────────────────────────────────

    async def _rescore_pairs(self) -> None:
        log.info("Rescoring pairs...")
        universe = self.cfg.pair_selection.universe
        price_dict: Dict[str, pd.DataFrame] = {}

        for symbol in universe:
            try:
                df = await self.exchange.fetch_history(
                    symbol, self.cfg.data.timeframe, self.cfg.data.history_days
                )
                if not df.empty:
                    price_dict[symbol] = df
            except Exception as e:
                log.warning("Failed to fetch %s: %s", symbol, e)

        if len(price_dict) < 2:
            log.warning("Not enough data for pair selection")
            return

        self._active_pairs = self.pair_selector.score_pairs(price_dict)
        self._price_cache = price_dict
        self._last_rescore = datetime.utcnow()

        # Initialise spread engine for each selected pair
        for pair in self._active_pairs:
            if pair.leg_a in price_dict and pair.leg_b in price_dict:
                prices_a = price_dict[pair.leg_a]["close"]
                prices_b = price_dict[pair.leg_b]["close"]
                self.spread_engine.init_pair(
                    pair.leg_a, pair.leg_b, prices_a, prices_b, pair.hedge_ratio
                )

        log.info("Active pairs: %s", [(p.leg_a, p.leg_b) for p in self._active_pairs])

    async def _square_off_all(self, reason: str) -> None:
        """Close all open positions."""
        open_trades = self.tracker.get_open_trades()
        for key, trade in open_trades.items():
            try:
                ticker_a = await self.exchange.fetch_ticker(trade.pair_leg_a)
                ticker_b = await self.exchange.fetch_ticker(trade.pair_leg_b)
                price_a = ticker_a["last"]
                price_b = ticker_b["last"]

                # Execute exit legs
                exit_side_a = Side.SHORT if trade.side_a == Side.LONG else Side.LONG
                exit_side_b = Side.SHORT if trade.side_b == Side.LONG else Side.LONG
                await self.executor.execute_order(trade.pair_leg_a, exit_side_a, trade.qty_a, price_a)
                await self.executor.execute_order(trade.pair_leg_b, exit_side_b, trade.qty_b, price_b)

                result = self.tracker.close_trade(
                    trade.pair_leg_a, trade.pair_leg_b,
                    price_a, price_b, 0.0, reason,
                )
                if result:
                    self.risk.record_pnl(result.pnl)
                    self.strategy.register_exit(trade.pair_leg_a, trade.pair_leg_b, reason)
            except Exception as e:
                log.error("Square-off error for %s: %s", key, e)

    async def _shutdown(self) -> None:
        log.info("Shutting down...")
        await self._square_off_all("shutdown")
        await self.exchange.close()
        self.db.close()
        log.info("Shutdown complete")

    def _timeframe_seconds(self) -> int:
        tf = self.cfg.data.timeframe
        multipliers = {"m": 60, "h": 3600, "d": 86400}
        for suffix, mult in multipliers.items():
            if tf.endswith(suffix):
                return int(tf[:-1]) * mult
        return 300  # default 5m


def main():
    cfg = Config.load()
    setup_logging(cfg)
    orchestrator = TradingOrchestrator(cfg)
    asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()
