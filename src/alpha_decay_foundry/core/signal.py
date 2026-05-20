"""Signal protocol for Alpha Decay Foundry.

In Grinold-Kahn vocabulary a Signal produces a 'forecast' or 'refined
alpha' — a numeric score per asset per time that ranks assets by
expected excess return.  Signals are the first stage of the
forecast-to-portfolio pipeline described in Active Portfolio Management
(Grinold & Kahn, 2nd ed., 2000), Chapters 6-7.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from .data import DataProvider
from .types import Timestamp
from .universe import Universe


@runtime_checkable
class Signal(Protocol):
    """Protocol for a single-factor alpha signal.

    A Signal transforms raw data into a numeric score per asset per date.
    Scores are then composed into target portfolio weights by a Strategy.

    Score conventions (Grinold & Kahn, Ch. 6 — Forecasting Returns):
    - Higher score means more attractive; a long position is favoured.
    - Negative score means unattractive; a short position is favoured.
    - NaN means no opinion for that asset at that date; the Strategy
      must handle NaN entries (typically by excluding the asset).

    The output of ``compute()`` is referred to as a 'forecast' or
    'refined alpha' in Grinold-Kahn vocabulary.
    """

    name: str

    def compute(
        self,
        data: DataProvider,
        universe: Universe,
        start: Timestamp,
        end: Timestamp,
    ) -> pd.DataFrame:
        """Compute alpha scores for all assets over [start, end].

        Args:
            data: DataProvider used to retrieve the underlying signal
                inputs.  During a backtest this will be an
                AsOfDataProvider ensuring no look-ahead bias.
            universe: Assets to score.  The returned DataFrame should
                have columns equal to the universe members at each date.
            start: Score window start (UTC-aware, inclusive).
            end: Score window end (UTC-aware, inclusive).

        Returns:
            DataFrame with UTC-aware DatetimeIndex (index), AssetId
            columns, and float scores as values.  NaN indicates no
            opinion for that (date, asset) pair.
        """
        ...
