#!/usr/bin/env python3
# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

READ_ONLY_TOOLSETS = "account,assets"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read Alpaca paper account status and market clock through MCP."
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON only.")
    args = parser.parse_args()

    result = asyncio.run(read_account_and_clock())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
        return

    account = result["account"]
    clock = result["clock"]
    print("Alpaca paper account")
    for key, value in account.items():
        print(f"{key}: {value}")
    print("\nMarket clock")
    for key, value in clock.items():
        print(f"{key}: {value}")


async def read_account_and_clock() -> dict[str, Any]:
    params = StdioServerParameters(
        command="uvx",
        args=["alpaca-mcp-server"],
        env=_mcp_env(),
    )
    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()
        await _require_tools(session, {"get_account_info", "get_clock"})
        account_result = await session.call_tool("get_account_info", {})
        clock_result = await session.call_tool("get_clock", {})

    return {
        "account": _sanitize_account(_payload(account_result)),
        "clock": _payload(clock_result),
        "called_tools": ["get_account_info", "get_clock"],
        "enabled_toolsets": READ_ONLY_TOOLSETS,
    }


def _mcp_env() -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[1]
    values = dotenv_values(repo_root / ".env")
    env = os.environ.copy()

    api_key = values.get("ALPACA_API_KEY") or env.get("ALPACA_API_KEY")
    secret = (
        values.get("ALPACA_API_SECRET")
        or values.get("ALPACA_SECRET_KEY")
        or env.get("ALPACA_SECRET_KEY")
    )
    if not api_key or not secret:
        raise RuntimeError("Missing Alpaca paper credentials in .env")

    env["ALPACA_API_KEY"] = api_key
    env["ALPACA_SECRET_KEY"] = secret
    env["ALPACA_PAPER_TRADE"] = "true"
    env["ALPACA_TOOLSETS"] = READ_ONLY_TOOLSETS
    env.pop("ALPACA_API_SECRET", None)
    return env


async def _require_tools(session: ClientSession, expected_tools: set[str]) -> None:
    tools = await session.list_tools()
    tool_names = {tool.name for tool in tools.tools}
    missing = sorted(expected_tools - tool_names)
    if missing:
        raise RuntimeError(f"Missing expected Alpaca MCP tools: {', '.join(missing)}")


def _payload(result: Any) -> dict[str, Any]:
    if not result.content:
        return {}
    item = result.content[0]
    text = getattr(item, "text", None)
    if text is not None:
        return json.loads(text)
    data = getattr(item, "data", None)
    return data or {}


def _sanitize_account(account: dict[str, Any]) -> dict[str, Any]:
    safe_fields = [
        "status",
        "crypto_status",
        "currency",
        "cash",
        "buying_power",
        "portfolio_value",
        "equity",
        "last_equity",
        "pattern_day_trader",
        "trading_blocked",
        "transfers_blocked",
        "account_blocked",
        "trade_suspended_by_user",
    ]
    return {field: account.get(field) for field in safe_fields}


if __name__ == "__main__":
    main()
