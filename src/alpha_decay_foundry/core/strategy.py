"""Strategy protocol for Alpha Decay Foundry.

In Grinold-Kahn vocabulary a Strategy converts 'forecasts' (signal
scores) into target portfolio weights.  It is the second stage of the
forecast-to-portfolio pipeline described in Active Portfolio Management
(Grinold & Kahn, 2nd ed., 2000), Chapter 8.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .data import DataProvider
from .types import TargetWeights, Timestamp
from .universe import Universe

if TYPE_CHECKING:
    # Placeholder until core/lifecycle.py is implemented in issue #9.
    # Replace with: from alpha_decay_foundry.core.lifecycle import StrategyLifecycle
    class StrategyLifecycle:
        """Stub for type-checking only; full class defined in issue #9."""


@runtime_checkable
class Strategy(Protocol):
    """Protocol for a signal-to-weights allocation strategy.

    A Strategy combines one or more Signal forecasts into target
    portfolio weights that are then consumed by an ExecutionEngine.

    Weight conventions (Grinold & Kahn, Ch. 8 — The Strategy):
    - Long weights are positive; short weights are negative.
    - Long-only portfolio: weights sum to 1.0.
    - Dollar-neutral long-short: weights sum to 0.0,
      sum of absolute weights (gross exposure) equals 2.0.
    - Strategy implementations are responsible for validating
      these invariants before returning from ``target_weights()``.
    """

    name: str
    lifecycle: StrategyLifecycle | None

    def target_weights(
        self,
        data: DataProvider,
        universe: Universe,
        start: Timestamp,
        end: Timestamp,
    ) -> TargetWeights:
        """Compute target portfolio weights for assets over [start, end].

        Args:
            data: DataProvider used to retrieve signal inputs and price
                data.  During a backtest this will be an
                AsOfDataProvider ensuring no look-ahead bias.
            universe: Assets eligible for inclusion.  The returned
                DataFrame should have columns equal to the universe
                members relevant to the strategy.
            start: Allocation window start (UTC-aware, inclusive).
            end: Allocation window end (UTC-aware, inclusive).

        Returns:
            TargetWeights DataFrame with UTC-aware DatetimeIndex (index),
            AssetId columns, and float weights as values.  Long positions
            are positive, short positions are negative.  NaN indicates
            no position in that (date, asset) pair.
        """
        ...
