"""Trading calendar abstractions for Alpha Decay Foundry.

All public methods accept and return UTC-aware Timestamps. The underlying
exchange_calendars library works with timezone-naive dates internally;
conversion happens at the boundary of every public method.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import exchange_calendars as xcals  # type: ignore[import-untyped]  # no py.typed marker
import pandas as pd

from .types import Timestamp


@runtime_checkable
class TradingCalendar(Protocol):
    """Protocol for a trading session calendar.

    Implementations must work with UTC-aware Timestamps in all public
    methods. Day-level granularity only; intraday minutes are out of scope
    for v0.1.
    """

    name: str

    def is_session(self, t: Timestamp) -> bool:
        """Return True if t is a trading session (market-open day).

        Args:
            t: UTC-aware timestamp to test.

        Returns:
            True if the date of t is a trading session.
        """
        ...

    def sessions_in_range(
        self, start: Timestamp, end: Timestamp
    ) -> pd.DatetimeIndex:
        """Return all trading sessions in [start, end], inclusive.

        Args:
            start: Range start (UTC-aware).
            end: Range end (UTC-aware).

        Returns:
            UTC-aware DatetimeIndex of session dates, calendar frequency.
        """
        ...

    def previous_session(self, t: Timestamp) -> Timestamp:
        """Return the trading session immediately before t.

        Args:
            t: UTC-aware timestamp; must itself be a trading session.

        Returns:
            UTC-aware Timestamp of the preceding session.
        """
        ...

    def next_session(self, t: Timestamp) -> Timestamp:
        """Return the trading session immediately after t.

        Args:
            t: UTC-aware timestamp; must itself be a trading session.

        Returns:
            UTC-aware Timestamp of the following session.
        """
        ...


class NYSECalendar:
    """NYSE trading calendar (XNYS) backed by exchange_calendars.

    All public methods accept UTC-aware Timestamps.  exchange_calendars
    operates on timezone-naive dates internally; this class strips and
    re-attaches the UTC timezone at every boundary.
    """

    name: str = "XNYS"

    def __init__(self) -> None:
        self._xcal = xcals.get_calendar("XNYS")

    @staticmethod
    def _to_naive(t: Timestamp) -> pd.Timestamp:
        """Strip timezone for exchange_calendars consumption."""
        return t.tz_localize(None) if t.tzinfo is None else t.tz_convert(None)

    @staticmethod
    def _to_utc(t: pd.Timestamp) -> Timestamp:
        """Attach UTC timezone to a naive Timestamp returned by exchange_calendars."""
        return t.tz_localize("UTC")

    def is_session(self, t: Timestamp) -> bool:
        """Return True if the date of t is an NYSE trading session.

        Args:
            t: UTC-aware timestamp to test.

        Returns:
            True if t falls on a trading day (not a weekend or holiday).
        """
        return bool(self._xcal.is_session(self._to_naive(t)))

    def sessions_in_range(
        self, start: Timestamp, end: Timestamp
    ) -> pd.DatetimeIndex:
        """Return all NYSE trading sessions in [start, end], inclusive.

        Args:
            start: Range start (UTC-aware).
            end: Range end (UTC-aware).

        Returns:
            UTC-aware DatetimeIndex of session dates at calendar frequency.
        """
        sessions: pd.DatetimeIndex = self._xcal.sessions_in_range(
            self._to_naive(start), self._to_naive(end)
        )
        return sessions.tz_localize("UTC")

    def previous_session(self, t: Timestamp) -> Timestamp:
        """Return the NYSE trading session immediately before t.

        Args:
            t: UTC-aware timestamp; must itself be a valid trading session.

        Returns:
            UTC-aware Timestamp of the preceding session.
        """
        return self._to_utc(self._xcal.previous_session(self._to_naive(t)))

    def next_session(self, t: Timestamp) -> Timestamp:
        """Return the NYSE trading session immediately after t.

        Args:
            t: UTC-aware timestamp; must itself be a valid trading session.

        Returns:
            UTC-aware Timestamp of the following session.
        """
        return self._to_utc(self._xcal.next_session(self._to_naive(t)))
