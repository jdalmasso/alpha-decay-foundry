"""Canonical Pydantic schemas for Alpha Decay Foundry data validation.

Each DataProvider translates its native wire format into one of these
schemas before persisting to the cache.  Consumers downstream (signals,
strategies, analytics) can assume canonical field names and units.

Schema conventions
------------------
- All numeric fields are ``float``.
- Returns are **decimal fractions**, not percent (0.01 = 1 %).
- Field names use snake_case; Pydantic aliases handle provider-specific names.
- DataFrame validation raises :class:`~alpha_decay_foundry.core.exceptions.CacheError`
  so the full exception hierarchy stays consistent.

PRD reference: Section 5.3.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd
from pydantic import BaseModel, field_validator, model_validator

from alpha_decay_foundry.core.exceptions import CacheError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETURNS_MIN = -1.0
_RETURNS_MAX = 10.0  # 1 000 % — beyond this we almost certainly have percent data


def _validate_dataframe(
    df: pd.DataFrame,
    schema_cls: type[BaseModel],
    source_label: str,
) -> None:
    """Validate every row of *df* against *schema_cls*.

    Args:
        df: DataFrame whose rows should conform to the schema.  Column names
            must match the schema field names exactly.
        schema_cls: Pydantic model class to validate against.
        source_label: Human-readable label included in any error message
            (e.g. ``"french/ff5_factors"``).

    Raises:
        CacheError: If any row fails schema validation.
    """
    errors: list[str] = []
    for i, row in enumerate(df.to_dict(orient="records")):
        try:
            schema_cls.model_validate(row)
        except Exception as exc:  # pydantic ValidationError
            errors.append(f"Row {i}: {exc}")
        if len(errors) >= 5:
            errors.append("… (truncated after 5 errors)")
            break

    if errors:
        raise CacheError(
            f"DataFrame from {source_label!r} failed schema validation "
            f"({schema_cls.__name__}):\n" + "\n".join(errors)
        )


# ---------------------------------------------------------------------------
# PriceSchema
# ---------------------------------------------------------------------------


class PriceSchema(BaseModel):
    """Canonical OHLCV + adjusted-close row.

    All price fields are in the instrument's native currency unit.
    ``adj_close`` incorporates splits and dividends; use it for return
    calculations.

    Args:
        open: Opening price.
        high: Intraday high.
        low: Intraday low.
        close: Unadjusted closing price.
        volume: Share volume traded.
        adj_close: Dividend- and split-adjusted closing price.
    """

    open: float
    high: float
    low: float
    close: float
    volume: float
    adj_close: float

    @model_validator(mode="after")
    def high_gte_low(self) -> PriceSchema:
        """Sanity-check: high must be ≥ low."""
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) < low ({self.low})")
        return self

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, source_label: str = "unknown") -> None:
        """Validate all rows of *df* against :class:`PriceSchema`.

        Args:
            df: DataFrame with columns matching ``PriceSchema`` field names.
            source_label: Descriptive label for error messages.

        Raises:
            CacheError: If any row fails validation.
        """
        _validate_dataframe(df, cls, source_label)


# ---------------------------------------------------------------------------
# ReturnsSchema
# ---------------------------------------------------------------------------


class ReturnsSchema(BaseModel):
    """Single-asset, single-period return in decimal form.

    Args:
        returns: Decimal return (e.g. ``0.01`` for 1 %).  Values outside
            ``[-1.0, 10.0]`` almost certainly indicate percent-scale data
            and are rejected.
    """

    returns: float

    @field_validator("returns")
    @classmethod
    def must_be_decimal(cls, v: float) -> float:
        """Reject values that look like percent-scale returns."""
        if v < _RETURNS_MIN or v > _RETURNS_MAX:
            raise ValueError(
                f"returns value {v!r} is outside the plausible decimal range "
                f"[{_RETURNS_MIN}, {_RETURNS_MAX}].  "
                "Did you forget to divide by 100?"
            )
        return v

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, source_label: str = "unknown") -> None:
        """Validate all rows of *df* against :class:`ReturnsSchema`.

        The DataFrame must contain a ``returns`` column.

        Args:
            df: DataFrame with a ``returns`` column (decimal values).
            source_label: Descriptive label for error messages.

        Raises:
            CacheError: If any row fails validation.
        """
        _validate_dataframe(df, cls, source_label)


# ---------------------------------------------------------------------------
# CharacteristicSchema
# ---------------------------------------------------------------------------


class CharacteristicSchema(BaseModel):
    """Single characteristic observation for one asset at one point in time.

    Args:
        characteristic_name: OSAP characteristic identifier (e.g. ``"bm"``).
        value: Numeric value of the characteristic.  May be ``NaN`` for
            assets missing the characteristic in a given period.
    """

    characteristic_name: str
    value: float

    @classmethod
    def validate_dataframe(cls, df: pd.DataFrame, source_label: str = "unknown") -> None:
        """Validate all rows of *df* against :class:`CharacteristicSchema`.

        Args:
            df: DataFrame with ``characteristic_name`` (str) and ``value``
                (float) columns.
            source_label: Descriptive label for error messages.

        Raises:
            CacheError: If any row fails validation.
        """
        _validate_dataframe(df, cls, source_label)


# ---------------------------------------------------------------------------
# FactorReturnSchema
# ---------------------------------------------------------------------------


class FactorReturnSchema(BaseModel):
    """Single-factor, single-period return in decimal form.

    Args:
        factor: Factor identifier (e.g. ``"mkt_rf"``, ``"smb"``, ``"hml"``).
        return_: Decimal factor return.  The trailing underscore avoids
            shadowing the Python built-in ``return`` keyword.  Values are
            validated to be in decimal range (same bounds as
            :class:`ReturnsSchema`).
    """

    factor: str
    return_: float

    @field_validator("return_")
    @classmethod
    def must_be_decimal(cls, v: float) -> float:
        """Reject values that look like percent-scale returns."""
        if v < _RETURNS_MIN or v > _RETURNS_MAX:
            raise ValueError(
                f"return_ value {v!r} is outside the plausible decimal range "
                f"[{_RETURNS_MIN}, {_RETURNS_MAX}].  "
                "Did you forget to divide by 100?"
            )
        return v

    @classmethod
    def validate_dataframe(
        cls,
        df: pd.DataFrame,
        source_label: str = "unknown",
        *,
        factor_col: str = "factor",
        return_col: str = "return_",
    ) -> None:
        """Validate all rows of *df* against :class:`FactorReturnSchema`.

        Args:
            df: DataFrame with ``factor`` and ``return_`` columns (or
                column names supplied via *factor_col* / *return_col*).
            source_label: Descriptive label for error messages.
            factor_col: Name of the factor column (default ``"factor"``).
            return_col: Name of the return column (default ``"return_"``).

        Raises:
            CacheError: If any row fails validation.
        """
        renamed = df.rename(columns={factor_col: "factor", return_col: "return_"})
        _validate_dataframe(renamed, cls, source_label)


# ---------------------------------------------------------------------------
# Public validate_dataframe convenience dispatch
# ---------------------------------------------------------------------------


def validate_dataframe(
    df: pd.DataFrame,
    schema: type[BaseModel],
    source_label: str = "unknown",
    **kwargs: Any,
) -> None:
    """Dispatch to the named schema's ``validate_dataframe`` classmethod.

    A thin convenience wrapper so callers don't need to import each schema
    class directly.

    Args:
        df: DataFrame to validate.
        schema: One of :class:`PriceSchema`, :class:`ReturnsSchema`,
            :class:`CharacteristicSchema`, or :class:`FactorReturnSchema`.
        source_label: Descriptive label for error messages.
        **kwargs: Passed through to the schema's ``validate_dataframe``.

    Raises:
        CacheError: If validation fails.
        AttributeError: If *schema* does not have a ``validate_dataframe``
            classmethod.
    """
    schema.validate_dataframe(df, source_label, **kwargs)  # type: ignore[attr-defined]
