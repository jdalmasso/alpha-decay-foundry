"""Tests for src/alpha_decay_foundry/storage/schema.py."""

from __future__ import annotations

import math

import pandas as pd
import pytest
from pydantic import ValidationError

from alpha_decay_foundry.core.exceptions import CacheError
from alpha_decay_foundry.storage.schema import (
    CharacteristicSchema,
    FactorReturnSchema,
    PriceSchema,
    ReturnsSchema,
    validate_dataframe,
)

# ---------------------------------------------------------------------------
# PriceSchema
# ---------------------------------------------------------------------------


class TestPriceSchema:
    def test_valid_construction(self) -> None:
        p = PriceSchema(open=100.0, high=105.0, low=99.0, close=103.0, volume=1e6, adj_close=103.0)
        assert p.close == 103.0

    def test_high_equals_low_accepted(self) -> None:
        """high == low is valid (e.g. halted stock)."""
        p = PriceSchema(open=50.0, high=50.0, low=50.0, close=50.0, volume=0.0, adj_close=50.0)
        assert p.high == p.low

    def test_high_less_than_low_rejected(self) -> None:
        with pytest.raises(ValidationError, match="high.*low"):
            PriceSchema(open=100.0, high=90.0, low=99.0, close=95.0, volume=1e6, adj_close=95.0)

    def test_wrong_type_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PriceSchema(  # type: ignore[arg-type]
                open="not_a_number",
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1e6,
                adj_close=103.0,
            )

    def test_validate_dataframe_valid(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "open": 100.0,
                    "high": 105.0,
                    "low": 99.0,
                    "close": 103.0,
                    "volume": 1e6,
                    "adj_close": 103.0,
                }
            ]
        )
        PriceSchema.validate_dataframe(df, source_label="test")  # must not raise

    def test_validate_dataframe_invalid_raises_cache_error(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "open": 100.0,
                    "high": 90.0,
                    "low": 99.0,
                    "close": 95.0,
                    "volume": 1e6,
                    "adj_close": 95.0,
                }
            ]
        )
        with pytest.raises(CacheError, match="PriceSchema"):
            PriceSchema.validate_dataframe(df, source_label="test/prices")

    def test_validate_dataframe_multiple_errors_truncated(self) -> None:
        """Validation stops reporting after 5 errors."""
        rows = [
            {
                "open": 100.0,
                "high": 80.0,
                "low": 99.0,
                "close": 90.0,
                "volume": 1e6,
                "adj_close": 90.0,
            }
        ] * 10
        df = pd.DataFrame(rows)
        with pytest.raises(CacheError, match="truncated"):
            PriceSchema.validate_dataframe(df)


# ---------------------------------------------------------------------------
# ReturnsSchema
# ---------------------------------------------------------------------------


class TestReturnsSchema:
    def test_valid_positive_return(self) -> None:
        r = ReturnsSchema(returns=0.05)
        assert r.returns == pytest.approx(0.05)

    def test_valid_negative_return(self) -> None:
        r = ReturnsSchema(returns=-0.03)
        assert r.returns == pytest.approx(-0.03)

    def test_zero_return_accepted(self) -> None:
        r = ReturnsSchema(returns=0.0)
        assert r.returns == 0.0

    def test_boundary_max_accepted(self) -> None:
        """Exactly 10.0 (1000%) is the boundary — unusual but accepted."""
        r = ReturnsSchema(returns=10.0)
        assert r.returns == 10.0

    def test_boundary_min_accepted(self) -> None:
        r = ReturnsSchema(returns=-1.0)
        assert r.returns == -1.0

    def test_percent_scale_too_large_rejected(self) -> None:
        """11.0 (1100%) looks like percent data — must be rejected."""
        with pytest.raises(ValidationError, match="decimal range"):
            ReturnsSchema(returns=11.0)

    def test_percent_scale_too_negative_rejected(self) -> None:
        with pytest.raises(ValidationError, match="decimal range"):
            ReturnsSchema(returns=-2.5)

    def test_validate_dataframe_valid(self) -> None:
        df = pd.DataFrame({"returns": [0.01, -0.005, 0.0]})
        ReturnsSchema.validate_dataframe(df, source_label="test")

    def test_validate_dataframe_percent_scale_raises_cache_error(self) -> None:
        # Values > 10.0 are outside the decimal plausibility range [-1, 10].
        # 15.0 and 23.0 as "returns" are almost certainly percent-scale data.
        df = pd.DataFrame({"returns": [15.0, 23.0]})
        with pytest.raises(CacheError, match="ReturnsSchema"):
            ReturnsSchema.validate_dataframe(df, source_label="test/returns")


# ---------------------------------------------------------------------------
# CharacteristicSchema
# ---------------------------------------------------------------------------


class TestCharacteristicSchema:
    def test_valid_construction(self) -> None:
        c = CharacteristicSchema(characteristic_name="bm", value=0.75)
        assert c.characteristic_name == "bm"
        assert c.value == pytest.approx(0.75)

    def test_nan_value_accepted(self) -> None:
        """NaN is valid — asset may be missing the characteristic."""
        c = CharacteristicSchema(characteristic_name="mom12m", value=float("nan"))
        assert math.isnan(c.value)

    def test_missing_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CharacteristicSchema(value=0.5)  # type: ignore[call-arg]

    def test_validate_dataframe_valid(self) -> None:
        df = pd.DataFrame({"characteristic_name": ["bm", "mom12m"], "value": [0.75, -0.12]})
        CharacteristicSchema.validate_dataframe(df, source_label="osap/chars")

    def test_validate_dataframe_wrong_type_raises_cache_error(self) -> None:
        df = pd.DataFrame({"characteristic_name": ["bm"], "value": ["not_a_float"]})
        with pytest.raises(CacheError, match="CharacteristicSchema"):
            CharacteristicSchema.validate_dataframe(df)


# ---------------------------------------------------------------------------
# FactorReturnSchema
# ---------------------------------------------------------------------------


class TestFactorReturnSchema:
    def test_valid_construction(self) -> None:
        f = FactorReturnSchema(factor="smb", return_=0.002)
        assert f.factor == "smb"
        assert f.return_ == pytest.approx(0.002)

    def test_percent_scale_rejected(self) -> None:
        with pytest.raises(ValidationError, match="decimal range"):
            FactorReturnSchema(factor="hml", return_=15.0)

    def test_validate_dataframe_valid(self) -> None:
        df = pd.DataFrame({"factor": ["mkt_rf", "smb"], "return_": [0.01, -0.002]})
        FactorReturnSchema.validate_dataframe(df, source_label="french/ff5")

    def test_validate_dataframe_custom_column_names(self) -> None:
        """validate_dataframe accepts alternate column names via kwargs."""
        df = pd.DataFrame({"f": ["mkt_rf"], "ret": [0.01]})
        FactorReturnSchema.validate_dataframe(
            df, source_label="french/ff5", factor_col="f", return_col="ret"
        )

    def test_validate_dataframe_percent_scale_raises_cache_error(self) -> None:
        df = pd.DataFrame({"factor": ["smb"], "return_": [12.5]})
        with pytest.raises(CacheError, match="FactorReturnSchema"):
            FactorReturnSchema.validate_dataframe(df)


# ---------------------------------------------------------------------------
# validate_dataframe convenience dispatcher
# ---------------------------------------------------------------------------


class TestValidateDataframe:
    def test_dispatches_to_price_schema(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "open": 100.0,
                    "high": 105.0,
                    "low": 99.0,
                    "close": 103.0,
                    "volume": 1e6,
                    "adj_close": 103.0,
                }
            ]
        )
        validate_dataframe(df, PriceSchema, "test")  # must not raise

    def test_dispatches_to_returns_schema(self) -> None:
        df = pd.DataFrame({"returns": [0.01]})
        validate_dataframe(df, ReturnsSchema, "test")

    def test_raises_cache_error_on_invalid(self) -> None:
        df = pd.DataFrame({"returns": [99.0]})  # percent scale
        with pytest.raises(CacheError):
            validate_dataframe(df, ReturnsSchema, "test")
