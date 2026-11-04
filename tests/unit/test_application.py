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


def test_application_adds_generator_as_composition_layer() -> None:
    from core.event_bus import EventBus
    from core.layer_manager import LayerManager

    application = Application.__new__(Application)
    application.events = EventBus()
    application.composition = Composition()
    application.layer_manager = LayerManager(application.composition, application.events)

    layer = application.add_generator_layer("text")

    assert layer.source_type == "generator"
    assert layer.generator_type == "text"
    assert layer.source_id == f"generator:{layer.id}"
    assert layer.generator_settings["text"].splitlines() == [
        "THE SHAPE OF", "A VANISHING", "SIGNAL"
    ]
    assert application.composition.layers[-1] is layer
