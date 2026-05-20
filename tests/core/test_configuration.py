"""Tests for src/alpha_decay_foundry/core/configuration.py."""

from __future__ import annotations

import pytest

from alpha_decay_foundry.core.configuration import Configuration

# ---------------------------------------------------------------------------
# Configuration.research() — defaults
# ---------------------------------------------------------------------------


def test_research_returns_configuration() -> None:
    cfg = Configuration.research()
    assert isinstance(cfg, Configuration)


def test_research_enforce_lifecycle_false() -> None:
    cfg = Configuration.research()
    assert cfg.enforce_lifecycle is False


def test_research_costs_none() -> None:
    cfg = Configuration.research()
    assert cfg.costs is None


def test_research_slippage_none() -> None:
    cfg = Configuration.research()
    assert cfg.slippage is None


def test_research_taxes_none() -> None:
    cfg = Configuration.research()
    assert cfg.taxes is None


def test_research_risk_overlays_empty_list() -> None:
    cfg = Configuration.research()
    assert cfg.risk_overlays == []


def test_research_risk_overlays_independent_instances() -> None:
    """Each call to research() returns an independent list instance."""
    cfg1 = Configuration.research()
    cfg2 = Configuration.research()
    cfg1.risk_overlays.append("something")
    assert cfg2.risk_overlays == []


# ---------------------------------------------------------------------------
# Configuration direct construction
# ---------------------------------------------------------------------------


def test_default_construction_matches_research() -> None:
    cfg_direct = Configuration()
    cfg_factory = Configuration.research()
    assert cfg_direct.enforce_lifecycle == cfg_factory.enforce_lifecycle
    assert cfg_direct.costs == cfg_factory.costs
    assert cfg_direct.slippage == cfg_factory.slippage
    assert cfg_direct.taxes == cfg_factory.taxes
    assert cfg_direct.risk_overlays == cfg_factory.risk_overlays


def test_enforce_lifecycle_can_be_set() -> None:
    cfg = Configuration(enforce_lifecycle=True)
    assert cfg.enforce_lifecycle is True


# ---------------------------------------------------------------------------
# Stub factories raise NotImplementedError
# ---------------------------------------------------------------------------


def test_realistic_backtest_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="v0.2"):
        Configuration.realistic_backtest()


def test_paper_trading_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="v0.4"):
        Configuration.paper_trading()
