# Windows setup guide

This guide covers a clean installation of ELI LAB AV Translation on Windows 10/11.

## 1. System requirements

- Windows 10/11, 64-bit.
- Python 3.12, 64-bit.
- Current GPU driver supporting OpenGL 3.3 Core Profile.
- Video codecs supported by the FFmpeg build bundled with PyAV.
- SSD and modern CPU/GPU recommended for four concurrent streams.
- A second display or projector is optional but recommended for output testing.

Four concurrent high-bitrate streams are not guaranteed on every computer. Begin with short 720p or 1080p H.264 clips.

## 2. Install Python 3.12

Install 64-bit Python 3.12 from https://www.python.org/downloads/ and enable the Python launcher.

Check in PowerShell:

    py -3.12 --version

## 3. Get the repository

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation
    git checkout main
    git pull

## 4. Create a virtual environment

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1

Upgrade pip:

    python -m pip install --upgrade pip

If PowerShell blocks activation, use the environment interpreter directly rather than changing the machine-wide execution policy:

    .\.venv\Scripts\python.exe -m pip install --upgrade pip

Continue using .\.venv\Scripts\python.exe instead of python in that terminal.

## 5. Install dependencies

For development and automated tests:

    python -m pip install -r requirements-dev.txt
    python -m pip install -e . --no-deps

For an application-only environment:

    python -m pip install -r requirements.txt
    python -m pip install -e . --no-deps

Dependency metadata is also declared in pyproject.toml. Keep all three files aligned when changing dependencies.

## 6. Launch the application

    python main.py

On first launch the application creates local data folders under:

    %LOCALAPPDATA%\ELI LAB\AV Translation\

The media database, thumbnails and logs are kept outside the repository.

## 7. First video test

Generate sample clips:

    python scripts/generate_test_videos.py --output test-footage

Then launch the app, drag test-footage from Windows Explorer into the Media Library panel, or select File → Add Media Folder. Assign the clips to the four decks and test playback, layer blending and transforms.

## 8. Run an unattended collage

1. Import one or more footage folders into the Media Library.
2. Open the AUTO PERFORMANCE panel.
3. Choose one footage folder or All imported footage.
4. Choose a session length: 30, 45, 60, 90 or 120 minutes, or Until stopped.
5. Choose cut rhythm, fragment length and loop probability.
6. Keep automatic layout and filter-look changes enabled for a fully changing set.
7. Press START AUTOMATIC SESSION.
8. Use deck or layer Lock controls to keep selected sources or visual layers fixed.
9. Press STOP AUTOMATION when the session is finished. Current deck playback is left running.

The director selects randomized in/out points and independently schedules cuts for each unlocked deck. A segment can loop or play once before its next scheduled cut.

## 9. Effects and overlays

Open EFFECTS + OVERLAYS to select a look and adjust:

- Brightness, contrast, saturation and gamma.
- Vignette and grain.
- Scanlines and RGB split.
- Signal glitch, pixelation, posterize and invert.

Looks are applied to the master composition and shared by the preview and projector output.

## 10. Fullscreen projector output

1. Connect and enable the second display or projector in Windows Display Settings.
2. Set the displays to Extend rather than Duplicate.
3. In AV Translation, select View → PROJECTOR OUTPUT → Display N.
4. The selected display opens a fullscreen live output.
5. Press Escape on that output display to close it. The main application remains open.

The projector window has its own GPU renderer. Both windows display the same video snapshots and effects; they do not create additional video decoder workers.

## 11. Tests and troubleshooting

Run:

    python -m compileall -q .
    python -m pytest tests/unit -v
    python -m ruff check .

### OpenGL initialization fails

- Update the Intel, AMD or NVIDIA graphics driver.
- Confirm OpenGL 3.3 Core Profile support.
- On laptops, set Python to use the high-performance GPU in Windows Graphics settings.
- Check %LOCALAPPDATA%\ELI LAB\AV Translation\logs.

### A video appears in the library but does not play

The scanner indexes supported file extensions, but actual playback needs a decodable video stream and a supported codec. Try a short H.264 MP4 file first.

### Playback is slow or drops frames

- Start with four 720p or 1080p H.264 clips.
- Avoid high-bitrate 4K footage during initial tests.
- Use an SSD and close other GPU-heavy programs.
- Reduce heavy looks such as glitch and pixelation if the GPU is struggling.
- Compare decoder and renderer performance separately.

### Projector output opens on the wrong display

Use Windows Display Settings to confirm the projector is connected and set to Extend. Reopen View → PROJECTOR OUTPUT after the display topology changes.

### Thumbnails are missing

Thumbnail generation runs in a background worker. Check PyAV and PySide6 installation and inspect the application log. The media list remains usable without thumbnails.

## 12. Data and project files

The application stores media indexing, thumbnails and logs under:

    %LOCALAPPDATA%\ELI LAB\AV Translation\

A .eliav project stores composition, source paths, segment settings, master effect settings and automation settings. It does not copy source video files.
