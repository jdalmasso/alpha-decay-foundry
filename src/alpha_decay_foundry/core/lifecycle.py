"""Strategy lifecycle enforcement for Alpha Decay Foundry.

Every strategy progresses through three phases before live deployment:
in-sample backtest → out-of-sample paper trading → live execution.
The three-period validation discipline is described in context.md §5.2.

For v0.1, only the IN_SAMPLE phase is exercised.  PAPER and LIVE are
valid enum values but no engine activates them until v0.4.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from .exceptions import LifecycleViolationError
from .types import Timestamp

logger = logging.getLogger(__name__)


class Phase(Enum):
    """Ordered phases a strategy must pass through before live deployment.

    The phase ordering is: IN_SAMPLE → PAPER → LIVE.
    Skipping a phase raises ``LifecycleViolationError``.
    """

    IN_SAMPLE = "in_sample"
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True)
class GoLiveDecision:
    """Immutable record of a go-live approval for a strategy phase transition.

    Created by ``StrategyLifecycle.can_go_live()`` when all criteria are
    met.  Stored on the lifecycle so the approval is auditable.

    Args:
        approved: Whether the transition was approved.
        from_phase: The phase the strategy is leaving.
        to_phase: The phase the strategy is entering.
        approved_at: UTC-aware timestamp of the decision.
        notes: Optional free-text rationale for the approval.
    """

    approved: bool
    from_phase: Phase
    to_phase: Phase
    approved_at: Timestamp
    notes: str = ""


@dataclass
class StrategyLifecycle:
    """Tracks and enforces the three-period validation lifecycle.

    Strategies begin in ``Phase.IN_SAMPLE``.  The ``can_go_live()``
    method validates that a requested phase transition is legal and
    records a ``GoLiveDecision``.

    In v0.1, only ``IN_SAMPLE`` is exercised.  The ``research_only()``
    factory creates a lifecycle that raises ``LifecycleViolationError``
    on any attempt to advance past ``IN_SAMPLE``, making it safe for
    pure research use.  The ``standard()`` factory allows the full
    three-phase progression and is intended for production strategies.

    Args:
        current_phase: Current lifecycle phase (default ``IN_SAMPLE``).
        allow_live: Whether advancing beyond ``IN_SAMPLE`` is permitted.
            Set ``False`` for pure research strategies.
        decisions: Ordered log of ``GoLiveDecision`` records.
    """

    # Permitted forward transitions (no skipping phases).  Never mutated, so
    # declared as a ClassVar rather than a per-instance default_factory field.
    _TRANSITIONS: ClassVar[dict[Phase, Phase]] = {
        Phase.IN_SAMPLE: Phase.PAPER,
        Phase.PAPER: Phase.LIVE,
    }

    current_phase: Phase = field(default=Phase.IN_SAMPLE)
    allow_live: bool = field(default=False)
    decisions: list[GoLiveDecision] = field(default_factory=list)

    @classmethod
    def research_only(cls) -> StrategyLifecycle:
        """Factory for pure-research strategies.

        Creates a lifecycle locked at ``IN_SAMPLE``.  Any attempt to
        call ``can_go_live()`` will raise ``LifecycleViolationError``
        regardless of other criteria.

        Returns:
            ``StrategyLifecycle`` with ``allow_live=False``.
        """
        return cls(current_phase=Phase.IN_SAMPLE, allow_live=False)

    @classmethod
    def standard(cls) -> StrategyLifecycle:
        """Factory for production strategies.

        Creates a lifecycle that permits the full IN_SAMPLE → PAPER →
        LIVE progression via ``can_go_live()``.

        Returns:
            ``StrategyLifecycle`` with ``allow_live=True``.
        """
        return cls(current_phase=Phase.IN_SAMPLE, allow_live=True)

    def can_go_live(
        self,
        approved_at: Timestamp,
        notes: str = "",
    ) -> GoLiveDecision:
        """Attempt to advance the lifecycle to the next phase.

        Validates that the transition is legal:
        - The lifecycle must have ``allow_live=True``.
        - The current phase must have a defined successor.

        On success, advances ``current_phase`` and appends a
        ``GoLiveDecision`` to ``decisions``.

        Args:
            approved_at: UTC-aware timestamp of the decision.
            notes: Optional free-text rationale.

        Returns:
            ``GoLiveDecision`` recording the approved transition.

        Raises:
            LifecycleViolationError: If the lifecycle is locked
                (``allow_live=False``) or the current phase has no
                defined successor (already at ``LIVE``).
        """
        if not self.allow_live:
            raise LifecycleViolationError(
                f"Strategy lifecycle is locked at {self.current_phase.value}. "
                "Use StrategyLifecycle.standard() to allow phase transitions."
            )

        next_phase = self._TRANSITIONS.get(self.current_phase)
        if next_phase is None:
            raise LifecycleViolationError(
                f"Strategy is already in {self.current_phase.value} phase; "
                "no further transitions are defined."
            )

        decision = GoLiveDecision(
            approved=True,
            from_phase=self.current_phase,
            to_phase=next_phase,
            approved_at=approved_at,
            notes=notes,
        )
        self.decisions.append(decision)
        self.current_phase = next_phase
        logger.info(
            "Lifecycle transition: %s → %s at %s",
            decision.from_phase.value,
            decision.to_phase.value,
            approved_at,
        )
        return decision
