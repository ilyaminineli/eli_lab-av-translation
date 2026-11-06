eli_lab AV Translator — PyInstaller build files

Copy these files/folders into the root of your existing eli_lab-av-translation repository, preserving their paths:

  AVTranslator.spec
  requirements-build-pyinstaller.txt
  scripts/build_pyinstaller.py
  scripts/pyinstaller_runtime.py
  docs/BUILD_PYINSTALLER_WINDOWS.md

Then, from the PyCharm Terminal at the repository root, run:

  python .\scripts\build_pyinstaller.py

The script uses the repository-local .venv (CPython 3.12 x64), installs the runtime/build requirements there, builds the one-file EXE, and runs the packaged self-check.

Expected output:

  dist\eli_lab AV Translator.exe

Full instructions are in docs/BUILD_PYINSTALLER_WINDOWS.md.
