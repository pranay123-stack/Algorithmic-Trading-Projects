"""Alert system for sending arbitrage notifications via Telegram and Discord."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from .config import Config
from .models import ArbOpportunity

logger = logging.getLogger(__name__)


def _format_alert(opp: ArbOpportunity) -> str:
    """Format an arbitrage opportunity into a readable alert message."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"{'='*40}\n"
        f"ARBITRAGE ALERT | {opp.spread_pct:+.2f}%\n"
        f"{'='*40}\n"
        f"Direction: {opp.direction}\n"
        f"Kalshi price: {opp.kalshi_price:.3f}\n"
        f"Polymarket price: {opp.poly_price:.3f}\n"
        f"Profit per $1: ${opp.expected_profit_per_dollar:.4f}\n"
        f"\n"
        f"Kalshi: {opp.match.kalshi_market.title}\n"
        f"  ID: {opp.match.kalshi_market.market_id}\n"
        f"Polymarket: {opp.match.poly_market.title}\n"
        f"  ID: {opp.match.poly_market.market_id}\n"
        f"\n"
        f"Match similarity: {opp.match.similarity:.3f}\n"
        f"Detected at: {now}\n"
        f"{'='*40}"
    )


async def send_telegram(
    client: httpx.AsyncClient,
    opportunities: list[ArbOpportunity],
) -> None:
    """Send alerts via Telegram Bot API."""
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram not configured, skipping")
        return

    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"

    for opp in opportunities:
        text = _format_alert(opp)
        payload = {
            "chat_id": Config.TELEGRAM_CHAT_ID,
            "text": f"```\n{text}\n```",
            "parse_mode": "Markdown",
        }
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info("Telegram alert sent for %s", opp.match.kalshi_market.market_id)
        except Exception as e:
            logger.error("Telegram send failed: %s", e)


async def send_discord(
    client: httpx.AsyncClient,
    opportunities: list[ArbOpportunity],
) -> None:
    """Send alerts via Discord webhook."""
    if not Config.DISCORD_WEBHOOK_URL:
        logger.warning("Discord webhook not configured, skipping")
        return

    for opp in opportunities:
        text = _format_alert(opp)
        payload = {"content": f"```\n{text}\n```"}
        try:
            resp = await client.post(Config.DISCORD_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
            logger.info("Discord alert sent for %s", opp.match.kalshi_market.market_id)
        except Exception as e:
            logger.error("Discord send failed: %s", e)


async def send_alerts(
    client: httpx.AsyncClient,
    opportunities: list[ArbOpportunity],
) -> None:
    """Dispatch alerts to all configured channels."""
    if not opportunities:
        return

    logger.info("Sending %d alerts to channels: %s", len(opportunities), Config.ALERT_CHANNELS)

    if "telegram" in Config.ALERT_CHANNELS:
        await send_telegram(client, opportunities)
    if "discord" in Config.ALERT_CHANNELS:
        await send_discord(client, opportunities)
