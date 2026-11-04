from core.application import Application
from core.composition import Composition


def test_application_starts_with_four_quadrant_video_layers() -> None:
    application = Application.__new__(Application)
    application.composition = Composition()

    application._create_default_layers()

    assert len(application.composition.layers) == 4
    assert [layer.position for layer in application.composition.layers] == [
        (0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)
    ]
    assert all(layer.scale == (0.5, 0.5) for layer in application.composition.layers)
