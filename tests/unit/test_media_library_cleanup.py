from __future__ import annotations

from media.library import MediaLibrary


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
