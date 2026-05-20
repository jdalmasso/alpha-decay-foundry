"""Tests for src/alpha_decay_foundry/core/exceptions.py."""

from __future__ import annotations

import pytest

from alpha_decay_foundry.core.exceptions import (
    CacheError,
    DataProviderError,
    FoundryError,
    LifecycleViolationError,
    LookAheadError,
    StrategyError,
    UniverseError,
)

_ALL_EXCEPTIONS = [
    LookAheadError,
    LifecycleViolationError,
    UniverseError,
    DataProviderError,
    CacheError,
    StrategyError,
]


def test_foundry_error_is_exception_subclass() -> None:
    assert issubclass(FoundryError, Exception)


def test_foundry_error_is_raiseable() -> None:
    with pytest.raises(FoundryError):
        raise FoundryError("test")


@pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
def test_each_is_foundry_error_subclass(exc_class: type[FoundryError]) -> None:
    assert issubclass(exc_class, FoundryError)


@pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
def test_each_is_exception_subclass(exc_class: type[FoundryError]) -> None:
    assert issubclass(exc_class, Exception)


@pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
def test_each_is_raiseable(exc_class: type[FoundryError]) -> None:
    with pytest.raises(exc_class):
        raise exc_class("test message")


@pytest.mark.parametrize("exc_class", _ALL_EXCEPTIONS)
def test_each_caught_as_foundry_error(exc_class: type[FoundryError]) -> None:
    with pytest.raises(FoundryError):
        raise exc_class("caught as base")


def test_look_ahead_error_message_preserved() -> None:
    msg = "requested 2025-01-01 but as_of is 2024-06-01"
    exc = LookAheadError(msg)
    assert str(exc) == msg


def test_lifecycle_violation_error_message_preserved() -> None:
    msg = "cannot transition to LIVE without paper trading period"
    exc = LifecycleViolationError(msg)
    assert str(exc) == msg
