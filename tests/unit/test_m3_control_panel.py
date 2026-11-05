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
