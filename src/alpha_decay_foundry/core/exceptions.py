"""Framework exception hierarchy for Alpha Decay Foundry.

All exceptions raised by the framework are subclasses of FoundryError,
allowing callers to catch the full hierarchy with a single except clause.
"""

from __future__ import annotations


class FoundryError(Exception):
    """Base exception for all Alpha Decay Foundry framework errors."""


class LookAheadError(FoundryError):
    """Raised when a strategy attempts to access data beyond the as-of date.

    This is the framework's primary defence against look-ahead bias.  The
    AsOfDataProvider raises this whenever a requested end timestamp exceeds
    the current simulation time.
    """


class LifecycleViolationError(FoundryError):
    """Raised when a strategy attempts to enter a phase it is not qualified for.

    For example, transitioning directly from IN_SAMPLE to LIVE without
    completing a paper-trading period raises this error.
    """


class UniverseError(FoundryError):
    """Raised for errors in universe construction or membership queries."""


class DataProviderError(FoundryError):
    """Raised for errors in data retrieval, parsing, or schema validation."""


class CacheError(FoundryError):
    """Raised for errors in the DuckDB + Parquet caching layer."""


class StrategyError(FoundryError):
    """Raised for errors in strategy construction or weight computation."""
