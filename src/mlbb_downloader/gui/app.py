"""GUI entrypoint."""

from __future__ import annotations

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from mlbb_downloader.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("MLBB Downloader")
    window = MainWindow()
    window.show()
    return app.exec()