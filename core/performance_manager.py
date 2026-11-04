from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Iterable

from core.composition import Layer
from media.models import MediaAsset


class PerformanceManager:
    """Deterministic helpers for randomized video sets and collage layouts."""

    BLEND_MODES = ("normal", "add", "screen", "multiply", "difference")

    def __init__(self, seed: int | None = None) -> None:
        self.random = random.Random(seed)
        self._shuffle_bags: dict[str, list[MediaAsset]] = defaultdict(list)

    def randomize_decks(
            self,
            assets: Iterable[MediaAsset],
            decks: Iterable[object],
    ) -> int:
        candidates = list(assets)
        unlocked = [deck for deck in decks if not getattr(deck, "locked", False)]
        if not candidates or not unlocked:
            return 0

        assigned = 0
        for deck in unlocked:
            collection_id = getattr(deck, "collection_id", None) or "all"
            bag = self._shuffle_bags[collection_id]
            if not bag:
                bag = list(candidates)
                self.random.shuffle(bag)
                self._shuffle_bags[collection_id] = bag
            asset = bag.pop()
            deck.load(asset.path, asset_id=asset.id, collection_id=asset.collection_id)
            assigned += 1
        return assigned

    def randomize_layout(self, layers: Iterable[Layer]) -> int:
        changed = 0
        for layer in layers:
            if layer.source_type != "video" or layer.locked:
                continue
            layer.position = (
                round(self.random.uniform(0.15, 0.85), 3),
                round(self.random.uniform(0.15, 0.85), 3),
            )
            scale = self.random.uniform(0.45, 1.15)
            layer.scale = (round(scale, 3), round(scale, 3))
            layer.opacity = round(self.random.uniform(0.55, 1.0), 3)
            layer.blend_mode = self.random.choice(self.BLEND_MODES)
            layer.rotation = round(self.random.uniform(-8.0, 8.0), 2)
            changed += 1
        return changed
