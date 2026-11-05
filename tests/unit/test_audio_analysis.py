from __future__ import annotations

import numpy as np

from core.audio_analysis import AudioAnalysisSettings, AudioAnalyzer


def _tone(frequency: float, sample_rate: int = 48000, frames: int = 2048) -> np.ndarray:
    times = np.arange(frames, dtype=np.float32) / sample_rate
    return (0.4 * np.sin(2 * np.pi * frequency * times)).astype(np.float32)


def test_audio_analyzer_reports_rms_peak_and_frequency_band_energy() -> None:
    analyzer = AudioAnalyzer()
    low = analyzer.process(_tone(110), 48000, now=1.0)
    high = analyzer.process(_tone(5000), 48000, now=1.1)

    assert 0.0 < low.rms <= 1.0
    assert 0.0 < low.peak <= 1.0
    assert low.low > low.mid
    assert high.high > high.low
    assert high.high > high.mid


def test_audio_analyzer_handles_multichannel_and_non_finite_samples() -> None:
    analyzer = AudioAnalyzer()
    left = _tone(120, frames=1024)
    right = _tone(600, frames=1024)
    stereo = np.column_stack((left, right))
    stereo[0, 0] = np.nan
    frame = analyzer.process(stereo, 48000, now=2.0)

    assert np.isfinite(frame.rms)
    assert all(0.0 <= value <= 1.0 for value in frame.sources().values())


def test_audio_analyzer_attack_release_and_sensitivity_are_configurable() -> None:
    settings = AudioAnalysisSettings(sensitivity=4.0, attack_ms=5, release_ms=800)
    analyzer = AudioAnalyzer(settings)
    loud = np.ones(1024, dtype=np.float32) * 0.15
    quiet = np.zeros(1024, dtype=np.float32)

    first = analyzer.process(loud, 48000, now=3.0)
    second = analyzer.process(quiet, 48000, now=3.03)
    assert first.rms > 0.4
    assert second.rms > 0.0


def test_audio_analyzer_estimates_tempo_from_repeated_transients() -> None:
    analyzer = AudioAnalyzer(AudioAnalysisSettings(
        sensitivity=3.0,
        attack_ms=1,
        release_ms=20,
        onset_threshold=0.10,
        beat_min_bpm=60,
        beat_max_bpm=180,
    ))
    sample_rate = 48000
    block_size = 1024
    frames = []
    for index in range(24 * 6):
        block = np.zeros(block_size, dtype=np.float32)
        if index % 24 == 0:
            block[:128] = np.linspace(0.9, 0.0, 128, dtype=np.float32)
        stamp = index * block_size / sample_rate
        frames.append(analyzer.process(block, sample_rate, now=stamp))

    assert frames[-1].bpm is not None
    assert 110 <= frames[-1].bpm <= 125
    assert frames[-1].beat_confidence >= 0.45


def test_audio_analysis_settings_clamp_to_safe_ranges() -> None:
    settings = AudioAnalysisSettings(
        sensitivity=99,
        attack_ms=0,
        release_ms=10000,
        onset_threshold=-1,
        beat_min_bpm=20,
        beat_max_bpm=500,
    )
    settings.normalize()

    assert settings.sensitivity == 12
    assert settings.attack_ms == 1
    assert settings.release_ms == 3000
    assert settings.onset_threshold == 0.02
    assert settings.beat_min_bpm == 40
    assert settings.beat_max_bpm == 240
