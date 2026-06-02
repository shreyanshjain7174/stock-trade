#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values


def main() -> int:
    env = os.environ.copy()
    values = dotenv_values(Path(__file__).resolve().parents[1] / ".env")

    api_key = values.get("ALPACA_API_KEY") or env.get("ALPACA_API_KEY")
    secret = (
        values.get("ALPACA_API_SECRET")
        or values.get("ALPACA_SECRET_KEY")
        or env.get("ALPACA_SECRET_KEY")
    )

    if not api_key or not secret:
        print(
            "Missing Alpaca paper credentials. Set ALPACA_API_KEY and ALPACA_API_SECRET in .env.",
            file=sys.stderr,
        )
        return 2

    env["ALPACA_API_KEY"] = api_key
    env["ALPACA_SECRET_KEY"] = secret
    env.setdefault("ALPACA_PAPER_TRADE", "true")
    env.setdefault("ALPACA_TOOLSETS", "assets,stock-data,news,corporate-actions")

    return subprocess.call(["uvx", "alpaca-mcp-server"], env=env)


if __name__ == "__main__":
    raise SystemExit(main())
