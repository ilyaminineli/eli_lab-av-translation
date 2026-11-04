from __future__ import annotations

import logging
import sys

from PySide6.QtGui import QIcon, QSurfaceFormat
from PySide6.QtWidgets import QApplication

from config import APP_NAME, APP_VERSION, ICON_PATH, configure_logging
from core.application import Application
from ui.main_window import MainWindow


def configure_opengl() -> None:
    """Request a predictable OpenGL context before QApplication is created."""
    surface_format = QSurfaceFormat()
    surface_format.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    surface_format.setVersion(3, 3)
    surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    surface_format.setDepthBufferSize(0)
    surface_format.setStencilBufferSize(0)
    surface_format.setSamples(0)
    QSurfaceFormat.setDefaultFormat(surface_format)


def main() -> int:
    configure_logging()
    configure_opengl()

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName(APP_NAME)
    qt_app.setApplicationVersion(APP_VERSION)
    qt_app.setOrganizationName("ELI LAB")

    if ICON_PATH.exists():
        qt_app.setWindowIcon(QIcon(str(ICON_PATH)))

    application = Application()
    window = MainWindow(application)
    application.set_window(window)
    window.show()

    logging.getLogger(__name__).info("%s %s started", APP_NAME, APP_VERSION)
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
