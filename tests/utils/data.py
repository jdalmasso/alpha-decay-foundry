"""Shared test doubles for data-provider tests."""

from __future__ import annotations

import pandas as pd

from alpha_decay_foundry.core.types import Timestamp
from alpha_decay_foundry.core.universe import Universe


class InMemoryDataProvider:
    """Thin in-memory DataProvider for use in tests.

    Accepts pre-built DataFrames at construction time and returns them
    directly from each method. No network access, no caching.

    Args:
        name: Provider label.
        panel: DataFrame returned by get_panel (MultiIndex rows).
        returns: DataFrame returned by get_returns (date x asset).
        factor_returns: DataFrame returned by get_factor_returns (date x factor).
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
