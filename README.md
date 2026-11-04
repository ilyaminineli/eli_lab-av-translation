# eli_lab-av-translation
program for live visuals based on videos and simple audioreactive visulals and sonic pi support

eli_lab-av-translation/
│
├── main.py
├── config.py
│
├── core/
│   ├── application.py
│   ├── project_manager.py
│   ├── render_engine.py
│   ├── composition.py
│   ├── layer_manager.py
│   ├── event_bus.py
│   └── performance_manager.py
│
├── media/
│   ├── library.py
│   ├── scanner.py
│   ├── thumbnails.py
│   ├── video_decoder.py
│   └── video_deck.py
│
├── generators/
│   ├── base.py
│   ├── geometry.py
│   ├── particles.py
│   ├── waveform.py
│   ├── typography.py
│   └── noise.py
│
├── effects/
│   ├── base.py
│   ├── blur.py
│   ├── glitch.py
│   ├── displacement.py
│   ├── feedback.py
│   ├── chromatic.py
│   └── shaders/
│
├── audio/
│   ├── input_manager.py
│   ├── analyzer.py
│   ├── fft.py
│   ├── beat_detector.py
│   └── modulation.py
│
├── integrations/
│   ├── sonic_pi/
│   │   ├── osc_receiver.py
│   │   ├── event_parser.py
│   │   └── visual_mapper.py
│   ├── midi/
│   └── external_video/
│
├── presets/
│   ├── preset_manager.py
│   └── library/
│
├── ui/
│   ├── main_window.py
│   ├── performance_view.py
│   ├── media_browser.py
│   ├── layer_panel.py
│   ├── generator_panel.py
│   ├── preset_browser.py
│   ├── audio_panel.py
│   └── osc_panel.py
│
└── resources/
    ├── icons/
    ├── textures/
    └── shaders/