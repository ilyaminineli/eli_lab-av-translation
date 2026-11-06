# Local Windows one-file build with PyInstaller

This build profile replaces the previous PySide6/Nuitka deployment script with a local PyInstaller build. It is intended for native Windows x64 builds.

## One-time setup

1. Open the `eli_lab-av-translation` repository root in PyCharm.
2. Create a project-local environment with 64-bit CPython 3.12 if it does not already exist:

   ```powershell
   py -3.12 -m venv .venv
   ```

3. Keep the environment at `.venv` inside this repository. The build script checks for it and automatically re-launches itself with this interpreter even when PyCharm's terminal has another project's environment activated.

## Build

From the repository root, run this single command in the PyCharm Terminal:

```powershell
python .\scripts\build_pyinstaller.py
```

The script installs/updates the runtime and packaging requirements in `eli_lab-av-translation\.venv`, checks dependency consistency, compiles the Python sources, builds the one-file executable, runs the packaged `--self-check`, and prints the executable's SHA-256.

If you want to invoke the project interpreter explicitly:

```powershell
& ".\.venv\Scripts\python.exe" .\scripts\build_pyinstaller.py
```

## Output

```text
dist\eli_lab AV Translator.exe
```

The executable embeds the Python runtime, installed Python packages, Qt runtime/plugins, PyAV/FFmpeg wheel DLLs, ModernGL/glcontext, SoundCard, OSC/MIDI packages, application resources, local dictionaries, and `resources\icons\Icon.ico` as the executable icon. The build report is written to `build\pyinstaller-build-report.txt`.

## Target computer

The target is Windows 11 x64 and does not need Python, pip, PyInstaller, FFmpeg or Visual Studio. It does still need:

- a current graphics driver with OpenGL 3.3 Core Profile support;
- Sonic Pi installed separately for the SONATA OSC workflow;
- any user media/footage and user-added asset folders copied separately.

Project files store media paths; the media itself is not embedded in the EXE. If footage paths differ on the target computer, re-import the copied media folder and relink the decks.

## Notes

- Build on Windows x64; PyInstaller is not a cross-compiler.
- The first one-file launch is slower because PyInstaller extracts the bundled runtime to a temporary directory.
- Keep several GB free on the system drive for build intermediates and one-file extraction.
- A successful packaged self-check validates imports, the H.264 decoder and bundled resources. It does not validate OpenGL context creation, audio-device loopback, projector output, sustained FPS or the full SONATA rehearsal; those still require a real test on the target laptop.
- The application writes logs and its local database under `%LOCALAPPDATA%\eli_lab\AV Translator\`.
