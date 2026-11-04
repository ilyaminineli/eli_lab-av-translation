from core.application import Application


def test_application_starts_with_four_quadrant_video_layers() -> None:
    # Avoid creating the persistent media index in a developer's actual app-data folder.
    from media.library import MediaLibrary
    import tempfile
    from pathlib import Path

    application = Application.__new__(Application)
    application.events = None
    application.project_manager = None
    application.media_library = MediaLibrary(Path(tempfile.mkdtemp()) / "library.sqlite3")
    application.performance_manager = None
    from media.video_deck import VideoDeck
    from core.composition import Composition
    from core.layer_manager import LayerManager

    application.decks = {
        key: VideoDeck(key) for key in ("deck_a", "deck_b", "deck_c", "deck_d")
    }
    application.composition = Composition()
    application.layer_manager = LayerManager(application.composition)
    application._create_default_layers()

    assert len(application.composition.layers) == 4
    assert [layer.position for layer in application.composition.layers] == [
        (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)
    ]
    assert all(layer.scale == (0.5, 0.5) for layer in application.composition.layers)
