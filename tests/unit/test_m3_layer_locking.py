from __future__ import annotations

import pytest

from core.application import Application
from core.modulation import ModulationRoute


def test_layer_lock_restores_modulated_generator_value_and_blocks_further_changes() -> None:
    application = Application()
    try:
        layer = application.add_generator_layer("geometry")
        layer.generator_settings["animation_amount"] = 0.15
        application.set_selected_layer_id(layer.id)
        application._audio_sources = {"audio.rms": 1.0}
        application.add_modulation_route(ModulationRoute(
            route_id="audio-motion",
            source_id="audio.rms",
            target_id="generator.animation_amount",
            output_min=0.2,
            output_max=0.4,
            smoothing_ms=0.0,
            attack_ms=1.0,
            release_ms=1.0,
        ))

        outputs = application.apply_modulation()
        assert outputs["generator.animation_amount"] == pytest.approx(0.4)
        assert layer.generator_settings["animation_amount"] == pytest.approx(0.4)

        application.set_layer_locked(layer.id, True)
        assert layer.locked is True
        assert layer.generator_settings["animation_amount"] == pytest.approx(0.15)
        assert application._get_modulation_target("generator.animation_amount") is None

        application._audio_sources = {"audio.rms": 0.1}
        application.apply_modulation()
        assert layer.generator_settings["animation_amount"] == pytest.approx(0.15)

        application.set_layer_locked(layer.id, False)
        assert layer.locked is False
    finally:
        application.shutdown()
