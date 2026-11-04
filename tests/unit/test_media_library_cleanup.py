from __future__ import annotations

import sqlite3

from media.library import MediaLibrary
from media.scanner import MediaScanner


def _library_with_clip(tmp_path):
    footage = tmp_path / "Footage A"
    footage.mkdir()
    source = footage / "clip.mp4"
    source.write_bytes(b"test video placeholder")
    thumbnails = tmp_path / "thumbnails"
    library = MediaLibrary(tmp_path / "library.sqlite3", thumbnails)
    assets = library.add_folder(footage)
    return library, source, assets[0], thumbnails


def test_remove_collection_keeps_original_video(tmp_path) -> None:
    library, source, asset, _thumbnails = _library_with_clip(tmp_path)

    assert library.remove_collection(asset.collection_id) == 1

    assert source.is_file()
    assert library.list_assets() == []
    assert library.list_collections() == []


def test_clear_index_keeps_original_videos_and_cleans_thumbnails(tmp_path) -> None:
    library, source, asset, thumbnails = _library_with_clip(tmp_path)
    cached = thumbnails / f"{asset.id}.jpg"
    thumbnails.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(b"cached image")
    library.update_thumbnail(asset.id, cached)

    assert library.clear_index() == 1

    assert source.is_file()
    assert library.list_assets() == []
    assert library.list_collections() == []
    assert not cached.exists()


def test_remove_missing_prunes_records_and_unused_thumbnails(tmp_path) -> None:
    library, source, asset, thumbnails = _library_with_clip(tmp_path)
    cached = thumbnails / f"{asset.id}.jpg"
    thumbnails.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(b"cached image")
    library.update_thumbnail(asset.id, cached)
    source.unlink()

    assert library.remove_missing() == 1

    assert library.list_assets() == []
    assert library.list_collections() == []
    assert not cached.exists()


def test_cleanup_thumbnail_cache_preserves_referenced_files(tmp_path) -> None:
    library, _source, asset, thumbnails = _library_with_clip(tmp_path)
    thumbnails.mkdir(parents=True, exist_ok=True)
    used = thumbnails / f"{asset.id}.jpg"
    orphan = thumbnails / "orphan.jpg"
    used.write_bytes(b"used")
    orphan.write_bytes(b"orphan")
    library.update_thumbnail(asset.id, used)

    assert library.cleanup_thumbnail_cache() == 1

    assert used.is_file()
    assert not orphan.exists()


def test_collection_listing_reports_folder_name_and_asset_count(tmp_path) -> None:
    library, _source, asset, _thumbnails = _library_with_clip(tmp_path)

    collections = library.list_collections()

    assert len(collections) == 1
    assert collections[0]["id"] == asset.collection_id
    assert collections[0]["name"] == "Footage A"
    assert collections[0]["asset_count"] == 1


def test_legacy_collection_root_is_recovered_from_asset_path(tmp_path) -> None:
    root = tmp_path / "Original Folder"
    nested = root / "Nested" / "Subfolder"
    nested.mkdir(parents=True)
    source = nested / "clip.mp4"
    source.write_bytes(b"legacy indexed clip")

    database = tmp_path / "legacy.sqlite3"
    collection_id = MediaScanner.collection_id_for(root)
    with sqlite3.connect(database) as connection:
        connection.execute(
            """
            CREATE TABLE assets (
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
            """
            INSERT INTO assets (
                id, path, collection_id, name, status, file_size, modified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "legacy-id",
                str(source),
                collection_id,
                source.name,
                "ready",
                source.stat().st_size,
                source.stat().st_mtime,
            ),
        )

    library = MediaLibrary(database, tmp_path / "thumbnails")
    collections = library.list_collections()

    assert len(collections) == 1
    assert collections[0]["root_path"] == str(root.resolve())
    assert collections[0]["name"] == "Original Folder"
    assert collections[0]["asset_count"] == 1
