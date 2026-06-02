from dataclasses import dataclass
from math import sqrt

import pandas as pd

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class BacktestMetrics:
    total_return: float
    cagr: float
    annual_volatility: float
    sharpe: float
    max_drawdown: float
    exposure: float
    turnover: float
    trades: int


@dataclass(frozen=True)
class BacktestResult:
    metrics: BacktestMetrics
    equity: pd.Series
    returns: pd.Series
    effective_position: pd.Series


def run_long_only_backtest(
    close: pd.Series,
    raw_position: pd.Series,
    initial_cash: float,
    fee_bps: float,
    slippage_bps: float,
) -> BacktestResult:
    close = close.astype(float).dropna()
    position = raw_position.reindex(close.index).fillna(0.0).clip(lower=0.0, upper=1.0)

    # Signals are known after the bar closes; execution exposure starts next bar.
    effective_position = position.shift(1).fillna(0.0)
    asset_returns = close.pct_change().fillna(0.0)
    gross_returns = asset_returns * effective_position

    turnover = effective_position.diff().abs().fillna(effective_position.abs())
    cost_rate = (fee_bps + slippage_bps) / 10_000
    net_returns = gross_returns - (turnover * cost_rate)
    equity = initial_cash * (1 + net_returns).cumprod()

    return BacktestResult(
        metrics=calculate_metrics(net_returns, equity, effective_position, turnover),
        equity=equity,
        returns=net_returns,
        effective_position=effective_position,
    )


def calculate_metrics(
    returns: pd.Series,
    equity: pd.Series,
    position: pd.Series,
    turnover: pd.Series,
) -> BacktestMetrics:
    returns = returns.dropna()
    if returns.empty or equity.empty:
        return BacktestMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0)

    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    years = max(len(returns) / TRADING_DAYS_PER_YEAR, 1 / TRADING_DAYS_PER_YEAR)
    cagr = float((1 + total_return) ** (1 / years) - 1) if total_return > -1 else -1.0
    returns_std = returns.std(ddof=0)
    annual_volatility = float(returns_std * sqrt(TRADING_DAYS_PER_YEAR))
    sharpe = (
        float((returns.mean() / returns_std) * sqrt(TRADING_DAYS_PER_YEAR))
        if returns_std
        else 0.0
    )
    drawdown = equity / equity.cummax() - 1
    trades = int((turnover > 0).sum())

    return BacktestMetrics(
        total_return=total_return,
        cagr=cagr,
        annual_volatility=annual_volatility,
        sharpe=sharpe,
        max_drawdown=float(drawdown.min()),
        exposure=float(position.mean()),
        turnover=float(turnover.sum()),
        trades=trades,
    )


def slice_result(result: BacktestResult, start: pd.Timestamp, end: pd.Timestamp) -> BacktestResult:
    returns = result.returns.loc[start:end]
    position = result.effective_position.loc[start:end]
    turnover = position.diff().abs().fillna(position.abs())
    equity = (1 + returns).cumprod()
    equity = equity / equity.iloc[0] if not equity.empty and equity.iloc[0] else equity
    return BacktestResult(
        metrics=calculate_metrics(returns, equity, position, turnover),
        equity=equity,
        returns=returns,
        effective_position=position,
    )