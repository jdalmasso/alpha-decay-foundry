"""Tests for src/alpha_decay_foundry/storage/cache.py (flat store/load/exists/query)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from alpha_decay_foundry.core.exceptions import CacheError
from alpha_decay_foundry.storage.cache import CacheLayer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cache(tmp_path: Path) -> CacheLayer:
    """Fresh CacheLayer backed by a temporary directory."""
    return CacheLayer(cache_dir=tmp_path)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Small DataFrame with numeric data for round-trip tests."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2020-01-02", periods=5, freq="B", tz="UTC")
    return pd.DataFrame(
        rng.normal(0, 0.01, (5, 3)),
        index=dates,
        columns=["AAPL", "MSFT", "GOOG"],
    )


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_cache_dir_created(tmp_path: Path) -> None:
    sub = tmp_path / "new_cache"
    CacheLayer(cache_dir=sub)
    assert sub.exists()


def test_metadata_db_created(tmp_path: Path) -> None:
    CacheLayer(cache_dir=tmp_path)
    assert (tmp_path / "metadata" / "downloads.duckdb").exists()


def test_context_manager(tmp_path: Path) -> None:
    with CacheLayer(cache_dir=tmp_path) as cache:
        assert cache.cache_dir == tmp_path


# ---------------------------------------------------------------------------
# store / load round-trip
# ---------------------------------------------------------------------------


def test_store_creates_parquet_file(
    cache: CacheLayer, sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    expected = tmp_path / "french" / "ff5_factors" / "snapshot_2020-01-01.parquet"
    assert expected.exists()


def test_load_returns_equivalent_dataframe(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    loaded = cache.load("french", "ff5_factors", version="2020-01-01")
    pd.testing.assert_frame_equal(loaded.reset_index(drop=True), sample_df.reset_index(drop=True))


def test_store_default_version_uses_today(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    today = str(date.today())
    cache.store("french", "ff5_factors", sample_df)
    assert cache.exists("french", "ff5_factors", version=today)


def test_load_without_version_returns_latest(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    cache.store("french", "ff5_factors", sample_df, version="2020-06-01")
    loaded = cache.load("french", "ff5_factors")
    assert loaded is not None


def test_store_is_atomic(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    """No temporary file left behind after a successful write."""
    cache.store("osap", "chars", sample_df, version="v1")
    tmp_files = list(cache.cache_dir.glob("**/.tmp_*.parquet"))
    assert tmp_files == []


def test_store_overwrites_existing_version(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5", sample_df, version="2020-01-01")
    new_df = sample_df * 2
    cache.store("french", "ff5", new_df, version="2020-01-01")
    loaded = cache.load("french", "ff5", version="2020-01-01")
    pd.testing.assert_frame_equal(loaded.reset_index(drop=True), new_df.reset_index(drop=True))


def test_load_with_filter_returns_subset(cache: CacheLayer) -> None:
    df = pd.DataFrame({"ticker": ["AAPL", "MSFT", "AAPL"], "value": [1.0, 2.0, 3.0]})
    cache.store("test", "prices", df, version="v1")
    loaded = cache.load("test", "prices", version="v1", filters={"ticker": "AAPL"})
    assert (loaded["ticker"] == "AAPL").all()
    assert len(loaded) == 2


# ---------------------------------------------------------------------------
# exists
# ---------------------------------------------------------------------------


def test_exists_true_after_store(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    assert cache.exists("french", "ff5_factors", version="2020-01-01") is True


def test_exists_false_before_store(cache: CacheLayer) -> None:
    assert cache.exists("french", "ff5_factors", version="2020-01-01") is False


def test_exists_without_version_true_if_any(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    assert cache.exists("french", "ff5_factors") is True


def test_exists_without_version_false_if_none(cache: CacheLayer) -> None:
    assert cache.exists("french", "ff5_factors") is False


# ---------------------------------------------------------------------------
# CacheError on miss
# ---------------------------------------------------------------------------


def test_load_raises_cache_error_on_miss(cache: CacheLayer) -> None:
    with pytest.raises(CacheError):
        cache.load("french", "ff5_factors", version="never-stored")


def test_load_without_version_raises_on_empty(cache: CacheLayer) -> None:
    with pytest.raises(CacheError):
        cache.load("french", "ff5_factors")


# ---------------------------------------------------------------------------
# Snapshot versioning
# ---------------------------------------------------------------------------


def test_multiple_versions_coexist(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("osap", "chars", sample_df, version="2020-01-01")
    cache.store("osap", "chars", sample_df * 2, version="2020-06-01")
    assert cache.exists("osap", "chars", version="2020-01-01")
    assert cache.exists("osap", "chars", version="2020-06-01")


def test_different_sources_independent(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5", sample_df, version="v1")
    assert not cache.exists("osap", "ff5", version="v1")


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


def test_query_snapshots_table(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    result = cache.query("SELECT source, dataset, version FROM snapshots ORDER BY source")
    assert len(result) == 1
    assert result["source"].iloc[0] == "french"
    assert result["version"].iloc[0] == "2020-01-01"


def test_stored_at_is_utc(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    """stored_at must be a timezone-aware timestamp stored as UTC (C-3).

    DuckDB returns TIMESTAMPTZ values localized to the session timezone, so
    tzinfo will not always be UTC on the wire.  What matters is that the value
    is timezone-aware (not naive) and converts to UTC correctly.
    """
    before = datetime.now(UTC)
    cache.store("french", "ff5_factors", sample_df, version="2020-01-01")
    after = datetime.now(UTC)

    result = cache.query("SELECT stored_at FROM snapshots")
    stored_at = result["stored_at"].iloc[0]

    # Must be timezone-aware
    assert stored_at.tzinfo is not None, "stored_at should be timezone-aware"
    # Normalise to UTC and verify the wall-clock value is within the store window
    stored_utc = stored_at.tz_convert("UTC").to_pydatetime()
    assert before - timedelta(seconds=1) <= stored_utc <= after + timedelta(seconds=1)


def test_query_invalid_sql_raises_cache_error(cache: CacheLayer) -> None:
    with pytest.raises(CacheError):
        cache.query("SELECT * FROM nonexistent_table_xyz")


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


def test_close_releases_connection(tmp_path: Path) -> None:
    """CacheLayer.close() should not raise."""
    cache = CacheLayer(cache_dir=tmp_path)
    cache.close()


# ---------------------------------------------------------------------------
# Security: path traversal rejection
# ---------------------------------------------------------------------------


def test_store_path_traversal_in_source_raises(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    """source='../../evil' must not escape the cache root."""
    with pytest.raises(CacheError, match="Unsafe path component"):
        cache.store("../../evil", "dataset", sample_df, version="v1")


def test_store_path_traversal_in_version_raises(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    """version='../../../etc/passwd' must not escape the cache root."""
    with pytest.raises(CacheError, match="Unsafe path component"):
        cache.store("french", "ff5", sample_df, version="../../../etc/passwd")


def test_store_path_traversal_in_dataset_raises(cache: CacheLayer, sample_df: pd.DataFrame) -> None:
    """dataset='../../evil' must not escape the cache root."""
    with pytest.raises(CacheError, match="Unsafe path component"):
        cache.store("french", "../../evil", sample_df, version="v1")


# ---------------------------------------------------------------------------
# Security: query() read-only enforcement
# ---------------------------------------------------------------------------


def test_query_write_statement_raises_cache_error(cache: CacheLayer) -> None:
    """query() must reject write statements before they reach DuckDB."""
    with pytest.raises(CacheError, match="read-only SQL"):
        cache.query("CREATE TABLE evil (x INT)")


def test_query_copy_statement_raises_cache_error(cache: CacheLayer) -> None:
    """COPY ... TO must be blocked by the write-keyword guard."""
    with pytest.raises(CacheError, match="read-only SQL"):
        cache.query("COPY snapshots TO '/tmp/exfil.csv'")


def test_query_export_database_blocked(cache: CacheLayer) -> None:
    """EXPORT DATABASE must be blocked (was a bypass in the old blacklist guard)."""
    with pytest.raises(CacheError, match="read-only SQL"):
        cache.query("EXPORT DATABASE '/tmp/exfil'")


def test_query_table_function_blocked(cache: CacheLayer) -> None:
    """DuckDB FROM-first table-function syntax must be blocked."""
    with pytest.raises(CacheError, match="read-only SQL"):
        cache.query("FROM read_parquet('/etc/shadow')")


def test_query_multi_statement_blocked(cache: CacheLayer) -> None:
    """Multi-statement SQL must be rejected to prevent injection after a valid read."""
    with pytest.raises(CacheError, match="multi-statement"):
        cache.query("SELECT 1; DROP TABLE snapshots")


# ---------------------------------------------------------------------------
# Hive-style partitioned store / load
# ---------------------------------------------------------------------------


def test_store_partitioned_creates_directory(cache: CacheLayer) -> None:
    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        {
            "year": ["2020", "2020", "2021"],
            "month": ["01", "02", "01"],
            "value": rng.normal(0, 1, 3),
        }
    )
    cache.store_partitioned("osap", "chars", df, partition_cols=["year", "month"])
    assert (cache.cache_dir / "osap" / "chars").is_dir()


def test_store_partitioned_records_metadata(cache: CacheLayer) -> None:
    rng = np.random.default_rng(2)
    df = pd.DataFrame({"year": ["2020"], "value": rng.normal(0, 1, 1)})
    cache.store_partitioned("osap", "chars", df, partition_cols=["year"], version="v1")
    assert cache.exists("osap", "chars", version="v1")


def test_load_partitioned_returns_dataframe(cache: CacheLayer) -> None:
    rng = np.random.default_rng(3)
    df = pd.DataFrame(
        {
            "year": ["2020", "2020"],
            "month": ["01", "02"],
            "value": rng.normal(0, 1, 2),
        }
    )
    cache.store_partitioned("osap", "chars", df, partition_cols=["year"])
    loaded = cache.load_partitioned("osap", "chars")
    assert isinstance(loaded, pd.DataFrame)
    assert len(loaded) == 2


def test_load_partitioned_raises_on_miss(cache: CacheLayer) -> None:
    with pytest.raises(CacheError):
        cache.load_partitioned("osap", "chars", version="never-stored")


def test_store_partitioned_path_traversal_raises(
    cache: CacheLayer,
) -> None:
    """store_partitioned() must reject traversal components."""
    rng = np.random.default_rng(4)
    df = pd.DataFrame({"year": ["2020"], "value": rng.normal(0, 1, 1)})
    with pytest.raises(CacheError, match="Unsafe path component"):
        cache.store_partitioned("../../evil", "chars", df, partition_cols=["year"], version="v1")


def test_store_partitioned_version_isolation(cache: CacheLayer) -> None:
    """Each version must be stored in its own directory tree (CC-1 regression)."""
    df_v1 = pd.DataFrame({"year": ["2020"], "value": [1.0]})
    df_v2 = pd.DataFrame({"year": ["2020"], "value": [2.0]})
    cache.store_partitioned("osap", "chars", df_v1, partition_cols=["year"], version="v1")
    cache.store_partitioned("osap", "chars", df_v2, partition_cols=["year"], version="v2")

    loaded_v1 = cache.load_partitioned("osap", "chars", version="v1")
    loaded_v2 = cache.load_partitioned("osap", "chars", version="v2")

    # Each version should have exactly one row with the value that was stored.
    assert len(loaded_v1) == 1
    assert len(loaded_v2) == 1
    assert float(loaded_v1["value"].iloc[0]) == pytest.approx(1.0)
    assert float(loaded_v2["value"].iloc[0]) == pytest.approx(2.0)
