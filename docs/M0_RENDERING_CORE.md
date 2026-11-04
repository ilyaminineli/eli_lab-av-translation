# M0 — Rendering Core

## Scope

- Windows desktop bootstrap with PySide6.
- OpenGL 3.3 Core request.
- ModernGL wrapper created from Qt's current OpenGL context.
- QOpenGLWidget master preview.
- Composition and layer data models.
- Event bus and atomic project persistence.
- Renderer diagnostics and clean resource shutdown.

## Acceptance

- Application opens and presents a master canvas.
- Renderer diagnostics identify the active OpenGL renderer.
- Preview resizes with the window.
- Composition/layers serialize and deserialize.
- Project save uses an atomic temporary-file replacement.
- Unit tests run without opening a GUI.
