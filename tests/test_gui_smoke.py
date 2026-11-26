from __future__ import annotations

import os

import pytest


@pytest.mark.skipif(os.name != "nt" and not os.environ.get("DISPLAY"), reason="No display")
def test_gui_main_window_smoke(monkeypatch, tmp_path) -> None:
    pytest.importorskip("PySide6")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from mlbb_downloader.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    window.output_edit.setText(str(tmp_path))
    assert window.windowTitle() == "MLBB Downloader"
    window.close()
    app.processEvents()
