# Windows setup guide

This guide covers a clean installation of ELI LAB AV Translation on Windows 10/11.

## 1. System requirements

### Required

- Windows 10 or Windows 11, 64-bit.
- Python 3.12, 64-bit.
- A graphics card and current driver supporting OpenGL 3.3 Core Profile.
- Internet access for the initial Python package installation.
- Sufficient free disk space for the Python environment, application cache and your own video files.

The application does not bundle your footage. Keep video files in your own folders; the media library stores paths and metadata.

### Recommended for video testing

- A dedicated or modern integrated GPU with up-to-date drivers.
- An SSD for the media library and footage.
- Four short 720p or 1080p H.264 test clips for the first playback test.
- Start with modest-bitrate footage before testing large 4K or high-bitrate files.

Four concurrent video streams are a workload, not a universal performance guarantee. Supported playback depends on the CPU, GPU, codec, resolution, bitrate and storage speed.

## 2. Install Python 3.12

Install 64-bit Python 3.12 from the official Python downloads page:

https://www.python.org/downloads/

During installation, enable the Python launcher (py). Then open PowerShell and check:

    py -3.12 --version

The command should report Python 3.12.x. If it does not, install Python 3.12 x64 or correct the launcher/PATH setup before continuing.

## 3. Get the repository

Clone the project:

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation

The first implementation is currently on:

    implementation/m0-m1-first-test

Switch to that branch:

    git fetch origin
    git checkout implementation/m0-m1-first-test

If the branch has already been merged into main, use the main branch instead.

## 4. Create a virtual environment

Run these commands from the repository root in PowerShell:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1

Upgrade pip:

    python -m pip install --upgrade pip

A virtual environment keeps the application's Python packages separate from other projects on your computer.

### If PowerShell blocks environment activation

You do not need to change the machine-wide execution policy. Use the virtual environment's Python executable directly:

    .\.venv\Scripts\python.exe -m pip install --upgrade pip

Continue using .\.venv\Scripts\python.exe instead of python for the remaining commands.

## 5. Install dependencies

### Standard application installation

Install only runtime dependencies:

    python -m pip install -r requirements.txt

Register the project in editable mode:

    python -m pip install -e . --no-deps

### Development installation

For development and automated tests, install the development requirements instead:

    python -m pip install -r requirements-dev.txt
    python -m pip install -e . --no-deps

requirements-dev.txt includes the runtime dependencies plus pytest, pytest-qt and Ruff.

Dependency metadata is also declared in pyproject.toml. Keep requirements.txt, requirements-dev.txt and pyproject.toml aligned when changing dependencies.

## 6. Launch the application

From the repository root:

    python main.py

On first launch the application creates its local data folders under the current Windows user's application data directory. The media database, thumbnails and logs are kept outside the repository.

If the main window opens, check the status bar for OpenGL renderer information. The preview widget should initialize without an OpenGL error.

## 7. Generate sample test footage

The repository includes a script that creates four short synthetic MP4 clips. It uses PyAV, which is installed with the runtime requirements.

    python scripts/generate_test_videos.py --output test-footage

The script creates:

- test-red.mp4
- test-green.mp4
- test-blue.mp4
- test-yellow.mp4

The generated test-footage directory is local test data and should not be committed to Git.

## 8. First video collage test

1. Launch the application with python main.py.
2. Select File → Add Media Folder.
3. Choose the generated test-footage directory, or a directory containing your own videos.
4. Wait for the scan to finish and thumbnails to appear.
5. In the Media Library panel, select the target deck in the Assign to dropdown.
6. Double-click a clip to load it into that deck.
7. Repeat for Deck B, C and D.
8. Use the deck controls to play, pause or stop individual clips.
9. Select a layer in the Layers dock and adjust its position, scale, rotation, opacity and blend mode.
10. Use RANDOM SET to assign clips and RANDOMIZE LAYOUT to generate a different collage.
11. Save the composition using File → Save Project As. Project files use the .eliav extension.

## 9. Run tests

Install development requirements first, then run:

    python -m compileall -q .
    python -m pytest tests/unit -v

Ruff is available for lint checks:

    python -m ruff check .

The GitHub Actions workflow runs compilation and unit tests on a Windows runner for pushes and pull requests.

## 10. Troubleshooting

### OpenGL initialization fails

- Update the Intel, AMD or NVIDIA graphics driver from the GPU manufacturer's support page.
- Confirm that the computer and selected GPU support OpenGL 3.3 Core Profile.
- If using a laptop with hybrid graphics, configure Windows Graphics settings to run Python with the high-performance GPU.
- Check the application log under %LOCALAPPDATA%\ELI LAB\AV Translation\logs.

### A video appears in the library but does not play

The scanner recognizes file extensions, but playback also requires a readable video stream and a codec supported by the FFmpeg build used by PyAV.

Try a short H.264 MP4 file first. A filename extension alone does not guarantee that a file is decodable.

### Thumbnails are missing

Thumbnail generation runs in a background worker. Check that PyAV and PySide6 installed correctly and inspect the application log. The media list remains usable without thumbnails.

### The application is slow or drops frames

- Start with four short 720p or 1080p H.264 clips.
- Avoid high-bitrate 4K footage during initial testing.
- Test the clips from an SSD.
- Close other GPU-heavy applications.
- Compare each deck's decoding capability with the master rendering frame rate.

### Qt window does not start in a Python environment with other Qt packages

Use the project's own .venv and avoid mixing PySide6 with unrelated Qt bindings in the same environment. If you have manually set QT_PLUGIN_PATH or QT_QPA_PLATFORM_PLUGIN_PATH, try clearing those variables for this terminal session before launching again.

## 11. Application data locations

The application uses the Windows local application-data directory:

    %LOCALAPPDATA%\ELI LAB\AV Translation\

Typical contents:

    media-library.sqlite3
    cache\thumbnails\
    logs\av-translation.log

Your video files remain in their original folders. The .eliav project stores references to media paths rather than copying source videos.

## 12. Current implementation boundaries

This first test build provides the M0 rendering foundation and the initial M1 video collage workflow.

Not implemented yet:

- Audio playback/mixing or audio-reactive analysis.
- Sonic Pi OSC control.
- Generative graphics and shader effect presets.
- Reverse playback and variable playback speed.
- Masks, advanced transitions and recording.
- Media relinking UI for moved source files.

These are planned for later milestones.
