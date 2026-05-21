"""Tests for src/alpha_decay_foundry/core/calendar.py."""

from __future__ import annotations

import pandas as pd
import pytest

from alpha_decay_foundry.core.calendar import NYSECalendar, TradingCalendar


@pytest.fixture(scope="module")
def cal() -> NYSECalendar:
    return NYSECalendar()


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_nyse_calendar_is_trading_calendar(cal: NYSECalendar) -> None:
    assert isinstance(cal, TradingCalendar)


def test_nyse_calendar_name(cal: NYSECalendar) -> None:
    assert cal.name == "XNYS"


# ---------------------------------------------------------------------------
# is_session — holidays and weekends
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("2023-12-25", False),  # Christmas
        ("2023-11-23", False),  # Thanksgiving
        ("2023-01-02", False),  # New Year's Day (observed)
        ("2023-07-04", False),  # Independence Day
        ("2023-09-04", False),  # Labor Day
        ("2023-12-23", False),  # Saturday
        ("2023-12-24", False),  # Sunday
        ("2023-12-26", True),  # Tuesday after Christmas
        ("2023-12-20", True),  # Regular Wednesday
        ("2024-01-02", True),  # Regular Tuesday
    ],
)
def test_is_session(cal: NYSECalendar, date_str: str, expected: bool) -> None:
    t = pd.Timestamp(date_str, tz="UTC")
    assert cal.is_session(t) is expected


# ---------------------------------------------------------------------------
# sessions_in_range
# ---------------------------------------------------------------------------


def test_sessions_in_range_excludes_christmas(cal: NYSECalendar) -> None:
    start = pd.Timestamp("2023-12-20", tz="UTC")
    end = pd.Timestamp("2023-12-29", tz="UTC")
    sessions = cal.sessions_in_range(start, end)
    # Christmas (Dec 25) and weekend days excluded; 7 trading days
    assert pd.Timestamp("2023-12-25", tz="UTC") not in sessions
    assert len(sessions) == 7


def test_sessions_in_range_endpoints_inclusive(cal: NYSECalendar) -> None:
    start = pd.Timestamp("2023-12-20", tz="UTC")
    end = pd.Timestamp("2023-12-20", tz="UTC")
    sessions = cal.sessions_in_range(start, end)
    assert len(sessions) == 1
    assert sessions[0] == start


def test_sessions_in_range_returns_utc_aware(cal: NYSECalendar) -> None:
    start = pd.Timestamp("2023-12-20", tz="UTC")
    end = pd.Timestamp("2023-12-27", tz="UTC")
    sessions = cal.sessions_in_range(start, end)
    assert sessions.tzinfo is not None
    assert str(sessions.tzinfo) == "UTC"


def test_sessions_in_range_is_datetime_index(cal: NYSECalendar) -> None:
    start = pd.Timestamp("2024-01-02", tz="UTC")
    end = pd.Timestamp("2024-01-05", tz="UTC")
    sessions = cal.sessions_in_range(start, end)
    assert isinstance(sessions, pd.DatetimeIndex)


# ---------------------------------------------------------------------------
# previous_session and next_session
# ---------------------------------------------------------------------------


def test_previous_session_skips_christmas(cal: NYSECalendar) -> None:
    # Dec 26 is the first trading day after Christmas; previous should be Dec 22
    dec_26 = pd.Timestamp("2023-12-26", tz="UTC")
    prev = cal.previous_session(dec_26)
    assert prev == pd.Timestamp("2023-12-22", tz="UTC")


def test_next_session_skips_thanksgiving(cal: NYSECalendar) -> None:
    # Nov 22 is Wednesday before Thanksgiving; next session is Nov 24 (Friday)
    nov_22 = pd.Timestamp("2023-11-22", tz="UTC")
    nxt = cal.next_session(nov_22)
    assert nxt == pd.Timestamp("2023-11-24", tz="UTC")


def test_previous_session_returns_utc_aware(cal: NYSECalendar) -> None:
    t = pd.Timestamp("2024-01-03", tz="UTC")
    prev = cal.previous_session(t)
    assert prev.tzinfo is not None
    assert prev == pd.Timestamp("2024-01-02", tz="UTC")


def test_next_session_returns_utc_aware(cal: NYSECalendar) -> None:
    t = pd.Timestamp("2024-01-02", tz="UTC")
    nxt = cal.next_session(t)
    assert nxt.tzinfo is not None
    assert nxt == pd.Timestamp("2024-01-03", tz="UTC")


def test_previous_then_next_is_identity(cal: NYSECalendar) -> None:
    t = pd.Timestamp("2024-01-03", tz="UTC")
    assert cal.next_session(cal.previous_session(t)) == t


def test_next_then_previous_is_identity(cal: NYSECalendar) -> None:
    t = pd.Timestamp("2024-01-03", tz="UTC")
    assert cal.previous_session(cal.next_session(t)) == t
