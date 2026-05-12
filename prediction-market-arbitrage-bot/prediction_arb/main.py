"""Main orchestrator for the prediction market arbitrage bot.

Runs a polling loop that:
1. Fetches markets from both Kalshi and Polymarket
2. Matches equivalent markets via NLP embeddings
3. Fetches order books for matched markets
4. Detects arbitrage opportunities
5. Sends alerts via configured channels
6. Prints a live dashboard to the terminal
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone

import httpx
from rich.console import Console
from rich.table import Table

from . import kalshi_client, polymarket_client
from .alerter import send_alerts
from .arbitrage import detect_arbitrage
from .config import Config
from .market_matcher import find_matches
from .models import ArbOpportunity, MarketMatch

logger = logging.getLogger(__name__)
console = Console()

# Graceful shutdown
_shutdown = asyncio.Event()


def _handle_signal(*_):
    console.print("\n[yellow]Shutting down...[/yellow]")
    _shutdown.set()


async def _enrich_orderbooks(
    client: httpx.AsyncClient,
    matches: list[MarketMatch],
) -> None:
    """Fetch order books for all matched markets concurrently."""
    tasks = []

    for match in matches:
        # Kalshi order book
        async def fetch_kalshi_ob(m=match):
            try:
                ob = await kalshi_client.fetch_orderbook(client, m.kalshi_market.market_id)
                m.kalshi_market.order_book = ob
            except Exception as e:
                logger.debug("Kalshi OB failed for %s: %s", m.kalshi_market.market_id, e)

        tasks.append(fetch_kalshi_ob())

        # Polymarket order book (need token_id - use first token = YES)
        async def fetch_poly_ob(m=match):
            tokens = m.poly_market.clob_token_ids
            if not tokens:
                return
            try:
                ob = await polymarket_client.fetch_orderbook(client, tokens[0])
                m.poly_market.order_book = ob
            except Exception as e:
                logger.debug("Poly OB failed for %s: %s", m.poly_market.market_id, e)

        tasks.append(fetch_poly_ob())

    await asyncio.gather(*tasks)


def _print_dashboard(
    matches: list[MarketMatch],
    opportunities: list[ArbOpportunity],
    cycle: int,
) -> None:
    """Print a rich terminal dashboard."""
    now = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    console.clear()
    console.print(f"[bold cyan]Prediction Market Arbitrage Bot[/bold cyan] | Cycle {cycle} | {now}")
    console.print(f"Poll interval: {Config.POLL_INTERVAL}s | Min spread: {Config.MIN_ARB_SPREAD}%\n")

    # Matches table
    match_table = Table(title=f"Matched Markets ({len(matches)})", show_lines=True)
    match_table.add_column("Sim", style="cyan", width=6)
    match_table.add_column("Kalshi", style="white", max_width=50)
    match_table.add_column("Polymarket", style="white", max_width=50)
    match_table.add_column("K.Yes", style="green", width=7)
    match_table.add_column("P.Yes", style="green", width=7)

    for m in matches[:20]:
        k_price = f"{m.kalshi_market.mid_yes:.2f}" if m.kalshi_market.mid_yes else "—"
        p_price = f"{m.poly_market.mid_yes:.2f}" if m.poly_market.mid_yes else "—"
        match_table.add_row(
            f"{m.similarity:.3f}",
            m.kalshi_market.title[:50],
            m.poly_market.title[:50],
            k_price,
            p_price,
        )

    console.print(match_table)

    # Arb table
    if opportunities:
        arb_table = Table(title=f"[bold red]Arbitrage Opportunities ({len(opportunities)})[/bold red]", show_lines=True)
        arb_table.add_column("Spread", style="bold red", width=8)
        arb_table.add_column("Direction", style="yellow", max_width=45)
        arb_table.add_column("K.Price", style="green", width=7)
        arb_table.add_column("P.Price", style="green", width=7)
        arb_table.add_column("$/$$", style="bold", width=8)
        arb_table.add_column("Market", style="white", max_width=50)

        for opp in opportunities[:10]:
            arb_table.add_row(
                f"{opp.spread_pct:+.2f}%",
                opp.direction,
                f"{opp.kalshi_price:.3f}",
                f"{opp.poly_price:.3f}",
                f"{opp.expected_profit_per_dollar:.4f}",
                opp.match.kalshi_market.title[:50],
            )

        console.print(arb_table)
    else:
        console.print("[dim]No arbitrage opportunities found this cycle.[/dim]")

    console.print(f"\n[dim]Press Ctrl+C to stop[/dim]")


async def run_cycle(
    client: httpx.AsyncClient,
    cycle: int,
) -> list[ArbOpportunity]:
    """Run one full scan cycle."""
    console.print(f"[cyan]Cycle {cycle}:[/cyan] Fetching markets...")

    # Fetch markets from both platforms concurrently
    kalshi_task = kalshi_client.fetch_all_markets(client)
    poly_task = polymarket_client.fetch_all_markets(client)
    kalshi_markets, poly_markets = await asyncio.gather(kalshi_task, poly_task)

    console.print(
        f"  Fetched {len(kalshi_markets)} Kalshi + {len(poly_markets)} Polymarket markets"
    )

    # Match markets
    console.print("  Matching markets via embeddings...")
    matches = find_matches(kalshi_markets, poly_markets)
    console.print(f"  Found {len(matches)} matches")

    if not matches:
        _print_dashboard([], [], cycle)
        return []

    # Fetch order books for matched markets
    console.print(f"  Fetching order books for {len(matches)} matches...")
    await _enrich_orderbooks(client, matches)

    # Detect arbitrage
    opportunities = detect_arbitrage(matches)

    # Display dashboard
    _print_dashboard(matches, opportunities, cycle)

    # Send alerts for new opportunities
    if opportunities:
        await send_alerts(client, opportunities)

    return opportunities


async def main() -> None:
    """Main entry point - runs the polling loop."""
    # Set up signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_signal)

    console.print("[bold cyan]Prediction Market Arbitrage Bot[/bold cyan]")
    console.print(f"  Poll interval: {Config.POLL_INTERVAL}s")
    console.print(f"  Min spread: {Config.MIN_ARB_SPREAD}%")
    console.print(f"  Match threshold: {Config.MATCH_THRESHOLD}")
    console.print(f"  Alert channels: {', '.join(Config.ALERT_CHANNELS)}")
    console.print(f"  Embedding model: {Config.EMBEDDING_MODEL}")
    console.print()

    cycle = 0
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        headers={"User-Agent": "PredictionArbBot/1.0"},
    ) as client:
        while not _shutdown.is_set():
            cycle += 1
            try:
                await run_cycle(client, cycle)
            except httpx.HTTPStatusError as e:
                logger.error("HTTP error: %s %s", e.response.status_code, e.response.text[:200])
                console.print(f"[red]HTTP error: {e.response.status_code}[/red]")
            except Exception as e:
                logger.error("Cycle error: %s", e, exc_info=True)
                console.print(f"[red]Error: {e}[/red]")

            # Wait for next cycle or shutdown
            try:
                await asyncio.wait_for(_shutdown.wait(), timeout=Config.POLL_INTERVAL)
                break  # shutdown signaled
            except asyncio.TimeoutError:
                pass  # timeout = time for next cycle

    console.print("[green]Bot stopped.[/green]")


def cli():
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler("arb_bot.log"), logging.StreamHandler()],
    )
    asyncio.run(main())


if __name__ == "__main__":
    cli()
