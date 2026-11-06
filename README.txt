# eli_lab AV Translator — PyInstaller (CPython 3.12–3.14)

## What this build profile does

Builds a native Windows x64 one-file executable using the AV Translator repository's own `.venv`. It collects the application's resources, icon, dictionaries, PySide6/Qt, PyAV/FFmpeg, ModernGL/glcontext, SoundCard, OSC and Mido packages.

## Important Python 3.14 note

PyInstaller 6.15 and later supports Python 3.14. The current PyAV Windows wheel uses the stable CPython 3.12 ABI (`abi3`) and can be used by CPython 3.14. The `python-rtmidi` project currently publishes a Windows x64 binary wheel for CPython 3.12, not CPython 3.14. Therefore the default Python 3.14 build treats native MIDI hardware input as optional. OSC/Sonic Pi integration and all other bundled features remain independent of this backend.

## Install files

Extract/merge this archive into the AV Translator repository root. Do not delete or replace the application's existing folders.

## Apply the one-time self-check compatibility patch

From the repository root:

```powershell
git apply .\patches\main_optional_rtmidi.patch
```

This changes only `main.py`'s `--self-check`: `rtmidi` is reported as an optional backend rather than a mandatory import. The runtime MIDI service already catches an unavailable backend and returns no devices; this patch does not fake MIDI support.

If `git apply` says the patch does not apply, do not force it. Compare `patches/main_optional_rtmidi.py` with the current `main.py` and make the same small change manually.

## Build

Run in the PyCharm terminal from the repository root:

```powershell
python .\scripts\build_pyinstaller.py
```

The script redirects to the repository's `.venv` if another project's venv is active. It supports 64-bit CPython 3.12, 3.13 and 3.14, installs required packages and PyInstaller, checks dependencies, compiles source, packages the EXE, runs `--self-check`, and writes a SHA-256 report.

Output:

`dist\eli_lab AV Translator.exe`

## Optional: native MIDI hardware input

For a Python 3.14 build with native MIDI input, install Visual Studio 2022 Build Tools with Desktop development with C++ and Windows SDK, then run:

```powershell
python .\scripts\build_pyinstaller.py --with-midi
```

That option compiles `python-rtmidi` from source. It can fail if the toolchain or Python 3.14 source compatibility is incomplete. The normal build deliberately does not require it.

## Target computer

The target computer does not need Python, pip, FFmpeg, PyInstaller or Visual Studio. It does need Windows 11 x64 and a graphics driver supporting OpenGL 3.3 Core. Sonic Pi remains a separate installation for SONATA OSC integration. Video footage, project files, and user-added media also remain separate and must be copied/relinked.

The self-check verifies imports and bundled data, not a real OpenGL context, audio loopback, projector output, MIDI device enumeration, multi-deck performance or long-duration stability. Test those on the actual performance laptop.
