import json
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from stock_trade.config import get_settings
from stock_trade.execution.planner import (
    TradePlan,
    TradePlanItem,
    build_trade_plan,
    resize_trade_plan,
)
from stock_trade.research.data import fetch_adjusted_close, normalize_symbols
from stock_trade.research.sweep import run_strategy_sweep
from stock_trade.research.walk_forward import run_walk_forward, summarize_walk_forward
from stock_trade.risk import RiskLimits

app = typer.Typer(help="Research strategies and execute gated Alpaca paper trades.")
console = Console()
DEFAULT_RESEARCH_OUTPUT_DIR = Path("artifacts/research")
DEFAULT_PLAN_FILE = Path("artifacts/research/trade_plan.json")


@app.command()
def research(
    symbols: Annotated[
        str,
        typer.Option(help="Comma-separated symbols. Defaults to DEFAULT_UNIVERSE."),
    ] = "",
    start: Annotated[str, typer.Option(help="Research start date.")] = "2018-01-01",
    end: Annotated[
        str | None,
        typer.Option(help="Exclusive end date, defaults to today."),
    ] = None,
    output_dir: Annotated[
        Path,
        typer.Option(help="Directory for outputs."),
    ] = DEFAULT_RESEARCH_OUTPUT_DIR,
) -> None:
    settings = get_settings()
    universe = normalize_symbols(symbols or settings.default_universe)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"Fetching adjusted daily closes for {', '.join(universe)}")
    close = fetch_adjusted_close(universe, start=start, end=end or date.today().isoformat())
    leaderboard = run_strategy_sweep(
        close=close,
        initial_cash=settings.initial_cash,
        fee_bps=settings.fee_bps,
        slippage_bps=settings.slippage_bps,
    )

    leaderboard_path = output_dir / "leaderboard.csv"
    leaderboard.to_csv(leaderboard_path, index=False)

    limits = _risk_limits(settings)
    plan = build_trade_plan(leaderboard, account_equity=settings.initial_cash, limits=limits)
    plan_path = output_dir / "trade_plan.json"
    plan_path.write_text(json.dumps(plan.to_dict(), indent=2), encoding="utf-8")

    _print_leaderboard(leaderboard.head(10))
    _print_plan(plan)
    console.print(f"Wrote {leaderboard_path} and {plan_path}")


@app.command("research-walk-forward")
def research_walk_forward(
    symbols: Annotated[
        str,
        typer.Option(help="Comma-separated symbols. Defaults to DEFAULT_UNIVERSE."),
    ] = "",
    start: Annotated[str, typer.Option(help="Research start date.")] = "2018-01-01",
    end: Annotated[
        str | None,
        typer.Option(help="Exclusive end date, defaults to today."),
    ] = None,
    train_size: Annotated[int, typer.Option(help="Training bars per rolling window.")] = 504,
    validation_size: Annotated[int, typer.Option(help="Validation bars per rolling window.")] = 126,
    test_size: Annotated[
        int,
        typer.Option(help="Out-of-sample test bars per rolling window."),
    ] = 126,
    step_size: Annotated[int, typer.Option(help="Bars to advance each rolling window.")] = 126,
    output_dir: Annotated[
        Path,
        typer.Option(help="Directory for outputs."),
    ] = DEFAULT_RESEARCH_OUTPUT_DIR,
) -> None:
    settings = get_settings()
    universe = normalize_symbols(symbols or settings.default_universe)
    output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"Fetching adjusted daily closes for {', '.join(universe)}")
    close = fetch_adjusted_close(universe, start=start, end=end or date.today().isoformat())
    windows = run_walk_forward(
        close=close,
        initial_cash=settings.initial_cash,
        fee_bps=settings.fee_bps,
        slippage_bps=settings.slippage_bps,
        train_size=train_size,
        validation_size=validation_size,
        test_size=test_size,
        step_size=step_size,
    )
    summary = summarize_walk_forward(
        windows,
        min_validation_sharpe=settings.min_validation_sharpe,
        max_drawdown_pct=settings.max_drawdown_pct,
    )

    windows_path = output_dir / "walk_forward_windows.csv"
    summary_path = output_dir / "walk_forward_summary.csv"
    windows.to_csv(windows_path, index=False)
    summary.to_csv(summary_path, index=False)

    _print_walk_forward_summary(summary.head(10))
    console.print(f"Wrote {windows_path} and {summary_path}")


@app.command("paper-plan")
def paper_plan(
    plan_file: Annotated[Path, typer.Option()] = DEFAULT_PLAN_FILE,
) -> None:
    plan = _read_plan(plan_file)
    _print_plan(plan)


@app.command("paper-execute")
def paper_execute(
    plan_file: Annotated[Path, typer.Option()] = DEFAULT_PLAN_FILE,
    yes: Annotated[
        bool,
        typer.Option("--yes", help="Submit orders after all env safety gates pass."),
    ] = False,
) -> None:
    settings = get_settings()
    plan = _read_plan(plan_file)
    _print_plan(plan)
    if not yes:
        console.print("Dry run only. Re-run with --yes after reviewing the plan.")
        raise typer.Exit(0)

    from stock_trade.brokers.alpaca_paper import AlpacaPaperBroker

    broker = AlpacaPaperBroker(settings)
    plan = resize_trade_plan(
        plan,
        account_equity=broker.account_equity(),
        limits=_risk_limits(settings),
    )
    _print_plan(plan)
    submitted = broker.submit_buy_plan(plan)
    console.print(f"Submitted {len(submitted)} Alpaca paper orders.")
    for order in submitted:
        console.print(
            f"{order.side.upper()} {order.symbol} ${order.notional:,.2f} "
            f"id={order.broker_order_id}"
        )


def _risk_limits(settings: object) -> RiskLimits:
    return RiskLimits(
        max_positions=settings.max_positions,
        max_position_pct=settings.max_position_pct,
        cash_buffer_pct=settings.cash_buffer_pct,
        max_drawdown_pct=settings.max_drawdown_pct,
        min_validation_sharpe=settings.min_validation_sharpe,
    )


def _read_plan(path: Path) -> TradePlan:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TradePlan(
        generated_at=raw["generated_at"],
        account_equity=float(raw["account_equity"]),
        mode=raw["mode"],
        items=[TradePlanItem(**item) for item in raw.get("items", [])],
    )


def _print_leaderboard(rows: object) -> None:
    table = Table(title="Top Research Results")
    for column in [
        "symbol",
        "strategy",
        "score",
        "validation_sharpe",
        "test_sharpe",
        "test_max_drawdown",
        "latest_signal",
    ]:
        table.add_column(column)
    for row in rows.itertuples(index=False):
        table.add_row(
            str(row.symbol),
            str(row.strategy),
            f"{row.score:.2f}",
            f"{row.validation_sharpe:.2f}",
            f"{row.test_sharpe:.2f}",
            f"{row.test_max_drawdown:.1%}",
            str(bool(row.latest_signal)),
        )
    console.print(table)


def _print_plan(plan: TradePlan) -> None:
    table = Table(title="Paper Trade Plan")
    for column in ["symbol", "strategy", "weight", "notional", "score", "test_sharpe", "test_dd"]:
        table.add_column(column)
    for item in plan.items:
        table.add_row(
            item.symbol,
            item.strategy,
            f"{item.target_weight:.1%}",
            f"${item.target_notional:,.2f}",
            f"{item.score:.2f}",
            f"{item.test_sharpe:.2f}",
            f"{item.test_max_drawdown:.1%}",
        )
    if not plan.items:
        table.add_row("-", "No candidates passed gates", "-", "-", "-", "-", "-")
    console.print(table)


def _print_walk_forward_summary(rows: object) -> None:
    table = Table(title="Top Walk-Forward Consistency")
    for column in [
        "symbol",
        "strategy",
        "windows",
        "validation_pass_rate",
        "test_pass_rate",
        "avg_test_sharpe",
        "worst_test_drawdown",
        "consistent",
    ]:
        table.add_column(column)
    for row in rows.itertuples(index=False):
        table.add_row(
            str(row.symbol),
            str(row.strategy),
            str(int(row.windows)),
            f"{row.validation_pass_rate:.0%}",
            f"{row.test_pass_rate:.0%}",
            f"{row.avg_test_sharpe:.2f}",
            f"{row.worst_test_drawdown:.1%}",
            str(bool(row.consistent)),
        )
    if getattr(rows, "empty", False):
        table.add_row("-", "No walk-forward rows", "-", "-", "-", "-", "-", "-")
    console.print(table)


def main() -> None:
    app()