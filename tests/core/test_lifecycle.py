"""Tests for src/alpha_decay_foundry/core/lifecycle.py."""

from __future__ import annotations

import pandas as pd
import pytest

from alpha_decay_foundry.core.exceptions import LifecycleViolationError
from alpha_decay_foundry.core.lifecycle import GoLiveDecision, Phase, StrategyLifecycle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = pd.Timestamp("2020-06-01", tz="UTC")


# ---------------------------------------------------------------------------
# Phase enum
# ---------------------------------------------------------------------------


def test_phase_enum_members() -> None:
    assert Phase.IN_SAMPLE.value == "in_sample"
    assert Phase.PAPER.value == "paper"
    assert Phase.LIVE.value == "live"


def test_phase_enum_has_three_members() -> None:
    assert len(Phase) == 3


def test_phase_in_sample_is_first() -> None:
    phases = list(Phase)
    assert phases[0] == Phase.IN_SAMPLE


# ---------------------------------------------------------------------------
# GoLiveDecision dataclass
# ---------------------------------------------------------------------------


def test_go_live_decision_fields() -> None:
    decision = GoLiveDecision(
        approved=True,
        from_phase=Phase.IN_SAMPLE,
        to_phase=Phase.PAPER,
        approved_at=_NOW,
        notes="test approval",
    )
    assert decision.approved is True
    assert decision.from_phase == Phase.IN_SAMPLE
    assert decision.to_phase == Phase.PAPER
    assert decision.approved_at == _NOW
    assert decision.notes == "test approval"


def test_go_live_decision_notes_default_empty() -> None:
    decision = GoLiveDecision(
        approved=True,
        from_phase=Phase.IN_SAMPLE,
        to_phase=Phase.PAPER,
        approved_at=_NOW,
    )
    assert decision.notes == ""


def test_go_live_decision_is_frozen() -> None:
    decision = GoLiveDecision(
        approved=True,
        from_phase=Phase.IN_SAMPLE,
        to_phase=Phase.PAPER,
        approved_at=_NOW,
    )
    # frozen=True raises FrozenInstanceError (AttributeError subclass) on mutation
    with pytest.raises(AttributeError):
        decision.approved = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# StrategyLifecycle factories
# ---------------------------------------------------------------------------


def test_research_only_starts_in_sample() -> None:
    lc = StrategyLifecycle.research_only()
    assert lc.current_phase == Phase.IN_SAMPLE


def test_research_only_allow_live_false() -> None:
    lc = StrategyLifecycle.research_only()
    assert lc.allow_live is False


def test_research_only_decisions_empty() -> None:
    lc = StrategyLifecycle.research_only()
    assert lc.decisions == []


def test_standard_starts_in_sample() -> None:
    lc = StrategyLifecycle.standard()
    assert lc.current_phase == Phase.IN_SAMPLE


def test_standard_allow_live_true() -> None:
    lc = StrategyLifecycle.standard()
    assert lc.allow_live is True


def test_standard_decisions_empty() -> None:
    lc = StrategyLifecycle.standard()
    assert lc.decisions == []


# ---------------------------------------------------------------------------
# can_go_live() — research_only raises immediately
# ---------------------------------------------------------------------------


def test_research_only_can_go_live_raises() -> None:
    lc = StrategyLifecycle.research_only()
    with pytest.raises(LifecycleViolationError, match="locked"):
        lc.can_go_live(_NOW)


def test_research_only_phase_unchanged_after_raise() -> None:
    lc = StrategyLifecycle.research_only()
    with pytest.raises(LifecycleViolationError):
        lc.can_go_live(_NOW)
    assert lc.current_phase == Phase.IN_SAMPLE


# ---------------------------------------------------------------------------
# can_go_live() — standard: valid transitions
# ---------------------------------------------------------------------------


def test_standard_in_sample_to_paper() -> None:
    lc = StrategyLifecycle.standard()
    decision = lc.can_go_live(_NOW)
    assert decision.from_phase == Phase.IN_SAMPLE
    assert decision.to_phase == Phase.PAPER
    assert decision.approved is True


def test_standard_advances_current_phase() -> None:
    lc = StrategyLifecycle.standard()
    lc.can_go_live(_NOW)
    assert lc.current_phase == Phase.PAPER


def test_standard_paper_to_live() -> None:
    lc = StrategyLifecycle.standard()
    lc.can_go_live(_NOW)
    decision = lc.can_go_live(_NOW)
    assert decision.from_phase == Phase.PAPER
    assert decision.to_phase == Phase.LIVE
    assert lc.current_phase == Phase.LIVE


def test_can_go_live_records_decision() -> None:
    lc = StrategyLifecycle.standard()
    lc.can_go_live(_NOW, notes="first approval")
    assert len(lc.decisions) == 1
    assert lc.decisions[0].notes == "first approval"


def test_can_go_live_accumulates_decisions() -> None:
    lc = StrategyLifecycle.standard()
    lc.can_go_live(_NOW)
    lc.can_go_live(_NOW)
    assert len(lc.decisions) == 2


def test_can_go_live_decision_approved_at() -> None:
    lc = StrategyLifecycle.standard()
    t = pd.Timestamp("2021-03-15", tz="UTC")
    decision = lc.can_go_live(t)
    assert decision.approved_at == t


# ---------------------------------------------------------------------------
# can_go_live() — standard: already at LIVE raises
# ---------------------------------------------------------------------------


def test_standard_at_live_raises_no_further_transitions() -> None:
    lc = StrategyLifecycle.standard()
    lc.can_go_live(_NOW)
    lc.can_go_live(_NOW)
    assert lc.current_phase == Phase.LIVE
    with pytest.raises(LifecycleViolationError, match="already in"):
        lc.can_go_live(_NOW)


def test_live_phase_unchanged_after_raise() -> None:
    lc = StrategyLifecycle.standard()
    lc.can_go_live(_NOW)
    lc.can_go_live(_NOW)
    with pytest.raises(LifecycleViolationError):
        lc.can_go_live(_NOW)
    assert lc.current_phase == Phase.LIVE


# ---------------------------------------------------------------------------
# Strategy protocol still satisfied after lifecycle.py exists
# ---------------------------------------------------------------------------


def test_strategy_with_lifecycle_instance_is_valid() -> None:
    """A Strategy with a real StrategyLifecycle satisfies the protocol."""
    from alpha_decay_foundry.core.data import DataProvider
    from alpha_decay_foundry.core.strategy import Strategy
    from alpha_decay_foundry.core.types import TargetWeights, Timestamp
    from alpha_decay_foundry.core.universe import Universe

    class ConcreteStrategy:
        name = "test"
        lifecycle = StrategyLifecycle.research_only()

        def target_weights(
            self,
            data: DataProvider,
            universe: Universe,
            start: Timestamp,
            end: Timestamp,
        ) -> TargetWeights:
            import pandas as pd

            return pd.DataFrame()

    strat = ConcreteStrategy()
    assert isinstance(strat, Strategy)
    assert strat.lifecycle is not None
    assert strat.lifecycle.current_phase == Phase.IN_SAMPLE
