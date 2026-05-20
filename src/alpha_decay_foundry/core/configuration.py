"""Configuration for Alpha Decay Foundry backtests.

Every realism feature (costs, slippage, taxes, lifecycle enforcement)
defaults to off.  v0.1 wires only the research defaults; later versions
populate paper/live behaviour.  See context.md §5.9 (Optionality with
sensible defaults).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Configuration:
    """Backtest and execution configuration.

    All realism features default to ``None`` / ``False`` so that pure
    research workflows require zero configuration.  Opt-in via factory
    classmethods or by constructing with explicit values.

    Args:
        enforce_lifecycle: If ``True``, the engine enforces the three-period
            ``StrategyLifecycle`` validation before allowing live deployment.
            Default ``False`` (research mode).
        costs: Transaction cost model.  ``None`` in v0.1; protocol stub
            and implementations arrive in v0.2.
        slippage: Slippage model.  ``None`` in v0.1; v0.2+.
        taxes: Tax model.  ``None`` in v0.1; v0.2+.
        risk_overlays: List of risk overlay instances applied after weight
            generation.  Empty list in v0.1; v0.2+.
    """

    enforce_lifecycle: bool = False
    costs: Any = None
    slippage: Any = None
    taxes: Any = None
    risk_overlays: list[Any] = field(default_factory=list)

    @classmethod
    def research(cls) -> Configuration:
        """Factory for pure-research configurations.

        Returns a ``Configuration`` with all realism features disabled.
        Suitable for exploratory backtests where friction is not modelled.

        Returns:
            ``Configuration`` with all fields at their default values.
        """
        return cls()

    @classmethod
    def realistic_backtest(cls) -> Configuration:
        """Factory for realistic backtests with costs and slippage.

        Raises:
            NotImplementedError: Cost and slippage models are implemented
                in v0.2.
        """
        raise NotImplementedError("Available in v0.2")

    @classmethod
    def paper_trading(cls) -> Configuration:
        """Factory for paper-trading configurations.

        Raises:
            NotImplementedError: Paper trading is implemented in v0.4.
        """
        raise NotImplementedError("Available in v0.4")
