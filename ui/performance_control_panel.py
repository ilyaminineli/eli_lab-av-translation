from __future__ import annotations

import time
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.application import Application
from core.audio_analysis import AudioAnalysisSettings
from core.audio_capture import AudioCaptureState
from core.modulation import (
    TARGET_SPECS,
    ModulationRoute,
)
from core.scene_profiles import SceneProfile
from generators.palettes import palette_names


class PerformanceControlPanel(QWidget):
    """Internal transport, audio-analysis monitor, scene profiles and modulation UI."""

    def __init__(self, application: Application, parent=None) -> None:
        super().__init__(parent)
        self.application = application
        self._loading = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.transport_group = QGroupBox("INTERNAL TRANSPORT / TEST CLOCK")
        transport_form = QFormLayout(self.transport_group)
        self.bpm_spin = QDoubleSpinBox()
        self.bpm_spin.setRange(20.0, 300.0)
        self.bpm_spin.setDecimals(1)
        self.bpm_spin.setSingleStep(1.0)
        self.bpm_spin.setValue(self.application.transport.bpm)
        self.meter_combo = QComboBox()
        for meter in (3, 4, 5, 6, 7, 8, 12):
            self.meter_combo.addItem(f"{meter}/4", meter)
        self.meter_combo.setCurrentIndex(
            max(0, self.meter_combo.findData(self.application.transport.beats_per_bar))
        )
        transport_form.addRow("TEMPO", self.bpm_spin)
        transport_form.addRow("METER", self.meter_combo)
        transport_buttons = QHBoxLayout()
        self.transport_start_button = QPushButton("START")
        self.transport_pause_button = QPushButton("PAUSE")
        self.transport_resume_button = QPushButton("RESUME")
        self.transport_stop_button = QPushButton("STOP")
        transport_buttons.addWidget(self.transport_start_button)
        transport_buttons.addWidget(self.transport_pause_button)
        transport_buttons.addWidget(self.transport_resume_button)
        transport_buttons.addWidget(self.transport_stop_button)
        transport_form.addRow(transport_buttons)
        self.transport_status = QLabel("STOP · INTERNAL · 120 BPM")
        self.transport_status.setWordWrap(True)
        transport_form.addRow("CLOCK", self.transport_status)
        root.addWidget(self.transport_group)

        self.scene_group = QGroupBox("SCENE PROFILES")
        scene_form = QFormLayout(self.scene_group)
        self.scene_combo = QComboBox()
        for profile in self.application.scene_profiles.all():
            self.scene_combo.addItem(
                f"{profile.label} · {profile.scene_id}",
                profile.scene_id,
            )
        self.scene_intensity_spin = self._float_spin(0.0, 1.0, 0.01, 0.01)
        self.scene_look_combo = QComboBox()
        from effects.settings import PRESETS
        self.scene_look_combo.addItems(list(PRESETS))
        self.scene_palette_combo = QComboBox()
        self.scene_palette_combo.addItems(palette_names())
        self.quantization_combo = QComboBox()
        self.quantization_combo.addItem("Immediate", "immediate")
        self.quantization_combo.addItem("Next beat", "beat")
        self.quantization_combo.addItem("Next bar", "bar")
        self.quantization_combo.addItem("Next phrase · 4 bars", "phrase")
        self.quantization_combo.setCurrentIndex(2)
        self.scene_apply_button = QPushButton("APPLY SCENE")
        self.scene_save_button = QPushButton("SAVE PROFILE")
        self.scene_buttons = QHBoxLayout()
        self.scene_buttons.addWidget(self.scene_apply_button)
        self.scene_buttons.addWidget(self.scene_save_button)
        scene_form.addRow("SCENE", self.scene_combo)
        scene_form.addRow("INTENSITY", self.scene_intensity_spin)
        scene_form.addRow("MASTER LOOK", self.scene_look_combo)
        scene_form.addRow("COLOUR PALETTE", self.scene_palette_combo)
        scene_form.addRow("QUANTIZE", self.quantization_combo)
        scene_form.addRow(self.scene_buttons)
        root.addWidget(self.scene_group)

        self.audio_group = QGroupBox("AUDIO INPUT / SYSTEM LOOPBACK")
        audio_layout = QVBoxLayout(self.audio_group)
        device_row = QHBoxLayout()
        self.audio_device_combo = QComboBox()
        self.audio_refresh_button = QPushButton("REFRESH")
        device_row.addWidget(self.audio_device_combo, 1)
        device_row.addWidget(self.audio_refresh_button)
        audio_layout.addLayout(device_row)
        audio_buttons = QHBoxLayout()
        self.audio_start_button = QPushButton("START INPUT")
        self.audio_stop_button = QPushButton("STOP INPUT")
        self.audio_stop_button.setEnabled(False)
        audio_buttons.addWidget(self.audio_start_button)
        audio_buttons.addWidget(self.audio_stop_button)
        audio_layout.addLayout(audio_buttons)

        analysis_form = QFormLayout()
        audio_settings = self.application.audio_capture.settings
        self.sensitivity_spin = self._float_spin(
            0.1, 12.0, 0.1, audio_settings.sensitivity
        )
        self.attack_spin = self._float_spin(
            1.0, 1000.0, 1.0, audio_settings.attack_ms
        )
        self.release_spin = self._float_spin(
            5.0, 3000.0, 5.0, audio_settings.release_ms
        )
        analysis_form.addRow("SENSITIVITY", self.sensitivity_spin)
        analysis_form.addRow("ATTACK · ms", self.attack_spin)
        analysis_form.addRow("RELEASE · ms", self.release_spin)
        audio_layout.addLayout(analysis_form)

        self._audio_discovery_error = ""
        self._last_device_poll = 0.0
        self.audio_state_label = QLabel("Audio disabled · video continues independently.")
        self.audio_state_label.setWordWrap(True)
        audio_layout.addWidget(self.audio_state_label)
        self.audio_meter_bars: dict[str, QProgressBar] = {}
        for key, label in (
            ("rms", "RMS / ENERGY"),
            ("low", "LOW"),
            ("mid", "MID"),
            ("high", "HIGH"),
            ("onset", "ONSET"),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setMaximumHeight(12)
            row.addWidget(bar, 1)
            self.audio_meter_bars[key] = bar
            audio_layout.addLayout(row)
        self.audio_tempo_label = QLabel("Tempo estimate · —")
        audio_layout.addWidget(self.audio_tempo_label)
        root.addWidget(self.audio_group)

        self.modulation_group = QGroupBox("MODULATION MATRIX")
        modulation_layout = QVBoxLayout(self.modulation_group)
        route_form = QFormLayout()
        self.source_combo = QComboBox()
        self.source_labels = {
            "audio.rms": "Audio · RMS",
            "audio.peak": "Audio · Peak",
            "audio.low": "Audio · Low band",
            "audio.mid": "Audio · Mid band",
            "audio.high": "Audio · High band",
            "audio.onset": "Audio · Onset",
            "audio.beat_confidence": "Audio · Beat confidence",
            "audio.bpm_normalized": "Audio · Tempo",
            "transport.intensity": "Transport · Scene intensity",
            "transport.phase": "Transport · Beat phase",
            "macro.energy": "Macro · Energy",
            "macro.cutoff": "Macro · Cutoff",
        }
        for source_id, label in self.source_labels.items():
            self.source_combo.addItem(label, source_id)
        self.target_combo = QComboBox()
        for target_id, spec in TARGET_SPECS.items():
            self.target_combo.addItem(spec.label, target_id)
        self.curve_combo = QComboBox()
        self.curve_combo.addItem("Linear", "linear")
        self.curve_combo.addItem("Smoothstep", "smoothstep")
        self.curve_combo.addItem("Exponential", "exponential")
        self.invert_check = QCheckBox("Invert")
        self.input_min_spin = self._float_spin(0.0, 1.0, 0.01, 0.0)
        self.input_max_spin = self._float_spin(0.0, 1.0, 0.01, 1.0)
        self.output_min_spin = self._float_spin(-180.0, 180.0, 0.01, 0.0)
        self.output_max_spin = self._float_spin(-180.0, 180.0, 0.01, 1.0)
        self.ceiling_spin = self._float_spin(0.0, 1.0, 0.01, 1.0)
        self.smoothing_spin = self._float_spin(0.0, 3000.0, 5.0, 80.0)
        self.attack_spin = self._float_spin(1.0, 2000.0, 5.0, 25.0)
        self.release_spin = self._float_spin(1.0, 5000.0, 5.0, 220.0)
        self.hold_spin = self._float_spin(0.0, 5000.0, 10.0, 0.0)
        route_form.addRow("SOURCE", self.source_combo)
        route_form.addRow("TARGET", self.target_combo)
        route_form.addRow("CURVE", self.curve_combo)
        route_form.addRow("INPUT MIN", self.input_min_spin)
        route_form.addRow("INPUT MAX", self.input_max_spin)
        route_form.addRow("OUTPUT MIN", self.output_min_spin)
        route_form.addRow("OUTPUT MAX", self.output_max_spin)
        route_form.addRow("INTENSITY CEILING", self.ceiling_spin)
        route_form.addRow("SMOOTHING · ms", self.smoothing_spin)
        route_form.addRow("ATTACK · ms", self.attack_spin)
        route_form.addRow("RELEASE · ms", self.release_spin)
        route_form.addRow("HOLD · ms", self.hold_spin)
        route_form.addRow(self.invert_check)
        modulation_layout.addLayout(route_form)
        route_buttons = QHBoxLayout()
        self.new_route_button = QPushButton("NEW ROUTE")
        self.add_route_button = QPushButton("ADD / UPDATE ROUTE")
        self.remove_route_button = QPushButton("REMOVE ROUTE")
        route_buttons.addWidget(self.new_route_button)
        route_buttons.addWidget(self.add_route_button)
        route_buttons.addWidget(self.remove_route_button)
        modulation_layout.addLayout(route_buttons)
        self.route_list = QListWidget()
        self.route_list.setMaximumHeight(140)
        modulation_layout.addWidget(self.route_list)
        self.modulation_status = QLabel("No modulation routes enabled.")
        self.modulation_status.setWordWrap(True)
        modulation_layout.addWidget(self.modulation_status)
        root.addWidget(self.modulation_group)

        root.addStretch(1)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)

        self.transport_start_button.clicked.connect(self._start_transport)
        self.transport_pause_button.clicked.connect(self.application.pause_internal_transport)
        self.transport_resume_button.clicked.connect(self.application.resume_internal_transport)
        self.transport_stop_button.clicked.connect(self.application.stop_internal_transport)
        self.bpm_spin.valueChanged.connect(self.application.set_internal_tempo)
        self.meter_combo.currentIndexChanged.connect(self._meter_changed)
        self.scene_combo.currentIndexChanged.connect(self._load_scene_profile)
        self.scene_apply_button.clicked.connect(self._apply_scene)
        self.scene_save_button.clicked.connect(self._save_scene_profile)
        self.audio_refresh_button.clicked.connect(self.refresh_audio_devices)
        self.audio_start_button.clicked.connect(self._start_audio)
        self.audio_stop_button.clicked.connect(self.application.stop_audio_capture)
        self.sensitivity_spin.valueChanged.connect(self._audio_settings_changed)
        self.attack_spin.valueChanged.connect(self._audio_settings_changed)
        self.release_spin.valueChanged.connect(self._audio_settings_changed)
        self.target_combo.currentIndexChanged.connect(self._target_changed)
        self.new_route_button.clicked.connect(self._new_route)
        self.add_route_button.clicked.connect(self._add_route)
        self.remove_route_button.clicked.connect(self._remove_route)
        self.route_list.itemChanged.connect(self._route_enabled_changed)
        self.route_list.currentItemChanged.connect(self._load_route_editor)

        self._load_scene_profile()
        self._target_changed()
        self.refresh_audio_devices()
        self.refresh_routes()
        self.refresh_monitor()

    def sync_from_application(self) -> None:
        transport = self.application.transport
        self.bpm_spin.blockSignals(True)
        self.bpm_spin.setValue(transport.bpm)
        self.bpm_spin.blockSignals(False)
        self.meter_combo.blockSignals(True)
        index = self.meter_combo.findData(transport.beats_per_bar)
        self.meter_combo.setCurrentIndex(max(0, index))
        self.meter_combo.blockSignals(False)

        settings = self.application.audio_capture.settings
        for control, value in (
            (self.sensitivity_spin, settings.sensitivity),
            (self.attack_spin, settings.attack_ms),
            (self.release_spin, settings.release_ms),
        ):
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)

        self.scene_combo.blockSignals(True)
        self.scene_combo.clear()
        for profile in self.application.scene_profiles.all():
            self.scene_combo.addItem(
                f"{profile.label} · {profile.scene_id}",
                profile.scene_id,
            )
        self.scene_combo.blockSignals(False)
        scene_id = self.application.performance_control.scene_id
        if scene_id not in {profile.scene_id for profile in self.application.scene_profiles.all()}:
            scene_id = self.application.scene_profiles.all()[0].scene_id
        self.sync_scene_selection(scene_id)
        self.refresh_routes()
        self.refresh_audio_devices()
        self.refresh_monitor()

    @staticmethod
    def _float_spin(
            minimum: float,
            maximum: float,
            step: float,
            value: float,
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setDecimals(2 if step < 1 else 1)
        spin.setValue(value)
        return spin

    def _start_transport(self) -> None:
        self.application.start_internal_transport(
            self.bpm_spin.value(),
            int(self.meter_combo.currentData()),
        )

    def _meter_changed(self, _index: int) -> None:
        meter = self.meter_combo.currentData()
        if meter is not None:
            self.application.set_transport_meter(int(meter))

    def _selected_scene_id(self) -> str:
        return str(self.scene_combo.currentData() or "in")

    def sync_scene_selection(self, scene_id: str) -> None:
        index = self.scene_combo.findData(scene_id)
        if index < 0:
            self.scene_combo.addItem(scene_id.replace("_", " ").title(), scene_id)
            index = self.scene_combo.findData(scene_id)
        self.scene_combo.blockSignals(True)
        self.scene_combo.setCurrentIndex(index)
        self.scene_combo.blockSignals(False)
        self._load_scene_profile()

    def _load_scene_profile(self, *_args) -> None:
        if not hasattr(self, "scene_intensity_spin"):
            return
        profile = self.application.scene_profiles.get(self._selected_scene_id())
        self.scene_intensity_spin.blockSignals(True)
        self.scene_intensity_spin.setValue(profile.intensity)
        self.scene_intensity_spin.blockSignals(False)
        self.scene_look_combo.blockSignals(True)
        self.scene_look_combo.setCurrentText(profile.master_look)
        self.scene_look_combo.blockSignals(False)
        self.scene_palette_combo.blockSignals(True)
        self.scene_palette_combo.setCurrentText(profile.palette)
        self.scene_palette_combo.blockSignals(False)

    def _save_scene_profile(self) -> None:
        profile = self.application.scene_profiles.get(self._selected_scene_id())
        self.application.update_scene_profile(SceneProfile(
            scene_id=profile.scene_id,
            label=profile.label,
            intensity=self.scene_intensity_spin.value(),
            master_look=self.scene_look_combo.currentText(),
            palette=self.scene_palette_combo.currentText(),
        ))
        self.scene_save_button.setText("SAVED")
        self.scene_save_button.setEnabled(False)
        self.scene_save_button.setToolTip("Scene profile saved in the current project.")
        self.scene_save_button.setEnabled(True)
        self.scene_save_button.setText("SAVE PROFILE")

    def _apply_scene(self) -> None:
        self._save_scene_profile()
        self.application.request_scene_selection(
            self._selected_scene_id(),
            self.quantization_combo.currentData(),
        )

    def refresh_audio_devices(self) -> None:
        selected = self.audio_device_combo.currentData()
        self.audio_device_combo.blockSignals(True)
        self.audio_device_combo.clear()
        self.audio_device_combo.addItem("Deterministic test signal", "test")
        try:
            devices = self.application.audio_capture.list_devices()
            for device in devices:
                self.audio_device_combo.addItem(device.label, device.id)
            message = f"{len(devices)} audio input(s) available."
        except Exception as exc:
            message = f"Audio backend unavailable · {exc}"
            self._audio_discovery_error = str(exc)
        else:
            self._audio_discovery_error = ""
        index = self.audio_device_combo.findData(selected)
        self.audio_device_combo.setCurrentIndex(index if index >= 0 else 0)
        self.audio_device_combo.blockSignals(False)
        self.audio_state_label.setText(message)

    def _start_audio(self) -> None:
        source = self.audio_device_combo.currentData()
        try:
            self.application.update_audio_analysis_settings(
                AudioAnalysisSettings(
                    sensitivity=self.sensitivity_spin.value(),
                    attack_ms=self.attack_spin.value(),
                    release_ms=self.release_spin.value(),
                )
            )
            if source == "test":
                self.application.start_audio_capture(test_signal=True)
            elif source:
                self.application.start_audio_capture(device_id=str(source))
            else:
                raise RuntimeError("No audio input is selected.")
        except Exception as exc:
            self.audio_state_label.setText(f"Audio unavailable · {exc}")

    def _audio_settings_changed(self, *_args) -> None:
        self.application.update_audio_analysis_settings(AudioAnalysisSettings(
            sensitivity=self.sensitivity_spin.value(),
            attack_ms=self.attack_spin.value(),
            release_ms=self.release_spin.value(),
        ))

    def _target_changed(self, *_args) -> None:
        target_id = self.target_combo.currentData()
        spec = TARGET_SPECS.get(str(target_id))
        if spec is None:
            return
        self.output_min_spin.setRange(spec.minimum, spec.maximum)
        self.output_max_spin.setRange(spec.minimum, spec.maximum)
        self.output_min_spin.setValue(spec.minimum)
        self.output_max_spin.setValue(spec.maximum)

    def _add_route(self) -> None:
        source_id = str(self.source_combo.currentData())
        target_id = str(self.target_combo.currentData())
        selected = self.route_list.currentItem()
        if selected is None and any(
            route.target_id == target_id for route in self.application.modulation.routes
        ):
            self.modulation_status.setText(
                "That target already has a route. Select it to edit, or choose another target."
            )
            return
        try:
            changes = {
                "source_id": source_id,
                "target_id": target_id,
                "input_min": self.input_min_spin.value(),
                "input_max": self.input_max_spin.value(),
                "output_min": self.output_min_spin.value(),
                "output_max": self.output_max_spin.value(),
                "curve": str(self.curve_combo.currentData()),
                "inverted": self.invert_check.isChecked(),
                "smoothing_ms": self.smoothing_spin.value(),
                "attack_ms": self.attack_spin.value(),
                "release_ms": self.release_spin.value(),
                "hold_ms": self.hold_spin.value(),
                "intensity_ceiling": self.ceiling_spin.value(),
            }
            if selected is not None:
                route_id = str(selected.data(Qt.ItemDataRole.UserRole))
                self.application.update_modulation_route(route_id, changes)
            else:
                route = ModulationRoute(
                    route_id=uuid4().hex[:10],
                    **changes,
                )
                self.application.add_modulation_route(route)
            self.refresh_routes()
        except (ValueError, TypeError, KeyError) as exc:
            self.modulation_status.setText(f"Route not saved · {exc}")

    def _new_route(self) -> None:
        self.route_list.blockSignals(True)
        self.route_list.setCurrentRow(-1)
        self.route_list.blockSignals(False)
        self.source_combo.setCurrentIndex(0)
        self.target_combo.setCurrentIndex(0)
        self._target_changed()
        self.curve_combo.setCurrentIndex(0)
        self.input_min_spin.setValue(0.0)
        self.input_max_spin.setValue(1.0)
        self.ceiling_spin.setValue(1.0)
        self.smoothing_spin.setValue(80.0)
        self.attack_spin.setValue(25.0)
        self.release_spin.setValue(220.0)
        self.hold_spin.setValue(0.0)
        self.invert_check.setChecked(False)

    def _load_route_editor(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
            return
        route_id = current.data(Qt.ItemDataRole.UserRole)
        route = next(
            (item for item in self.application.modulation.routes if item.route_id == route_id),
            None,
        )
        if route is None:
            return
        controls = (
            (self.source_combo, route.source_id),
            (self.target_combo, route.target_id),
            (self.curve_combo, route.curve),
        )
        for control, value in controls:
            control.blockSignals(True)
            control.setCurrentIndex(max(0, control.findData(value)))
            control.blockSignals(False)
        self._target_changed()
        for control, value in (
            (self.input_min_spin, route.input_min),
            (self.input_max_spin, route.input_max),
            (self.output_min_spin, route.output_min),
            (self.output_max_spin, route.output_max),
            (self.ceiling_spin, route.intensity_ceiling),
            (self.smoothing_spin, route.smoothing_ms),
            (self.attack_spin, route.attack_ms),
            (self.release_spin, route.release_ms),
            (self.hold_spin, route.hold_ms),
        ):
            control.setValue(value)
        self.invert_check.setChecked(route.inverted)

    def _remove_route(self) -> None:
        item = self.route_list.currentItem()
        if item is None:
            return
        route_id = item.data(Qt.ItemDataRole.UserRole)
        self.application.remove_modulation_route(str(route_id))
        self.refresh_routes()

    def _route_enabled_changed(self, item: QListWidgetItem) -> None:
        route_id = item.data(Qt.ItemDataRole.UserRole)
        route = next(
            (item for item in self.application.modulation.routes if item.route_id == route_id),
            None,
        )
        if route is not None:
            route.enabled = item.checkState() == Qt.CheckState.Checked
            self.application.events.publish("performance.modulation.updated")
            self.application.apply_modulation()

    def refresh_routes(self) -> None:
        self.route_list.blockSignals(True)
        self.route_list.clear()
        for route in self.application.modulation.routes:
            item = QListWidgetItem(
                f"{self.source_labels.get(route.source_id, route.source_id)}  →  "
                f"{TARGET_SPECS[route.target_id].label}"
            )
            item.setData(Qt.ItemDataRole.UserRole, route.route_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if route.enabled else Qt.CheckState.Unchecked
            )
            self.route_list.addItem(item)
        self.route_list.blockSignals(False)

    def refresh_monitor(self) -> None:
        transport = self.application.transport
        transport_state = (
            "RUN" if transport.running and not transport.paused
            else "PAUSE" if transport.paused
            else "STOP"
        )
        self.transport_status.setText(
            f"{transport_state} · {transport.bpm:g} BPM · BAR {transport.bar_index} · "
            f"BEAT {transport.beat_index + 1}/{transport.beats_per_bar} · "
            f"PHRASE {transport.phrase_index}"
        )
        state = self.application.audio_capture.state
        if (
            self.application.audio_capture.source_kind in {"input", "loopback"}
            and state == AudioCaptureState.RUNNING
            and time.monotonic() - self._last_device_poll >= 3.0
        ):
            self._last_device_poll = time.monotonic()
            self.application.audio_capture.refresh_device_state()
            state = self.application.audio_capture.state
        name = self.application.audio_capture.selected_device_name
        error = self.application.audio_capture.error or self._audio_discovery_error
        self.audio_state_label.setText(
            f"{state.value.upper()} · {name or 'No source'}"
            + (f" · {error}" if error else "")
        )
        active = state in {AudioCaptureState.RUNNING, AudioCaptureState.STARTING}
        self.audio_start_button.setEnabled(not active)
        self.audio_stop_button.setEnabled(active or state == AudioCaptureState.ERROR)
        features = self.application.audio_analysis_snapshot()
        for key, bar in self.audio_meter_bars.items():
            bar.setValue(round(float(features.get(key, 0.0) or 0.0) * 100))
        bpm = features.get("bpm")
        confidence = float(features.get("beat_confidence", 0.0) or 0.0)
        self.audio_tempo_label.setText(
            f"Tempo estimate · {bpm:g} BPM · confidence {confidence:.2f}"
            if bpm is not None else "Tempo estimate · listening for transients…"
        )
        outputs = self.application.modulation.outputs()
        self.modulation_status.setText(
            " · ".join(
                f"{TARGET_SPECS[key].label}: {value:.2f}"
                for key, value in outputs.items()
            )
            if outputs else "No modulation outputs active. Enable audio or select a control source."
        )
