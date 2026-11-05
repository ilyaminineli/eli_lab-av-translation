# Third-party notices and release audit

This file records the direct runtime/build components used by the Windows x64 release profile. It is a notice index, not a substitute for the full licence texts that accompany each wheel or native library. The build packages the licence files supplied by the upstream distributions where present, and this project retains this notice with the executable.

## Direct runtime dependencies

| Component | Pinned release profile | Upstream licence / notice |
|---|---:|---|
| Qt for Python / PySide6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; commercial licensing is also available. Qt contains additional third-party components and some modules are GPL-only. See [Qt Licensing](https://doc.qt.io/qt-6.12/licensing.html). |
| ModernGL | 5.13.0 | MIT. See [ModernGL on PyPI](https://pypi.org/project/moderngl/5.13.0/). |
| glcontext | dependency of ModernGL | MIT. See [glcontext licence](https://github.com/moderngl/glcontext/blob/main/LICENSE). |
| PyAV | 19.0.2 | PyAV Python bindings: BSD-3-Clause. See [PyAV source](https://github.com/PyAV-Org/PyAV). |
| FFmpeg libraries | bundled by the PyAV Windows wheel | FFmpeg is generally LGPL-2.1-or-later; optional components and external libraries can change the licence of a particular binary. See [FFmpeg licence information](https://github.com/FFmpeg/FFmpeg/blob/master/LICENSE.md). |
| NumPy | 2.5.4 | BSD-3-Clause plus notices for vendored components (including 0BSD, MIT, Zlib and CC0). See [NumPy licence](https://numpy.org/doc/stable/license.html). |
| SoundCard | 0.4.6 | BSD-3-Clause. See [SoundCard on PyPI](https://pypi.org/project/SoundCard/0.4.6/). |
| python-osc | 1.10.2 | Unlicense / public-domain dedication. See [python-osc on PyPI](https://pypi.org/project/python-osc/1.10.2/). |
| Mido | 1.3.3 | MIT. See [Mido on PyPI](https://pypi.org/project/mido/). |
| python-rtmidi | 1.5.8 | MIT. See [python-rtmidi on PyPI](https://pypi.org/project/python-rtmidi/1.5.8/). |

The Windows release profile also installs ordered-set and zstandard for Nuitka deployment. They are build dependencies; they are not application features. The build tools Nuitka and Ruff are likewise build-time dependencies, not part of the Python application's declared runtime requirements.

## Important Qt and FFmpeg conditions

PySide6/Qt is available under LGPL/GPL and commercial terms. Packaging Qt libraries inside a one-file executable does not by itself establish compliance with the applicable licence. Before distributing the executable to other people, review the exact Qt modules and native libraries collected by the generated deployment spec and confirm that the LGPL/GPL requirements (including notices, source access and replaceability/relinking where applicable) are satisfied. A commercial Qt licence is an alternative where appropriate.

PyAV's Python bindings are BSD-3-Clause, but a PyAV wheel also brings FFmpeg native libraries. The licence of those exact FFmpeg binaries depends on their configure options and enabled external libraries. Upstream discussion has raised a specific concern about GPL-enabled FFmpeg components in PyAV binary wheels. The pinned wheel's actual notices/configuration must therefore be inspected before public redistribution. The build self-check reports FFmpeg library versions; it does not prove licence compliance.

## Bundled visual resources — clearance still required

The repository bundles image libraries under resources/textures/, including directories named centurion_assets_pack and texturelabs_assets_pack, plus the resources/sketches_and_strokes/ collection and other textures. A complete licence/attribution register for every bundled asset was not present in the repository at the time of this audit.

**Do not treat this file as evidence that those image assets are cleared for redistribution.** Before publishing or sharing the one-file executable outside your own devices, identify the source and licence for each asset pack, verify whether redistribution inside an executable is allowed, and add the required attribution or remove assets that are not cleared. This build is intended for the author's own Windows systems until that review is complete.

## Application authorship

eli_lab AV Translator is authored by Ilya Minin (Eli), eli_lab, 2026. No separate project-wide open-source licence file was present in the repository during this audit; do not assume that the application source itself is licensed for unrestricted redistribution.
