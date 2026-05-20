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
import uuid
from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from alpha_decay_foundry.core.exceptions import CacheError

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path.home() / ".alpha_decay_foundry" / "cache"


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
        """Create the snapshots metadata table if it does not exist."""
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                source      VARCHAR NOT NULL,
                dataset     VARCHAR NOT NULL,
                version     VARCHAR NOT NULL,
                path        VARCHAR NOT NULL,
                stored_at   TIMESTAMP DEFAULT current_timestamp,
                PRIMARY KEY (source, dataset, version)
            )
            """
        )

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
            raise CacheError(
                f"Failed to store {source}/{dataset}@{version}: {exc}"
            ) from exc

        try:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO snapshots (source, dataset, version, path)
                VALUES (?, ?, ?, ?)
                """,
                [source, dataset, version, str(target)],
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
            raise CacheError(
                f"Failed to read cached file for {source}/{dataset}: {exc}"
            ) from exc

        if filters:
            for col, val in filters.items():
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
        """Execute an arbitrary DuckDB SQL query and return results.

        The query runs against the metadata DuckDB connection, which can
        also access Parquet files via DuckDB's ``read_parquet()`` table
        function.

        Args:
            sql: DuckDB-dialect SQL statement.

        Returns:
            DataFrame containing all result rows.

        Raises:
            CacheError: If DuckDB raises an error executing the query.
        """
        try:
            result: pd.DataFrame = self._conn.execute(sql).df()
        except Exception as exc:
            raise CacheError(f"Query failed: {exc}") from exc
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _snapshot_path(self, source: str, dataset: str, version: str) -> Path:
        return self.cache_dir / source / dataset / f"snapshot_{version}.parquet"

    def _resolve_path(
        self, source: str, dataset: str, version: str | None
    ) -> str:
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
