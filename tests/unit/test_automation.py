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
