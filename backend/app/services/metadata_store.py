"""SQLite persistence for generated video metadata (swappable for cloud metadata later)."""

from __future__ import annotations

import sqlite3
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class VideoRow:
    video_id: str
    status: str
    prompt: str
    style: str
    resolution: str
    aspect_ratio: str
    duration_seconds: float
    negative_prompt: str | None
    video_path: str | None
    thumbnail_path: str | None
    error: str | None
    created_at: str
    updated_at: str


class VideoMetadataStore:
    """Thread-safe SQLite access for video job records."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _connect(self) -> Any:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            # WAL improves concurrent reads (API) + writes (worker) on the same SQLite file.
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    style TEXT NOT NULL,
                    resolution TEXT NOT NULL,
                    aspect_ratio TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    negative_prompt TEXT,
                    video_path TEXT,
                    thumbnail_path TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_pending(
        self,
        *,
        prompt: str,
        style: str,
        resolution: str,
        aspect_ratio: str,
        duration_seconds: float,
        negative_prompt: str | None,
    ) -> str:
        video_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO videos (
                    video_id, status, prompt, style, resolution, aspect_ratio,
                    duration_seconds, negative_prompt, video_path, thumbnail_path,
                    error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (
                    video_id,
                    "processing",
                    prompt,
                    style,
                    resolution,
                    aspect_ratio,
                    duration_seconds,
                    negative_prompt,
                    now,
                    now,
                ),
            )
        return video_id

    def mark_completed(
        self,
        video_id: str,
        *,
        video_path: str,
        thumbnail_path: str,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE videos SET
                    status = 'completed',
                    video_path = ?,
                    thumbnail_path = ?,
                    error = NULL,
                    updated_at = ?
                WHERE video_id = ?
                """,
                (video_path, thumbnail_path, now, video_id),
            )

    def mark_failed(self, video_id: str, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE videos SET
                    status = 'failed',
                    error = ?,
                    updated_at = ?
                WHERE video_id = ?
                """,
                (error, now, video_id),
            )

    def get(self, video_id: str) -> VideoRow | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM videos WHERE video_id = ?", (video_id,)
            ).fetchone()
        if row is None:
            return None
        return VideoRow(
            video_id=row["video_id"],
            status=row["status"],
            prompt=row["prompt"],
            style=row["style"],
            resolution=row["resolution"],
            aspect_ratio=row["aspect_ratio"],
            duration_seconds=row["duration_seconds"],
            negative_prompt=row["negative_prompt"],
            video_path=row["video_path"],
            thumbnail_path=row["thumbnail_path"],
            error=row["error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def delete(self, video_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM videos WHERE video_id = ?", (video_id,))
            return cur.rowcount > 0

    def list_recent(self, limit: int = 50) -> list[VideoRow]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM videos
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        out: list[VideoRow] = []
        for row in rows:
            out.append(
                VideoRow(
                    video_id=row["video_id"],
                    status=row["status"],
                    prompt=row["prompt"],
                    style=row["style"],
                    resolution=row["resolution"],
                    aspect_ratio=row["aspect_ratio"],
                    duration_seconds=row["duration_seconds"],
                    negative_prompt=row["negative_prompt"],
                    video_path=row["video_path"],
                    thumbnail_path=row["thumbnail_path"],
                    error=row["error"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
            )
        return out
