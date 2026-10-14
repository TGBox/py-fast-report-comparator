"""py-fast-report-comparator – compare two FastReport VCL (.fr3) templates."""

from __future__ import annotations

import difflib
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QDragEnterEvent,
    QDropEvent,
    QFont,
    QKeySequence,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.differ import Difference, diff_reports
from src.explain import OBJECT_NAMES, explain, object_label
from src.parser import Node, parse_report
from src.preview import MARK_COLORS, PreviewView

APP_NAME = "FastReport-Vergleich"
CATEGORIES = {"content": "Inhalt", "layout": "Layout", "meta": "Metadaten"}
FOCUS_ROLE = int(Qt.ItemDataRole.UserRole) + 1
KIND_LABELS = {
    "added": "neu in B",
    "removed": "entfernt in B",
    "changed": "geändert",
    "renamed": "umbenannt",
}

# Light table metaphor: cool grey desk, white paper, violet "copying pencil" for focus.
THEMES = {
    "light": {
        "canvas": "#E9ECEF",
        "surface": "#F8F9FA",
        "ink": "#1D232B",
        "muted": "#5F6B78",
        "line": "#D3D8DE",
        "accent": "#5B4BB7",
        "accent_ink": "#FFFFFF",
    },
    "dark": {
        "canvas": "#16191E",
        "surface": "#1F242B",
        "ink": "#E4E7EB",
        "muted": "#8E99A6",
        "line": "#2E353E",
        "accent": "#A99BF2",
        "accent_ink": "#16191E",
    },
}
QSS = """
QMainWindow, QWidget {{ background: {surface}; color: {ink};
    font-family: "Segoe UI", sans-serif; font-size: 10pt; }}
QToolBar {{ background: {surface}; border: none; border-bottom: 1px solid {line};
    padding: 6px; spacing: 8px; }}
QToolButton {{ padding: 5px 10px; border: 1px solid {line}; border-radius: 4px; }}
QToolButton:hover {{ border-color: {accent}; }}
QToolButton:focus, QTreeWidget:focus, QPlainTextEdit:focus {{ border: 1px solid {accent}; }}
QLabel#fileLabel {{ font-family: "Bahnschrift", "Segoe UI"; font-size: 11pt; }}
QLabel#paneTitle {{ font-family: "Bahnschrift", "Segoe UI"; font-size: 11pt;
    padding: 6px 2px; color: {muted}; }}
QLabel#summary {{ font-family: "Bahnschrift", "Segoe UI"; color: {muted}; }}
QTreeWidget, QPlainTextEdit {{ background: {surface}; border: 1px solid {line};
    border-radius: 4px; }}
QTreeWidget::item {{ padding: 3px 0; }}
QTreeWidget::item:selected {{ background: {accent}; color: {accent_ink}; }}
QPlainTextEdit {{ font-family: "Cascadia Mono", "Consolas", monospace; font-size: 9pt; }}
QGraphicsView {{ background: {canvas}; border: 1px solid {line}; border-radius: 4px; }}
QSplitter::handle {{ background: {line}; }}
QStatusBar {{ color: {muted}; }}
"""


class CompareThread(QThread):
    """Parses both files (and diffs them if both are given) off the UI thread."""

    done = Signal(object, object, object)  # report_a, report_b, differences
    failed = Signal(str)

    def __init__(self, path_a: Path | None, path_b: Path | None):
        super().__init__()
        self.paths = (path_a, path_b)

    def run(self) -> None:
        reports: list[Node | None] = []
        for path in self.paths:
            try:
                reports.append(parse_report(path) if path else None)
            except Exception as error:  # noqa: BLE001 – any parse error is shown to the user
                self.failed.emit(
                    f"„{path.name}“ konnte nicht gelesen werden: {error}. "
                    "Ist das eine FastReport-Vorlage (.fr3, XML)?"
                )
                return
        a, b = reports
        try:
            differences = diff_reports(a, b) if a and b else []
        except Exception as error:  # noqa: BLE001
            self.failed.emit(f"Vergleich fehlgeschlagen: {error}")
            return
        self.done.emit(a, b, differences)


def _location_label(key: str) -> str:
    return {"Data": "Datenseite"}.get(key) or OBJECT_NAMES.get(key, key)


class MainWindow(QMainWindow):
    def __init__(self, path_a: Path | None = None, path_b: Path | None = None):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setAcceptDrops(True)
        self.settings = QSettings("Carasent", "py-fast-report-comparator")
        self.paths: list[Path | None] = [path_a, path_b]
        self.reports: list[Node | None] = [None, None]
        self.differences: list[Difference] = []
        self._worker: CompareThread | None = None
        self._syncing = False  # guards the A<->B scroll/zoom mirroring against feedback
        self._build_ui()
        self._restore()
        self._reload()

    # -- UI -----------------------------------------------------------------
    def _build_ui(self) -> None:
        bar = QToolBar("Werkzeuge")
        bar.setMovable(False)
        self.addToolBar(bar)
        self.file_labels = [QLabel(), QLabel()]
        for side, label in enumerate(self.file_labels):
            action = QAction(f"Vorlage {'AB'[side]} öffnen …", self)
            action.setShortcut(QKeySequence(f"Ctrl+{side + 1}"))
            action.triggered.connect(lambda _=False, s=side: self._choose(s))
            bar.addAction(action)
            label.setObjectName("fileLabel")
            bar.addWidget(label)
            bar.addSeparator()
        swap = QAction("A und B tauschen", self)
        swap.triggered.connect(self._swap)
        bar.addAction(swap)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bar.addWidget(spacer)
        self.filters: dict[str, QCheckBox] = {}
        for key, text in CATEGORIES.items():
            box = QCheckBox(text)
            box.toggled.connect(self._fill_tree)
            self.filters[key] = box
            bar.addWidget(box)
        bar.addSeparator()
        self.theme_action = QAction("Dunkles Design", self, checkable=True)
        self.theme_action.toggled.connect(self._apply_theme)
        bar.addAction(self.theme_action)
        fullscreen = QAction("Vollbild", self)
        fullscreen.setShortcut(QKeySequence("F11"))
        fullscreen.triggered.connect(self._toggle_fullscreen)
        self.addAction(fullscreen)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Unterschied", "Art"])
        self.tree.setColumnWidth(0, 430)
        self.tree.currentItemChanged.connect(self._on_select)
        self.summary = QLabel()
        self.summary.setObjectName("summary")
        self.detail = QPlainTextEdit(readOnly=True)
        self.detail.setPlaceholderText("Wähle links einen Unterschied, um Details zu sehen.")

        list_pane = QWidget()
        list_layout = QVBoxLayout(list_pane)
        list_layout.setContentsMargins(8, 8, 4, 8)
        list_layout.addWidget(self.summary)
        list_layout.addWidget(self.tree)
        self.left_split = QSplitter(Qt.Orientation.Vertical)
        self.left_split.addWidget(list_pane)
        self.left_split.addWidget(self.detail)
        self.left_split.setStretchFactor(0, 3)

        self.previews = [PreviewView(), PreviewView()]
        self.pane_titles = [QLabel(), QLabel()]
        preview_split = QSplitter(Qt.Orientation.Horizontal)
        for view, title in zip(self.previews, self.pane_titles, strict=True):
            title.setObjectName("paneTitle")
            pane = QWidget()
            layout = QVBoxLayout(pane)
            layout.setContentsMargins(4, 4, 4, 8)
            layout.addWidget(title)
            layout.addWidget(view)
            preview_split.addWidget(pane)
        a, b = self.previews
        for src, dst in ((a, b), (b, a)):
            self._link(src.horizontalScrollBar(), dst.horizontalScrollBar())
            self._link(src.verticalScrollBar(), dst.verticalScrollBar())
            src.zoomed.connect(lambda f, s=src, d=dst: self._follow_zoom(s, d, f))

        self.main_split = QSplitter(Qt.Orientation.Horizontal)
        self.main_split.addWidget(self.left_split)
        self.main_split.addWidget(preview_split)
        self.main_split.setStretchFactor(1, 2)
        self.setCentralWidget(self.main_split)

    def _link(self, source, target) -> None:
        def follow(value: int) -> None:
            if not self._syncing:
                self._syncing = True
                try:
                    target.setValue(value)
                finally:
                    self._syncing = False

        source.valueChanged.connect(follow)

    def _follow_zoom(self, source: PreviewView, target: PreviewView, factor: float) -> None:
        self._syncing = True
        try:
            target.apply_zoom(factor)
            target.horizontalScrollBar().setValue(source.horizontalScrollBar().value())
            target.verticalScrollBar().setValue(source.verticalScrollBar().value())
        finally:
            self._syncing = False

    def _focus(self, name_a: str | None, name_b: str | None) -> None:
        self._syncing = True  # each side centres on its own object
        try:
            self.previews[0].focus_object(name_a)
            self.previews[1].focus_object(name_b)
        finally:
            self._syncing = False

    def _restore(self) -> None:
        s = self.settings
        if geometry := s.value("geometry"):
            self.restoreGeometry(geometry)
        else:
            self.resize(1500, 900)
        if state := s.value("mainSplit"):
            self.main_split.restoreState(state)
        if state := s.value("leftSplit"):
            self.left_split.restoreState(state)
        for key, box in self.filters.items():
            box.setChecked(s.value(f"filter/{key}", key != "meta", type=bool))
        dark = s.value("dark", False, type=bool)
        self.theme_action.setChecked(dark)
        self._apply_theme(dark)
        if not any(self.paths):
            stored = [s.value(f"path{i}", "") for i in range(2)]
            self.paths = [Path(p) if p and Path(p).is_file() else None for p in stored]

    def closeEvent(self, event) -> None:
        if self._worker is not None:
            self._worker.wait()
        s = self.settings
        s.setValue("geometry", self.saveGeometry())
        s.setValue("mainSplit", self.main_split.saveState())
        s.setValue("leftSplit", self.left_split.saveState())
        s.setValue("dark", self.theme_action.isChecked())
        for key, box in self.filters.items():
            s.setValue(f"filter/{key}", box.isChecked())
        for i, path in enumerate(self.paths):
            s.setValue(f"path{i}", str(path) if path else "")
        super().closeEvent(event)

    def _apply_theme(self, dark: bool) -> None:
        theme = THEMES["dark" if dark else "light"]
        QApplication.instance().setStyleSheet(QSS.format(**theme))
        for view in self.previews:
            view.focus_color = QColor(theme["accent"])

    def _toggle_fullscreen(self) -> None:
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    # -- files --------------------------------------------------------------
    def _choose(self, side: int) -> None:
        start = str(self.paths[side] or self.settings.value("lastDir", ""))
        name, _ = QFileDialog.getOpenFileName(
            self, f"Vorlage {'AB'[side]} öffnen", start, "FastReport-Vorlagen (*.fr3);;Alle (*)"
        )
        if name:
            self._set_path(side, Path(name))

    def _set_path(self, side: int, path: Path) -> None:
        self.paths[side] = path
        self.settings.setValue("lastDir", str(path.parent))
        self._reload()

    def _swap(self) -> None:
        self.paths.reverse()
        self._reload()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        files = [Path(u.toLocalFile()) for u in event.mimeData().urls() if u.isLocalFile()]
        if files:
            event.acceptProposedAction()
        if len(files) >= 2:
            self.paths = files[:2]
            self._reload()
        elif files:
            side = 1 if event.position().x() > self.width() * 0.66 else 0
            self._set_path(side, files[0])

    def _reload(self) -> None:
        for side, label in enumerate(self.file_labels):
            path = self.paths[side]
            label.setText(f"{'AB'[side]}: {path.name if path else 'keine Datei'}")
            label.setToolTip(str(path or ""))
            self.pane_titles[side].setText(
                f"Vorlage {'AB'[side]}" + (f" · {path.stem}" if path else "")
            )
        self.statusBar().showMessage("Lade Vorlagen …")
        if self._worker is not None:
            self._worker.wait()  # parsing takes milliseconds; never drop a running QThread
        self._worker = CompareThread(*self.paths)
        self._worker.done.connect(self._on_compared)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def _on_failed(self, message: str) -> None:
        self.statusBar().showMessage(message)
        self.detail.setPlainText(message)

    def _on_compared(self, a: Node | None, b: Node | None, differences: list[Difference]) -> None:
        self.reports = [a, b]
        self.differences = differences
        # An object is red/green only if it disappeared/appeared itself, otherwise yellow.
        marks_a = {
            d.obj_a: "removed" if d.kind == "removed" and d.path[-1] == d.obj_a else "changed"
            for d in differences
            if d.obj_a and d.path
        }
        marks_b = {
            d.obj_b: "added" if d.kind == "added" and d.path[-1] == d.obj_b else "changed"
            for d in differences
            if d.obj_b and d.path
        }
        for side, (report, marks) in enumerate(((a, marks_a), (b, marks_b))):
            self.previews[side].show_report(
                report,
                marks,
                f"Vorlage {'AB'[side]} hierher ziehen oder mit Strg+{side + 1} öffnen.",
            )
        self._fill_tree()
        if a and b:
            self.statusBar().showMessage("Vergleich abgeschlossen.", 4000)
        else:
            self.statusBar().showMessage("Wähle eine zweite Vorlage, um zu vergleichen.")

    # -- difference list ----------------------------------------------------
    def _fill_tree(self) -> None:
        self.tree.clear()
        visible = [d for d in self.differences if self.filters[d.category].isChecked()]
        counts = {c: sum(d.category == c for d in self.differences) for c in CATEGORIES}
        if not all(self.reports):
            self.summary.setText("")
        elif not self.differences:
            self.summary.setText("Keine Unterschiede gefunden.")
        else:
            parts = ", ".join(f"{n} {CATEGORIES[c]}" for c, n in counts.items() if n)
            self.summary.setText(f"{len(self.differences)} Unterschiede: {parts}")

        nodes: dict[tuple[str, ...], QTreeWidgetItem] = {}
        for d in visible:
            parent = self.tree.invisibleRootItem()
            if not d.path:
                key = ("__report__",)
                if key not in nodes:
                    nodes[key] = QTreeWidgetItem(parent, ["Bericht (Einstellungen, Skript)"])
                parent = nodes[key]
            for depth in range(1, len(d.path) + 1):
                key = d.path[:depth]
                if key not in nodes:
                    is_object = depth == len(d.path) and d.kind == "changed"
                    text = object_label(d) if is_object else _location_label(key[-1])
                    nodes[key] = QTreeWidgetItem(parent, [text])
                    nodes[key].setData(0, FOCUS_ROLE, key[-1])
                parent = nodes[key]
            if d.kind == "changed" or not d.path:
                item = QTreeWidgetItem(parent, [explain(d), CATEGORIES[d.category]])
            else:  # added/removed/renamed: the object row itself carries the sentence
                item = parent
                item.setText(0, explain(d))
                item.setText(1, KIND_LABELS[d.kind])
            item.setData(0, Qt.ItemDataRole.UserRole, d)
            item.setToolTip(0, explain(d))
            color = MARK_COLORS.get(d.kind if d.kind != "renamed" else "changed")
            item.setForeground(1, QBrush(QColor(color)))
        self.tree.expandAll()

    def _on_select(self, current: QTreeWidgetItem | None, _previous=None) -> None:
        if current is None:
            return
        d: Difference | None = current.data(0, Qt.ItemDataRole.UserRole)
        if d is None:  # page/band/object row without own difference: just show it
            name = current.data(0, FOCUS_ROLE)
            self._focus(name, name)
            self.detail.clear()
            return
        self._focus(d.obj_a or d.obj_b, d.obj_b or d.obj_a)
        where = " › ".join(d.path) or "Bericht"
        lines = [
            f"Ort: {where}",
            f"Objekttyp: {OBJECT_NAMES.get(d.tag, d.tag)}",
            f"Kategorie: {CATEGORIES[d.category]}",
            "",
            explain(d),
            "",
        ]
        if d.prop:
            old, new = (d.old or "").splitlines(), (d.new or "").splitlines()
            if len(old) > 1 or len(new) > 1:
                lines += list(difflib.unified_diff(old, new, "A", "B", lineterm="", n=2))
            else:
                lines += [
                    f"A: {d.old if d.old is not None else '(nicht gesetzt)'}",
                    f"B: {d.new if d.new is not None else '(nicht gesetzt)'}",
                ]
        elif d.old or d.new:
            lines += ["Inhalt:", d.old or d.new or ""]
        self.detail.setPlainText("\n".join(lines))


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setFont(QFont("Segoe UI", 10))
    args = [Path(a) for a in sys.argv[1:3]]
    window = MainWindow(*(args + [None, None])[:2])
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
