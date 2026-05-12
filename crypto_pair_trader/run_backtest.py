"""Standalone backtest runner — run from CLI."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config
from backtesting.engine import BacktestEngine
from database.store import DatabaseStore
from exchanges.factory import create_exchange
from pair_selection.selector import PairSelector
from utils.log import setup_logging, get_logger

log = get_logger(__name__)


async def run_backtest():
    cfg = Config.load()
    setup_logging(cfg)

    log.info("=== BACKTEST RUNNER ===")
    log.info("Period: %s to %s", cfg.backtest.start_date, cfg.backtest.end_date)

    exchange = create_exchange(cfg)
    db = DatabaseStore(cfg)
    pair_selector = PairSelector(cfg)
    bt_engine = BacktestEngine(cfg)

    # Fetch historical data for universe
    log.info("Fetching historical data for %d symbols...", len(cfg.pair_selection.universe))
    price_dict = {}
    for symbol in cfg.pair_selection.universe:
        try:
            df = await exchange.fetch_history(symbol, cfg.data.timeframe, cfg.data.history_days)
            if not df.empty:
                price_dict[symbol] = df
                log.info("  %s: %d candles", symbol, len(df))
        except Exception as e:
            log.warning("  %s: FAILED — %s", symbol, e)

    if len(price_dict) < 2:
        log.error("Not enough data to form pairs")
        await exchange.close()
        return

    # Select pairs
    log.info("Scoring pairs...")
    pairs = pair_selector.score_pairs(price_dict)
    if not pairs:
        log.error("No valid pairs found")
        await exchange.close()
        return

    log.info("Selected %d pairs for backtest", len(pairs))

    # Run backtest on each pair
    all_results = []
    for pair in pairs:
        if pair.leg_a not in price_dict or pair.leg_b not in price_dict:
            continue

        data_a = price_dict[pair.leg_a]
        data_b = price_dict[pair.leg_b]

        result = bt_engine.run(pair, data_a, data_b)
        summary = result.summary()
        all_results.append({
            "pair": f"{pair.leg_a}/{pair.leg_b}",
            **summary,
        })

        # Persist backtest result
        import uuid
        db.insert_backtest_result({
            "run_id": str(uuid.uuid4())[:8],
            "params": {
                "pair": f"{pair.leg_a}/{pair.leg_b}",
                "timeframe": cfg.data.timeframe,
                "zscore_entry": cfg.strategy.zscore_entry,
                "zscore_exit": cfg.strategy.zscore_exit,
                "lookback": cfg.strategy.lookback,
            },
            **summary,
        })

    # Print summary table
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 80)
    header = f"{'Pair':<20} {'Trades':>7} {'WinRate':>8} {'PnL':>10} {'PF':>6} {'Sharpe':>7} {'MDD%':>7}"
    print(header)
    print("-" * 80)
    for r in all_results:
        print(
            f"{r['pair']:<20} {r['total_trades']:>7} "
            f"{r['win_rate']*100:>7.1f}% {r['total_pnl']:>10.2f} "
            f"{r['profit_factor']:>6.2f} {r['sharpe_ratio']:>7.2f} "
            f"{r['max_drawdown']*100:>6.2f}%"
        )
    print("=" * 80)

    await exchange.close()
    db.close()


if __name__ == "__main__":
    asyncio.run(run_backtest())
