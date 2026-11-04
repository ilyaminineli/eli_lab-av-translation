from __future__ import annotations

import random
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from core.composition import Layer
from effects.settings import PRESETS, EffectSettings
from media.models import MediaAsset


@dataclass
class AutomationSettings:
    """Timing and probability controls for unattended collage performance."""

    min_segment_seconds: float = 4.0
    max_segment_seconds: float = 16.0
    min_cut_interval: float = 8.0
    max_cut_interval: float = 24.0
    loop_probability: float = 0.58
    clip_switch_probability: float = 0.38
    randomize_layout: bool = True
    randomize_effects: bool = True
    min_layout_interval: float = 14.0
    max_layout_interval: float = 32.0
    min_effect_interval: float = 10.0
    max_effect_interval: float = 26.0

    def normalize(self) -> None:
        self.min_segment_seconds = max(0.5, float(self.min_segment_seconds))
        self.max_segment_seconds = max(
            self.min_segment_seconds, float(self.max_segment_seconds)
        )
        self.min_cut_interval = max(1.0, float(self.min_cut_interval))
        self.max_cut_interval = max(self.min_cut_interval, float(self.max_cut_interval))
        self.loop_probability = max(0.0, min(1.0, float(self.loop_probability)))
        self.clip_switch_probability = max(
            0.0, min(1.0, float(self.clip_switch_probability))
        )
        self.min_layout_interval = max(2.0, float(self.min_layout_interval))
        self.max_layout_interval = max(
            self.min_layout_interval, float(self.max_layout_interval)
        )
        self.min_effect_interval = max(2.0, float(self.min_effect_interval))
        self.max_effect_interval = max(
            self.min_effect_interval, float(self.max_effect_interval)
        )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def choose_random_segment(
    duration: float | None,
    minimum: float,
    maximum: float,
    rng: random.Random,
) -> tuple[float, float | None]:
    """Return a random in/out range contained in the clip duration."""
    minimum = max(0.5, float(minimum))
    maximum = max(minimum, float(maximum))
    if duration is None or duration <= 0:
        return 0.0, None

    safe_duration = max(0.1, float(duration))
    segment_length = min(safe_duration, rng.uniform(minimum, maximum))
    latest_start = max(0.0, safe_duration - segment_length)
    start = rng.uniform(0.0, latest_start) if latest_start > 0 else 0.0
    end = min(safe_duration, start + segment_length)
    return round(start, 3), round(end, 3)


class AutomationDirector:
    """Schedules clip cuts, random in/out segments, layouts and master looks."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.settings = AutomationSettings()
        self.running = False
        self.started_at = 0.0
        self.ends_at: float | None = None
        self.last_action = "Idle"
        self._assets: list[MediaAsset] = []
        self._decks: dict[str, object] = {}
        self._layers: list[Layer] = []
        self._effects: EffectSettings | None = None
        self._deck_due: dict[str, float] = {}
        self._layout_due: float | None = None
        self._effects_due: float | None = None

    @staticmethod
    def _interval(rng: random.Random, low: float, high: float) -> float:
        return rng.uniform(low, high)

    def start(
        self,
        assets: Iterable[MediaAsset],
        decks: Iterable[object] | dict[str, object],
        layers: list[Layer],
        effects: EffectSettings,
        settings: AutomationSettings | None = None,
        duration_seconds: float | None = 1800.0,
        now: float | None = None,
    ) -> int:
        candidates = [
            asset for asset in assets
            if asset.status not in {"error", "unsupported"} and Path(asset.path).is_file()
        ]
        if not candidates:
            raise ValueError("No playable video files are available for automation.")

        self.settings = settings or AutomationSettings()
        self.settings.normalize()
        self._assets = candidates
        if isinstance(decks, dict):
            self._decks = decks
        else:
            self._decks = {str(getattr(deck, "id")): deck for deck in decks}
        self._layers = layers
        self._effects = effects
        started = time.monotonic() if now is None else float(now)
        self.started_at = started
        self.ends_at = (
            started + max(1.0, float(duration_seconds))
            if duration_seconds is not None else None
        )
        self._deck_due.clear()
        self.running = True
        loaded = 0

        for deck_id, deck in self._decks.items():
            if getattr(deck, "locked", False):
                continue
            self._load_random_segment(deck, None, started)
            loaded += 1

        if not loaded:
            self.running = False
            raise ValueError("All video decks are locked. Unlock at least one deck.")

        if self.settings.randomize_layout:
            self._randomize_layout()
        if self.settings.randomize_effects:
            self._randomize_effects()
        self._layout_due = started + self._interval(
            self.rng,
            self.settings.min_layout_interval,
            self.settings.max_layout_interval,
        )
        self._effects_due = started + self._interval(
            self.rng,
            self.settings.min_effect_interval,
            self.settings.max_effect_interval,
        )
        self.last_action = f"Automation started · {loaded} deck(s)"
        return loaded

    def _load_random_segment(
        self,
        deck: object,
        current_asset_id: str | None,
        now: float,
    ) -> None:
        if not self._assets:
            return
        switch = (
            current_asset_id is None
            or self.rng.random() < self.settings.clip_switch_probability
        )
        if not switch and current_asset_id:
            current = next(
                (asset for asset in self._assets if asset.id == current_asset_id),
                None,
            )
            asset = current or self.rng.choice(self._assets)
        else:
            alternatives = [item for item in self._assets if item.id != current_asset_id]
            asset = self.rng.choice(alternatives or self._assets)

        segment_start, segment_end = choose_random_segment(
            asset.duration,
            self.settings.min_segment_seconds,
            self.settings.max_segment_seconds,
            self.rng,
        )
        should_loop = self.rng.random() < self.settings.loop_probability
        deck.load(
            asset.path,
            asset_id=asset.id,
            collection_id=asset.collection_id,
            segment_start=segment_start,
            segment_end=segment_end,
            loop=should_loop,
        )
        deck_id = str(getattr(deck, "id"))
        self._deck_due[deck_id] = now + self._interval(
            self.rng,
            self.settings.min_cut_interval,
            self.settings.max_cut_interval,
        )

    def _randomize_layout(self) -> None:
        active = [layer for layer in self._layers if not layer.locked]
        if not active:
            return
        patterns = [
            [(0.25, 0.25, 0.5), (0.75, 0.25, 0.5), (0.25, 0.75, 0.5), (0.75, 0.75, 0.5)],
            [(0.5, 0.5, 1.0), (0.78, 0.22, 0.28), (0.78, 0.78, 0.28), (0.22, 0.78, 0.28)],
            [(0.5, 0.17, 1.0), (0.5, 0.50, 1.0), (0.5, 0.83, 1.0), (0.5, 0.5, 0.45)],
            [(0.17, 0.5, 1.0), (0.50, 0.5, 1.0), (0.83, 0.5, 1.0), (0.5, 0.5, 0.45)],
            [(0.34, 0.34, 0.68), (0.68, 0.34, 0.42), (0.34, 0.68, 0.42), (0.72, 0.72, 0.34)],
            [(0.5, 0.5, 0.82), (0.5, 0.5, 0.62), (0.5, 0.5, 0.40), (0.5, 0.5, 0.22)],
        ]
        pattern = self.rng.choice(patterns)
        for index, layer in enumerate(active):
            x, y, size = pattern[index % len(pattern)]
            jitter = 0.035
            layer.position = (
                max(0.0, min(1.0, x + self.rng.uniform(-jitter, jitter))),
                max(0.0, min(1.0, y + self.rng.uniform(-jitter, jitter))),
            )
            scale = max(0.12, size * self.rng.uniform(0.88, 1.12))
            layer.scale = (scale, scale)
            layer.rotation = self.rng.uniform(-5.0, 5.0)
            layer.opacity = self.rng.uniform(0.78, 1.0)
            layer.blend_mode = self.rng.choice(
                ("normal", "normal", "screen", "add", "multiply", "difference")
            )

    def _randomize_effects(self) -> None:
        if self._effects is None:
            return
        names = [name for name in PRESETS if name != "Clean"]
        self._effects.apply_preset(self.rng.choice(names))

    def tick(self, now: float | None = None) -> bool:
        if not self.running:
            return False
        current = time.monotonic() if now is None else float(now)
        if self.ends_at is not None and current >= self.ends_at:
            self.running = False
            self.last_action = "Automation session completed"
            return True

        changed = False
        for deck_id, deck in self._decks.items():
            due = self._deck_due.get(deck_id, float("inf"))
            if getattr(deck, "locked", False) or current < due:
                continue
            asset_id = getattr(deck, "asset_id", None)
            self._load_random_segment(deck, asset_id, current)
            self.last_action = f"Random cut · {deck_id.upper()}"
            changed = True

        if (
            self.settings.randomize_layout
            and self._layout_due is not None
            and current >= self._layout_due
        ):
            self._randomize_layout()
            self._layout_due = current + self._interval(
                self.rng,
                self.settings.min_layout_interval,
                self.settings.max_layout_interval,
            )
            self.last_action = "Collage layout changed"
            changed = True

        if (
            self.settings.randomize_effects
            and self._effects_due is not None
            and current >= self._effects_due
        ):
            self._randomize_effects()
            self._effects_due = current + self._interval(
                self.rng,
                self.settings.min_effect_interval,
                self.settings.max_effect_interval,
            )
            self.last_action = f"Overlay look · {self._effects.preset_name}"
            changed = True
        return changed

    def stop(self) -> None:
        self.running = False
        self.last_action = "Automation stopped"

    def remaining_seconds(self, now: float | None = None) -> float | None:
        if self.ends_at is None:
            return None
        current = time.monotonic() if now is None else float(now)
        return max(0.0, self.ends_at - current)
