from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.automation import (
    AutomationDirector,
    AutomationSettings,
    choose_random_segment,
)
from core.composition import Layer
from effects.settings import EffectSettings
from media.models import MediaAsset


@dataclass
class FakeDeck:
    id: str
    locked: bool = False
    path: str | None = None
    asset_id: str | None = None
    collection_id: str | None = None
    segment_start: float = 0.0
    segment_end: float | None = None
    loop: bool = True
    load_count: int = 0

    def load(
            self,
            path: str,
            asset_id: str | None = None,
            collection_id: str | None = None,
            segment_start: float = 0.0,
            segment_end: float | None = None,
            loop: bool | None = None,
    ) -> None:
        self.path = path
        self.asset_id = asset_id
        self.collection_id = collection_id
        self.segment_start = segment_start
        self.segment_end = segment_end
        if loop is not None:
            self.loop = loop
        self.load_count += 1


def make_asset(folder: Path, name: str, duration: float = 90.0) -> MediaAsset:
    path = folder / name
    path.write_bytes(b"video placeholder")
    return MediaAsset(
        id=name,
        path=str(path),
        collection_id="collection-a",
        name=name,
        duration=duration,
    )


def test_random_segment_is_inside_clip_bounds() -> None:
    import random

    start, end = choose_random_segment(70.0, 5.0, 15.0, random.Random(7))

    assert 0.0 <= start < end <= 70.0
    assert 5.0 <= end - start <= 15.0


def test_unknown_duration_uses_full_clip_range() -> None:
    import random

    assert choose_random_segment(None, 5.0, 15.0, random.Random(1)) == (0.0, None)


def test_automation_loads_random_segments_and_respects_locked_decks(tmp_path) -> None:
    assets = [
        make_asset(tmp_path, "clip-a.mp4"),
        make_asset(tmp_path, "clip-b.mp4"),
    ]
    decks = {
        "deck_a": FakeDeck("deck_a"),
        "deck_b": FakeDeck("deck_b", locked=True),
    }
    director = AutomationDirector(seed=12)
    settings = AutomationSettings(
        min_segment_seconds=4.0,
        max_segment_seconds=9.0,
        loop_probability=1.0,
        clip_switch_probability=1.0,
        randomize_layout=False,
        randomize_effects=False,
    )

    loaded = director.start(
        assets,
        decks,
        [Layer(id="layer-a")],
        EffectSettings(),
        settings=settings,
        duration_seconds=120,
        now=10.0,
    )

    assert loaded == 1
    assert decks["deck_a"].load_count == 1
    assert decks["deck_b"].load_count == 0
    assert decks["deck_a"].segment_start < decks["deck_a"].segment_end <= 90.0
    assert decks["deck_a"].loop is True
    assert director.running


def test_automation_runs_due_cut_then_stops_at_session_end(tmp_path) -> None:
    assets = [
        make_asset(tmp_path, "one.mp4"),
        make_asset(tmp_path, "two.mp4"),
    ]
    deck = FakeDeck("deck_a")
    director = AutomationDirector(seed=3)
    settings = AutomationSettings(
        min_segment_seconds=2.0,
        max_segment_seconds=2.0,
        min_cut_interval=1.0,
        max_cut_interval=1.0,
        clip_switch_probability=1.0,
        randomize_layout=False,
        randomize_effects=False,
    )

    director.start(
        assets,
        [deck],
        [Layer(id="layer-a")],
        EffectSettings(),
        settings=settings,
        duration_seconds=3.0,
        now=100.0,
    )
    first_asset = deck.asset_id

    assert director.tick(now=102.0) is True
    assert deck.load_count == 2
    assert deck.asset_id != first_asset
    assert director.running

    assert director.tick(now=104.0) is True
    assert director.running is False
    assert director.last_action == "Automation session completed"


def test_automation_randomizes_layout_and_effects(tmp_path) -> None:
    assets = [make_asset(tmp_path, "single.mp4")]
    deck = FakeDeck("deck_a")
    layer = Layer(id="layer-a", position=(0.5, 0.5), scale=(1.0, 1.0))
    effects = EffectSettings()
    director = AutomationDirector(seed=19)
    settings = AutomationSettings(
        min_cut_interval=50.0,
        max_cut_interval=50.0,
        min_layout_interval=2.0,
        max_layout_interval=2.0,
        min_effect_interval=2.0,
        max_effect_interval=2.0,
        randomize_layout=True,
        randomize_effects=True,
    )

    director.start(
        assets,
        [deck],
        [layer],
        effects,
        settings=settings,
        duration_seconds=None,
        now=1.0,
    )
    original_position = layer.position

    assert director.tick(now=4.0) is True
    assert layer.position != original_position or layer.scale != (1.0, 1.0)
    assert effects.preset_name != "Clean"


def test_one_shot_fragment_advances_when_segment_finishes(tmp_path) -> None:
    asset = make_asset(tmp_path, "one-shot.mp4", duration=60.0)
    deck = FakeDeck("deck_a")
    director = AutomationDirector(seed=4)
    settings = AutomationSettings(
        min_segment_seconds=4.0,
        max_segment_seconds=4.0,
        min_cut_interval=30.0,
        max_cut_interval=30.0,
        loop_probability=0.0,
        clip_switch_probability=0.0,
        randomize_layout=False,
        randomize_effects=False,
    )

    director.start(
        [asset],
        [deck],
        [Layer(id="layer-a")],
        EffectSettings(),
        settings=settings,
        duration_seconds=None,
        now=50.0,
    )
    assert deck.loop is False
    assert deck.segment_end is not None
    expected_cut = 50.0 + (deck.segment_end - deck.segment_start)

    assert director.tick(now=expected_cut - 0.1) is False
    assert deck.load_count == 1
    assert director.tick(now=expected_cut + 0.1) is True
    assert deck.load_count == 2


def test_live_media_pool_refresh_does_not_interrupt_current_clip(tmp_path) -> None:
    first = make_asset(tmp_path, "first-pool.mp4")
    second = make_asset(tmp_path, "second-pool.mp4")
    deck = FakeDeck("deck_a")
    director = AutomationDirector(seed=8)
    settings = AutomationSettings(
        min_segment_seconds=2.0,
        max_segment_seconds=2.0,
        min_cut_interval=1.0,
        max_cut_interval=1.0,
        clip_switch_probability=1.0,
        randomize_layout=False,
        randomize_effects=False,
    )

    director.start(
        [first, second],
        [deck],
        [Layer(id="layer-a")],
        EffectSettings(),
        settings=settings,
        duration_seconds=120.0,
        now=10.0,
    )
    current_asset_id = deck.asset_id
    assert deck.load_count == 1

    director.replace_assets([second], now=10.0)

    # Editing the source pool must not force a hard cut on the current frame.
    assert deck.asset_id == current_asset_id
    assert deck.load_count == 1
    assert director.tick(now=12.0) is True
    assert deck.asset_id == second.id
    assert deck.load_count == 2

    director.replace_assets([], now=13.0)
    assert deck.asset_id == second.id
    assert deck.load_count == 2
    assert director.tick(now=100.0) is False
    assert deck.asset_id == second.id
    assert deck.load_count == 2


def test_deck_unlocked_after_session_start_joins_automation(tmp_path) -> None:
    asset = make_asset(tmp_path, "unlocked-later.mp4")
    active = FakeDeck("deck_a")
    locked = FakeDeck("deck_b", locked=True)
    director = AutomationDirector(seed=5)
    settings = AutomationSettings(
        min_segment_seconds=2.0,
        max_segment_seconds=2.0,
        min_cut_interval=1.0,
        max_cut_interval=1.0,
        randomize_layout=False,
        randomize_effects=False,
    )

    director.start(
        [asset],
        [active, locked],
        [Layer(id="layer-a")],
        EffectSettings(),
        settings=settings,
        duration_seconds=60.0,
        now=10.0,
    )
    assert locked.load_count == 0

    locked.locked = False
    director.tick(now=10.5)
    assert locked.load_count == 0
    assert director.tick(now=12.0) is True
    assert locked.load_count == 1


def test_automation_skips_unreadable_clip_and_starts_with_next_candidate(tmp_path) -> None:
    class PartiallyFailingDeck(FakeDeck):
        def load(self, path: str, **kwargs) -> None:
            if path.endswith("bad.mp4"):
                raise RuntimeError("unreadable clip")
            super().load(path, **kwargs)

    bad = make_asset(tmp_path, "bad.mp4")
    good = make_asset(tmp_path, "good.mp4")
    deck = PartiallyFailingDeck("deck_a")
    director = AutomationDirector(seed=2)
    settings = AutomationSettings(
        randomize_layout=False,
        randomize_effects=False,
    )

    loaded = director.start(
        [bad, good],
        [deck],
        [Layer(id="video-layer")],
        EffectSettings(),
        settings=settings,
        duration_seconds=None,
        now=10.0,
    )

    assert loaded == 1
    assert deck.path == good.path
    assert director.running


def test_automation_start_failure_leaves_director_stopped(tmp_path) -> None:
    class BrokenDeck(FakeDeck):
        def load(self, path: str, **kwargs) -> None:
            raise RuntimeError("decoder could not open clip")

    asset = make_asset(tmp_path, "broken.mp4")
    deck = BrokenDeck("deck_a")
    director = AutomationDirector(seed=3)

    try:
        director.start(
            [asset],
            [deck],
            [Layer(id="video-layer")],
            EffectSettings(),
            settings=AutomationSettings(randomize_layout=False, randomize_effects=False),
            duration_seconds=None,
            now=1.0,
        )
    except ValueError as exc:
        assert "could load a playable clip" in str(exc)
    else:
        raise AssertionError("Auto Mode should reject a session with no loadable decks")

    assert director.running is False
    assert director._deck_due == {}


def test_auto_layout_does_not_move_generator_layers(tmp_path) -> None:
    asset = make_asset(tmp_path, "layout.mp4")
    deck = FakeDeck("deck_a")
    video = Layer(id="video-layer", source_type="video")
    generator = Layer(
        id="text-layer",
        source_type="generator",
        generator_type="text",
        position=(0.3, 0.6),
        scale=(0.7, 0.7),
    )
    director = AutomationDirector(seed=42)

    director.start(
        [asset],
        [deck],
        [video, generator],
        EffectSettings(),
        settings=AutomationSettings(
            randomize_layout=True,
            randomize_effects=False,
            min_layout_interval=2.0,
            max_layout_interval=2.0,
        ),
        duration_seconds=None,
        now=1.0,
    )

    assert generator.position == (0.3, 0.6)
    assert generator.scale == (0.7, 0.7)


def test_automation_varies_text_and_generator_settings_but_respects_layer_locks(tmp_path) -> None:
    asset = make_asset(tmp_path, "generator-auto.mp4")
    deck = FakeDeck("deck_a")
    from generators.catalog import default_generator_settings
    text_layer = Layer(
        id="text-layer", source_type="generator", generator_type="text",
        generator_settings=default_generator_settings("text"),
    )
    locked_text = Layer(
        id="locked-text", source_type="generator", generator_type="text",
        locked=True, generator_settings=default_generator_settings("text"),
    )
    original_locked = dict(locked_text.generator_settings)
    director = AutomationDirector(seed=18)
    settings = AutomationSettings(
        randomize_layout=False, randomize_effects=False,
        randomize_generators=True, randomize_text=True,
        randomize_layer_effects=False,
        min_generator_interval=2.0, max_generator_interval=2.0,
    )
    director.start([asset], [deck], [text_layer, locked_text], EffectSettings(),
                   settings=settings, duration_seconds=None, now=1.0)
    before = text_layer.generator_settings["text"]
    assert director.tick(now=4.0) is True
    assert text_layer.generator_settings["text"] != before
    assert locked_text.generator_settings == original_locked


def test_automation_can_randomize_independent_layer_effects(tmp_path) -> None:
    asset = make_asset(tmp_path, "layer-fx-auto.mp4")
    deck = FakeDeck("deck_a")
    layer = Layer(id="fx-layer", layer_effects={"enabled": True, "monochrome": 1.0})
    director = AutomationDirector(seed=21)
    settings = AutomationSettings(
        randomize_layout=False, randomize_effects=False,
        randomize_generators=False, randomize_layer_effects=True,
        min_generator_interval=2.0, max_generator_interval=2.0,
    )
    director.start([asset], [deck], [layer], EffectSettings(), settings=settings,
                   duration_seconds=None, now=1.0)
    original = dict(layer.layer_effects)
    assert director.tick(now=4.0) is True
    assert layer.layer_effects != original or layer.layer_effects["enabled"]


def test_automation_varies_text_and_respects_layer_locks(tmp_path) -> None:
    from generators.catalog import default_generator_settings

    asset = make_asset(tmp_path, "generator-auto.mp4")
    deck = FakeDeck("deck_a")
    active = Layer(
        id="text-layer", source_type="generator", generator_type="text",
        generator_settings=default_generator_settings("text"),
    )
    locked = Layer(
        id="locked-text", source_type="generator", generator_type="text",
        locked=True, generator_settings=default_generator_settings("text"),
    )
    original_locked = dict(locked.generator_settings)
    director = AutomationDirector(seed=18)
    director.start(
        [asset], [deck], [active, locked], EffectSettings(),
        settings=AutomationSettings(
            randomize_layout=False, randomize_effects=False,
            randomize_generators=True, randomize_text=True,
            randomize_layer_effects=False,
            min_generator_interval=2.0, max_generator_interval=2.0,
        ),
        duration_seconds=None, now=1.0,
    )
    before = active.generator_settings["text"]
    assert director.tick(now=4.0) is True
    assert active.generator_settings["text"] != before
    assert locked.generator_settings == original_locked


def test_automation_varies_enabled_layer_fx(tmp_path) -> None:
    asset = make_asset(tmp_path, "layer-fx-auto.mp4")
    deck = FakeDeck("deck_a")
    layer = Layer(id="fx-layer", layer_effects={"enabled": True, "monochrome": 1.0})
    director = AutomationDirector(seed=21)
    director.start(
        [asset], [deck], [layer], EffectSettings(),
        settings=AutomationSettings(
            randomize_layout=False, randomize_effects=False,
            randomize_generators=True, randomize_text=False,
            randomize_layer_effects=True,
            min_generator_interval=2.0, max_generator_interval=2.0,
        ),
        duration_seconds=None, now=1.0,
    )
    before = dict(layer.layer_effects)
    assert director.tick(now=4.0) is True
    assert layer.layer_effects != before


def test_layer_fx_automation_respects_manual_cooldown(tmp_path) -> None:
    import time

    asset = make_asset(tmp_path, "layer-fx-cooldown.mp4")
    deck = FakeDeck("deck_a")
    layer = Layer(
        id="manual-fx",
        layer_effects={"enabled": True, "monochrome": 1.0},
        fx_manual_override_until=time.time() + 120.0,
    )
    director = AutomationDirector(seed=22)
    director.start(
        [asset], [deck], [layer], EffectSettings(),
        settings=AutomationSettings(
            randomize_layout=False, randomize_effects=False,
            randomize_generators=False, randomize_layer_effects=True,
            min_generator_interval=2.0, max_generator_interval=2.0,
        ),
        duration_seconds=None, now=1.0,
    )
    original = dict(layer.layer_effects)
    assert director.tick(now=4.0) is False
    assert layer.layer_effects == original


def test_overlay_automation_varies_transform_but_respects_manual_cooldown(tmp_path) -> None:
    import time

    asset = make_asset(tmp_path, "overlay-auto.mp4")
    deck = FakeDeck("deck_a")
    overlay = Layer(
        id="overlay-auto", source_type="overlay", source_id="overlay:auto",
        overlay_manual_override_until=time.time() + 120.0,
    )
    director = AutomationDirector(seed=23)
    director.start(
        [asset], [deck], [overlay], EffectSettings(),
        settings=AutomationSettings(
            randomize_layout=False, randomize_effects=False,
            randomize_generators=False, randomize_layer_effects=False,
            randomize_overlays=True,
            min_generator_interval=2.0, max_generator_interval=2.0,
        ),
        duration_seconds=None, now=1.0,
    )
    original = (overlay.opacity, overlay.scale, overlay.rotation, overlay.blend_mode)
    assert director.tick(now=4.0) is False
    assert (overlay.opacity, overlay.scale, overlay.rotation, overlay.blend_mode) == original
    overlay.overlay_manual_override_until = 0.0
    assert director.tick(now=7.0) is True
    assert (overlay.opacity, overlay.scale, overlay.rotation, overlay.blend_mode) != original


def test_auto_performance_can_vary_palette_without_changing_generator_parameters(tmp_path) -> None:
    from generators.catalog import default_generator_settings
    from generators.palettes import JP_PALETTE_LOOKS

    asset = make_asset(tmp_path, "palette-only.mp4")
    deck = FakeDeck("deck_a")
    layer = Layer(id="geometry-palette", source_type="generator", generator_type="geometry",
                  generator_settings=default_generator_settings("geometry"))
    original_pattern = layer.generator_settings["pattern"]
    director = AutomationDirector(seed=32)
    director.start([asset], [deck], [layer], EffectSettings(),
                   settings=AutomationSettings(randomize_layout=False, randomize_effects=False,
                                               randomize_generators=False, randomize_text=False,
                                               randomize_palette=True, randomize_layer_effects=False,
                                               randomize_overlays=False, min_generator_interval=2.0,
                                               max_generator_interval=2.0),
                   duration_seconds=None, now=1.0)
    assert director.tick(now=4.0) is True
    assert layer.generator_settings["pattern"] == original_pattern
    assert layer.generator_settings["primary_color"] in {
        colour for palette in JP_PALETTE_LOOKS.values() for colour in palette
    }
