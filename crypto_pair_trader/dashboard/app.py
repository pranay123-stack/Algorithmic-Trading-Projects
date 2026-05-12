"""Streamlit dashboard for the crypto pair trading system."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import Config
from database.store import DatabaseStore
from analytics.metrics import compute_metrics, trade_log_df

# ── Page config ────────────────────────────────────────────
st.set_page_config(
    page_title="Crypto Pair Trader",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_db() -> DatabaseStore:
    cfg = Config.load()
    return DatabaseStore(cfg)


@st.cache_resource
def get_cfg() -> Config:
    return Config.load()


def main() -> None:
    cfg = get_cfg()
    db = get_db()

    st.title("Crypto Pair Trading Dashboard")
    st.caption(f"Mode: **{cfg.mode.upper()}** | Exchange: **{cfg.exchange.name}** | Timeframe: **{cfg.data.timeframe}**")

    # ── Sidebar ────────────────────────────────────────────
    st.sidebar.header("Controls")
    auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
    if auto_refresh:
        refresh_s = cfg.dashboard.refresh_seconds
        st.sidebar.info(f"Refreshing every {refresh_s}s")

    st.sidebar.divider()
    st.sidebar.subheader("Risk Parameters")
    st.sidebar.metric("Capital", f"${cfg.risk.capital:,.0f}")
    st.sidebar.metric("Max Daily Loss", f"${cfg.risk.max_daily_loss_usd:,.0f}")
    st.sidebar.metric("Max Open Pairs", cfg.risk.max_open_pairs)

    # ── Fetch data ─────────────────────────────────────────
    all_trades = db.get_all_trades(limit=1000)
    open_trades = db.get_open_trades()
    trades_df = trade_log_df(all_trades)
    metrics = compute_metrics(trades_df, cfg.risk.capital)

    # ── KPI row ────────────────────────────────────────────
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Trades", metrics["total_trades"])
    col2.metric("Win Rate", f"{metrics['win_rate'] * 100:.1f}%")
    col3.metric("Total PnL", f"${metrics['total_pnl']:,.2f}")
    col4.metric("Profit Factor", f"{metrics['profit_factor']:.2f}")
    col5.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    col6.metric("Max Drawdown", f"{metrics['max_drawdown_pct']:.1f}%")

    # ── Tabs ───────────────────────────────────────────────
    tab_live, tab_trades, tab_equity, tab_analysis = st.tabs(
        ["Live Spreads", "Trade History", "Equity Curve", "Analysis"]
    )

    # ── Live Spreads tab ───────────────────────────────────
    with tab_live:
        st.subheader("Open Positions")
        if open_trades:
            open_df = pd.DataFrame(open_trades)
            st.dataframe(open_df, use_container_width=True)
        else:
            st.info("No open positions")

        # Spread and z-score charts (from signals table)
        st.subheader("Recent Spread & Z-Score")
        try:
            with db._cursor() as cur:
                cur.execute(
                    "SELECT * FROM signals ORDER BY timestamp DESC LIMIT 500"
                )
                signals = [dict(r) for r in cur.fetchall()]
            if signals:
                sig_df = pd.DataFrame(signals)
                sig_df["timestamp"] = pd.to_datetime(sig_df["timestamp"])
                sig_df = sig_df.sort_values("timestamp")

                # Group by pair
                for pair_key, group in sig_df.groupby(["pair_leg_a", "pair_leg_b"]):
                    st.markdown(f"**{pair_key[0]} / {pair_key[1]}**")
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                        subplot_titles=["Spread", "Z-Score"],
                                        vertical_spacing=0.08)

                    fig.add_trace(
                        go.Scatter(x=group["timestamp"], y=group["spread"],
                                   mode="lines", name="Spread",
                                   line=dict(color="#2196F3")),
                        row=1, col=1,
                    )
                    fig.add_trace(
                        go.Scatter(x=group["timestamp"], y=group["zscore"],
                                   mode="lines", name="Z-Score",
                                   line=dict(color="#FF9800")),
                        row=2, col=1,
                    )
                    # Threshold lines
                    for thresh in [cfg.strategy.zscore_entry, -cfg.strategy.zscore_entry]:
                        fig.add_hline(y=thresh, line_dash="dash",
                                      line_color="red", opacity=0.5, row=2, col=1)
                    fig.add_hline(y=0, line_dash="dot",
                                  line_color="gray", opacity=0.5, row=2, col=1)

                    fig.update_layout(height=400, showlegend=False,
                                      margin=dict(l=40, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No signal data yet")
        except Exception as e:
            st.warning(f"Could not load signals: {e}")

    # ── Trade History tab ──────────────────────────────────
    with tab_trades:
        st.subheader("Trade Log")
        if not trades_df.empty:
            display_cols = [
                "trade_id", "pair_leg_a", "pair_leg_b",
                "side_a", "side_b", "entry_price_a", "entry_price_b",
                "exit_price_a", "exit_price_b", "pnl", "exit_reason",
                "timestamp_open", "timestamp_close",
            ]
            available = [c for c in display_cols if c in trades_df.columns]
            st.dataframe(
                trades_df[available].style.applymap(
                    lambda v: "color: green" if isinstance(v, (int, float)) and v > 0 else
                              ("color: red" if isinstance(v, (int, float)) and v < 0 else ""),
                    subset=["pnl"] if "pnl" in available else [],
                ),
                use_container_width=True,
                height=400,
            )
        else:
            st.info("No trades recorded yet")

    # ── Equity Curve tab ───────────────────────────────────
    with tab_equity:
        st.subheader("Equity Curve")
        if not trades_df.empty:
            closed = trades_df[trades_df["timestamp_close"].notna()].copy()
            if not closed.empty:
                closed = closed.sort_values("timestamp_close")
                equity = cfg.risk.capital + closed["pnl"].cumsum()
                equity.index = closed["timestamp_close"]

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=equity.index, y=equity.values,
                    mode="lines", name="Equity",
                    fill="tozeroy", fillcolor="rgba(33, 150, 243, 0.1)",
                    line=dict(color="#2196F3", width=2),
                ))
                fig.add_hline(y=cfg.risk.capital, line_dash="dash",
                              line_color="gray", opacity=0.5)
                fig.update_layout(
                    height=400,
                    yaxis_title="Equity ($)",
                    margin=dict(l=40, r=20, t=20, b=20),
                )
                st.plotly_chart(fig, use_container_width=True)

                # Drawdown chart
                running_max = equity.cummax()
                dd_pct = (equity - running_max) / running_max * 100
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=dd_pct.index, y=dd_pct.values,
                    mode="lines", name="Drawdown %",
                    fill="tozeroy", fillcolor="rgba(244, 67, 54, 0.2)",
                    line=dict(color="#F44336", width=1.5),
                ))
                fig_dd.update_layout(
                    height=250,
                    yaxis_title="Drawdown (%)",
                    margin=dict(l=40, r=20, t=20, b=20),
                )
                st.plotly_chart(fig_dd, use_container_width=True)
            else:
                st.info("No closed trades yet")
        else:
            st.info("No trade data available")

    # ── Analysis tab ───────────────────────────────────────
    with tab_analysis:
        st.subheader("Performance Analysis")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Detailed Metrics**")
            for k, v in metrics.items():
                st.text(f"{k}: {v}")

        with col_b:
            if not trades_df.empty and "pnl" in trades_df.columns:
                st.markdown("**PnL Distribution**")
                closed = trades_df[trades_df["timestamp_close"].notna()]
                if not closed.empty:
                    fig_hist = go.Figure()
                    fig_hist.add_trace(go.Histogram(
                        x=closed["pnl"], nbinsx=30,
                        marker_color="#2196F3", opacity=0.7,
                    ))
                    fig_hist.update_layout(
                        height=300, xaxis_title="PnL ($)",
                        yaxis_title="Count",
                        margin=dict(l=40, r=20, t=20, b=20),
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)

                # Exit reason breakdown
                if "exit_reason" in closed.columns:
                    st.markdown("**Exit Reasons**")
                    reason_counts = closed["exit_reason"].value_counts()
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=reason_counts.index,
                        values=reason_counts.values,
                        hole=0.4,
                    )])
                    fig_pie.update_layout(
                        height=300,
                        margin=dict(l=20, r=20, t=20, b=20),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)

    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(cfg.dashboard.refresh_seconds)
        st.rerun()


if __name__ == "__main__":
    main()
