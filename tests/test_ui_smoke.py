"""Offscreen smoke tests for the Qt layer (spec success criteria 1 and 5)."""

import os
from pathlib import Path

import pytest

if not Path("testdata").is_dir():  # testdata/ holds real templates and is git-ignored
    pytest.skip("testdata/ fehlt", allow_module_level=True)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from src.main import MainWindow  # noqa: E402
from src.parser import parse_report  # noqa: E402
from src.preview import ReportScene  # noqa: E402

TESTDATA = Path("testdata")


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_all_testdata_files_render():
    app()
    for path in sorted(TESTDATA.glob("*.fr3")):
        scene = ReportScene(parse_report(path), {"Memo1": "changed"})
        assert scene.items(), path.name


def test_main_window_compares_a_pair():
    qt = app()
    window = MainWindow(
        TESTDATA / "Terminuebersicht_Terminübersicht.fr3",
        TESTDATA / "Terminuebersicht_Terminübersicht Neu.fr3",
    )
    window._worker.wait()
    qt.processEvents()
    assert window.tree.topLevelItemCount() > 0
    window.tree.setCurrentItem(window.tree.topLevelItem(0))
    assert "Unterschiede" in window.summary.text()
