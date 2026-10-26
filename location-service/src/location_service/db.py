"""SQLite storage for Larry's location history.

Plain stdlib sqlite3 -- the schema is a single table and queries are simple
enough that an ORM would be pure overhead.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from location_service.findmy_client import LocationPoint

_SCHEMA = """
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    confidence INTEGER NOT NULL,
    horizontal_accuracy INTEGER NOT NULL,
    status INTEGER NOT NULL,
    fetched_at TEXT NOT NULL,
    UNIQUE (timestamp, latitude, longitude)
);
CREATE INDEX IF NOT EXISTS idx_locations_timestamp ON locations (timestamp);
"""


@contextmanager
def connect(db_path: str) -> Iterator[sqlite3.Connection]:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with connect(db_path) as conn:
        conn.executescript(_SCHEMA)
        conn.commit()


def insert_points(db_path: str, points: list[LocationPoint]) -> int:
    """Insert new points, silently skipping ones already stored. Returns count inserted."""
    if not points:
        return 0

    fetched_at = datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        cursor = conn.executemany(
            """
            INSERT OR IGNORE INTO locations
                (timestamp, latitude, longitude, confidence, horizontal_accuracy, status, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    p.timestamp.isoformat(),
                    p.latitude,
                    p.longitude,
                    p.confidence,
                    p.horizontal_accuracy,
                    p.status,
                    fetched_at,
                )
                for p in points
            ],
        )
        conn.commit()
        return cursor.rowcount


def get_points(db_path: str, since: datetime | None = None, limit: int = 1000) -> list[dict]:
    query = "SELECT id, timestamp, latitude, longitude, confidence, horizontal_accuracy, status FROM locations"
    params: list[object] = []
    if since is not None:
        query += " WHERE timestamp >= ?"
        params.append(since.isoformat())
    query += " ORDER BY timestamp ASC LIMIT ?"
    params.append(limit)

    with connect(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]


def get_point(db_path: str, point_id: int) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, timestamp, latitude, longitude, confidence, horizontal_accuracy, status
            FROM locations WHERE id = ?
            """,
            (point_id,),
        ).fetchone()
        return dict(row) if row else None


def get_latest_point(db_path: str) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, timestamp, latitude, longitude, confidence, horizontal_accuracy, status
            FROM locations ORDER BY timestamp DESC LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None


# Columns a manual edit may touch. Whitelisted so `update_point` can never be
# used to build a query from an untrusted/arbitrary column name.
_UPDATABLE_COLUMNS = {"timestamp", "latitude", "longitude", "confidence", "horizontal_accuracy", "status"}


def update_point(db_path: str, point_id: int, fields: dict) -> bool:
    """Apply a partial update to one point. Returns whether a row was changed."""
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE_COLUMNS}
    if not fields:
        return False

    assignments = ", ".join(f"{column} = ?" for column in fields)
    with connect(db_path) as conn:
        cursor = conn.execute(
            f"UPDATE locations SET {assignments} WHERE id = ?",  # noqa: S608 -- columns are whitelisted above
            (*fields.values(), point_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_point(db_path: str, point_id: int) -> bool:
    """Delete one point. Returns whether a row was removed."""
    with connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM locations WHERE id = ?", (point_id,))
        conn.commit()
        return cursor.rowcount > 0


def delete_points(db_path: str, point_ids: list[int]) -> int:
    """Delete several points at once (e.g. a whole trip). Returns count removed."""
    if not point_ids:
        return 0

    placeholders = ", ".join("?" for _ in point_ids)
    with connect(db_path) as conn:
        cursor = conn.execute(f"DELETE FROM locations WHERE id IN ({placeholders})", point_ids)
        conn.commit()
        return cursor.rowcount
