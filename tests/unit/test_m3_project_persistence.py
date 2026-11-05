from __future__ import annotations

from core.application import Application
from core.audio_analysis import AudioAnalysisSettings
from core.modulation import ModulationRoute
from core.scene_profiles import SceneProfile


def test_application_round_trips_m3_profiles_routes_and_analysis_settings(tmp_path) -> None:
    application = Application()
    path = tmp_path / "m3-settings.eliav"
    try:
        application.transport.set_tempo(92.0)
        application.transport.set_meter(4)
        application.update_audio_analysis_settings(AudioAnalysisSettings(
            sensitivity=3.2,
            attack_ms=12.0,
            release_ms=420.0,
            beat_confidence_min=0.6,
        ))
        application.add_modulation_route(ModulationRoute(
            route_id="energy-grain",
            source_id="macro.energy",
            target_id="master.grain",
            input_min=0.1,
            input_max=0.9,
            output_min=0.05,
            output_max=0.8,
            curve="smoothstep",
            attack_ms=40.0,
            release_ms=500.0,
            hold_ms=120.0,
        ))
        application.update_scene_profile(SceneProfile(
            scene_id="dev",
            label="Development",
            intensity=0.73,
            master_look="Cold Steel",
            palette="Ai · 藍",
        ))
        application.save_project(path)

        application.transport.set_tempo(140.0)
        application.update_audio_analysis_settings(AudioAnalysisSettings())
        application.modulation.load_dict([])
        application.update_scene_profile(SceneProfile(
            scene_id="dev",
            label="Development",
            intensity=0.1,
            master_look="Clean",
            palette="Sumi · 墨",
        ))

        application.load_project(path)

        assert application.transport.bpm == 92.0
        assert application.transport.beats_per_bar == 4
        assert application.performance_control.bpm == 92.0
        assert application.audio_capture.settings.sensitivity == 3.2
        assert application.audio_capture.settings.attack_ms == 12.0
        assert application.audio_capture.settings.release_ms == 420.0
        assert application.audio_capture.settings.beat_confidence_min == 0.6

        route = application.modulation.routes[0]
        assert route.route_id == "energy-grain"
        assert route.source_id == "macro.energy"
        assert route.target_id == "master.grain"
        assert route.curve == "smoothstep"
        assert route.hold_ms == 120.0

        profile = application.scene_profiles.get("dev")
        assert profile.intensity == 0.73
        assert profile.master_look == "Cold Steel"
        assert profile.palette == "Ai · 藍"
        assert application.audio_capture.state.value == "stopped"
        assert application.audio_capture.latest_frame() is None
    finally:
        application.shutdown()


def test_older_project_without_m3_settings_restores_default_control_configuration(tmp_path) -> None:
    application = Application()
    path = tmp_path / "legacy-control.eliav"
    try:
        application.transport.set_tempo(144.0)
        application.update_audio_analysis_settings(AudioAnalysisSettings(
            sensitivity=9.0,
        ))
        application.modulation.add_route(ModulationRoute(
            route_id="temporary",
            source_id="audio.rms",
            target_id="master.grain",
        ))
        application.project_manager.save(
            path,
            application.composition,
            [deck.to_dict() for deck in application.decks.values()],
            app_state={
                "effects": {},
                "automation_settings": {},
            },
        )

        application.load_project(path)

        assert application.transport.bpm == 120.0
        assert application.transport.beats_per_bar == 4
        assert application.audio_capture.settings.sensitivity == 1.8
        assert application.modulation.routes == []
        assert application.scene_profiles.get("in").scene_id == "in"
    finally:
        application.shutdown()

def test_application_round_trips_modulator_bank_followers_presets_and_assignments(tmp_path) -> None:
    from core.modulator_bank import ModulatorDefinition
    from core.performance_modifiers import LayerPerformanceModifier

    application = Application()
    path = tmp_path / "modulator-bank.eliav"
    try:
        layer = application.add_generator_layer("waveform")
        definition = ModulatorDefinition(
            modulator_id="saved-sonata-cutoff",
            name="SONATA cutoff",
            kind="follower",
            input_source="macro.cutoff",
            input_attack_ms=55.0,
            input_release_ms=340.0,
        )
        application.add_modulator(definition)
        preset_id = application.apply_modulator_preset(
            definition.modulator_id,
            "SONATA cutoff to waveform",
        )
        application.add_layer_performance_modifier(
            layer.id,
            LayerPerformanceModifier(
                modifier_id="saved-cutoff-frequency",
                name="Cutoff → waveform frequency",
                source_id=f"modulator.{definition.modulator_id}",
                target_id="generator.waveform_frequency",
                depth=0.35,
                polarity="positive",
                curve="linear",
            ),
        )
        application.save_project(path)

        application.remove_modulator(definition.modulator_id)
        application.delete_modulator_preset(preset_id)
        application.load_project(path)

        restored = application.modulator_bank.get(definition.modulator_id)
        assert restored is not None
        assert restored.kind == "follower"
        assert restored.input_source == "macro.cutoff"
        assert restored.input_attack_ms == 55.0
        assert restored.input_release_ms == 340.0
        assert application.modulator_bank.presets[preset_id].name == (
            "SONATA cutoff to waveform"
        )

        restored_layer = application.composition.get_layer(layer.id)
        assert restored_layer is not None
        assert restored_layer.performance_modifiers[0]["source_id"] == (
            f"modulator.{definition.modulator_id}"
        )
        assert restored_layer.performance_modifiers[0]["target_id"] == (
            "generator.waveform_frequency"
        )
    finally:
        application.shutdown()

