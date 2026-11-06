# Windows x64 one-file build and deployment

## Target

The release profile targets a native **Windows 11 x64** machine. The executable is built on Windows x64 with CPython 3.12 and Visual Studio C++ Build Tools. Do not try to cross-compile this Windows application from Linux or macOS.

The target computer does **not** need Python, pip, FFmpeg, Visual Studio or the C++ build tools. The one-file executable includes the Python runtime, PySide6/Qt modules and plugins, ModernGL, PyAV with its FFmpeg wheel libraries, SoundCard, OSC/MIDI packages, the application's resources and the local text dictionaries.

The target computer still needs:
- Windows 11 64-bit.
- A current AMD graphics driver and OpenGL 3.3 Core Profile support.
- A working display driver and HDMI output path for the projector.
- Sonic Pi installed separately when using the SONATA OSC patch.
- User footage and project media copied separately; video files are not embedded in the executable.

## Recommended target configuration

The linked Lenovo product page describes a configurable IdeaPad Slim 5 Gen 10 16-inch AMD family rather than one unique hardware SKU. Lenovo lists Ryzen 5 8645HS / Ryzen 7 8845HS variants, Radeon 760M / 780M integrated graphics, 16 GB or 32 GB memory configurations and an HDMI port. Check the machine's exact MTM/model number before assuming its RAM, panel or HDMI refresh-rate limit.

For AV Translator, prefer:
- 32 GB RAM, especially for multiple decks and the bundled visual library. 16 GB is a workable lighter-use configuration, but gives less headroom because the integrated Radeon GPU shares system memory.
- NVMe SSD with at least 5 GB free for the application data and one-file extraction; more is needed for video libraries and caches.
- 1080p H.264 sources for the first show test. Four high-bitrate 4K streams are not guaranteed on an integrated GPU.
- HDMI output set to Extend in Windows Display Settings. Start with 1920×1080 at 60 Hz, then test the projector's native mode and refresh rate.
- AC power and Windows Best performance power mode during a show.

The Lenovo family page confirms an HDMI connector, but the HDMI mode/refresh capability depends on the exact SKU and display configuration. Verify this against the model's Lenovo PSREF before setting a 4K or high-refresh projector mode.

## Build machine prerequisites

1. Windows 10/11 x64.
2. 64-bit CPython 3.12 and the Windows Python Launcher (py.exe).
3. Visual Studio Build Tools 2022 with **Desktop development with C++** and the x64 MSVC tools. The Qt deployment helper uses dumpbin.exe; the build script loads the MSVC x64 environment automatically.
4. Internet access for the pinned Python wheels and compiler components.
5. Enough disk space for the virtual environment, compiler cache, intermediate build directory and final executable. Keep at least 10 GB free for a clean build.

## Build command

From PowerShell, clone the repository and switch to the release-readiness branch (use main after this release branch has been merged):

    git clone https://github.com/ilyaminineli/eli_lab-av-translation.git
    cd eli_lab-av-translation
    git fetch origin
    git checkout release/windows-onefile-readiness
    powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1

The script:
1. Verifies Windows x64 and CPython 3.12 x64.
2. Locates Visual Studio Build Tools and activates its x64 compiler environment.
3. Creates .venv-release and installs requirements-build-win-x64.txt.
4. Runs pip check, Python compilation and Ruff.
5. Generates pysidedeploy.spec from the deployment settings in pyproject.toml.
6. Calls pyside6-deploy in onefile mode.
7. Runs the executable's --self-check and prints the executable size and SHA-256.

The output is the single executable under:

    dist\eli_lab AV Translator.exe

If the actual output filename differs, use the only .exe in dist. The script stops if it finds zero or multiple executables.

The build settings are held in pyproject.toml. The generated pysidedeploy.spec is a local build file and is ignored by Git; the script regenerates it so that pyproject.toml remains authoritative.

## Run on the Lenovo

1. Copy the one .exe from dist to the Lenovo.
2. Double-click it. The first start can take longer because Nuitka onefile extracts the packaged runtime and data into a temporary directory.
3. Keep enough free space on the system temporary drive. If Windows has a restricted or nearly full TEMP location, correct that before launching.
4. Run the executable with --self-check from PowerShell to inspect imports, FFmpeg versions, H.264 decoder presence and bundled resources. This check does not initialise OpenGL or test a projector.
5. Open AV Translator, then inspect the renderer status. A successful app launch is not proof of a working OpenGL 3.3 renderer.
6. Connect the projector via HDMI, choose Extend, open View → PROJECTOR OUTPUT and verify the active renderer/FPS.
7. Install and launch Sonic Pi separately, open SONATA Expanded, then arm PERFORMANCE MODE and run the patch.

No Python installation is needed on the Lenovo. Sonic Pi, GPU drivers, Windows audio devices and user footage remain external to the EXE.

## User data and media portability

The application keeps its writable database, thumbnail cache and logs under:

    %LOCALAPPDATA%\eli_lab\AV Translator\

The one-file extraction directory is temporary and is not a place for persistent user data.

Project files (.eliav) and performance sets (.eliset) store source paths and composition state; they do not copy video files into the project. When moving to the Lenovo, copy the footage folders as well. If the folder paths differ, import the copied footage folders into the Media Library and reassign/relink the decks in the composition before performing. Keep the same folder layout where possible.

The executable includes the application's bundled visual textures/sketches and bilingual text dictionaries. User-added asset folders and media remain external and should be copied separately.

## Build workflow

The repository's Windows Onefile Build workflow can be started manually from GitHub Actions or by pushing a version tag matching v*. It uploads a Windows x64 EXE artifact for 30 days. The workflow is a build convenience; it does not validate a particular Lenovo, audio device or HDMI projector.

## Troubleshooting

### OpenGL initialisation fails
- Update the AMD Radeon driver through Lenovo/AMD support or Windows Update.
- Verify that the app's renderer status reports a real OpenGL renderer and version.
- Check Windows Graphics settings and choose the high-performance graphics preference if that option exists.
- If local preview is hidden, its status can say LOCAL PREVIEW IDLE; check the active projector renderer separately.

### Slow playback
- Connect AC power and use Best performance.
- Start with one or two 1080p H.264 clips, then add decks.
- Reduce source resolution/bitrate before reducing the visual composition.
- Close browsers, games and GPU-heavy applications.
- Avoid high-cost master effects until baseline output is stable.

### Audio loopback is unavailable
- Check Windows playback and recording devices.
- Refresh the AUDIO / CONTROL device list.
- Sonic Pi energy/cutoff OSC macros still work without local audio capture; actual low/mid/high band and onset analysis requires a working loopback source.

### Windows Defender or SmartScreen
A one-file executable made with Nuitka may be unfamiliar to a new machine or trigger scanning because it extracts itself. Build from the trusted repository and inspect its SHA-256 before copying. Do not disable Defender globally to run an unverified executable.

## Release verification boundary

A successful --self-check verifies Python package imports and bundled data directories only. It does not prove:
- OpenGL context creation on the target AMD driver.
- Stable 30 FPS at the projector's chosen output resolution.
- Audio loopback device selection/reconnect.
- Four-deck codec support for the user's footage.
- Full 384-bar SONATA timing, long-duration stability or projector hot-plug.

Those must be tested on the actual Lenovo and projector before treating the build as a signed-off performance release.
