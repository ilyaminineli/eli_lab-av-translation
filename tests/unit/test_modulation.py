from __future__ import annotations

import pytest

from core.modulation import TARGET_SPECS, ModulationMatrix, ModulationRoute


def test_modulation_maps_source_to_registered_target_range() -> None:
    matrix = ModulationMatrix()
    matrix.add_route(ModulationRoute(
        route_id="rms-grain",
        source_id="audio.rms",
        target_id="master.grain",
        output_min=0.1,
        output_max=0.9,
    ))
    outputs, released = matrix.evaluate({"audio.rms": 0.5}, now=1.0)
    assert outputs["master.grain"] == pytest.approx(0.5)
    assert released == set()


def test_modulation_supports_inversion_curves_and_intensity_ceiling() -> None:
    matrix = ModulationMatrix()
    matrix.add_route(ModulationRoute(
        route_id="low-contrast",
        source_id="audio.low",
        target_id="master.contrast",
        output_min=0.25,
        output_max=2.25,
        inverted=True,
        curve="smoothstep",
        intensity_ceiling=0.5,
    ))
    outputs, _ = matrix.evaluate({"audio.low": 0.0}, now=1.0)
    assert outputs["master.contrast"] == pytest.approx(1.25)


def test_modulation_rejects_unknown_sources_and_unsafe_target_ranges() -> None:
    with pytest.raises(ValueError):
        ModulationRoute("bad-source", "file.path", "master.grain").normalize()

    with pytest.raises(ValueError):
        ModulationRoute(
            "bad-target-range",
            "audio.rms",
            "master.grain",
            output_min=-1,
            output_max=2,
        ).normalize()


def test_modulation_manual_override_yields_and_then_releases_target() -> None:
    matrix = ModulationMatrix()
    matrix.add_route(ModulationRoute(
        "audio-to-grain",
        "audio.rms",
        "master.grain",
        output_min=0.0,
        output_max=1.0,
    ))
    first, _ = matrix.evaluate({"audio.rms": 0.8}, now=1.0)
    assert first["master.grain"] == pytest.approx(0.8)

    matrix.manual_override("master.grain", 2.0, now=1.1)
    held, released = matrix.evaluate({"audio.rms": 0.2}, now=1.5)
    assert "master.grain" not in held
    assert released == {"master.grain"}

    resumed, released = matrix.evaluate({"audio.rms": 0.2}, now=3.2)
    assert resumed["master.grain"] == pytest.approx(0.2, abs=0.0001)
    assert released == set()


def test_modulation_disabled_route_releases_its_target() -> None:
    matrix = ModulationMatrix()
    route = ModulationRoute("rms", "audio.rms", "master.grain")
    matrix.add_route(route)
    matrix.evaluate({"audio.rms": 0.5}, now=1.0)
    route.enabled = False
    outputs, released = matrix.evaluate({"audio.rms": 0.2}, now=2.0)
    assert outputs == {}
    assert released == {"master.grain"}


def test_target_registry_has_explicit_safe_ranges() -> None:
    assert TARGET_SPECS["master.grain"].minimum == 0.0
    assert TARGET_SPECS["master.grain"].maximum == 1.0
    assert "master.brightness" in TARGET_SPECS
    assert "generator.density" in TARGET_SPECS
    assert "automation.loop_probability" in TARGET_SPECS


def test_modulation_matrix_rejects_multiple_routes_for_same_target() -> None:
    matrix = ModulationMatrix()
    matrix.add_route(ModulationRoute(
        "first",
        "audio.rms",
        "master.grain",
    ))
    with pytest.raises(ValueError):
        matrix.add_route(ModulationRoute(
            "second",
            "audio.low",
            "master.grain",
        ))


def test_modulation_matrix_edits_route_and_resets_smoothing_state() -> None:
    matrix = ModulationMatrix()
    matrix.add_route(ModulationRoute(
        "edit-me",
        "audio.rms",
        "master.grain",
    ))
    matrix.evaluate({"audio.rms": 0.5}, now=1.0)
    matrix.update_route("edit-me", {
        "source_id": "audio.low",
        "output_min": 0.2,
        "output_max": 0.8,
        "curve": "smoothstep",
    })

    route = matrix.routes[0]
    assert route.source_id == "audio.low"
    assert route.output_min == 0.2
    assert route.output_max == 0.8
    assert route.curve == "smoothstep"
    assert matrix.outputs() == {}

def test_modulation_registry_exposes_visual_and_auto_performance_targets() -> None:
    expected = {
        "selected_layer.scale",
        "selected_layer.position_x",
        "generator.animation_speed",
        "generator.text_animation_speed",
        "generator.text_animation_amount",
        "generator.waveform_frequency",
        "generator.particle_speed",
        "overlay.playback_speed",
        "automation.clip_switch_probability",
        "automation.layout_interval",
        "automation.effect_interval",
        "automation.generator_interval",
    }
    assert expected.issubset(TARGET_SPECS)
    route = ModulationRoute(
        "audio-to-text-motion",
        "audio.high",
        "generator.text_animation_amount",
    ).normalize()
    assert route.output_min == pytest.approx(0.0)
    assert route.output_max == pytest.approx(0.18)

