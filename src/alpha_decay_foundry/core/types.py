"""Core type definitions for Alpha Decay Foundry.

All Timestamp values must be UTC-aware. Conversion to/from exchange
timezone happens only at I/O boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NewType

import pandas as pd

AssetId = NewType("AssetId", str)
"""Unique identifier for a tradable asset (e.g. permno, ticker, ISIN)."""

Timestamp = pd.Timestamp
"""UTC-aware timestamp. Never use naive datetime in public APIs."""

TargetWeights = pd.DataFrame
"""Target portfolio weights.

Conventions:
- Long weights are positive, short weights are negative.
- Long-only: weights sum to 1.0.
- Dollar-neutral long/short: weights sum to 0.0, gross exposure = 2.0.
- Index: pd.DatetimeIndex (UTC-aware). Columns: AssetId.
"""


@dataclass(frozen=True)
class DateRange:
    """Closed interval [start, end] used to specify data request windows.

    Args:
        start: Start of the range (inclusive), UTC-aware.
        end: End of the range (inclusive), UTC-aware.

    Raises:
        ValueError: If start > end.
    """

    start: Timestamp
    end: Timestamp

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"start {self.start} > end {self.end}")

    def days(self) -> int:
        """Return the number of calendar days in the range (end - start).

        Returns:
            Integer number of calendar days.
        """
        return (self.end - self.start).days

    def contains(self, t: Timestamp) -> bool:
        """Return True iff t falls within [start, end] (inclusive).

        Args:
            t: Timestamp to test, should be UTC-aware.

        Returns:
            True if start <= t <= end.
        """
        return self.start <= t <= self.end
