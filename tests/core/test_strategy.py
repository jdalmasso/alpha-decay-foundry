"""Tests for src/alpha_decay_foundry/core/strategy.py."""

from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_decay_foundry.core.data import DataProvider
from alpha_decay_foundry.core.strategy import Strategy
from alpha_decay_foundry.core.types import AssetId, TargetWeights, Timestamp
from alpha_decay_foundry.core.universe import StaticUniverse
from tests.utils.data import InMemoryDataProvider

# ---------------------------------------------------------------------------
# Minimal concrete Strategy for protocol tests
# ---------------------------------------------------------------------------


class EqualWeightStrategy:
    """Assigns equal long weight to every universe member on every date."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.lifecycle = None

    def target_weights(
        self,
        data: DataProvider,
        universe: StaticUniverse,
        start: Timestamp,
        end: Timestamp,
    ) -> TargetWeights:
        """Return 1/N equal weights for all universe members over [start, end]."""
        dates = pd.date_range(start=start, end=end, freq="D", tz="UTC")
        members = sorted(universe.members_at(start))
        weight = 1.0 / len(members)
        return pd.DataFrame(weight, index=dates, columns=members)


class DollarNeutralStrategy:
    """Long top half, short bottom half; dollar-neutral (weights sum to 0)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.lifecycle = None

    def target_weights(
        self,
        data: DataProvider,
        universe: StaticUniverse,
        start: Timestamp,
        end: Timestamp,
    ) -> TargetWeights:
        """Return +0.5 / -0.5 split on a two-asset universe."""
        dates = pd.date_range(start=start, end=end, freq="D", tz="UTC")
        members = sorted(universe.members_at(start))
        # Simple alternating +/-; assumes even number of members
        half = len(members) // 2
        weights = [1.0 / half] * half + [-1.0 / half] * half
        return pd.DataFrame([weights] * len(dates), index=dates, columns=members)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ASSETS = [AssetId("AAPL"), AssetId("MSFT"), AssetId("GOOG")]
START = pd.Timestamp("2020-01-02", tz="UTC")
END = pd.Timestamp("2020-01-31", tz="UTC")


def _make_provider() -> InMemoryDataProvider:
    dates = pd.date_range(START, END, freq="B", tz="UTC")
    rng = np.random.default_rng(0)
    panel = pd.DataFrame(
        {"close": rng.uniform(50, 500, len(dates) * len(ASSETS))},
        index=pd.MultiIndex.from_product([dates, ASSETS], names=["timestamp", "asset_id"]),
    )
    returns = pd.DataFrame(
        rng.normal(0, 0.01, (len(dates), len(ASSETS))), index=dates, columns=ASSETS
    )
    factor_returns = pd.DataFrame(
        rng.normal(0, 0.008, (len(dates), 3)),
        index=dates,
        columns=["mkt_rf", "smb", "hml"],
    )
    return InMemoryDataProvider("test", panel, returns, factor_returns)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_equal_weight_strategy_is_strategy() -> None:
    strat = EqualWeightStrategy("ew")
    assert isinstance(strat, Strategy)


def test_dollar_neutral_strategy_is_strategy() -> None:
    strat = DollarNeutralStrategy("dn")
    assert isinstance(strat, Strategy)


def test_strategy_name() -> None:
    strat = EqualWeightStrategy("my_strategy")
    assert strat.name == "my_strategy"


def test_strategy_lifecycle_none() -> None:
    strat = EqualWeightStrategy("ew")
    assert strat.lifecycle is None


# ---------------------------------------------------------------------------
# target_weights() output shape and conventions
# ---------------------------------------------------------------------------


def test_target_weights_returns_dataframe() -> None:
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = strat.target_weights(provider, universe, START, END)
    assert isinstance(result, pd.DataFrame)


def test_target_weights_index_utc_aware() -> None:
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = strat.target_weights(provider, universe, START, END)
    assert result.index.tzinfo is not None


def test_target_weights_columns_are_asset_ids() -> None:
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = strat.target_weights(provider, universe, START, END)
    assert set(result.columns) == set(ASSETS)


def test_target_weights_are_float() -> None:
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = strat.target_weights(provider, universe, START, END)
    assert all(pd.api.types.is_float_dtype(d) for d in result.dtypes)


# ---------------------------------------------------------------------------
# Weight conventions
# ---------------------------------------------------------------------------


def test_long_only_weights_sum_to_one() -> None:
    """Long-only: weights per row sum to 1.0."""
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = strat.target_weights(provider, universe, START, END)
    row_sums = result.sum(axis=1)
    assert (row_sums - 1.0).abs().max() < 1e-9


def test_long_only_weights_positive() -> None:
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = strat.target_weights(provider, universe, START, END)
    assert (result > 0).all(axis=None)


def test_dollar_neutral_weights_sum_to_zero() -> None:
    """Dollar-neutral L/S: weights per row sum to 0.0."""
    assets = [AssetId("AAPL"), AssetId("MSFT")]
    strat = DollarNeutralStrategy("dn")
    provider = _make_provider()
    universe = StaticUniverse("test", set(assets))
    result = strat.target_weights(provider, universe, START, END)
    row_sums = result.sum(axis=1)
    assert (row_sums).abs().max() < 1e-9


def test_dollar_neutral_gross_exposure() -> None:
    """Dollar-neutral L/S: sum of absolute weights equals 2.0."""
    assets = [AssetId("AAPL"), AssetId("MSFT")]
    strat = DollarNeutralStrategy("dn")
    provider = _make_provider()
    universe = StaticUniverse("test", set(assets))
    result = strat.target_weights(provider, universe, START, END)
    gross = result.abs().sum(axis=1)
    assert (gross - 2.0).abs().max() < 1e-9


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_target_weights_single_day_range() -> None:
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", {AssetId("AAPL")})
    result = strat.target_weights(provider, universe, START, START)
    assert len(result) == 1


def test_target_weights_single_asset_long_only() -> None:
    """Single-asset long-only: weight should be 1.0."""
    strat = EqualWeightStrategy("ew")
    provider = _make_provider()
    universe = StaticUniverse("test", {AssetId("AAPL")})
    result = strat.target_weights(provider, universe, START, END)
    assert (result - 1.0).abs().max().max() < 1e-9
