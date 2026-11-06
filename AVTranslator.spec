# -*- mode: python ; coding: utf-8 -*-
"""Windows x64 one-file build for eli_lab AV Translator."""

from pathlib import Path
import sysconfig

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve()
ICON = ROOT / "resources" / "icons" / "Icon.ico"

required_paths = (
    ROOT / "main.py",
    ROOT / "config.py",
    ROOT / "resources",
    ROOT / "resources" / "icons" / "Icon.ico",
    ROOT / "dictionary",
    ROOT / "THIRD_PARTY_NOTICES.md",
)
missing = [str(path) for path in required_paths if not path.exists()]
if missing:
    raise FileNotFoundError("Required AV Translator build inputs are missing:\n" + "\n".join(missing))

# Ship application-owned read-only assets at the paths expected by config.py.
datas = [
    (str(ROOT / "resources"), "resources"),
    (str(ROOT / "dictionary"), "dictionary"),
    (str(ROOT / "THIRD_PARTY_NOTICES.md"), "."),
]
binaries = []
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
]

# These modules are partly loaded dynamically or ship package-local DLLs.
# collect_all() gathers package data, extension binaries and submodules.
for package in (
    "av",          # PyAV + FFmpeg Python bindings
    "moderngl",    # ModernGL renderer
    "glcontext",   # OpenGL context providers
    "soundcard",   # Windows audio loopback/input
    "pythonosc",   # Sonic Pi OSC receiver
    "mido",        # MIDI abstraction layer
    "rtmidi",      # Native MIDI backend (python-rtmidi distribution)
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas.extend(package_datas)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_hiddenimports)

# Some PyAV Windows wheels place FFmpeg DLLs beside the av package in an
# "av.libs" directory. Keep those DLLs at the bundle root so Windows' DLL
# search path can resolve them after one-file extraction.
site_packages = Path(sysconfig.get_paths()["purelib"])
for libs_dir in site_packages.glob("av.libs"):
    binaries.extend((str(dll), ".") for dll in libs_dir.rglob("*.dll"))

# Stable de-duplication avoids duplicate TOC warnings when hooks collect the
# same Qt/FFmpeg dependency through more than one package.
def deduplicate(items):
    seen = set()
    result = []
    for item in items:
        key = tuple(str(part) for part in item)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


datas = deduplicate(datas)
binaries = deduplicate(binaries)
hiddenimports = sorted(set(hiddenimports))

analysis = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "scripts" / "pyinstaller_runtime.py")],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.datas,
    [],
    name="eli_lab AV Translator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON),
)
