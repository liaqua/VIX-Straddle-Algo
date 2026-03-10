import pandas as pd
import numpy as np
import yfinance as yf
import quantstats as qs
import matplotlib.pyplot as plt
from datetime import datetime

# Extend pandas functionality with QuantStats
qs.extend_pandas()


def get_vol_data(start_date, end_date):
    """Fetch VIX and VVIX data."""
    tickers = ["^VIX", "^VVIX"]
    data = yf.download(tickers, start=start_date, end=end_date, interval="1d", progress=False)
    # Handle multi-level columns
    if isinstance(data.columns, pd.MultiIndex):
        data = data['Close']
    return data.dropna()


def get_price_data(start_date, end_date):
    """Fetch UGA and USO price data."""
    tickers = ["UGA", "USO"]
    data = yf.download(tickers, start=start_date, end=end_date, interval="1d", progress=False)
    # Handle multi-level columns - use Close instead of Adj Close
    if isinstance(data.columns, pd.MultiIndex):
        data = data['Close']
    return data.dropna()


def zscore(series, window=20):
    """Calculate z-score."""
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    return (series - mean) / std


def generate_signals(vol_data):
    """Generate trading signals based on VVIX z-score and day of week."""
    signals = pd.DataFrame(index=vol_data.index)
    signals['vvix'] = vol_data["^VVIX"]
    signals['z_vvix'] = zscore(signals['vvix'], window=20)

    # Check if it's Thursday (3) or Friday (4)
    signals['is_late_week'] = signals.index.dayofweek.isin([3, 4])

    # Generate entry/exit signals
    signals['position'] = 0

    for i in range(len(signals)):
        z = signals['z_vvix'].iloc[i]
        is_late = signals['is_late_week'].iloc[i]

        if pd.notna(z):
            if z > 1.5 and is_late:
                signals['position'].iloc[i] = 1  # Enter position
            elif z < 0.5:
                signals['position'].iloc[i] = 0  # Exit position
            elif i > 0:
                signals['position'].iloc[i] = signals['position'].iloc[i - 1]  # Hold previous

    return signals


def backtest_strategy(start_date="2020-01-01", end_date="2024-12-31"):
    """Run backtest and generate performance metrics."""

    print("Downloading data...")
    vol_data = get_vol_data(start_date, end_date)
    price_data = get_price_data(start_date, end_date)

    print("Generating signals...")
    signals = generate_signals(vol_data)

    # Align signals with price data
    df = price_data.join(signals[['position']], how='inner')
    df['position'] = df['position'].fillna(method='ffill').fillna(0)

    # Calculate daily returns
    df['uga_returns'] = df['UGA'].pct_change()
    df['uso_returns'] = df['USO'].pct_change()

    # Strategy returns: Long UGA, Short USO when position = 1
    df['strategy_returns'] = df['position'] * (df['uga_returns'] - df['uso_returns'])

    # Benchmark: Buy and hold UGA
    df['benchmark_returns'] = df['uga_returns']

    # Calculate cumulative returns
    df['strategy_cumulative'] = (1 + df['strategy_returns']).cumprod()
    df['benchmark_cumulative'] = (1 + df['benchmark_returns']).cumprod()

    # Drop NaN values
    strategy_returns = df['strategy_returns'].dropna()
    benchmark_returns = df['benchmark_returns'].dropna()

    print(f"\n{'=' * 60}")
    print("BACKTEST RESULTS")
    print(f"{'=' * 60}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Total Trading Days: {len(strategy_returns)}")
    print(f"Days in Position: {(df['position'] == 1).sum()}")
    print(f"Position Rate: {(df['position'] == 1).sum() / len(df) * 100:.1f}%")

    # Performance metrics
    print(f"\n{'Strategy Performance':^60}")
    print(f"{'-' * 60}")
    total_return = (df['strategy_cumulative'].iloc[-1] - 1) * 100
    print(f"Total Return: {total_return:.2f}%")
    print(f"Sharpe Ratio: {qs.stats.sharpe(strategy_returns):.2f}")
    print(f"Max Drawdown: {qs.stats.max_drawdown(strategy_returns) * 100:.2f}%")
    print(f"Win Rate: {(strategy_returns > 0).sum() / len(strategy_returns) * 100:.1f}%")

    print(f"\n{'Benchmark Performance (UGA Buy & Hold)':^60}")
    print(f"{'-' * 60}")
    bench_return = (df['benchmark_cumulative'].iloc[-1] - 1) * 100
    print(f"Total Return: {bench_return:.2f}%")
    print(f"Sharpe Ratio: {qs.stats.sharpe(benchmark_returns):.2f}")
    print(f"Max Drawdown: {qs.stats.max_drawdown(benchmark_returns) * 100:.2f}%")

    # Plot results
    fig, axes = plt.subplots(3, 1, figsize=(14, 10))

    # Cumulative returns
    axes[0].plot(df.index, df['strategy_cumulative'], label='Strategy', linewidth=2)
    axes[0].plot(df.index, df['benchmark_cumulative'], label='Benchmark (UGA)', linewidth=2, alpha=0.7)
    axes[0].set_title('Cumulative Returns', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Cumulative Return')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Drawdown
    strategy_dd = qs.stats.to_drawdown_series(strategy_returns)
    axes[1].fill_between(strategy_dd.index, strategy_dd * 100, 0, alpha=0.3, color='red')
    axes[1].set_title('Strategy Drawdown', fontsize=14, fontweight='bold')
    axes[1].set_ylabel('Drawdown (%)')
    axes[1].grid(True, alpha=0.3)

    # Position indicator
    axes[2].fill_between(df.index, 0, df['position'], alpha=0.3, label='In Position')
    axes[2].set_title('Position Status', fontsize=14, fontweight='bold')
    axes[2].set_ylabel('Position (0=Out, 1=In)')
    axes[2].set_ylim([-0.1, 1.1])
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('backtest_results.png', dpi=300, bbox_inches='tight')
    print(f"\n📊 Chart saved as 'backtest_results.png'")
    plt.show()

    # Generate full QuantStats report
    print("\nGenerating detailed QuantStats report...")
    qs.reports.html(strategy_returns, benchmark_returns,
                    output='quantstats_report.html',
                    title='VVIX Energy Pairs Strategy')
    print("📈 Full report saved as 'quantstats_report.html'")

    return df, strategy_returns, benchmark_returns


if __name__ == "__main__":
    # Run backtest for the last 5 years
    df, strat_returns, bench_returns = backtest_strategy(
        start_date="2020-01-01",
        end_date="2024-12-31"
    )