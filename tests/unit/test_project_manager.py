from core.composition import Composition, Layer
from core.project_manager import ProjectManager


def test_project_save_and_load_round_trip(tmp_path) -> None:
    composition = Composition(name="Test Scene", width=1280, height=720, fps=30)
    composition.add_layer(
        Layer(id="layer_a", name="Deck A", source_id="deck_a",
              opacity=0.5, position=(0.2, 0.6))
    )
    composition.add_layer(
        Layer(
            id="text_art",
            name="Text Art",
            source_type="generator",
            source_id="generator:text_art",
            generator_type="text",
            generator_settings={"text": "memory / signal", "font_size": 180},
        )
    )
    decks = [{"id": "deck_a", "path": "C:/Footage/clip.mp4",
              "asset_id": "asset-a", "loop": True}]
    path = tmp_path / "scene.eliav"
    manager = ProjectManager()
    manager.save(path, composition, decks)
    restored, restored_decks = manager.load(path)
    assert restored.name == "Test Scene"
    assert (restored.width, restored.height, restored.fps) == (1280, 720, 30)
    assert restored.layers[0].opacity == 0.5
    assert restored.layers[0].position == (0.2, 0.6)
    generator = restored.get_layer("text_art")
    assert generator is not None
    assert generator.generator_type == "text"
    assert generator.generator_settings == {
        "text": "memory / signal",
        "font_size": 180,
    }
    assert restored_decks == decks


def test_project_manager_rejects_unrelated_json(tmp_path) -> None:
    path = tmp_path / "not-a-project.json"
    path.write_text('{"hello": "world"}', encoding="utf-8")
    try:
        ProjectManager().load(path)
    except ValueError as exc:
        assert "not an eli_lab" in str(exc)
    else:
        raise AssertionError("Unrecognized project should raise ValueError")


def test_overlay_and_per_layer_effect_settings_survive_project_round_trip(tmp_path) -> None:
    composition = Composition(name="Mixed media scene")
    layer = Layer(
        id="paper-overlay",
        name="Paper Texture",
        source_type="overlay",
        source_id="overlay:paper-overlay",
        overlay_path="C:/Assets/paper.gif",
        overlay_kind="image",
        overlay_loop=False,
        layer_effects={
            "enabled": True,
            "mix": 0.75,
            "monochrome": 1.0,
            "threshold": 0.55,
        },
        opacity=0.82,
        blend_mode="multiply",
    )
    composition.add_layer(layer)
    path = tmp_path / "overlays.eliav"

    manager = ProjectManager()
    manager.save(path, composition, [])
    restored, _ = manager.load(path)
    overlay = restored.get_layer("paper-overlay")

    assert overlay is not None
    assert overlay.source_type == "overlay"
    assert overlay.overlay_path == "C:/Assets/paper.gif"
    assert overlay.overlay_kind == "image"
    assert overlay.overlay_loop is False
    assert overlay.blend_mode == "multiply"
    assert overlay.opacity == 0.82
    assert overlay.layer_effects == layer.layer_effects
