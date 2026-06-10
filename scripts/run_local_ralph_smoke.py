#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi.testclient import TestClient

from stock_trade.api.app import create_app
from stock_trade.config import Settings
from stock_trade.events.bus import EventBus
from stock_trade.execution.planner import TradePlan
from stock_trade.loop.ralph import run_cycle
from stock_trade.store.sqlite import SQLiteStore


class SmokeBrokerSnapshot:
    def __init__(self, plan: TradePlan) -> None:
        self._plan = plan

    def account_snapshot(self) -> dict[str, Any]:
        return {"equity": 100_000, "cash": 100_000, "mode": "paper-demo"}

    def positions(self) -> list[dict[str, Any]]:
        return [
            {
                "symbol": item.symbol,
                "market_value": item.target_notional,
                "target_weight": item.target_weight,
            }
            for item in self._plan.items
        ]

    def open_orders(self) -> list[dict[str, Any]]:
        return []

    def recent_fills(self) -> list[dict[str, Any]]:
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local offline RALPH smoke test.")
    parser.add_argument("--db-path", type=Path, default=Path("artifacts/smoke/ralph-smoke.db"))
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON only.")
    args = parser.parse_args()

    summary = run_smoke(args.db_path)
    if args.json:
        print(json.dumps(summary, sort_keys=True))
    else:
        print("Local RALPH smoke complete")
        print(json.dumps(summary, indent=2, sort_keys=True))


def run_smoke(db_path: Path) -> dict[str, Any]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    settings = Settings(min_validation_sharpe=0.10)
    store = SQLiteStore(db_path)
    bus = EventBus()
    result = run_cycle(
        settings=settings,
        bus=bus,
        store=store,
        prices=_prices(),
        run_id="local-smoke",
    )

    client = TestClient(
        create_app(
            settings=settings,
            store=store,
            broker_snapshot=SmokeBrokerSnapshot(result.plan),
        )
    )

    health_response = client.get("/health")
    run_response = client.get(f"/api/research/runs/{result.run_id}")
    leaderboard_response = client.get(f"/api/research/runs/{result.run_id}/leaderboard")
    trace_response = client.get(f"/api/agent/runs/{result.run_id}/trace")
    api_responses = [
        health_response,
        client.get("/api/account/snapshot"),
        client.get("/api/positions"),
        client.get("/api/orders/open"),
        client.get("/api/risk/status"),
        client.get("/api/research/runs"),
        run_response,
        leaderboard_response,
        trace_response,
    ]

    paper_execute_without_confirmation = client.post(
        "/api/paper/execute",
        json={"paper_only": True},
    )
    paper_execute_with_confirmation = client.post(
        "/api/paper/execute",
        json={"paper_only": True, "confirmation_token": "execute-paper"},
    )
    api_responses.extend([paper_execute_without_confirmation, paper_execute_with_confirmation])

    response_text = "\n".join(response.text for response in api_responses)

    return {
        "run_id": result.run_id,
        "event_count": len(store.list_events(result.run_id)),
        "plan_item_count": len(result.plan.items),
        "submitted_order_count": len(result.submitted_orders),
        "health": health_response.json(),
        "api": {
            "runs_status": client.get("/api/research/runs").status_code,
            "run_status": run_response.status_code,
            "leaderboard_status": leaderboard_response.status_code,
            "trace_status": trace_response.status_code,
            "paper_execute_without_confirmation": paper_execute_without_confirmation.status_code,
            "paper_execute_with_confirmation": paper_execute_with_confirmation.status_code,
        },
        "secret_marker_present": _has_secret_marker(response_text),
    }


def _prices(length: int = 620) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "SPY": [100 + (index * 0.20) + ((index % 5) * 0.05) for index in range(length)],
            "QQQ": [120 + (index * 0.25) + ((index % 7) * 0.04) for index in range(length)],
        },
        index=pd.date_range("2020-01-01", periods=length, freq="D"),
    )


def _has_secret_marker(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in ["raw-secret", "alpaca_secret", "api key", "private key", "sk_live"]
    )


if __name__ == "__main__":
    main()
