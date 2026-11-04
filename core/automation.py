from __future__ import annotations

import logging
import random
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

from core.composition import Layer
from effects.settings import PRESETS, EffectSettings
from effects.layer_settings import LAYER_EFFECT_PRESETS, apply_layer_effect_preset
from generators.catalog import GENERATOR_TYPES, normalize_settings
from generators.text_pools import random_text_sample
from media.models import MediaAsset

_LOG = logging.getLogger(__name__)


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
    randomize_generators: bool = True
    randomize_text: bool = True
    randomize_layer_effects: bool = True
    min_generator_interval: float = 18.0
    max_generator_interval: float = 42.0
    text_language: str = "bilingual"
    text_theme: str = "random"
    text_fragments: int = 16

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
        self.min_generator_interval = max(3.0, float(self.min_generator_interval))
        self.max_generator_interval = max(
            self.min_generator_interval, float(self.max_generator_interval)
        )
        if self.text_language not in {"english", "japanese", "bilingual"}:
            self.text_language = "bilingual"
        if self.text_theme not in {"random", "memory", "body", "signal", "ritual", "identity"}:
            self.text_theme = "random"
        self.text_fragments = max(1, min(60, int(self.text_fragments)))

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
        self._generators_due: float | None = None

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
            if self._load_random_segment(deck, None, started):
                loaded += 1

        if not loaded:
            self.running = False
            self._deck_due.clear()
            raise ValueError(
                "No unlocked video deck could load a playable clip. "
                "Unlock a deck and check that the imported videos are readable."
            )

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
        self._generators_due = started + self._interval(
            self.rng,
            self.settings.min_generator_interval,
            self.settings.max_generator_interval,
        )
        self.last_action = f"Automation started · {loaded} deck(s)"
        return loaded

    def replace_assets(
            self,
            assets: Iterable[MediaAsset],
            now: float | None = None,
    ) -> None:
        """Refresh the live source pool without interrupting currently loaded clips."""
        self._assets = [
            asset for asset in assets
            if asset.status not in {"error", "unsupported"} and Path(asset.path).is_file()
        ]
        if not self.running:
            return

        current = time.monotonic() if now is None else float(now)
        if not self._assets:
            # Keep the current deck frames playing, but do not repeatedly schedule
            # random cuts when the library has been emptied.
            self._deck_due.clear()
            self.last_action = "Source pool empty · current clips continue playing"
            return

        for deck_id in self._decks:
            self._deck_due[deck_id] = current + self._interval(
                self.rng,
                self.settings.min_cut_interval,
                self.settings.max_cut_interval,
            )
        self.last_action = f"Source pool refreshed · {len(self._assets)} clip(s)"

    def _load_random_segment(
            self,
            deck: object,
            current_asset_id: str | None,
            now: float,
    ) -> bool:
        if not self._assets:
            return False

        deck_id = str(getattr(deck, "id"))
        switch = (
                current_asset_id is None
                or self.rng.random() < self.settings.clip_switch_probability
        )
        current_asset = next(
            (asset for asset in self._assets if asset.id == current_asset_id),
            None,
        )
        if not switch and current_asset is not None:
            ordered_assets = [current_asset]
            ordered_assets.extend(
                asset for asset in self._assets if asset.id != current_asset.id
            )
        else:
            alternatives = [
                asset for asset in self._assets if asset.id != current_asset_id
            ]
            self.rng.shuffle(alternatives)
            if current_asset is not None:
                alternatives.append(current_asset)
            ordered_assets = alternatives or list(self._assets)

        # A single corrupt or unreadable clip must not abort a whole Auto session.
        for asset in ordered_assets:
            segment_start, segment_end = choose_random_segment(
                asset.duration,
                self.settings.min_segment_seconds,
                self.settings.max_segment_seconds,
                self.rng,
            )
            should_loop = self.rng.random() < self.settings.loop_probability
            try:
                deck.load(
                    asset.path,
                    asset_id=asset.id,
                    collection_id=asset.collection_id,
                    segment_start=segment_start,
                    segment_end=segment_end,
                    loop=should_loop,
                )
            except Exception:
                _LOG.exception(
                    "Auto Mode could not load %s into %s; trying another clip",
                    asset.path,
                    deck_id,
                )
                continue

            if not should_loop and segment_end is not None:
                # One-shot fragments advance as soon as their out point is reached.
                cut_delay = max(0.5, segment_end - segment_start)
            else:
                cut_delay = self._interval(
                    self.rng,
                    self.settings.min_cut_interval,
                    self.settings.max_cut_interval,
                )
            self._deck_due[deck_id] = now + cut_delay
            return True

        self._deck_due[deck_id] = now + self._interval(
            self.rng,
            self.settings.min_cut_interval,
            self.settings.max_cut_interval,
        )
        self.last_action = f"No readable footage found for {deck_id.upper()}"
        return False

    def _randomize_layout(self) -> None:
        # Auto Mode randomizes video layouts without disturbing authored generator
        # typography and procedural graphics.
        active = [
            layer for layer in self._layers
            if layer.source_type == "video" and not layer.locked
        ]
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

    def _randomize_generators(self) -> int:
        changed = 0
        for layer in self._layers:
            if layer.locked or not layer.visible:
                continue
            if layer.source_type == "generator" and layer.generator_type in GENERATOR_TYPES:
                kind = layer.generator_type
                values = normalize_settings(kind, layer.generator_settings)
                if kind == "text" and self.settings.randomize_text:
                    values.update({
                        "text": random_text_sample(
                            self.settings.text_language,
                            self.settings.text_theme,
                            self.settings.text_fragments,
                            seed=self.rng.randrange(0, 2 ** 31 - 1),
                        ),
                        "text_layout": self.rng.choice(("single", "collage")),
                        "collage_seed": self.rng.randrange(0, 2 ** 31 - 1),
                        "text_color_mode": self.rng.choice(("single", "alternate")),
                        "text_animation": self.rng.choice(
                            ("type_on", "word_reveal", "line_wave", "jitter", "crawl", "glitch")
                        ),
                        "text_animation_speed": self.rng.uniform(0.35, 2.8),
                        "text_animation_amount": self.rng.uniform(0.015, 0.12),
                    })
                elif kind == "geometry":
                    values.update({
                        "pattern": self.rng.choice(
                            ("rings", "grid", "radial", "crosshatch", "spiral", "moire", "hexgrid")
                        ),
                        "density": self.rng.randint(6, 34),
                        "rotation": self.rng.uniform(-35, 35),
                    })
                elif kind == "waveform":
                    values.update({
                        "pattern": self.rng.choice(("sine", "lissajous", "orbit", "radial", "rose")),
                        "density": self.rng.randint(2, 9),
                        "amplitude": self.rng.uniform(0.08, 0.38),
                        "frequency": self.rng.uniform(0.8, 8.0),
                        "phase_offset": self.rng.uniform(0.0, 6.283),
                    })
                elif kind == "particles":
                    values.update({
                        "density": self.rng.randint(16, 100),
                        "speed": self.rng.uniform(0.05, 0.8),
                        "size": self.rng.uniform(0.06, 0.36),
                        "spread": self.rng.uniform(0.15, 0.9),
                        "trail": self.rng.uniform(0.05, 0.65),
                        "mode": self.rng.choice(("drift", "rise", "fall", "orbit")),
                    })
                layer.generator_settings = normalize_settings(kind, values)
                changed += 1
            if self.settings.randomize_layer_effects and layer.source_type in {
                "video", "generator", "overlay"
            }:
                # Do not activate FX on a pristine layer unexpectedly; vary stacks that
                # are already part of the composition.
                fx = layer.layer_effects if isinstance(layer.layer_effects, dict) else {}
                if fx.get("enabled", False):
                    preset_names = [name for name in LAYER_EFFECT_PRESETS if name != "Clean"]
                    layer.layer_effects = apply_layer_effect_preset(self.rng.choice(preset_names))
                    changed += 1
        return changed

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
            if getattr(deck, "locked", False):
                continue
            due = self._deck_due.get(deck_id)
            if due is None:
                self._deck_due[deck_id] = current + self._interval(
                    self.rng,
                    self.settings.min_cut_interval,
                    self.settings.max_cut_interval,
                )
                continue
            if current < due:
                continue
            asset_id = getattr(deck, "asset_id", None)
            loaded = self._load_random_segment(deck, asset_id, current)
            if loaded:
                self.last_action = f"Random cut · {deck_id.upper()}"
            changed = changed or loaded

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

        if (
                self.settings.randomize_generators
                and self._generators_due is not None
                and current >= self._generators_due
        ):
            count = self._randomize_generators()
            self._generators_due = current + self._interval(
                self.rng,
                self.settings.min_generator_interval,
                self.settings.max_generator_interval,
            )
            if count:
                self.last_action = f"Generators / text / layer FX varied · {count} change(s)"
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
