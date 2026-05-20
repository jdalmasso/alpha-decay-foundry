"""Tests for src/alpha_decay_foundry/core/types.py."""

from __future__ import annotations

import pandas as pd
import pytest

from alpha_decay_foundry.core.types import AssetId, DateRange, Timestamp

# ---------------------------------------------------------------------------
# AssetId
# ---------------------------------------------------------------------------


def test_asset_id_is_str_subtype() -> None:
    a = AssetId("AAPL")
    assert isinstance(a, str)
    assert a == "AAPL"


# ---------------------------------------------------------------------------
# DateRange construction
# ---------------------------------------------------------------------------


def test_daterange_equal_start_end_is_valid() -> None:
    t = pd.Timestamp("2020-01-01", tz="UTC")
    dr = DateRange(start=t, end=t)
    assert dr.start == t
    assert dr.end == t


def test_daterange_start_before_end() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2023-12-31", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.start == start
    assert dr.end == end


def test_daterange_start_after_end_raises() -> None:
    start = pd.Timestamp("2023-12-31", tz="UTC")
    end = pd.Timestamp("2020-01-01", tz="UTC")
    with pytest.raises(ValueError, match="start .* > end"):
        DateRange(start=start, end=end)


def test_daterange_is_frozen() -> None:
    import dataclasses

    dr = DateRange(
        start=pd.Timestamp("2020-01-01", tz="UTC"),
        end=pd.Timestamp("2020-12-31", tz="UTC"),
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        # intentional: assigning to a frozen field to confirm the runtime error fires
        dr.start = pd.Timestamp("2021-01-01", tz="UTC")  # type: ignore[misc]


# ---------------------------------------------------------------------------
# DateRange.days()
# ---------------------------------------------------------------------------


def test_daterange_days_zero_for_equal_start_end() -> None:
    t = pd.Timestamp("2020-06-15", tz="UTC")
    dr = DateRange(start=t, end=t)
    assert dr.days() == 0


def test_daterange_days_one_day_apart() -> None:
    start = pd.Timestamp("2020-06-15", tz="UTC")
    end = pd.Timestamp("2020-06-16", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.days() == 1


def test_daterange_days_calendar_not_trading() -> None:
    # Spans a weekend: 5 calendar days regardless of trading days
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-01-06", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.days() == 5


def test_daterange_days_full_year() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2021-01-01", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.days() == 366  # 2020 is a leap year


# ---------------------------------------------------------------------------
# DateRange.contains()
# ---------------------------------------------------------------------------


def test_contains_start_boundary() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-12-31", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.contains(start) is True


def test_contains_end_boundary() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-12-31", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.contains(end) is True


def test_contains_interior_point() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-12-31", tz="UTC")
    mid = pd.Timestamp("2020-06-15", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.contains(mid) is True


def test_contains_before_start() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-12-31", tz="UTC")
    before = pd.Timestamp("2019-12-31", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.contains(before) is False


def test_contains_after_end() -> None:
    start = pd.Timestamp("2020-01-01", tz="UTC")
    end = pd.Timestamp("2020-12-31", tz="UTC")
    after = pd.Timestamp("2021-01-01", tz="UTC")
    dr = DateRange(start=start, end=end)
    assert dr.contains(after) is False


def test_contains_single_point_range() -> None:
    t = pd.Timestamp("2020-06-15", tz="UTC")
    dr = DateRange(start=t, end=t)
    assert dr.contains(t) is True
    assert dr.contains(pd.Timestamp("2020-06-14", tz="UTC")) is False
    assert dr.contains(pd.Timestamp("2020-06-16", tz="UTC")) is False


# ---------------------------------------------------------------------------
# Timestamp alias
# ---------------------------------------------------------------------------


def test_timestamp_alias_is_pd_timestamp() -> None:
    t: Timestamp = pd.Timestamp("2020-01-01", tz="UTC")
    assert isinstance(t, pd.Timestamp)
    assert t.tzinfo is not None


# ---------------------------------------------------------------------------
# Timezone-naive edge cases (documenting current behavior, not enforcing UTC)
# ---------------------------------------------------------------------------


def test_daterange_accepts_naive_timestamps_silently() -> None:
    # DateRange has no UTC validation; two naive timestamps are accepted.
    # Callers are responsible for passing UTC-aware values (module docstring).
    naive_start = pd.Timestamp("2020-01-01")
    naive_end = pd.Timestamp("2020-12-31")
    dr = DateRange(start=naive_start, end=naive_end)
    assert dr.start == naive_start
    assert dr.end == naive_end


def test_contains_naive_vs_aware_raises_type_error() -> None:
    # Mixing naive and aware timestamps in contains() propagates a pandas
    # TypeError. This is the expected failure mode when callers violate the
    # UTC-aware contract; no FoundryError is raised at this layer.
    aware_start = pd.Timestamp("2020-01-01", tz="UTC")
    aware_end = pd.Timestamp("2020-12-31", tz="UTC")
    dr = DateRange(start=aware_start, end=aware_end)
    naive_t = pd.Timestamp("2020-06-15")
    with pytest.raises(TypeError, match="tz-naive"):
        dr.contains(naive_t)
