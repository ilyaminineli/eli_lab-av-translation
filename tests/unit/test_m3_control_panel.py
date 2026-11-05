from __future__ import annotations

from core.application import Application
from ui.performance_control_panel import PerformanceControlPanel


def test_performance_control_panel_exposes_transport_audio_and_route_controls(qtbot) -> None:
    application = Application()
    try:
        panel = PerformanceControlPanel(application)
        qtbot.addWidget(panel)

        assert panel.bpm_spin.value() == 120.0
        assert panel.meter_combo.currentData() == 4
        assert panel.scene_combo.count() >= 16
        assert panel.source_combo.findData("audio.low") >= 0
        assert panel.target_combo.findData("master.grain") >= 0
        assert panel.input_min_spin.value() == 0.0
        assert panel.input_max_spin.value() == 1.0

        panel.bpm_spin.setValue(92.0)
        assert application.transport.bpm == 92.0
        panel.meter_combo.setCurrentIndex(panel.meter_combo.findData(7))
        assert application.transport.beats_per_bar == 7

        panel.source_combo.setCurrentIndex(panel.source_combo.findData("audio.rms"))
        panel.target_combo.setCurrentIndex(panel.target_combo.findData("master.grain"))
        panel.output_min_spin.setValue(0.1)
        panel.output_max_spin.setValue(0.8)
        panel.add_route_button.click()
        assert len(application.modulation.routes) == 1
        assert application.modulation.routes[0].target_id == "master.grain"

        panel.route_list.setCurrentRow(0)
        panel.output_max_spin.setValue(0.6)
        panel.add_route_button.click()
        assert application.modulation.routes[0].output_max == 0.6
    finally:
        application.shutdown()


def test_selected_layer_lock_checkbox_disables_layer_editors(qtbot) -> None:
    from ui.layer_panel import LayerPanel

    application = Application()
    try:
        layer = application.add_generator_layer("geometry")
        panel = LayerPanel(application)
        qtbot.addWidget(panel)

        panel.select_layer(layer.id)
        assert panel.transform_group.isEnabled()
        panel.layer_lock_check.setChecked(True)

        assert layer.locked is True
        assert panel.transform_group.isEnabled() is False
        assert panel.layer_fx_group.isEnabled() is False

        panel.layer_lock_check.setChecked(False)
        assert layer.locked is False
        assert panel.transform_group.isEnabled() is True
    finally:
        application.shutdown()

def test_performance_panel_surfaces_sonic_pi_and_reactive_route_presets(qtbot) -> None:
    from core.modulation import ModulationRoute

    application = Application()
    try:
        panel = PerformanceControlPanel(application)
        qtbot.addWidget(panel)

        assert "SONIC PI" in panel.osc_group.title()
        assert panel.osc_start_button.text() == "START OSC RECEIVER"
        assert panel.osc_port_spin.value() == 57121
        assert panel.source_combo.findData("macro.energy") >= 0
        assert panel.source_combo.findData("macro.cutoff") >= 0
        assert panel.source_combo.findData("transport.beat_pulse") >= 0
        assert panel.source_combo.findData("transport.downbeat_pulse") >= 0
        assert panel.source_combo.findData("transport.phrase_pulse") >= 0
        assert panel.target_combo.findData("generator.text_animation_amount") >= 0
        assert panel.target_combo.findData("automation.clip_switch_probability") >= 0
        assert panel.audio_attack_spin is not panel.attack_spin
        assert panel.audio_release_spin is not panel.release_spin

        layout = panel.scroll.widget().layout()
        group_positions = [
            next(i for i in range(layout.count()) if layout.itemAt(i).widget() is group)
            for group in (panel.osc_group, panel.scene_group)
        ]
        assert group_positions[0] < group_positions[1]

        panel.audio_reactive_button.click()
        targets = {route.target_id for route in application.modulation.routes}
        assert {
            "generator.animation_speed",
            "generator.density",
            "generator.text_animation_amount",
            "automation.cut_interval",
            "automation.clip_switch_probability",
            "selected_layer.opacity",
        }.issubset(targets)

        custom = ModulationRoute(
            "operator-authored-loop-route",
            "audio.low",
            "automation.loop_probability",
            output_min=0.35,
            output_max=0.7,
        )
        application.add_modulation_route(custom)
        panel.sonic_pi_reactive_button.click()
        preserved = next(
            route for route in application.modulation.routes
            if route.target_id == "automation.loop_probability"
        )
        assert preserved.source_id == "audio.low"
        assert preserved.output_min == 0.35
        assert "existing custom route(s) preserved" in panel.modulation_status.text()
    finally:
        application.shutdown()

def test_layer_stack_exposes_resizable_table_and_effect_sections(qtbot) -> None:
    from PySide6.QtCore import Qt

    from ui.layer_panel import LayerPanel

    application = Application()
    try:
        panel = LayerPanel(application)
        qtbot.addWidget(panel)
        assert panel.panel_splitter.orientation() == Qt.Orientation.Vertical
        assert panel.panel_splitter.count() == 2
        assert panel.panel_splitter.widget(0) is panel.table
        assert panel.panel_splitter.widget(1) is panel.controls_scroll
    finally:
        application.shutdown()

def test_layer_panel_adds_rhythmic_modifiers_to_selected_generator(qtbot) -> None:
    from ui.layer_panel import LayerPanel

    application = Application()
    try:
        geometry = application.add_generator_layer("geometry")
        text_layer = application.add_generator_layer("text")
        panel = LayerPanel(application)
        qtbot.addWidget(panel)

        panel.select_layer(geometry.id)
        assert panel.performance_modifiers_group.isEnabled()
        panel.modifier_beat_button.click()

        assert len(geometry.performance_modifiers) == 1
        geometry_modifier = geometry.performance_modifiers[0]
        assert geometry_modifier["source_id"] == "transport.beat_pulse"
        assert geometry_modifier["target_id"] == "generator.animation_amount"
        assert geometry_modifier["depth"] == 0.1
        assert panel.modifier_list.count() == 1

        panel.select_layer(text_layer.id)
        panel.modifier_phrase_button.click()
        text_modifier = text_layer.performance_modifiers[0]
        assert text_modifier["source_id"] == "transport.phrase_pulse"
        assert text_modifier["target_id"] == "generator.letter_spacing"
        assert text_modifier["depth"] == 0.34

        # Text animation amount becomes available once a text motion mode is enabled.
        text_layer.generator_settings["text_animation"] = "line_wave"
        panel.refresh()
        panel.select_layer(text_layer.id)
        assert panel.modifier_target_combo.findData("generator.text_animation_amount") >= 0

        panel.refresh_performance_modifiers()
        assert panel.modifier_list.count() == 1
        assert "BEAT" in panel.modifier_rhythm_status.text()
    finally:
        application.shutdown()

def test_layer_modifier_targets_only_offer_animated_overlay_playback(qtbot) -> None:
    from core.composition import Layer
    from ui.layer_panel import LayerPanel

    class AnimatedImageStub:
        animated = True

        def close(self) -> None:
            pass

    application = Application()
    try:
        overlay = Layer(
            id="overlay-target-filter",
            name="Still overlay",
            source_type="overlay",
            source_id="overlay:still",
            overlay_kind="image",
        )
        application.composition.add_layer(overlay)
        panel = LayerPanel(application)
        qtbot.addWidget(panel)

        still_targets = set(panel._modifier_targets_for_layer(overlay))
        assert "layer.opacity" in still_targets
        assert "overlay.playback_speed" not in still_targets

        application._overlay_images[overlay.id] = AnimatedImageStub()
        animated_targets = set(panel._modifier_targets_for_layer(overlay))
        assert "overlay.playback_speed" in animated_targets
        assert "overlay.frame_hold" in animated_targets
    finally:
        application.shutdown()

def test_modulator_bank_panel_loads_preset_and_assigns_to_selected_layer(qtbot) -> None:
    from ui.modulator_bank_panel import ModulatorBankPanel

    application = Application()
    try:
        layer = application.add_generator_layer("geometry")
        application.set_selected_layer_id(layer.id)
        panel = ModulatorBankPanel(application)
        qtbot.addWidget(panel)

        preset_index = panel.preset_combo.findData("lfo-sine-swell")
        assert preset_index >= 0
        panel.preset_combo.setCurrentIndex(preset_index)
        panel._load_preset()

        definition = panel._selected_definition()
        assert definition is not None
        assert definition.kind == "lfo"
        assert definition.waveform == "sine"
        assert panel.assignment_target_combo.currentData() == (
            "generator.animation_amount"
        )

        panel._assign_selected()

        assert len(layer.performance_modifiers) == 1
        assignment = layer.performance_modifiers[0]
        assert assignment["source_id"] == f"modulator.{definition.modulator_id}"
        assert assignment["target_id"] == "generator.animation_amount"
        assert assignment["polarity"] == "bipolar"
    finally:
        application.shutdown()


def test_layer_panel_lists_active_bank_modulators_as_sources(qtbot) -> None:
    from core.modulator_bank import ModulatorDefinition
    from ui.layer_panel import LayerPanel

    application = Application()
    try:
        layer = application.add_generator_layer("geometry")
        application.set_selected_layer_id(layer.id)
        definition = ModulatorDefinition(
            modulator_id="bank-ui-source",
            name="My slow LFO",
            kind="lfo",
        )
        application.add_modulator(definition)
        panel = LayerPanel(application)
        qtbot.addWidget(panel)

        panel.sync_performance_modifier_sources()

        assert panel.modifier_source_combo.findData(
            "modulator.bank-ui-source"
        ) >= 0
        assert panel.modifier_source_combo.currentText() != ""
    finally:
        application.shutdown()

def test_sonic_pi_cutoff_follower_assigns_to_waveform_frequency(qtbot) -> None:
    from ui.modulator_bank_panel import ModulatorBankPanel

    application = Application()
    try:
        layer = application.add_generator_layer("waveform")
        application.set_selected_layer_id(layer.id)
        panel = ModulatorBankPanel(application)
        qtbot.addWidget(panel)

        panel._create_modulator("follower")
        definition = panel._selected_definition()
        assert definition is not None
        assert definition.kind == "follower"

        panel.input_source_combo.setCurrentIndex(
            panel.input_source_combo.findData("macro.cutoff")
        )
        panel.input_attack_spin.setValue(50.0)
        panel.input_release_spin.setValue(250.0)
        panel._apply_editor()

        target_index = panel.assignment_target_combo.findData(
            "generator.waveform_frequency"
        )
        assert target_index >= 0
        panel.assignment_target_combo.setCurrentIndex(target_index)
        panel.assignment_depth.setValue(35)
        panel._assign_selected()

        assert len(layer.performance_modifiers) == 1
        assignment = layer.performance_modifiers[0]
        assert assignment["source_id"] == f"modulator.{definition.modulator_id}"
        assert assignment["target_id"] == "generator.waveform_frequency"
        assert assignment["polarity"] == "positive"
        assert application.modulator_bank.get(
            definition.modulator_id
        ).input_source == "macro.cutoff"
    finally:
        application.shutdown()

def test_performance_matrix_exposes_modulator_bank_sources(qtbot) -> None:
    from core.modulator_bank import ModulatorDefinition

    application = Application()
    try:
        definition = ModulatorDefinition(
            modulator_id="global-matrix-lfo",
            name="Global motion LFO",
            kind="lfo",
        )
        application.add_modulator(definition)
        panel = PerformanceControlPanel(application)
        qtbot.addWidget(panel)

        panel.sync_modulator_sources()

        source_id = f"modulator.{definition.modulator_id}"
        assert panel.source_combo.findData(source_id) >= 0
        panel.source_combo.setCurrentIndex(panel.source_combo.findData(source_id))
        panel.target_combo.setCurrentIndex(
            panel.target_combo.findData("master.grain")
        )
        panel.add_route_button.click()

        route = next(
            route for route in application.modulation.routes
            if route.source_id == source_id
        )
        assert route.target_id == "master.grain"
        assert source_id in panel.route_list.item(0).text()
        assert "Global motion LFO" in panel.route_list.item(0).text()
    finally:
        application.shutdown()

