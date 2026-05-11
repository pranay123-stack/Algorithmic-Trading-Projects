"""Prometheus metrics for Polybot.

Exposes counters, gauges, and histograms covering the full trading
pipeline: polling, signals, orders, fills, risk, and balance.
"""

from __future__ import annotations

from threading import Thread

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)


class MetricsCollector:
    """Central Prometheus metrics registry."""

    def __init__(self, port: int = 9090) -> None:
        self._port = port
        self._server_thread: Thread | None = None

        # Counters
        self.polls_total = Counter(
            "polybot_polls_total", "Total polling cycles", ["status"],
        )
        self.signals_total = Counter(
            "polybot_signals_total", "Signals generated", ["rule_name", "action"],
        )
        self.orders_total = Counter(
            "polybot_orders_total", "Orders placed", ["market_id", "side"],
        )
        self.fills_total = Counter(
            "polybot_fills_total", "Fills executed", ["market_id"],
        )
        self.risk_rejections_total = Counter(
            "polybot_risk_rejections_total", "Risk rejections", ["reason"],
        )
        self.notifications_total = Counter(
            "polybot_notifications_total", "Notifications sent", ["event_type"],
        )

        # Gauges
        self.balance_usdc = Gauge("polybot_balance_usdc", "Current USDC balance")
        self.total_exposure_usdc = Gauge("polybot_total_exposure_usdc", "Total open exposure")
        self.positions_open = Gauge("polybot_positions_open", "Number of open positions")
        self.pnl_realized = Gauge("polybot_pnl_realized", "Realized PnL")
        self.pnl_unrealized = Gauge("polybot_pnl_unrealized", "Unrealized PnL")

        # Histograms
        self.poll_latency_seconds = Histogram(
            "polybot_poll_latency_seconds",
            "Polling cycle latency",
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

    def start(self) -> None:
        """Start the Prometheus HTTP server in a daemon thread."""
        start_http_server(self._port)

    def stop(self) -> None:
        """No-op; prometheus_client server shuts down with the process."""
