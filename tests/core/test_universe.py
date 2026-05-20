"""Tests for src/alpha_decay_foundry/core/universe.py."""

from __future__ import annotations

import pandas as pd
import pytest

from alpha_decay_foundry.core.types import AssetId
from alpha_decay_foundry.core.universe import StaticUniverse, Universe


@pytest.fixture
def members() -> set[AssetId]:
    return {AssetId("AAPL"), AssetId("MSFT"), AssetId("GOOG")}


@pytest.fixture
def universe(members: set[AssetId]) -> StaticUniverse:
    return StaticUniverse(name="test", members=members)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_static_universe_is_universe(universe: StaticUniverse) -> None:
    assert isinstance(universe, Universe)


def test_static_universe_name(universe: StaticUniverse) -> None:
    assert universe.name == "test"


# ---------------------------------------------------------------------------
# members_at
# ---------------------------------------------------------------------------


def test_members_at_returns_full_set(universe: StaticUniverse, members: set[AssetId]) -> None:
    t = pd.Timestamp("2020-06-15", tz="UTC")
    assert universe.members_at(t) == members


def test_members_at_is_copy(universe: StaticUniverse) -> None:
    t = pd.Timestamp("2020-06-15", tz="UTC")
    result = universe.members_at(t)
    result.add(AssetId("EXTRA"))
    assert AssetId("EXTRA") not in universe.members_at(t)


def test_members_at_ignores_timestamp(universe: StaticUniverse) -> None:
    t1 = pd.Timestamp("2000-01-01", tz="UTC")
    t2 = pd.Timestamp("2030-12-31", tz="UTC")
    assert universe.members_at(t1) == universe.members_at(t2)


def test_members_at_single_member() -> None:
    u = StaticUniverse("one", {AssetId("X")})
    t = pd.Timestamp("2023-01-01", tz="UTC")
    assert u.members_at(t) == {AssetId("X")}


def test_members_at_empty_universe() -> None:
    u = StaticUniverse("empty", set())
    t = pd.Timestamp("2023-01-01", tz="UTC")
    assert u.members_at(t) == set()


# ---------------------------------------------------------------------------
# members_between
# ---------------------------------------------------------------------------


def test_members_between_shape(universe: StaticUniverse, members: set[AssetId]) -> None:
    start = pd.Timestamp("2023-01-02", tz="UTC")
    end = pd.Timestamp("2023-01-06", tz="UTC")  # 5 calendar days
    df = universe.members_between(start, end)
    assert df.shape == (5, len(members))


def test_members_between_all_true(universe: StaticUniverse) -> None:
    start = pd.Timestamp("2023-01-02", tz="UTC")
    end = pd.Timestamp("2023-01-06", tz="UTC")
    df = universe.members_between(start, end)
    assert df.all(axis=None)


def test_members_between_index_utc_aware(universe: StaticUniverse) -> None:
    start = pd.Timestamp("2023-01-02", tz="UTC")
    end = pd.Timestamp("2023-01-04", tz="UTC")
    df = universe.members_between(start, end)
    assert df.index.tzinfo is not None
    assert str(df.index.tzinfo) == "UTC"


def test_members_between_index_daily_frequency(universe: StaticUniverse) -> None:
    start = pd.Timestamp("2023-01-02", tz="UTC")
    end = pd.Timestamp("2023-01-06", tz="UTC")
    df = universe.members_between(start, end)
    # All five calendar days present (including weekend)
    assert pd.Timestamp("2023-01-07", tz="UTC") not in df.index
    assert pd.Timestamp("2023-01-02", tz="UTC") in df.index
    assert pd.Timestamp("2023-01-06", tz="UTC") in df.index


def test_members_between_columns_are_asset_ids(universe: StaticUniverse) -> None:
    start = pd.Timestamp("2023-01-02", tz="UTC")
    end = pd.Timestamp("2023-01-04", tz="UTC")
    df = universe.members_between(start, end)
    assert set(df.columns) == {AssetId("AAPL"), AssetId("MSFT"), AssetId("GOOG")}


def test_members_between_single_day(universe: StaticUniverse) -> None:
    t = pd.Timestamp("2023-06-15", tz="UTC")
    df = universe.members_between(t, t)
    assert len(df) == 1
    assert df.index[0] == t


def test_members_between_empty_universe() -> None:
    u = StaticUniverse("empty", set())
    start = pd.Timestamp("2023-01-02", tz="UTC")
    end = pd.Timestamp("2023-01-05", tz="UTC")
    df = u.members_between(start, end)
    assert df.empty
    assert len(df) == 4  # 4 calendar days, 0 columns


# ---------------------------------------------------------------------------
# OSAPUniverse stub
# ---------------------------------------------------------------------------


def test_osap_universe_raises_not_implemented() -> None:
    from alpha_decay_foundry.core.universe import OSAPUniverse

    with pytest.raises(NotImplementedError, match="OSAPUniverse requires"):
        # intentional: None satisfies the signature so NotImplementedError fires
        OSAPUniverse("test", osap_provider=None)  # type: ignore[arg-type]
