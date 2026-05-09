"""
Comprehensive Backtesting Engine for ICT × SMC Strategy
Includes performance metrics, visualization, and optimization
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')


@dataclass
class BacktestMetrics:
    """Performance metrics from backtest"""
    total_return_pct: float
    annual_return_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    max_win: float
    max_loss: float
    avg_trade_duration_hours: float
    expectancy: float


class Backtester:
    """
    Comprehensive backtesting engine with performance analytics
    """

    def __init__(
        self,
        initial_capital: float = 10000,
        commission_pct: float = 0.04,  # 0.04% per trade (Binance futures)
        slippage_pct: float = 0.02,  # 0.02% slippage
    ):
        """
        Initialize backtester

        Args:
            initial_capital: Starting capital
            commission_pct: Commission per trade
            slippage_pct: Slippage percentage
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct / 100
        self.slippage_pct = slippage_pct / 100

    def run_backtest(
        self,
        df: pd.DataFrame,
        leverage: float = 3.0,
        compound: bool = True
    ) -> Tuple[pd.DataFrame, BacktestMetrics]:
        """
        Run backtest on DataFrame with signals

        Args:
            df: DataFrame with signal columns
            leverage: Leverage multiplier
            compound: Whether to compound profits

        Returns:
            (Results DataFrame, Metrics)
        """
        df = df.copy()

        # Initialize tracking columns
        df['position'] = 0  # 0=flat, 1=long, -1=short
        df['position_size'] = 0.0
        df['entry_price'] = np.nan
        df['exit_price'] = np.nan
        df['trade_pnl'] = 0.0
        df['trade_pnl_pct'] = 0.0
        df['capital'] = float(self.initial_capital)
        df['portfolio_value'] = float(self.initial_capital)
        df['drawdown'] = 0.0
        df['drawdown_pct'] = 0.0

        capital = self.initial_capital
        position = 0
        entry_price = 0
        stop_loss = 0
        take_profit = 0
        position_size = 0
        peak_value = self.initial_capital

        trades = []

        for i in range(len(df)):
            current_price = df['close'].iloc[i]

            # Check for new signals
            signal = df['signal'].iloc[i] if 'signal' in df.columns else 0

            # Entry logic
            if position == 0 and signal in [1, -1]:  # Long or Short signal
                entry_price = current_price
                stop_loss = df['stop_loss'].iloc[i]
                take_profit = df['take_profit'].iloc[i]

                # Apply slippage to entry
                if signal == 1:  # Long
                    entry_price *= (1 + self.slippage_pct)
                else:  # Short
                    entry_price *= (1 - self.slippage_pct)

                # Calculate position size with leverage
                risk_amount = capital * 0.01  # 1% risk
                price_risk = abs(entry_price - stop_loss)
                position_size = (risk_amount / price_risk) * leverage if price_risk > 0 else 0

                # Cap at max position size
                max_position_value = capital * 0.1 * leverage  # 10% of capital with leverage
                position_size = min(position_size, max_position_value / entry_price)

                # CRITICAL FIX: Check capital adequacy
                required_margin = (position_size * entry_price) / leverage
                commission = position_size * entry_price * self.commission_pct

                # Skip trade if insufficient capital (leave 5% buffer)
                if required_margin + commission > capital * 0.95:
                    continue  # Skip this trade - insufficient capital

                position = signal
                df.loc[df.index[i], 'position'] = position
                df.loc[df.index[i], 'position_size'] = position_size
                df.loc[df.index[i], 'entry_price'] = entry_price

                trades.append({
                    'entry_time': df.index[i],
                    'entry_price': entry_price,
                    'position_type': 'LONG' if signal == 1 else 'SHORT',
                    'position_size': position_size,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'commission': commission
                })

            # Exit logic
            elif position != 0:
                exit_signal = False
                exit_price = current_price

                # CRITICAL FIX: Check high/low for intra-bar execution
                candle_high = df['high'].iloc[i]
                candle_low = df['low'].iloc[i]

                # Check stop loss and take profit using high/low
                if position == 1:  # Long position
                    # Check if stop loss was hit (use low)
                    if candle_low <= stop_loss:
                        exit_signal = True
                        exit_price = stop_loss
                    # Check if take profit was hit (use high)
                    elif candle_high >= take_profit:
                        exit_signal = True
                        exit_price = take_profit
                    elif signal == -1:  # Reverse signal
                        exit_signal = True

                elif position == -1:  # Short position
                    # Check if stop loss was hit (use high)
                    if candle_high >= stop_loss:
                        exit_signal = True
                        exit_price = stop_loss
                    # Check if take profit was hit (use low)
                    elif candle_low <= take_profit:
                        exit_signal = True
                        exit_price = take_profit
                    elif signal == 1:  # Reverse signal
                        exit_signal = True

                # Calculate unrealized PnL
                if position == 1:
                    unrealized_pnl = position_size * (current_price - entry_price)
                else:
                    unrealized_pnl = position_size * (entry_price - current_price)

                # Update portfolio value
                portfolio_value = capital + unrealized_pnl
                df.loc[df.index[i], 'portfolio_value'] = portfolio_value

                # Exit position
                if exit_signal:
                    # Apply slippage to exit
                    if position == 1:
                        exit_price *= (1 - self.slippage_pct)
                    else:
                        exit_price *= (1 + self.slippage_pct)

                    # Calculate PnL
                    if position == 1:
                        trade_pnl = position_size * (exit_price - entry_price)
                    else:
                        trade_pnl = position_size * (entry_price - exit_price)

                    # Subtract commission
                    exit_commission = position_size * exit_price * self.commission_pct
                    trade_pnl -= (trades[-1]['commission'] + exit_commission)

                    trade_pnl_pct = (trade_pnl / capital) * 100

                    # Update capital
                    if compound:
                        capital += trade_pnl
                    else:
                        capital = self.initial_capital + (capital - self.initial_capital) + trade_pnl

                    df.loc[df.index[i], 'exit_price'] = exit_price
                    df.loc[df.index[i], 'trade_pnl'] = trade_pnl
                    df.loc[df.index[i], 'trade_pnl_pct'] = trade_pnl_pct
                    df.loc[df.index[i], 'capital'] = capital
                    df.loc[df.index[i], 'portfolio_value'] = capital

                    # Update trade record
                    trades[-1].update({
                        'exit_time': df.index[i],
                        'exit_price': exit_price,
                        'pnl': trade_pnl,
                        'pnl_pct': trade_pnl_pct,
                        'exit_commission': exit_commission,
                        'duration': df.index[i] - trades[-1]['entry_time']
                    })

                    position = 0
                    position_size = 0

            # Update capital tracking
            if position == 0:
                df.loc[df.index[i], 'capital'] = capital
                df.loc[df.index[i], 'portfolio_value'] = capital

            # Calculate drawdown
            if df['portfolio_value'].iloc[i] > peak_value:
                peak_value = df['portfolio_value'].iloc[i]

            drawdown = peak_value - df['portfolio_value'].iloc[i]
            drawdown_pct = (drawdown / peak_value) * 100 if peak_value > 0 else 0

            df.loc[df.index[i], 'drawdown'] = drawdown
            df.loc[df.index[i], 'drawdown_pct'] = drawdown_pct

        # Calculate metrics
        metrics = self._calculate_metrics(df, trades)

        return df, metrics

    def _calculate_metrics(
        self,
        df: pd.DataFrame,
        trades: List[Dict]
    ) -> BacktestMetrics:
        """Calculate performance metrics"""

        # Filter completed trades
        completed_trades = [t for t in trades if 'pnl' in t]

        if not completed_trades:
            return BacktestMetrics(
                total_return_pct=0, annual_return_pct=0, sharpe_ratio=0,
                sortino_ratio=0, max_drawdown_pct=0, win_rate=0,
                profit_factor=0, total_trades=0, winning_trades=0,
                losing_trades=0, avg_win=0, avg_loss=0, max_win=0,
                max_loss=0, avg_trade_duration_hours=0, expectancy=0
            )

        # Total return
        final_capital = df['capital'].iloc[-1]
        total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # Annualized return
        days = (df.index[-1] - df.index[0]).total_seconds() / (24 * 3600)
        years = days / 365.25
        annual_return_pct = ((final_capital / self.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # Returns for Sharpe/Sortino
        df['returns'] = df['portfolio_value'].pct_change()
        returns = df['returns'].dropna()

        # CRITICAL FIX: Auto-detect timeframe and calculate correct annualization factor
        if len(df) > 1:
            timeframe_minutes = (df.index[1] - df.index[0]).total_seconds() / 60
        else:
            timeframe_minutes = 15  # Default to 15m

        # Calculate periods per year based on timeframe
        if timeframe_minutes == 1:
            periods_per_year = 252 * 24 * 60  # 1-minute
        elif timeframe_minutes == 5:
            periods_per_year = 252 * 24 * 12  # 5-minute
        elif timeframe_minutes == 15:
            periods_per_year = 252 * 24 * 4   # 15-minute (CORRECT!)
        elif timeframe_minutes == 30:
            periods_per_year = 252 * 24 * 2   # 30-minute
        elif timeframe_minutes == 60:
            periods_per_year = 252 * 24       # 1-hour
        elif timeframe_minutes == 240:
            periods_per_year = 252 * 6        # 4-hour
        elif timeframe_minutes >= 1440:
            periods_per_year = 252            # Daily or higher
        else:
            # Custom timeframe - estimate
            periods_per_year = int(252 * 24 * 60 / timeframe_minutes)

        # Sharpe ratio (assuming risk-free rate = 0)
        if returns.std() > 0:
            sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(periods_per_year)
        else:
            sharpe_ratio = 0

        # Sortino ratio (downside deviation)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = (returns.mean() / downside_returns.std()) * np.sqrt(periods_per_year)
        else:
            sortino_ratio = 0

        # Max drawdown
        max_drawdown_pct = df['drawdown_pct'].max()

        # Win rate and trade stats
        pnls = [t['pnl'] for t in completed_trades]
        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        total_trades = len(completed_trades)
        num_winning = len(winning_trades)
        num_losing = len(losing_trades)
        win_rate = (num_winning / total_trades) * 100 if total_trades > 0 else 0

        # Profit factor
        gross_profit = sum(winning_trades) if winning_trades else 0
        gross_loss = abs(sum(losing_trades)) if losing_trades else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # Average win/loss
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        max_win = max(winning_trades) if winning_trades else 0
        max_loss = min(losing_trades) if losing_trades else 0

        # Average trade duration
        durations = [t['duration'].total_seconds() / 3600 for t in completed_trades]  # in hours
        avg_trade_duration_hours = np.mean(durations) if durations else 0

        # Expectancy
        expectancy = (win_rate / 100 * avg_win) + ((1 - win_rate / 100) * avg_loss)

        return BacktestMetrics(
            total_return_pct=total_return_pct,
            annual_return_pct=annual_return_pct,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown_pct=max_drawdown_pct,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=num_winning,
            losing_trades=num_losing,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_win=max_win,
            max_loss=max_loss,
            avg_trade_duration_hours=avg_trade_duration_hours,
            expectancy=expectancy
        )

    def plot_results(
        self,
        df: pd.DataFrame,
        metrics: BacktestMetrics,
        save_path: Optional[str] = None
    ):
        """
        Plot backtest results

        Args:
            df: Results DataFrame
            metrics: Performance metrics
            save_path: Path to save plot
        """
        fig, axes = plt.subplots(3, 2, figsize=(16, 12))
        fig.suptitle('ICT × SMC Strategy Backtest Results', fontsize=16, fontweight='bold')

        # 1. Portfolio value over time
        ax = axes[0, 0]
        ax.plot(df.index, df['portfolio_value'], label='Portfolio Value', linewidth=1.5)
        ax.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.5, label='Initial Capital')
        ax.fill_between(df.index, self.initial_capital, df['portfolio_value'],
                        where=(df['portfolio_value'] >= self.initial_capital),
                        color='green', alpha=0.3, label='Profit')
        ax.fill_between(df.index, self.initial_capital, df['portfolio_value'],
                        where=(df['portfolio_value'] < self.initial_capital),
                        color='red', alpha=0.3, label='Loss')
        ax.set_title('Portfolio Value Over Time')
        ax.set_xlabel('Date')
        ax.set_ylabel('Value ($)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Drawdown
        ax = axes[0, 1]
        ax.fill_between(df.index, 0, df['drawdown_pct'], color='red', alpha=0.5)
        ax.set_title(f'Drawdown (Max: {metrics.max_drawdown_pct:.2f}%)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Drawdown (%)')
        ax.invert_yaxis()
        ax.grid(True, alpha=0.3)

        # 3. Cumulative returns
        ax = axes[1, 0]
        df['cumulative_return_pct'] = ((df['portfolio_value'] - self.initial_capital) / self.initial_capital) * 100
        ax.plot(df.index, df['cumulative_return_pct'], color='purple', linewidth=1.5)
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.set_title(f'Cumulative Returns (Total: {metrics.total_return_pct:.2f}%)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Return (%)')
        ax.grid(True, alpha=0.3)

        # 4. Trade PnL distribution
        ax = axes[1, 1]
        trade_pnls = df[df['trade_pnl'] != 0]['trade_pnl']
        if len(trade_pnls) > 0:
            ax.hist(trade_pnls, bins=30, color='steelblue', edgecolor='black', alpha=0.7)
            ax.axvline(x=0, color='red', linestyle='--', linewidth=2)
            ax.set_title(f'Trade PnL Distribution (Win Rate: {metrics.win_rate:.1f}%)')
            ax.set_xlabel('PnL ($)')
            ax.set_ylabel('Frequency')
            ax.grid(True, alpha=0.3)

        # 5. Monthly returns heatmap
        ax = axes[2, 0]
        df['year'] = df.index.year
        df['month'] = df.index.month
        monthly_returns = df.groupby(['year', 'month'])['returns'].sum() * 100
        if len(monthly_returns) > 0:
            pivot = monthly_returns.unstack(fill_value=0)
            sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                       ax=ax, cbar_kws={'label': 'Return (%)'})
            ax.set_title('Monthly Returns Heatmap')
            ax.set_xlabel('Month')
            ax.set_ylabel('Year')

        # 6. Metrics table
        ax = axes[2, 1]
        ax.axis('off')
        metrics_text = f"""
        PERFORMANCE METRICS
        ═══════════════════════════════
        Total Return:        {metrics.total_return_pct:>10.2f}%
        Annual Return:       {metrics.annual_return_pct:>10.2f}%
        Sharpe Ratio:        {metrics.sharpe_ratio:>10.2f}
        Sortino Ratio:       {metrics.sortino_ratio:>10.2f}
        Max Drawdown:        {metrics.max_drawdown_pct:>10.2f}%

        TRADE STATISTICS
        ═══════════════════════════════
        Total Trades:        {metrics.total_trades:>10}
        Win Rate:            {metrics.win_rate:>10.2f}%
        Profit Factor:       {metrics.profit_factor:>10.2f}

        Avg Win:             ${metrics.avg_win:>10.2f}
        Avg Loss:            ${metrics.avg_loss:>10.2f}
        Max Win:             ${metrics.max_win:>10.2f}
        Max Loss:            ${metrics.max_loss:>10.2f}

        Expectancy:          ${metrics.expectancy:>10.2f}
        Avg Duration:        {metrics.avg_trade_duration_hours:>10.1f}h
        """
        ax.text(0.1, 0.5, metrics_text, fontfamily='monospace', fontsize=10,
               verticalalignment='center')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")

        plt.show()

    def print_metrics(self, metrics: BacktestMetrics):
        """Print formatted metrics"""
        print("\n" + "="*60)
        print(" "*15 + "BACKTEST PERFORMANCE METRICS")
        print("="*60)
        print(f"\n{'RETURNS':-^60}")
        print(f"Total Return:            {metrics.total_return_pct:>10.2f}%")
        print(f"Annual Return:           {metrics.annual_return_pct:>10.2f}%")
        print(f"\n{'RISK METRICS':-^60}")
        print(f"Sharpe Ratio:            {metrics.sharpe_ratio:>10.2f}")
        print(f"Sortino Ratio:           {metrics.sortino_ratio:>10.2f}")
        print(f"Max Drawdown:            {metrics.max_drawdown_pct:>10.2f}%")
        print(f"\n{'TRADE STATISTICS':-^60}")
        print(f"Total Trades:            {metrics.total_trades:>10}")
        print(f"Winning Trades:          {metrics.winning_trades:>10}")
        print(f"Losing Trades:           {metrics.losing_trades:>10}")
        print(f"Win Rate:                {metrics.win_rate:>10.2f}%")
        print(f"Profit Factor:           {metrics.profit_factor:>10.2f}")
        print(f"\n{'PROFIT/LOSS':-^60}")
        print(f"Average Win:             ${metrics.avg_win:>10.2f}")
        print(f"Average Loss:            ${metrics.avg_loss:>10.2f}")
        print(f"Max Win:                 ${metrics.max_win:>10.2f}")
        print(f"Max Loss:                ${metrics.max_loss:>10.2f}")
        print(f"Expectancy:              ${metrics.expectancy:>10.2f}")
        print(f"\n{'OTHER':-^60}")
        print(f"Avg Trade Duration:      {metrics.avg_trade_duration_hours:>10.1f} hours")
        print("="*60 + "\n")


if __name__ == "__main__":
    # Example backtest
    from data_fetcher import MultiTimeframeDataFetcher
    from ict_indicators import ICTIndicators
    from strategy import ICTSMCStrategy

    print("Fetching data...")
    fetcher = MultiTimeframeDataFetcher(symbol='BTC/USDT')
    data = fetcher.fetch_multi_timeframe(['5m', '1h', '4h', '1d'], days_back=60)

    print("Calculating indicators...")
    ict = ICTIndicators(data['5m'])
    df = ict.calculate_all_indicators()

    for htf in ['1h', '4h', '1d']:
        df = ict.get_higher_timeframe_poi(data[htf], htf_name=htf)

    print("Generating signals...")
    strategy = ICTSMCStrategy(risk_per_trade=0.01, rr_ratio=2.5)
    df_signals = strategy.generate_signals(df, min_confidence=0.6)

    print("Running backtest...")
    backtester = Backtester(initial_capital=10000)
    results_df, metrics = backtester.run_backtest(df_signals, leverage=3.0)

    backtester.print_metrics(metrics)
    backtester.plot_results(results_df, metrics, save_path='./backtest_results.png')
