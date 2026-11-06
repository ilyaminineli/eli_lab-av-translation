# Windows setup and operation

There are two ways to use AV Translator:

- **Performance machine:** copy and run the single Windows x64 executable. Python and development tools are not required.
- **Development/build machine:** install CPython 3.12 x64 and Visual Studio Build Tools, then run the source or build the one-file executable.

For the native Windows one-file build, follow [BUILD_WINDOWS.md](BUILD_WINDOWS.md). This document covers daily use and troubleshooting.

## 1. Target system requirements

- Windows 11 64-bit.
- GPU driver with OpenGL 3.3 Core Profile support.
- SSD storage.
- HDMI or supported USB-C DisplayPort output for a projector.
- Sonic Pi installed separately when using SONATA Expanded.
- H.264 MP4 footage is recommended for the first test.

For the Lenovo IdeaPad Slim 5 Gen 10 16-inch AMD family, 32 GB RAM is the preferred configuration for multi-deck performances. A 16 GB model can be used for lighter shows, but integrated Radeon graphics share system memory with the CPU. Check the exact Lenovo MTM/SKU for the supported HDMI resolution and refresh rate. Four simultaneous high-bitrate 4K streams are not guaranteed on an integrated GPU.

## 2. Install the one-file executable

1. Obtain the Windows x64 EXE from the release artifact or from the build output described in [BUILD_WINDOWS.md](BUILD_WINDOWS.md).
2. Copy the EXE to a local folder on the performance computer.
3. Double-click to start it.
4. On the first launch, allow time for one-file extraction and Windows Defender scanning.
5. The writable application database, thumbnails and logs are created under:

    %LOCALAPPDATA%\eli_lab\AV Translator\

The target computer does not need Python, pip, FFmpeg, Visual Studio or Nuitka. The executable bundles the Python application/runtime, Qt/PySide6, rendering/media/audio/OSC/MIDI dependencies and the repository's bundled visual resources and dictionaries.

Sonic Pi, GPU drivers, Windows audio devices and your own video files are not part of the EXE.

## 3. Prepare footage and projects

A .eliav project and an .eliset performance set store composition state and source paths; they do not contain the original video files.

When moving a project to a different computer:
1. Copy the video and user asset folders to the new computer.
2. Keep the folder structure the same where practical.
3. Import those folders into the Media Library on the new computer.
4. Reassign/relink the four decks and any media overlays if their absolute paths changed.
5. Save a fresh project/performance set on that computer.

Do not expect a project JSON file alone to transfer the video media.

## 4. Connect the projector

1. Connect HDMI before opening the fullscreen output.
2. In Windows Display Settings, choose **Extend these displays**.
3. Start AV Translator.
4. Set the projector to 1920×1080 at 60 Hz for the first validation. Test higher resolutions only after checking the actual projector and laptop SKU.
5. Select View → PROJECTOR OUTPUT → Display N.
6. Confirm the status bar reports the active projector renderer and FPS.
7. Press Escape on the projector output to close it. The main application remains open.

The preview and projector have separate OpenGL contexts but share the same application composition and CPU frame snapshots.

## 5. Run an autonomous Sonic Pi performance

1. Prepare a composition with video decks and/or generator layers.
2. In AUDIO / CONTROL, choose System Loopback for actual audio-band/onset analysis, or Sonic Pi macros only when local capture is unavailable or not needed.
3. In AUTO PERFORMANCE, choose Generative or Structured style, musical sync and duration.
4. Press PERFORMANCE MODE.
5. Run SONATA Expanded in Sonic Pi.
6. Confirm the application moves from ARMED to LIVE and the audio/OSC status is healthy.
7. Open the projector output.
8. Stop SONATA to end the current AUTO pass. Performance Mode re-arms for a subsequent patch run. Press STOP PERFORMANCE MODE when the show is finished.

Sonic Pi energy/cutoff macros are normalized musical control signals, not raw audio samples. System loopback is required for the actual low/mid/high audio analysis.

See [SONATA integration notes](SONIC_PI_SONATA_INTEGRATION.md) for remote-computer OSC addressing and the exact protocol.

## 6. Developer setup (source run)

Only use these steps on the development/build computer.

Install 64-bit CPython 3.12, clone the repository, and prepare an environment:

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation
    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt
    python -m pip install -e . --no-deps
    python main.py

If PowerShell blocks activation, use .venv\Scripts\python.exe directly. The source-run application uses the same writable LOCALAPPDATA location as the one-file executable.

## 7. Developer quality checks

The historical unit-test suite and pytest dependency were removed at the user's request. Current CI performs Python compilation and Ruff only:

    python -m compileall -q main.py config.py core effects generators media rendering ui
    python -m ruff check main.py config.py core effects generators media rendering ui

Do not describe a green compile/Ruff workflow as a passing runtime or hardware test.

## 8. Diagnostics

The one-file build supports:

    "eli_lab AV Translator.exe" --self-check

It reports whether the Python packages import, which FFmpeg libraries are present, whether the H.264 decoder is available, and whether the packaged icon/textures/sketches/dictionaries are present. It does not initialise an OpenGL context or test the HDMI/projector.

The normal application log is:

    %LOCALAPPDATA%\eli_lab\AV Translator\logs\av-translator.log

## 9. Troubleshooting

### OpenGL initialisation fails
- Update the AMD Radeon graphics driver.
- Confirm OpenGL 3.3 Core Profile support.
- Check the status bar for the active renderer's actual error.
- LOCAL PREVIEW IDLE means the local preview tab is hidden; it does not mean that the projector renderer failed.
- The projector renderer reports its own initialisation result and FPS.

### Playback is slow or drops frames
- Connect AC power and use Windows Best performance mode.
- Begin with one or two 1080p H.264 clips, then add decks.
- Use the local NVMe SSD rather than a slow external drive.
- Close browser tabs, games and other GPU-heavy software.
- Reduce source resolution/bitrate before simplifying the visual composition.
- Compare renderer FPS, decode time, conversion time and dropped-frame counters.

### Audio loopback is unavailable
- Check Windows playback and recording devices.
- Refresh the device list in AUDIO / CONTROL.
- Sonic Pi transport and energy/cutoff macros can still operate without local audio capture.
- Actual low/mid/high bands and onset analysis require a supported loopback source.

### Projector appears on the wrong display
- Confirm Windows is set to Extend.
- Close the output window and reopen View → PROJECTOR OUTPUT after changing display topology.
- Verify the target HDMI mode and refresh rate are supported by the exact laptop and projector models.

### Media is missing after moving the project
The project stores source paths, not copies of the video files. Copy the original folders and import/reassign them on the target computer.

### Windows Defender/SmartScreen warns about the EXE
One-file applications extract their payload to a temporary directory and may trigger an unfamiliar-app scan. Obtain the EXE from the trusted build workflow, compare its SHA-256 value and allow Windows to finish scanning. Do not disable Defender globally to run an unverified executable.
