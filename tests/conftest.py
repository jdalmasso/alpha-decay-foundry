"""Shared pytest fixtures for Alpha Decay Foundry tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from alpha_decay_foundry.core.types import AssetId, DateRange
from alpha_decay_foundry.core.universe import StaticUniverse
from tests.utils.data import InMemoryDataProvider

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

ASSETS = [AssetId("AAPL"), AssetId("MSFT"), AssetId("GOOG")]
SAMPLE_START = pd.Timestamp("2020-01-02", tz="UTC")
SAMPLE_END = pd.Timestamp("2020-12-31", tz="UTC")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def sample_date_range() -> DateRange:
    """DateRange covering 2020-2023 for integration tests."""
    return DateRange(
        start=pd.Timestamp("2020-01-02", tz="UTC"),
        end=pd.Timestamp("2023-12-29", tz="UTC"),
    )


@pytest.fixture
def mock_data_provider() -> InMemoryDataProvider:
    """In-memory DataProvider with synthetic daily data for 2020.

    Panel: MultiIndex (date, asset_id), columns = ["close", "volume"].
    Returns: date x asset_id, decimal daily returns.
    Factor returns: date x factor, columns = ["mkt_rf", "smb", "hml"].
    """
    dates = pd.date_range(SAMPLE_START, SAMPLE_END, freq="B", tz="UTC")
    rng = np.random.default_rng(42)

    # Panel: (date, asset_id) MultiIndex
    rows = []
    for date in dates:
        for asset in ASSETS:
            rows.append(
                {
                    "timestamp": date,
                    "asset_id": asset,
                    "close": float(rng.uniform(50, 500)),
                    "volume": float(rng.integers(1_000_000, 10_000_000)),
                }
            )
    panel_df = pd.DataFrame(rows).set_index(["timestamp", "asset_id"])

    # Returns: date x asset_id
    returns_data = rng.normal(0.0005, 0.01, size=(len(dates), len(ASSETS)))
    returns_df = pd.DataFrame(returns_data, index=dates, columns=ASSETS)

    # Factor returns: date x factor
    factors = ["mkt_rf", "smb", "hml"]
    factor_data = rng.normal(0.0002, 0.008, size=(len(dates), len(factors)))
    factor_df = pd.DataFrame(factor_data, index=dates, columns=factors)

    return InMemoryDataProvider(
        name="mock",
        panel=panel_df,
        returns=returns_df,
        factor_returns=factor_df,
    )


@pytest.fixture
def sample_universe() -> StaticUniverse:
    """Small three-asset StaticUniverse for unit tests."""
    return StaticUniverse(
        name="sample",
        members={AssetId("AAPL"), AssetId("MSFT"), AssetId("GOOG")},
    )
