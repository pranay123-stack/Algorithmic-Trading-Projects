"""Polybot CLI entrypoint and main event loop.

Usage::

    python -m polybot.main --mode paper --config config/example.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import random
import signal
import time
from collections.abc import AsyncIterator

from polybot.config import load_config
from polybot.config.settings import ExecutionMode, PolybotConfig
from polybot.data.client import PolymarketClient
from polybot.data.poller import MarketPoller
from polybot.execution.base import BaseExecutor
from polybot.execution.paper import PaperExecutor
from polybot.notifications.telegram import TelegramNotifier
from polybot.risk.manager import RiskManager
from polybot.strategy.engine import StrategyEngine
from polybot.strategy.models import signal_to_order
from polybot.telemetry import get_logger, setup_logging
from polybot.telemetry.audit import AuditLog
from polybot.telemetry.metrics import MetricsCollector
from polybot.types import Market, PriceSnapshot, TokenPair


logger = get_logger(__name__)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="polybot",
        description="Automated prediction market trading engine for Polymarket",
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["paper", "live"],
        help="Execution mode",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to YAML configuration file",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Market discovery
# ---------------------------------------------------------------------------

async def _discover_markets(
    client: PolymarketClient,
    config: PolybotConfig,
) -> list[Market]:
    """Fetch and filter markets from Polymarket API.

    Falls back to synthetic demo markets if the API is unreachable.
    """
    markets: list[Market] = []

    # If explicit market IDs are configured, try to fetch them
    if config.market_filter.market_ids:
        for mid in config.market_filter.market_ids:
            try:
                data = await client.get_market(mid)
                markets.append(_parse_market(data))
            except Exception as exc:
                logger.warning("market_fetch_failed", market_id=mid, error=str(exc))

    # If no explicit IDs, fetch by tags
    if not markets:
        for tag in config.market_filter.tags or [""]:
            try:
                raw = await client.get_markets(tag=tag or None, limit=50)
                items = raw if isinstance(raw, list) else raw.get("data", [])  # type: ignore[union-attr]
                for item in items:
                    if isinstance(item, dict):
                        m = _parse_market(item)
                        markets.append(m)
            except Exception as exc:
                logger.warning("market_discovery_failed", tag=tag, error=str(exc))

    # Apply filters
    filtered = []
    for m in markets:
        if m.last_price:
            if m.last_price.volume_24h < config.market_filter.min_volume_24h:
                continue
            if m.last_price.liquidity < config.market_filter.min_liquidity:
                continue
        filtered.append(m)

    if not filtered:
        logger.info("no_live_markets_found_using_demo_markets")
        filtered = _demo_markets()

    logger.info("markets_discovered", count=len(filtered))
    return filtered


def _parse_market(data: dict) -> Market:  # type: ignore[type-arg]
    """Parse a raw API response into a Market object."""
    tokens_raw = data.get("tokens", [])
    yes_token = ""
    no_token = ""
    for t in tokens_raw:
        if not isinstance(t, dict):
            continue
        outcome = t.get("outcome", "").upper()
        if outcome == "YES":
            yes_token = t.get("token_id", "")
        elif outcome == "NO":
            no_token = t.get("token_id", "")

    condition_id = data.get("condition_id", data.get("id", ""))
    return Market(
        id=data.get("id", ""),
        question=data.get("question", data.get("title", "")),
        condition_id=condition_id,
        tokens=TokenPair(condition_id, yes_token or "yes-default", no_token or "no-default"),
        end_date=data.get("end_date_iso", ""),
        tags=data.get("tags", []),
    )


def _demo_markets() -> list[Market]:
    """Synthetic markets for paper-trading demos."""
    return [
        Market(
            id="demo-btc-100k",
            question="Will BTC exceed $100k by end of 2026?",
            condition_id="demo-cond-1",
            tokens=TokenPair("demo-cond-1", "demo-yes-1", "demo-no-1"),
            end_date="2026-12-31",
            tags=["crypto"],
            last_price=PriceSnapshot("demo-btc-100k", 0.42, 0.58, 50000.0, 25000.0, time.time()),
        ),
        Market(
            id="demo-election",
            question="Will candidate X win the 2026 election?",
            condition_id="demo-cond-2",
            tokens=TokenPair("demo-cond-2", "demo-yes-2", "demo-no-2"),
            end_date="2026-11-05",
            tags=["politics"],
            last_price=PriceSnapshot("demo-election", 0.65, 0.35, 120000.0, 80000.0, time.time()),
        ),
        Market(
            id="demo-weather",
            question="Will it rain in NYC this weekend?",
            condition_id="demo-cond-3",
            tokens=TokenPair("demo-cond-3", "demo-yes-3", "demo-no-3"),
            end_date="2026-05-18",
            tags=["weather"],
            last_price=PriceSnapshot("demo-weather", 0.12, 0.88, 8000.0, 3000.0, time.time()),
        ),
    ]


# ---------------------------------------------------------------------------
# Demo poller for paper mode (no API needed)
# ---------------------------------------------------------------------------

class DemoPoller:
    """Simulated price feed that generates random walks for demo markets.

    Produces realistic price movements without requiring a live API
    connection, making paper mode fully functional offline.
    """

    def __init__(self, markets: list[Market], interval: float = 5.0) -> None:
        self._markets = markets
        self._interval = interval
        self._shutdown = asyncio.Event()
        self._prices: dict[str, float] = {}
        for m in markets:
            self._prices[m.id] = m.last_price.yes_price if m.last_price else 0.5

    def stop(self) -> None:
        self._shutdown.set()

    async def iter_snapshots(self) -> AsyncIterator[dict[str, PriceSnapshot]]:
        """Yield simulated price snapshots with random-walk movements."""
        while not self._shutdown.is_set():
            snapshots: dict[str, PriceSnapshot] = {}
            for market in self._markets:
                # Random walk: drift +-2% per tick, clamped to [0.02, 0.98]
                current = self._prices[market.id]
                change = random.gauss(0, 0.015)
                new_price = max(0.02, min(0.98, current + change))
                self._prices[market.id] = new_price

                snap = PriceSnapshot(
                    market_id=market.id,
                    yes_price=round(new_price, 4),
                    no_price=round(1.0 - new_price, 4),
                    volume_24h=random.uniform(5000, 150000),
                    liquidity=random.uniform(2000, 100000),
                    timestamp=time.time(),
                )
                snapshots[market.id] = snap
                market.last_price = snap

            yield snapshots

            try:
                await asyncio.wait_for(self._shutdown.wait(), timeout=self._interval)
                break
            except asyncio.TimeoutError:
                pass


# ---------------------------------------------------------------------------
# Executor factory
# ---------------------------------------------------------------------------

async def _create_executor(
    config: PolybotConfig,
    client: PolymarketClient | None,
) -> BaseExecutor:
    """Create the appropriate executor based on config mode."""
    if config.execution.mode == ExecutionMode.LIVE:
        from polybot.execution.live import LiveExecutor

        assert client is not None, "Live mode requires a PolymarketClient"
        executor = LiveExecutor(
            client,
            chain_id=config.execution.chain_id,
            polygon_rpc_url=config.execution.polygon_rpc_url,
        )
    else:
        executor = PaperExecutor(
            initial_balance=config.execution.initial_balance_usdc,
            taker_fee_bps=config.execution.taker_fee_bps,
        )
    return executor


# ---------------------------------------------------------------------------
# Main event loop
# ---------------------------------------------------------------------------

async def _run(config: PolybotConfig, mode: str) -> None:
    """Main event loop."""
    # --- Telemetry ---
    audit = AuditLog(config.telemetry.audit_db_url)
    await audit.init()

    metrics = MetricsCollector(port=config.telemetry.prometheus_port)
    try:
        metrics.start()
    except Exception as exc:
        logger.warning("metrics_server_failed", error=str(exc))

    # --- Telegram ---
    notifier: TelegramNotifier | None = None
    if config.telegram.enabled and config.telegram.bot_token:
        notifier = TelegramNotifier(
            bot_token=config.telegram.bot_token,
            chat_id=config.telegram.chat_id,
            notify_on=config.telegram.notify_on,
        )
        await notifier.start()

    # --- Determine if we need the live API ---
    use_demo = mode == "paper"

    if use_demo:
        # Paper mode: use demo markets + simulated prices (no API needed)
        markets = _demo_markets()
        market_map = {m.id: m for m in markets}
        engine = StrategyEngine(rules=config.rules, markets=market_map)
        risk = RiskManager(config.risk)
        executor = await _create_executor(config, None)

        async with executor:
            metrics.balance_usdc.set(await executor.get_balance())
            poller = DemoPoller(markets, interval=config.polling.interval_seconds)

            shutdown = asyncio.Event()

            def _handle_signal(sig: int, frame: object) -> None:
                logger.info("shutdown_signal", signal=sig)
                shutdown.set()
                poller.stop()

            signal.signal(signal.SIGINT, _handle_signal)
            signal.signal(signal.SIGTERM, _handle_signal)

            logger.info(
                "polybot_running",
                mode=mode,
                markets=len(markets),
                rules=len(config.rules),
            )

            await _main_loop(poller, engine, risk, executor, metrics, audit, notifier, shutdown)

            cancelled = await executor.cancel_all()
            logger.info("shutdown_complete", cancelled_orders=cancelled)
    else:
        # Live mode: use real Polymarket API
        async with PolymarketClient(
            base_url=config.polling.markets_endpoint,
            timeout=config.polling.timeout_seconds,
            max_retries=config.polling.max_retries,
        ) as client:
            markets = await _discover_markets(client, config)
            market_map = {m.id: m for m in markets}
            engine = StrategyEngine(rules=config.rules, markets=market_map)
            risk = RiskManager(config.risk)
            executor = await _create_executor(config, client)

            async with executor:
                metrics.balance_usdc.set(await executor.get_balance())
                poller = MarketPoller(
                    client=client,
                    markets=markets,
                    interval=config.polling.interval_seconds,
                )

                shutdown = asyncio.Event()

                def _handle_signal(sig: int, frame: object) -> None:
                    logger.info("shutdown_signal", signal=sig)
                    shutdown.set()
                    poller.stop()

                signal.signal(signal.SIGINT, _handle_signal)
                signal.signal(signal.SIGTERM, _handle_signal)

                logger.info(
                    "polybot_running",
                    mode=mode,
                    markets=len(markets),
                    rules=len(config.rules),
                )

                await _main_loop(poller, engine, risk, executor, metrics, audit, notifier, shutdown)

                cancelled = await executor.cancel_all()
                logger.info("shutdown_complete", cancelled_orders=cancelled)

    await audit.close()
    if notifier:
        await notifier.stop()


async def _main_loop(
    poller: MarketPoller | DemoPoller,
    engine: StrategyEngine,
    risk: RiskManager,
    executor: BaseExecutor,
    metrics: MetricsCollector,
    audit: AuditLog,
    notifier: TelegramNotifier | None,
    shutdown: asyncio.Event,
) -> None:
    """Core trading loop shared between paper and live modes."""
    cycle = 0
    async for snapshots in poller.iter_snapshots():
        if shutdown.is_set():
            break

        cycle += 1
        t0 = time.monotonic()
        metrics.polls_total.labels(status="success").inc()

        # Paper executor: check fills
        if isinstance(executor, PaperExecutor):
            fills = executor.process_snapshots(snapshots)
            for fill in fills:
                await audit.log_event("ORDER_FILLED", {
                    "order_id": fill.order_id,
                    "price": fill.price,
                    "size": fill.size,
                })
                metrics.fills_total.labels(market_id="").inc()
                if notifier:
                    await notifier.notify(
                        "order_filled",
                        TelegramNotifier.format_fill(fill),
                    )

        # Evaluate rules
        signals = engine.evaluate(snapshots)
        for sig in signals:
            metrics.signals_total.labels(
                rule_name=sig.rule_name,
                action=sig.action.name,
            ).inc()
            await audit.log_event("SIGNAL_GENERATED", {
                "rule": sig.rule_name,
                "market": sig.market_id,
                "action": sig.action.name,
                "price": sig.target_price,
            })
            if notifier:
                await notifier.notify(
                    "signal",
                    TelegramNotifier.format_signal(sig),
                )

            # Risk check
            positions = await executor.get_positions()
            balance = await executor.get_balance()
            passed, reason = risk.check_order(sig, positions, balance)

            if not passed:
                metrics.risk_rejections_total.labels(reason=reason).inc()
                await audit.log_event("RISK_REJECTION", {
                    "rule": sig.rule_name,
                    "reason": reason,
                })
                logger.info("risk_rejected", rule=sig.rule_name, reason=reason)
                if notifier:
                    await notifier.notify(
                        "risk_breach",
                        f"Rule {sig.rule_name} rejected: {reason}",
                    )
                continue

            # Place order
            order = signal_to_order(sig)
            order = await executor.place_order(order)
            metrics.orders_total.labels(
                market_id=order.market_id,
                side=order.side.name,
            ).inc()
            await audit.log_event("ORDER_PLACED", {
                "order_id": order.client_order_id,
                "market": order.market_id,
                "side": order.side.name,
                "price": order.price,
                "size": order.size,
                "status": order.status.name,
            })
            if notifier:
                await notifier.notify(
                    "order_placed",
                    TelegramNotifier.format_order(order),
                )

        # Update metrics
        balance = await executor.get_balance()
        positions = await executor.get_positions()
        metrics.balance_usdc.set(balance)
        metrics.positions_open.set(len(positions))
        total_exposure = sum(p.size * p.current_price for p in positions)
        metrics.total_exposure_usdc.set(total_exposure)

        elapsed = time.monotonic() - t0
        metrics.poll_latency_seconds.observe(elapsed)

        if cycle % 12 == 0:  # Log status every ~minute at 5s interval
            logger.info(
                "status",
                cycle=cycle,
                balance=round(balance, 2),
                positions=len(positions),
                exposure=round(total_exposure, 2),
            )


async def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    config = load_config(args.config)
    setup_logging(
        level=config.telemetry.log_level,
        json_output=config.execution.mode == ExecutionMode.LIVE,
    )
    logger.info("polybot_starting", mode=args.mode, version="0.1.0")
    await _run(config, args.mode)


def cli() -> None:
    """CLI entrypoint (registered in pyproject.toml)."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
