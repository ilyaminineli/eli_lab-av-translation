from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from config import MEDIA_DB_PATH
from media.models import MediaAsset
from media.scanner import MediaScanner


class MediaLibrary:
    """SQLite-backed index. Source videos remain in their original folders."""

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = Path(database_path or MEDIA_DB_PATH).expanduser()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.scanner = MediaScanner()
        self._initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL UNIQUE,
                    collection_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    duration REAL,
                    width INTEGER,
                    height INTEGER,
                    fps REAL,
                    codec TEXT,
                    thumbnail_path TEXT,
                    status TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    modified_at REAL NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_assets_collection ON assets(collection_id)"
            )

    def add_folder(self, folder: str | Path, recursive: bool = True) -> list[MediaAsset]:
        assets = self.scanner.scan_folder(folder, recursive=recursive)
        with self._connection() as connection:
            for asset in assets:
                connection.execute(
                    """
                    INSERT INTO assets (
                        id, path, collection_id, name, duration, width, height,
                        fps, codec, thumbnail_path, status, file_size, modified_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path) DO UPDATE SET
                        collection_id=excluded.collection_id,
                        name=excluded.name,
                        duration=excluded.duration,
                        width=excluded.width,
                        height=excluded.height,
                        fps=excluded.fps,
                        codec=excluded.codec,
                        status=excluded.status,
                        file_size=excluded.file_size,
                        modified_at=excluded.modified_at
                    """,
                    (
                        asset.id, asset.path, asset.collection_id, asset.name,
                        asset.duration, asset.width, asset.height, asset.fps,
                        asset.codec, asset.thumbnail_path, asset.status,
                        asset.file_size, asset.modified_at,
                    ),
                )
        return assets

    def list_assets(self, collection_id: str | None = None) -> list[MediaAsset]:
        with self._connection() as connection:
            if collection_id:
                rows = connection.execute(
                    "SELECT * FROM assets WHERE collection_id=? ORDER BY name COLLATE NOCASE",
                    (collection_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM assets ORDER BY name COLLATE NOCASE"
                ).fetchall()
        return [MediaAsset.from_row(row) for row in rows]

    def get_asset(self, asset_id: str) -> MediaAsset | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM assets WHERE id=?", (asset_id,)
            ).fetchone()
        return MediaAsset.from_row(row) if row else None

    def update_thumbnail(self, asset_id: str, thumbnail_path: str | Path) -> None:
        with self._connection() as connection:
            connection.execute(
                "UPDATE assets SET thumbnail_path=? WHERE id=?",
                (str(thumbnail_path), asset_id),
            )

    def remove_missing(self) -> int:
        with self._connection() as connection:
            rows = connection.execute("SELECT id, path FROM assets").fetchall()
            missing = [row["id"] for row in rows if not Path(row["path"]).is_file()]
            connection.executemany("DELETE FROM assets WHERE id=?", [(item,) for item in missing])
        return len(missing)
