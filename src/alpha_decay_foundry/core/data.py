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
