"""DataProvider protocol for Alpha Decay Foundry.

DataProvider is the single gateway through which strategies access all
market data. Wrapping it with AsOfDataProvider (issue #6) enforces
point-in-time correctness during backtests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from .exceptions import LookAheadError
from .types import Timestamp
from .universe import Universe


@runtime_checkable
class DataProvider(Protocol):
    """Protocol for point-in-time data access.

    Implementations must ensure that data for timestamp t reflects only
    information that was known at t — no look-ahead revisions.

    During backtests the framework wraps any DataProvider with
    AsOfDataProvider (issue #6), which enforces this contract at the
    call boundary.
    """

    name: str

    def get_panel(
        self,
        fields: list[str],
        start: Timestamp,
        end: Timestamp,
        universe: Universe | None = None,
    ) -> pd.DataFrame:
        """Return a panel of field values for assets over [start, end].

        Args:
            fields: Column names to retrieve (e.g. ["close", "volume"]).
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            universe: If provided, restrict to assets in the universe at
                each date. None returns all available assets.

        Returns:
            DataFrame with a two-level MultiIndex (timestamp: Timestamp,
            asset_id: AssetId) as the row index and fields as columns.
            All timestamps are UTC-aware.
        """
        ...

    def get_returns(
        self,
        start: Timestamp,
        end: Timestamp,
        universe: Universe,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Return an asset-return matrix over [start, end].

        Args:
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            universe: Assets to include.
            frequency: Aggregation frequency — "daily" or "monthly".

        Returns:
            DataFrame with UTC-aware DatetimeIndex (index) and
            AssetId columns. Values are decimal returns (not percent).
        """
        ...

    def get_factor_returns(
        self,
        factors: list[str],
        start: Timestamp,
        end: Timestamp,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Return factor returns for providers that publish them directly.

        Intended for providers such as Ken French or OSAP that supply
        pre-computed factor portfolios (e.g. SMB, HML, RMW, CMA).

        Args:
            factors: Factor names to retrieve (e.g. ["smb", "hml"]).
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            frequency: Aggregation frequency — "daily" or "monthly".

        Returns:
            DataFrame with UTC-aware DatetimeIndex (index) and factor
            names as columns. Values are decimal returns (not percent).
        """
        ...


class AsOfDataProvider:
    """Wraps any DataProvider with strict point-in-time semantics.

    Any request whose end timestamp exceeds as_of raises LookAheadError.
    This is the framework's primary defence against look-ahead bias: the
    backtesting engine constructs a new AsOfDataProvider at each rebalance
    date, and strategies literally cannot read data from the future.

    Args:
        inner: The underlying DataProvider to delegate valid requests to.
        as_of: The current simulation date. Requests ending after this
            timestamp are rejected.
    """

    def __init__(self, inner: DataProvider, as_of: Timestamp) -> None:
        self._inner = inner
        self._as_of = as_of
        self.name = f"{inner.name}@{as_of.date()}"

    @property
    def as_of(self) -> Timestamp:
        """Return the current simulation cutoff date."""
        return self._as_of

    def _check(self, end: Timestamp) -> None:
        if end > self._as_of:
            raise LookAheadError(
                f"Strategy requested data through {end} but as_of is "
                f"{self._as_of}. This indicates look-ahead bias."
            )

    def get_panel(
        self,
        fields: list[str],
        start: Timestamp,
        end: Timestamp,
        universe: Universe | None = None,
    ) -> pd.DataFrame:
        """Delegate to inner provider after enforcing the as-of cutoff.

        Args:
            fields: Column names to retrieve.
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            universe: Optional universe filter; passed through to inner.

        Returns:
            Panel DataFrame from the inner provider.

        Raises:
            LookAheadError: If end > as_of.
        """
        self._check(end)
        return self._inner.get_panel(fields, start, end, universe)

    def get_returns(
        self,
        start: Timestamp,
        end: Timestamp,
        universe: Universe,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Delegate to inner provider after enforcing the as-of cutoff.

        Args:
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            universe: Assets to include.
            frequency: Aggregation frequency.

        Returns:
            Returns DataFrame from the inner provider.

        Raises:
            LookAheadError: If end > as_of.
        """
        self._check(end)
        return self._inner.get_returns(start, end, universe, frequency)

    def get_factor_returns(
        self,
        factors: list[str],
        start: Timestamp,
        end: Timestamp,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Delegate to inner provider after enforcing the as-of cutoff.

        Args:
            factors: Factor names to retrieve.
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            frequency: Aggregation frequency.

        Returns:
            Factor returns DataFrame from the inner provider.

        Raises:
            LookAheadError: If end > as_of.
        """
        self._check(end)
        return self._inner.get_factor_returns(factors, start, end, frequency)
