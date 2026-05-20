"""Universe abstractions for Alpha Decay Foundry.

A Universe defines which assets are tradable at each point in time,
handling IPOs, delistings, and index-membership changes.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from .types import AssetId, Timestamp


@runtime_checkable
class Universe(Protocol):
    """Protocol for a tradable-asset universe.

    Implementations must be point-in-time correct: membership at time t
    must not reflect information unavailable at t.
    """

    name: str

    def members_at(self, t: Timestamp) -> set[AssetId]:
        """Return the set of tradable assets at time t.

        Args:
            t: UTC-aware timestamp for the membership query.

        Returns:
            Set of AssetId values that were tradable at t.
        """
        ...

    def members_between(self, start: Timestamp, end: Timestamp) -> pd.DataFrame:
        """Return a daily membership matrix over [start, end].

        Args:
            start: Start of range (UTC-aware, inclusive).
            end: End of range (UTC-aware, inclusive).

        Returns:
            DataFrame with UTC-aware DatetimeIndex (daily calendar days),
            columns of AssetId, and boolean values indicating membership.
        """
        ...


class StaticUniverse:
    """Universe with fixed membership across all time, intended for testing.

    All timestamps return the same set of members. No point-in-time
    correctness is implied; do not use in production backtests.

    Args:
        name: Human-readable label for this universe.
        members: Fixed set of asset identifiers.
    """

    def __init__(self, name: str, members: set[AssetId]) -> None:
        self.name = name
        self._members = frozenset(members)

    def members_at(self, t: Timestamp) -> set[AssetId]:
        """Return the fixed member set (ignores t).

        Args:
            t: UTC-aware timestamp (ignored; membership is static).

        Returns:
            The fixed set of AssetId values supplied at construction.
        """
        return set(self._members)

    def members_between(self, start: Timestamp, end: Timestamp) -> pd.DataFrame:
        """Return a daily membership matrix with all members present every day.

        Args:
            start: Start of range (UTC-aware, inclusive).
            end: End of range (UTC-aware, inclusive).

        Returns:
            DataFrame with UTC-aware DatetimeIndex at daily calendar
            frequency, columns of AssetId, all values True.
        """
        index = pd.date_range(start=start, end=end, freq="D", tz="UTC")
        columns = sorted(self._members)
        return pd.DataFrame(True, index=index, columns=columns)


class OSAPUniverse:
    """Universe defined by Open Source Asset Pricing (OSAP) coverage.

    v0.1 proxy: membership is approximated by OSAP characteristic
    coverage at each date.  Real point-in-time index membership
    (survivorship-free) is deferred to v0.1.2 via NorgateDataProvider.

    Full implementation deferred to issue #14 (data_providers/osap.py).
    This stub satisfies the import surface required by other modules.

    TODO(v0.1-clarify): should OSAPUniverse derive membership from the
    set of permnos present in the OSAP characteristics panel for a given
    date, or from a separate OSAP portfolio-membership file?
    Provisional choice: use permnos present in the characteristics panel
    (widest possible coverage, simplest implementation for v0.1).
    Alternative: restrict to assets appearing in the OSAP long-short
    portfolio files, which gives a cleaner factor-relevant universe.
    Tracked in issue #14.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        raise NotImplementedError(
            "OSAPUniverse requires OSAPDataProvider (issue #14). "
            "Use StaticUniverse for unit tests."
        )

    def members_at(self, t: Timestamp) -> set[AssetId]:  # pragma: no cover
        raise NotImplementedError

    def members_between(  # pragma: no cover
        self, start: Timestamp, end: Timestamp
    ) -> pd.DataFrame:
        raise NotImplementedError
