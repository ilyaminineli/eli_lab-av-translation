from __future__ import annotations

import json
import math
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

PERFORMANCE_SET_FORMAT = "eli_lab_performance_set"
PERFORMANCE_SET_VERSION = 1


@dataclass
class MIDIMapping:
    """Stable MIDI-to-performance binding with scaling and pickup semantics."""

    mapping_id: str = field(default_factory=lambda: uuid4().hex[:12])
    device_id: str = "*"
    channel: int = 0
    message: str = "cc"
    number: int = 1
    target: str = "macro.energy"
    minimum: float = 0.0
    maximum: float = 1.0
    curve: str = "linear"
    pickup: bool = True
    enabled: bool = True
    last_physical: float | None = None

    def normalize(self) -> None:
        self.mapping_id = str(self.mapping_id).strip()[:40] or uuid4().hex[:12]
        self.device_id = str(self.device_id).strip()[:128] or "*"
        self.channel = max(0, min(15, int(self.channel)))
        if self.message not in {"cc", "note", "pitch"}:
            raise ValueError("MIDI message must be cc, note or pitch.")
        self.number = max(0, min(127, int(self.number)))
        self.target = str(self.target).strip()[:128]
        if not self.target:
            raise ValueError("MIDI mapping target cannot be empty.")
        self.minimum = float(self.minimum)
        self.maximum = float(self.maximum)
        if not math.isfinite(self.minimum) or not math.isfinite(self.maximum):
            raise ValueError("MIDI mapping range must be finite.")
        if self.maximum <= self.minimum:
            raise ValueError("MIDI mapping maximum must exceed minimum.")
        if self.curve not in {"linear", "smoothstep", "exponential"}:
            self.curve = "linear"
        if self.last_physical is not None:
            value = float(self.last_physical)
            self.last_physical = max(0.0, min(1.0, value)) if math.isfinite(value) else None
        self.enabled = bool(self.enabled)
        self.pickup = bool(self.pickup)

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        value = asdict(self)
        value.pop("last_physical", None)  # pickup runtime is deliberately transient
        return value

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MIDIMapping":
        allowed = set(cls.__dataclass_fields__)
        mapping = cls(**{k: v for k, v in data.items() if k in allowed})
        mapping.normalize()
        return mapping


class MIDIMappingEngine:
    """Pure MIDI event mapper; device/port ownership belongs to an adapter."""

    def __init__(self) -> None:
        self.mappings: list[MIDIMapping] = []
        self._pickup_armed: dict[str, bool] = {}
        self._last_values: dict[str, float] = {}

    def replace_mappings(self, mappings: list[MIDIMapping | dict[str, Any]]) -> None:
        normalized: list[MIDIMapping] = []
        seen: set[str] = set()
        for raw in mappings:
            item = raw if isinstance(raw, MIDIMapping) else MIDIMapping.from_dict(raw)
            item.normalize()
            if item.mapping_id in seen:
                raise ValueError(f"Duplicate MIDI mapping ID: {item.mapping_id}")
            seen.add(item.mapping_id)
            normalized.append(item)
        self.mappings = normalized
        self._pickup_armed.clear()
        self._last_values.clear()

    @staticmethod
    def _shape(value: float, curve: str) -> float:
        value = max(0.0, min(1.0, value))
        if curve == "smoothstep":
            return value * value * (3.0 - 2.0 * value)
        if curve == "exponential":
            return value * value
        return value

    def process(self, device_id: str, message: str, channel: int, number: int,
                value: float, current_targets: dict[str, float] | None = None
                ) -> list[tuple[str, float]]:
        """Return target/value pairs for one normalized MIDI event."""
        raw = float(value)
        if not math.isfinite(raw):
            return []
        physical = max(0.0, min(1.0, raw))
        output: list[tuple[str, float]] = []
        current_targets = current_targets or {}
        for mapping in self.mappings:
            if not mapping.enabled:
                continue
            if mapping.device_id not in {"*", str(device_id)}:
                continue
            if (mapping.message, mapping.channel, mapping.number) != (
                    message, int(channel), int(number)):
                continue
            previous = self._last_values.get(mapping.mapping_id)
            self._last_values[mapping.mapping_id] = physical
            if mapping.pickup:
                target = current_targets.get(mapping.target)
                if target is not None:
                    normalized_target = (float(target) - mapping.minimum) / (
                        mapping.maximum - mapping.minimum
                    )
                    crossed = (
                        previous is not None
                        and (previous - normalized_target) *
                            (physical - normalized_target) <= 0
                    )
                    close = abs(physical - normalized_target) <= 0.015
                    armed = self._pickup_armed.get(mapping.mapping_id, False)
                    if not (armed or crossed or close):
                        continue
                    self._pickup_armed[mapping.mapping_id] = True
            shaped = self._shape(physical, mapping.curve)
            mapped = mapping.minimum + shaped * (mapping.maximum - mapping.minimum)
            output.append((mapping.target, mapped))
            mapping.last_physical = physical
        return output

    def to_dict(self) -> list[dict[str, Any]]:
        return [mapping.to_dict() for mapping in self.mappings]

    def load_dict(self, values: object) -> None:
        if not isinstance(values, list):
            self.replace_mappings([])
            return
        self.replace_mappings([item for item in values if isinstance(item, dict)])


@dataclass
class PerformanceScene:
    scene_id: str
    label: str
    snapshot: dict[str, Any]
    cue: str = ""

    def normalize(self) -> None:
        self.scene_id = str(self.scene_id).strip()[:64]
        self.label = str(self.label).strip()[:80] or self.scene_id
        self.cue = str(self.cue).strip()[:128]
        if not self.scene_id:
            raise ValueError("Performance scene ID cannot be empty.")
        if not isinstance(self.snapshot, dict):
            raise ValueError("Performance scene snapshot must be an object.")

    def to_dict(self) -> dict[str, Any]:
        self.normalize()
        return asdict(self)


class PerformanceSetStore:
    """Atomic, versioned JSON persistence for whole performance setups."""

    @staticmethod
    def build_payload(composition: dict[str, Any], decks: list[dict[str, Any]],
                      effects: dict[str, Any], automation_settings: dict[str, Any],
                      performance_settings: dict[str, Any],
                      scenes: list[PerformanceScene] | None = None,
                      midi_mappings: list[MIDIMapping] | None = None,
                      metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "format": PERFORMANCE_SET_FORMAT,
            "version": PERFORMANCE_SET_VERSION,
            "created_at": time.time(),
            "composition": composition,
            "decks": decks,
            "effects": effects,
            "automation_settings": automation_settings,
            "performance_settings": performance_settings,
            "scenes": [scene.to_dict() for scene in (scenes or [])],
            "midi_mappings": [mapping.to_dict() for mapping in (midi_mappings or [])],
            "metadata": metadata or {},
        }

    @staticmethod
    def save(path: str | Path, payload: dict[str, Any]) -> Path:
        destination = Path(path).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = dict(payload)
        data["format"] = PERFORMANCE_SET_FORMAT
        data["version"] = PERFORMANCE_SET_VERSION
        temporary = destination.with_name(destination.name + ".tmp")
        try:
            temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
            temporary.replace(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return destination

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        payload = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or payload.get("format") != PERFORMANCE_SET_FORMAT:
            raise ValueError("This file is not an eli_lab performance set.")
        version = int(payload.get("version", 0))
        if version > PERFORMANCE_SET_VERSION:
            raise ValueError(
                f"Performance set version {version} is newer than supported version "
                f"{PERFORMANCE_SET_VERSION}."
            )
        for key, expected in (("composition", dict), ("decks", list),
                              ("effects", dict), ("automation_settings", dict),
                              ("performance_settings", dict)):
            if key in payload and not isinstance(payload[key], expected):
                raise ValueError(f"Performance set field {key!r} has an invalid type.")
        return payload


@dataclass
class SceneMorph:
    """Time-based interpolation between compatible numeric values."""

    start: dict[str, float]
    end: dict[str, float]
    started_at: float
    duration: float
    quantization: str = "immediate"

    def value(self, now: float | None = None) -> tuple[float, dict[str, float]]:
        stamp = time.monotonic() if now is None else float(now)
        fraction = 1.0 if self.duration <= 0 else max(
            0.0, min(1.0, (stamp - self.started_at) / self.duration)
        )
        eased = fraction * fraction * (3.0 - 2.0 * fraction)
        common = self.start.keys() & self.end.keys()
        values = {key: self.start[key] + (self.end[key] - self.start[key]) * eased
                  for key in common}
        return fraction, values


class MIDIInputService:
    """Optional mido input adapter with bounded event handoff."""

    def __init__(self, callback, queue_capacity: int = 256) -> None:
        self.callback = callback
        self.queue_capacity = max(1, int(queue_capacity))
        self._events: list[tuple[str, str, int, int, float]] = []
        self._lock = threading.Lock()
        self._port = None
        self.state = "stopped"
        self.error = ""
        self.device_id = ""
        self.dropped_events = 0

    @staticmethod
    def discover() -> list[str]:
        try:
            import mido
            return list(mido.get_input_names())
        except ImportError:
            return []
        except Exception:
            return []

    def start(self, device_name: str) -> bool:
        if self.state == "running":
            self.stop()
        try:
            import mido
            self._port = mido.open_input(
                device_name, callback=lambda message: self._receive(device_name, message)
            )
            self.device_id = str(device_name)
            self.error = ""
            self.state = "running"
            return True
        except Exception as exc:
            self.error = str(exc)
            self.state = "error"
            self._port = None
            return False

    def _receive(self, device_name: str, message) -> None:
        kind = getattr(message, "type", "")
        channel = int(getattr(message, "channel", 0))
        if kind == "control_change":
            event = (device_name, "cc", channel, int(message.control),
                     float(message.value) / 127.0)
        elif kind in {"note_on", "note_off"}:
            value = float(message.velocity) / 127.0 if kind == "note_on" else 0.0
            event = (device_name, "note", channel, int(message.note), value)
        elif kind == "pitchwheel":
            event = (device_name, "pitch", channel, 0,
                     (float(message.pitch) + 8192.0) / 16383.0)
        else:
            return
        with self._lock:
            if len(self._events) >= self.queue_capacity:
                self.dropped_events += 1
                return
            self._events.append(event)

    def drain(self, limit: int = 64) -> int:
        with self._lock:
            batch = self._events[:max(0, int(limit))]
            del self._events[:len(batch)]
        for event in batch:
            self.callback(*event)
        return len(batch)

    def stop(self) -> None:
        port, self._port = self._port, None
        if port is not None:
            try:
                port.close()
            except Exception:
                pass
        with self._lock:
            self._events.clear()
        self.state = "stopped"