from __future__ import annotations

import hashlib
import os
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT_PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
REQUIREMENTS = ROOT / "requirements-build-pyinstaller.txt"
SPEC = ROOT / "AVTranslator.spec"
EXE = ROOT / "dist" / "eli_lab AV Translator.exe"


def run(command: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    print("\n> " + subprocess.list2cmdline(command), flush=True)
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        check=True,
        timeout=timeout,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relaunch_in_project_venv() -> None:
    """Avoid accidentally building in a different project's activated venv."""
    if not PROJECT_PYTHON.is_file():
        raise SystemExit(
            "Project virtual environment not found:\n"
            f"  {PROJECT_PYTHON}\n\n"
            "Create the AV Translator environment first (Python 3.12 x64):\n"
            "  py -3.12 -m venv .venv\n\n"
            "Then run this build script again from the repository root."
        )

    current = Path(sys.executable).resolve()
    expected = PROJECT_PYTHON.resolve()
    if current != expected:
        print(
            "Using the AV Translator project's own .venv instead of the currently "
            "activated interpreter:\n"
            f"  {expected}",
            flush=True,
        )
        result = subprocess.run(
            [str(expected), str(Path(__file__).resolve()), *sys.argv[1:]],
            cwd=ROOT,
        )
        raise SystemExit(result.returncode)


def validate_environment() -> None:
    if os.name != "nt":
        raise SystemExit("This packaging profile creates a native Windows executable and must run on Windows.")
    if struct.calcsize("P") * 8 != 64:
        raise SystemExit("A 64-bit Python interpreter is required for the Windows x64 executable.")
    if sys.implementation.name != "cpython" or sys.version_info[:2] != (3, 12):
        raise SystemExit(
            "This AV Translator build profile requires 64-bit CPython 3.12.\n"
            f"Current interpreter: {sys.version.split()[0]} ({sys.implementation.name}).\n"
            "Use the AV Translator-local .venv created with: py -3.12 -m venv .venv"
        )

    required = (ROOT / "main.py", ROOT / "config.py", ROOT / "resources", ROOT / "dictionary", ROOT / "THIRD_PARTY_NOTICES.md", SPEC, REQUIREMENTS)
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing required project/build files:\n" + "\n".join(missing))


def main() -> int:
    relaunch_in_project_venv()
    validate_environment()
    python = str(PROJECT_PYTHON.resolve())

    print("=" * 72)
    print("eli_lab AV Translator — local PyInstaller one-file build")
    print(f"Python: {sys.version.split()[0]} x64")
    print(f"Environment: {PROJECT_PYTHON}")
    print("=" * 72)

    # Install the app's runtime packages, MIDI support, and PyInstaller into
    # the AV Translator-local .venv only. No other project environment is used.
    run([python, "-m", "pip", "install", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    run([python, "-m", "pip", "check"])

    # Catch syntax errors before starting the packaging process.
    run([
        python,
        "-m",
        "compileall",
        "-q",
        "main.py",
        "config.py",
        "core",
        "effects",
        "generators",
        "media",
        "rendering",
        "ui",
    ])

    # PyInstaller's spec defines the logo, Qt plugins, FFmpeg/PyAV DLLs,
    # ModernGL/glcontext, SoundCard, OSC/MIDI modules and application assets.
    run([
        python,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / "pyinstaller"),
        str(SPEC),
    ])

    if not EXE.is_file():
        raise SystemExit(f"PyInstaller completed without producing the expected executable: {EXE}")

    # Run the packaged program's existing import/resource/FFmpeg self-check.
    # The spec uses a windowed bootloader; its exit code remains testable even
    # though no console window is shown.
    print("\nRunning packaged --self-check ...", flush=True)
    check = subprocess.run(
        [str(EXE), "--self-check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=240,
    )
    if check.returncode != 0:
        details = "\n".join(part for part in (check.stdout, check.stderr) if part)
        raise SystemExit(
            "The packaged executable failed --self-check "
            f"(exit code {check.returncode}).\n{details}\n"
            "The full application log is under %LOCALAPPDATA%\\eli_lab\\AV Translator\\logs."
        )

    size_mib = EXE.stat().st_size / (1024 * 1024)
    digest = sha256_file(EXE)
    report = (
        "eli_lab AV Translator — PyInstaller build report\n"
        f"Built (UTC): {datetime.now(timezone.utc).isoformat()}\n"
        f"Python: {sys.version.split()[0]} x64\n"
        f"PyInstaller: {__import__('PyInstaller').__version__}\n"
        f"Executable: {EXE}\n"
        f"Size: {size_mib:.1f} MiB\n"
        f"SHA-256: {digest}\n"
        "Packaged self-check: PASS\n"
    )
    report_path = ROOT / "build" / "pyinstaller-build-report.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print("\n" + "=" * 72)
    print("BUILD COMPLETE")
    print(f"Executable: {EXE}")
    print(f"Size:       {size_mib:.1f} MiB")
    print(f"SHA-256:    {digest}")
    print(f"Report:     {report_path}")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode or 1) from exc
