"""Tests for src/alpha_decay_foundry/core/signal.py."""

from __future__ import annotations

import numpy as np
import pandas as pd

from alpha_decay_foundry.core.data import DataProvider
from alpha_decay_foundry.core.signal import Signal
from alpha_decay_foundry.core.types import AssetId, Timestamp
from alpha_decay_foundry.core.universe import StaticUniverse
from tests.utils.data import InMemoryDataProvider

# ---------------------------------------------------------------------------
# Minimal concrete Signal for protocol tests
# ---------------------------------------------------------------------------


class ConstantSignal:
    """Returns a fixed score for every asset on every date."""

    def __init__(self, name: str, score: float = 1.0) -> None:
        self.name = name
        self._score = score

    def compute(
        self,
        data: DataProvider,
        universe: StaticUniverse,
        start: Timestamp,
        end: Timestamp,
    ) -> pd.DataFrame:
        """Return constant score for all universe members over [start, end]."""
        dates = pd.date_range(start=start, end=end, freq="D", tz="UTC")
        members = sorted(universe.members_at(start))
        return pd.DataFrame(self._score, index=dates, columns=members)


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


def test_constant_signal_is_signal() -> None:
    sig = ConstantSignal("const")
    assert isinstance(sig, Signal)


def test_constant_signal_name() -> None:
    sig = ConstantSignal("momentum")
    assert sig.name == "momentum"


# ---------------------------------------------------------------------------
# compute() output shape and conventions
# ---------------------------------------------------------------------------


def test_compute_returns_dataframe() -> None:
    sig = ConstantSignal("const", score=0.5)
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = sig.compute(provider, universe, START, END)
    assert isinstance(result, pd.DataFrame)


def test_compute_index_utc_aware() -> None:
    sig = ConstantSignal("const")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = sig.compute(provider, universe, START, END)
    assert result.index.tzinfo is not None


def test_compute_columns_are_asset_ids() -> None:
    sig = ConstantSignal("const")
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = sig.compute(provider, universe, START, END)
    assert set(result.columns) == set(ASSETS)


def test_compute_scores_are_float() -> None:
    sig = ConstantSignal("const", score=2.0)
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = sig.compute(provider, universe, START, END)
    assert all(pd.api.types.is_float_dtype(d) for d in result.dtypes)


def test_compute_positive_score_convention() -> None:
    # Positive score = long (attractive); negative = short (unattractive)
    sig_long = ConstantSignal("long", score=1.0)
    sig_short = ConstantSignal("short", score=-1.0)
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    long_scores = sig_long.compute(provider, universe, START, END)
    short_scores = sig_short.compute(provider, universe, START, END)
    assert (long_scores > 0).all(axis=None)
    assert (short_scores < 0).all(axis=None)


def test_compute_nan_convention() -> None:
    """NaN scores are allowed and indicate no opinion."""

    class NaNSignal:
        name = "nan_signal"

        def compute(
            self,
            data: DataProvider,
            universe: StaticUniverse,
            start: Timestamp,
            end: Timestamp,
        ) -> pd.DataFrame:
            dates = pd.date_range(start=start, end=end, freq="D", tz="UTC")
            members = sorted(universe.members_at(start))
            return pd.DataFrame(float("nan"), index=dates, columns=members)

    sig = NaNSignal()
    assert isinstance(sig, Signal)
    provider = _make_provider()
    universe = StaticUniverse("test", set(ASSETS))
    result = sig.compute(provider, universe, START, END)
    assert result.isna().all(axis=None)


def test_compute_single_day_range() -> None:
    sig = ConstantSignal("const", score=0.0)
    provider = _make_provider()
    universe = StaticUniverse("test", {AssetId("AAPL")})
    result = sig.compute(provider, universe, START, START)
    assert len(result) == 1
