from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    trading_mode: Literal["research", "paper"] = "research"
    allow_paper_orders: bool = False
    alpaca_api_key: str | None = None
    alpaca_api_secret: SecretStr | None = None

    default_universe: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["SPY", "QQQ", "IWM", "GLD", "TLT", "XLK", "XLF", "XLE", "XLV"]
    )
    initial_cash: float = 100_000.0
    max_positions: int = 3
    max_position_pct: float = 0.25
    cash_buffer_pct: float = 0.10
    max_drawdown_pct: float = 0.25
    min_validation_sharpe: float = 0.35
    fee_bps: float = 1.0
    slippage_bps: float = 5.0

    @field_validator("default_universe", mode="before")
    @classmethod
    def parse_universe(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
        return [symbol.upper() for symbol in value]

    def require_paper_trading(self) -> None:
        if self.trading_mode != "paper":
            raise RuntimeError("Set TRADING_MODE=paper before submitting paper orders.")
        if not self.allow_paper_orders:
            raise RuntimeError("Set ALLOW_PAPER_ORDERS=true before submitting paper orders.")
        if not self.alpaca_api_key or not self.alpaca_api_secret:
            raise RuntimeError("Set ALPACA_API_KEY and ALPACA_API_SECRET for Alpaca paper trading.")


@lru_cache
def get_settings() -> Settings:
    return Settings()