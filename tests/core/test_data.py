"""Tests for src/alpha_decay_foundry/core/data.py (DataProvider protocol)."""

from __future__ import annotations

import pandas as pd
import pytest

from alpha_decay_foundry.core.data import DataProvider, InMemoryDataProvider
from alpha_decay_foundry.core.types import AssetId
from alpha_decay_foundry.core.universe import StaticUniverse

# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_in_memory_provider_is_data_provider(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    assert isinstance(mock_data_provider, DataProvider)


def test_in_memory_provider_name(mock_data_provider: InMemoryDataProvider) -> None:
    assert mock_data_provider.name == "mock"


# ---------------------------------------------------------------------------
# get_panel
# ---------------------------------------------------------------------------


def test_get_panel_returns_dataframe(mock_data_provider: InMemoryDataProvider) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-31", tz="UTC")
    df = mock_data_provider.get_panel(["close"], start, end)
    assert isinstance(df, pd.DataFrame)


def test_get_panel_has_multiindex(mock_data_provider: InMemoryDataProvider) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-31", tz="UTC")
    df = mock_data_provider.get_panel(["close", "volume"], start, end)
    assert df.index.nlevels == 2


def test_get_panel_respects_date_range(mock_data_provider: InMemoryDataProvider) -> None:
    start = pd.Timestamp("2020-03-01", tz="UTC")
    end = pd.Timestamp("2020-03-31", tz="UTC")
    df = mock_data_provider.get_panel(["close"], start, end)
    dates = df.index.get_level_values(0)
    assert dates.min() >= start
    assert dates.max() <= end


def test_get_panel_selects_requested_fields(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-31", tz="UTC")
    df = mock_data_provider.get_panel(["close"], start, end)
    assert "close" in df.columns
    assert "volume" not in df.columns


def test_get_panel_universe_none_accepted(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-10", tz="UTC")
    df = mock_data_provider.get_panel(["close"], start, end, universe=None)
    assert not df.empty


# ---------------------------------------------------------------------------
# get_returns
# ---------------------------------------------------------------------------


def test_get_returns_returns_dataframe(mock_data_provider: InMemoryDataProvider) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-31", tz="UTC")
    universe = StaticUniverse(
        "test", {AssetId("AAPL"), AssetId("MSFT"), AssetId("GOOG")}
    )
    df = mock_data_provider.get_returns(start, end, universe)
    assert isinstance(df, pd.DataFrame)


def test_get_returns_index_utc_aware(mock_data_provider: InMemoryDataProvider) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-03-31", tz="UTC")
    universe = StaticUniverse("test", {AssetId("AAPL")})
    df = mock_data_provider.get_returns(start, end, universe)
    assert df.index.tzinfo is not None


def test_get_returns_respects_date_range(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-06-01", tz="UTC")
    end = pd.Timestamp("2020-06-30", tz="UTC")
    universe = StaticUniverse("test", {AssetId("AAPL")})
    df = mock_data_provider.get_returns(start, end, universe)
    assert df.index.min() >= start
    assert df.index.max() <= end


# ---------------------------------------------------------------------------
# get_factor_returns
# ---------------------------------------------------------------------------


def test_get_factor_returns_returns_dataframe(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-31", tz="UTC")
    df = mock_data_provider.get_factor_returns(["mkt_rf", "smb"], start, end)
    assert isinstance(df, pd.DataFrame)


def test_get_factor_returns_selects_factors(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-01-31", tz="UTC")
    df = mock_data_provider.get_factor_returns(["smb"], start, end)
    assert "smb" in df.columns
    assert "mkt_rf" not in df.columns


def test_get_factor_returns_respects_date_range(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-09-01", tz="UTC")
    end = pd.Timestamp("2020-09-30", tz="UTC")
    df = mock_data_provider.get_factor_returns(["hml"], start, end)
    assert df.index.min() >= start
    assert df.index.max() <= end


def test_get_factor_returns_index_utc_aware(
    mock_data_provider: InMemoryDataProvider,
) -> None:
    start = pd.Timestamp("2020-01-02", tz="UTC")
    end = pd.Timestamp("2020-06-30", tz="UTC")
    df = mock_data_provider.get_factor_returns(["mkt_rf"], start, end)
    assert df.index.tzinfo is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method", ["get_panel", "get_returns", "get_factor_returns"])
def test_single_day_range(
    mock_data_provider: InMemoryDataProvider, method: str
) -> None:
    t = pd.Timestamp("2020-06-15", tz="UTC")
    universe = StaticUniverse("test", {AssetId("AAPL")})
    if method == "get_panel":
        df = mock_data_provider.get_panel(["close"], t, t)
    elif method == "get_returns":
        df = mock_data_provider.get_returns(t, t, universe)
    else:
        df = mock_data_provider.get_factor_returns(["mkt_rf"], t, t)
    assert isinstance(df, pd.DataFrame)
