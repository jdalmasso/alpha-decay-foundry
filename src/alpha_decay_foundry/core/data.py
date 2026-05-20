"""DataProvider protocol for Alpha Decay Foundry.

DataProvider is the single gateway through which strategies access all
market data. Wrapping it with AsOfDataProvider (issue #6) enforces
point-in-time correctness during backtests.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

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


class InMemoryDataProvider:
    """Thin in-memory DataProvider for use in tests.

    Accepts pre-built DataFrames at construction time and returns them
    directly from each method. No network access, no caching.

    Args:
        name: Provider label.
        panel: DataFrame returned by get_panel (MultiIndex rows).
        returns: DataFrame returned by get_returns (date × asset).
        factor_returns: DataFrame returned by get_factor_returns (date × factor).
    """

    def __init__(
        self,
        name: str,
        panel: pd.DataFrame,
        returns: pd.DataFrame,
        factor_returns: pd.DataFrame,
    ) -> None:
        self.name = name
        self._panel = panel
        self._returns = returns
        self._factor_returns = factor_returns

    def get_panel(
        self,
        fields: list[str],
        start: Timestamp,
        end: Timestamp,
        universe: Universe | None = None,
    ) -> pd.DataFrame:
        """Return stored panel filtered to [start, end] at the outer index level.

        Args:
            fields: Column names to select (ignored if not present).
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            universe: Unused; included for protocol conformance.

        Returns:
            Slice of the stored panel DataFrame.
        """
        idx = self._panel.index.get_level_values(0)
        mask = (idx >= start) & (idx <= end)
        available = [f for f in fields if f in self._panel.columns]
        return self._panel.loc[mask, available] if available else self._panel.loc[mask]

    def get_returns(
        self,
        start: Timestamp,
        end: Timestamp,
        universe: Universe,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Return stored returns filtered to [start, end].

        Args:
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            universe: Unused; included for protocol conformance.
            frequency: Unused; included for protocol conformance.

        Returns:
            Slice of the stored returns DataFrame.
        """
        return self._returns.loc[start:end]

    def get_factor_returns(
        self,
        factors: list[str],
        start: Timestamp,
        end: Timestamp,
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Return stored factor returns filtered to [start, end].

        Args:
            factors: Factor columns to select.
            start: Range start (UTC-aware, inclusive).
            end: Range end (UTC-aware, inclusive).
            frequency: Unused; included for protocol conformance.

        Returns:
            Slice of the stored factor_returns DataFrame.
        """
        available = [f for f in factors if f in self._factor_returns.columns]
        df = self._factor_returns.loc[start:end]
        return df[available] if available else df
