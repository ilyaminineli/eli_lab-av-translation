from media.library import MediaLibrary


def test_media_library_indexes_supported_files(tmp_path) -> None:
    folder = tmp_path / "footage"
    folder.mkdir()
    (folder / "clip.MP4").write_bytes(b"not a real video")
    (folder / "notes.txt").write_text("ignore me", encoding="utf-8")
    library = MediaLibrary(tmp_path / "library.sqlite3")
    assets = library.add_folder(folder)
    assert len(assets) == 1
    assert assets[0].name == "clip.MP4"
    assert len(library.list_assets()) == 1
    assert library.get_asset(assets[0].id) is not None


def test_media_library_does_not_duplicate_same_path(tmp_path) -> None:
    folder = tmp_path / "footage"
    folder.mkdir()
    (folder / "clip.mp4").write_bytes(b"fake")
    library = MediaLibrary(tmp_path / "library.sqlite3")
    library.add_folder(folder)
    library.add_folder(folder)
    assert len(library.list_assets()) == 1
