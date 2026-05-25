"""DuckDB + Parquet caching layer for Alpha Decay Foundry.

All downloaded data is cached as Parquet files under
``~/.alpha_decay_foundry/cache/`` (or a custom path).  A DuckDB
database at ``cache_dir/metadata/downloads.duckdb`` tracks every
cached snapshot for reproducibility and cache-hit checks.

Cache layout (see PRD §5.1)::

    cache_dir/
    ├── <source>/<dataset>/snapshot_<version>.parquet
    └── metadata/
        └── downloads.duckdb
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from alpha_decay_foundry.core.exceptions import CacheError

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path.home() / ".alpha_decay_foundry" / "cache"

# Whitelist of DuckDB statement types that are safe for query().
# A blacklist approach has known bypass vectors (EXPORT DATABASE, FROM-first
# table-function syntax, multi-statement injection); a whitelist is strictly
# stronger.  Only SELECT / WITH (CTEs) / read-only introspection keywords are
# permitted.  Note: a proper read_only=True DuckDB connection would be ideal,
# but DuckDB rejects a second connection with a different access mode to the
# same file while a write connection is open.
# TODO(v0.1-clarify): revisit when DuckDB adds per-cursor access-mode control.
# Provisional choice: whitelist regex; alternative: subprocess isolation.
_READ_SQL_WHITELIST = re.compile(
    r"^\s*(SELECT|WITH|SHOW|DESCRIBE|EXPLAIN|PRAGMA)\b",
    re.IGNORECASE | re.DOTALL,
)


class CacheLayer:
    """DuckDB + Parquet cache for reproducibility-first data access.

    Each dataset snapshot is stored as a Snappy-compressed Parquet file.
    Writes are atomic: data is first written to a temporary file in the
    same directory, then renamed into place.

    A DuckDB database records metadata (source, dataset, version, path,
    stored_at) for every cached snapshot so that ``exists()`` and
    ``query()`` work without scanning the filesystem.

    Args:
        cache_dir: Root directory for all cached data.  Defaults to
            ``~/.alpha_decay_foundry/cache/``.  Created on first use.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        metadata_dir = self.cache_dir / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)

        self._conn = duckdb.connect(str(metadata_dir / "downloads.duckdb"))
        self._init_schema()

    def _init_schema(self) -> None:
        """Create the snapshots metadata table if it does not exist.

        If the table already exists with the legacy ``TIMESTAMP`` (local-time)
        type for ``stored_at``, it is migrated in-place to ``TIMESTAMPTZ`` so
        that ordering by ``stored_at`` is correct regardless of the host
        timezone.
        """
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                source      VARCHAR NOT NULL,
                dataset     VARCHAR NOT NULL,
                version     VARCHAR NOT NULL,
                path        VARCHAR NOT NULL,
                stored_at   TIMESTAMPTZ NOT NULL,
                PRIMARY KEY (source, dataset, version)
            )
            """
        )
        # Migrate databases created before C-3 fix: if the column is still the
        # legacy TIMESTAMP type, alter it to TIMESTAMPTZ in-place.
        col_info = self._conn.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name='snapshots' AND column_name='stored_at'"
        ).fetchone()
        if col_info is not None and col_info[0].upper() == "TIMESTAMP":
            self._conn.execute("ALTER TABLE snapshots ALTER stored_at TYPE TIMESTAMPTZ")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        source: str,
        dataset: str,
        data: pd.DataFrame,
        version: str | None = None,
    ) -> None:
        """Write ``data`` to a versioned Parquet snapshot and record metadata.

        The write is atomic: data is written to a temporary file in the
        same directory as the final path, then renamed into place.

        Args:
            source: Data source name (e.g. ``"french"``, ``"osap"``).
            dataset: Dataset name within the source (e.g.
                ``"ff5_factors"``).
            data: DataFrame to persist.
            version: Snapshot version tag.  Defaults to today's ISO date
                (``YYYY-MM-DD``) if not provided.

        Raises:
            CacheError: If the write or metadata update fails.
        """
        version = version or str(date.today())
        target = self._snapshot_path(source, dataset, version)
        target.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = target.parent / f".tmp_{uuid.uuid4().hex}.parquet"
        try:
            table = pa.Table.from_pandas(data)
            # pyarrow has no py.typed marker; pq.write_table is untyped
            pq.write_table(  # type: ignore[no-untyped-call]
                table, str(tmp_path), compression="snappy"
            )
            tmp_path.rename(target)
        except Exception as exc:
            if tmp_path.exists():
                tmp_path.unlink()
            raise CacheError(f"Failed to store {source}/{dataset}@{version}: {exc}") from exc

        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (source, dataset, version, path, stored_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [source, dataset, version, str(target), datetime.now(UTC)],
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to record metadata for {source}/{dataset}@{version}: {exc}"
            ) from exc

        logger.info("Cached %s/%s@%s → %s", source, dataset, version, target)

    def load(
        self,
        source: str,
        dataset: str,
        version: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        """Load a cached snapshot into a DataFrame.

        Args:
            source: Data source name.
            dataset: Dataset name within the source.
            version: Snapshot version tag.  If ``None``, loads the most
                recently stored snapshot for the dataset.
            filters: Optional column-equality filters applied after load
                (``{column: value}``).  Applied as pandas boolean masks.

        Returns:
            DataFrame loaded from the cached Parquet file.

        Raises:
            CacheError: If no matching snapshot is found.
        """
        path = self._resolve_path(source, dataset, version)

        try:
            df: pd.DataFrame = pd.read_parquet(path)
        except Exception as exc:
            raise CacheError(f"Failed to read cached file for {source}/{dataset}: {exc}") from exc

        if filters:
            for col, val in filters.items():
                if col not in df.columns:
                    raise CacheError(
                        f"Filter column {col!r} not found in {source}/{dataset}. "
                        f"Available columns: {list(df.columns)}"
                    )
                df = df.loc[df[col] == val]

        return df

    def exists(
        self,
        source: str,
        dataset: str,
        version: str | None = None,
    ) -> bool:
        """Return ``True`` iff a matching snapshot is recorded in metadata.

        Args:
            source: Data source name.
            dataset: Dataset name.
            version: Snapshot version.  If ``None``, returns ``True`` if
                any version of the dataset exists.

        Returns:
            ``True`` if found, ``False`` otherwise.
        """
        if version is not None:
            row = self._conn.execute(
                "SELECT 1 FROM snapshots WHERE source=? AND dataset=? AND version=?",
                [source, dataset, version],
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT 1 FROM snapshots WHERE source=? AND dataset=?",
                [source, dataset],
            ).fetchone()
        return row is not None

    def query(self, sql: str) -> pd.DataFrame:
        """Execute a DuckDB SQL query against cached metadata and return results.

        Only ``SELECT``, ``WITH`` (CTEs), ``SHOW``, ``DESCRIBE``, ``EXPLAIN``,
        and ``PRAGMA`` statements are accepted.  All other statement types —
        including ``EXPORT DATABASE``, ``COPY``, ``INSERT``, ``UPDATE``,
        ``DELETE``, ``CREATE``, ``DROP``, ``ALTER``, ``TRUNCATE``, ``ATTACH``,
        ``DETACH``, and bare table-function calls (e.g.
        ``FROM read_parquet(...)`` in DuckDB's FROM-first syntax) — are
        rejected before reaching DuckDB.

        Multi-statement SQL (two or more statements separated by ``;``) is also
        rejected to prevent injection of write statements after an otherwise
        valid read.

        **Security note**: ``sql`` must never be derived from external sources
        (config files, CLI flags, downloaded content).  The guards here prevent
        accidental misuse and common injection patterns but are not a full SQL
        sandbox; callers are responsible for ensuring ``sql`` originates from
        trusted application code.

        Args:
            sql: DuckDB-dialect SQL statement.  Must be a single read-only
                query (SELECT, WITH, SHOW, DESCRIBE, EXPLAIN, or PRAGMA).

        Returns:
            DataFrame containing all result rows.

        Raises:
            CacheError: If ``sql`` does not start with an allowed keyword, if
                it contains multiple statements, or if DuckDB raises an error.
        """
        # Whitelist guard: only read-only statement types are allowed.
        if not _READ_SQL_WHITELIST.match(sql):
            raise CacheError(
                "query() only accepts read-only SQL (SELECT, WITH, SHOW, DESCRIBE, "
                "EXPLAIN, PRAGMA). Use store() for writes to the cache."
            )
        # Multi-statement guard: strip a trailing semicolon, then reject any
        # remaining semicolons.  This blocks injection patterns such as
        # "SELECT 1; DROP TABLE snapshots".
        if ";" in sql.rstrip().rstrip(";"):
            raise CacheError(
                "query() does not accept multi-statement SQL. Submit one statement at a time."
            )
        try:
            result: pd.DataFrame = self._conn.execute(sql).df()
        except CacheError:
            raise
        except Exception as exc:
            raise CacheError(f"Query failed: {exc}") from exc
        return result

    # ------------------------------------------------------------------
    # Hive-style partitioned store / load
    # ------------------------------------------------------------------

    def store_partitioned(
        self,
        source: str,
        dataset: str,
        data: pd.DataFrame,
        partition_cols: list[str],
        version: str | None = None,
    ) -> None:
        """Write Hive-style partitioned Parquet files for time-series data.

        Partitions are written as ``<col>=<value>/data.parquet`` sub-paths
        under ``cache_dir/<source>/<dataset>/<version>/``.  Each version gets
        its own isolated partition tree so that multiple versions of the same
        dataset can coexist without overwriting each other.  A single metadata
        row records the versioned partition root (not each individual file).

        Args:
            source: Data source name.
            dataset: Dataset name.
            data: DataFrame containing the partition columns.
            partition_cols: Columns to partition by (e.g.
                ``["year", "month"]``).
            version: Snapshot version tag.  Defaults to today's ISO date.

        Raises:
            CacheError: If any path component escapes the cache root, or
                if the write or metadata update fails.
        """
        version = version or str(date.today())
        self._validate_path_components(source, dataset, version)
        root = self.cache_dir / source / dataset / version
        root.mkdir(parents=True, exist_ok=True)

        try:
            table = pa.Table.from_pandas(data)
            # pyarrow has no py.typed marker; pq.write_to_dataset is untyped
            pq.write_to_dataset(  # type: ignore[no-untyped-call]
                table,
                root_path=str(root),
                partition_cols=partition_cols,
                compression="snappy",
                existing_data_behavior="overwrite_or_ignore",
            )
        except CacheError:
            raise
        except Exception as exc:
            raise CacheError(
                f"Failed to store partitioned {source}/{dataset}@{version}: {exc}"
            ) from exc

        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (source, dataset, version, path, stored_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [source, dataset, version, str(root), datetime.now(UTC)],
            )
        except Exception as exc:
            raise CacheError(
                f"Failed to record metadata for {source}/{dataset}@{version}: {exc}"
            ) from exc

        logger.info("Cached partitioned %s/%s@%s → %s", source, dataset, version, root)

    def load_partitioned(
        self,
        source: str,
        dataset: str,
        version: str | None = None,
        filters: list[tuple[str, str, Any]] | None = None,
    ) -> pd.DataFrame:
        """Load a Hive-style partitioned dataset.

        Args:
            source: Data source name.
            dataset: Dataset name.
            version: Snapshot version tag.  If ``None``, loads the most
                recently stored version.
            filters: Optional PyArrow-style row filters, e.g.
                ``[("year", "=", "2024"), ("month", "=", "01")]``.

        Returns:
            DataFrame with all partitions merged.

        Raises:
            CacheError: If no matching snapshot is found or read fails.
        """
        root_str = self._resolve_path(source, dataset, version)
        root = Path(root_str)
        if not root.is_dir():
            raise CacheError(f"Partitioned dataset root not found for {source}/{dataset}: {root}")

        try:
            # pyarrow has no py.typed marker; ParquetDataset and read_pandas are untyped
            dataset_obj = pq.ParquetDataset(  # type: ignore[no-untyped-call]
                str(root),
                filters=filters,
            )
            df: pd.DataFrame = dataset_obj.read_pandas().to_pandas()  # type: ignore[no-untyped-call]
        except CacheError:
            raise
        except Exception as exc:
            raise CacheError(f"Failed to read partitioned {source}/{dataset}: {exc}") from exc
        return df

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_path_components(self, source: str, dataset: str, version: str) -> None:
        """Raise CacheError if any path component escapes the cache root.

        Resolves the joined path and asserts it starts with
        ``cache_dir.resolve()``.  Rejects components containing ``..``
        or absolute path separators that would route writes or reads
        outside the cache directory.

        Args:
            source: Data source name to validate.
            dataset: Dataset name to validate.
            version: Version tag to validate.

        Raises:
            CacheError: If the resolved path escapes ``cache_dir``.
        """
        resolved = (self.cache_dir / source / dataset / version).resolve()
        if not resolved.is_relative_to(self.cache_dir.resolve()):
            raise CacheError(
                f"Unsafe path component — resolved path escapes cache root: "
                f"{source!r}/{dataset!r}/{version!r}"
            )

    def _snapshot_path(self, source: str, dataset: str, version: str) -> Path:
        self._validate_path_components(source, dataset, version)
        return self.cache_dir / source / dataset / f"snapshot_{version}.parquet"

    def _resolve_path(self, source: str, dataset: str, version: str | None) -> str:
        """Return the filesystem path for a snapshot, or raise CacheError."""
        if version is not None:
            row = self._conn.execute(
                "SELECT path FROM snapshots WHERE source=? AND dataset=? AND version=?",
                [source, dataset, version],
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT path FROM snapshots
                WHERE source=? AND dataset=?
                ORDER BY stored_at DESC
                LIMIT 1
                """,
                [source, dataset],
            ).fetchone()

        if row is None:
            desc = f"{source}/{dataset}" + (f"@{version}" if version else "")
            raise CacheError(f"No cached snapshot found for {desc}")

        return str(row[0])

    def close(self) -> None:
        """Close the DuckDB connection."""
        self._conn.close()

    def __enter__(self) -> CacheLayer:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
