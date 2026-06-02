import pytest

from stock_trade.config import Settings


def test_paper_trading_requires_explicit_gates() -> None:
    settings = Settings(trading_mode="research", allow_paper_orders=False)

    with pytest.raises(RuntimeError, match="TRADING_MODE=paper"):
        settings.require_paper_trading()


def test_paper_trading_requires_allow_paper_orders_gate() -> None:
    settings = Settings(
        trading_mode="paper",
        allow_paper_orders=False,
        alpaca_api_key="paper-key",
        alpaca_api_secret="paper-secret",
    )

    with pytest.raises(RuntimeError, match="ALLOW_PAPER_ORDERS=true"):
        settings.require_paper_trading()


def test_paper_trading_requires_credentials() -> None:
    settings = Settings(
        trading_mode="paper",
        allow_paper_orders=True,
        alpaca_api_key=None,
        alpaca_api_secret=None,
    )

    with pytest.raises(RuntimeError, match="ALPACA_API_KEY"):
        settings.require_paper_trading()


def test_settings_do_not_expose_raw_secret() -> None:
    raw_secret = "raw-paper-secret"
    settings = Settings(
        trading_mode="paper",
        allow_paper_orders=True,
        alpaca_api_key="paper-key",
        alpaca_api_secret=raw_secret,
    )

    assert raw_secret not in repr(settings)
    assert raw_secret not in str(settings)
    assert raw_secret not in settings.model_dump_json()


def test_default_universe_accepts_csv_env_file(tmp_path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("DEFAULT_UNIVERSE=SPY,QQQ,IWM\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.default_universe == ["SPY", "QQQ", "IWM"]