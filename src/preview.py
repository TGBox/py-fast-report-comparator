"""Sketch rendering of a parsed .fr3 report with fake data (QGraphicsScene)."""

from __future__ import annotations

import re

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen, QWheelEvent
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QStyleOptionGraphicsItem,
    QWidget,
)

from src.fakedata import fill
from src.parser import Node
from src.units import PX_PER_MM, color_rgb, parse_number

MARK_COLORS = {"added": "#2E9E5B", "removed": "#D2452F", "changed": "#D19A0F"}
DATA_BANDS = {"TfrxMasterData", "TfrxDetailData", "TfrxSubdetailData"}
FAKE_ROWS = 3
PAGE_GAP = 48
LABEL_COLOR = QColor("#8A94A3")
_HTML_TAG = re.compile(r"<[^>]+>")
_H_ALIGN = {
    "haCenter": Qt.AlignmentFlag.AlignHCenter,
    "haRight": Qt.AlignmentFlag.AlignRight,
    "haBlock": Qt.AlignmentFlag.AlignJustify,
}
_V_ALIGN = {"vaCenter": Qt.AlignmentFlag.AlignVCenter, "vaBottom": Qt.AlignmentFlag.AlignBottom}


def _pen(color: QColor, width: float = 1.0, style: Qt.PenStyle = Qt.PenStyle.SolidLine) -> QPen:
    return QPen(QBrush(color), width, style)


def _num(node: Node, prop: str, default: float = 0.0) -> float:
    value = parse_number(node.attrs.get(prop))
    return default if value is None else value


def _color(value: str | None, default: QColor | None) -> QColor | None:
    if value is None:
        return default
    rgb = color_rgb(value)
    return QColor(*rgb) if rgb else None


def _font(node: Node) -> QFont:
    font = QFont(node.attrs.get("Font.Name", "Arial"))
    font.setPixelSize(max(1, int(abs(_num(node, "Font.Height", -13)))))
    style = int(_num(node, "Font.Style"))
    font.setBold(bool(style & 1))
    font.setItalic(bool(style & 2))
    font.setUnderline(bool(style & 4))
    font.setStrikeOut(bool(style & 8))
    return font


class BoxItem(QGraphicsRectItem):
    """A memo/cell/shape: fill, optional text and FastReport frame lines."""

    def __init__(self, rect: QRectF, node: Node, text: str = "", ellipse: bool = False):
        super().__init__(rect)
        self.text = text
        self.ellipse = ellipse
        self.font = _font(node)
        self.text_color = _color(node.attrs.get("Font.Color"), QColor("black"))
        self.fill = _color(node.attrs.get("Fill.BackColor") or node.attrs.get("Color"), None)
        self.frame_bits = 15 if ellipse else int(_num(node, "Frame.Typ"))
        frame_color = _color(node.attrs.get("Frame.Color"), QColor("black")) or QColor("black")
        self.frame_pen = _pen(frame_color, max(0.5, _num(node, "Frame.Width", 1)))
        self.setPen(self.frame_pen)  # so boundingRect() covers the real frame width
        flags = _H_ALIGN.get(node.attrs.get("HAlign", ""), Qt.AlignmentFlag.AlignLeft).value
        flags |= _V_ALIGN.get(node.attrs.get("VAlign", ""), Qt.AlignmentFlag.AlignTop).value
        if node.attrs.get("WordWrap", "True") == "True":
            flags |= Qt.TextFlag.TextWordWrap.value
        self.text_flags = int(flags)
        self.gap = QPointF(_num(node, "GapX", 2), _num(node, "GapY", 1))

    def paint(
        self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget | None = None
    ) -> None:
        r = self.rect()
        painter.setPen(Qt.PenStyle.NoPen)
        if self.fill is not None:
            painter.setBrush(self.fill)
            painter.drawEllipse(r) if self.ellipse else painter.drawRect(r)
        if self.text:
            painter.save()
            painter.setClipRect(r)
            painter.setFont(self.font)
            painter.setPen(self.text_color or QColor("black"))
            inner = r.adjusted(self.gap.x(), self.gap.y(), -self.gap.x(), -self.gap.y())
            painter.drawText(inner, self.text_flags, self.text)
            painter.restore()
        painter.setPen(self.frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if self.ellipse:
            painter.drawEllipse(r)
            return
        for bit, (a, b) in (
            (1, (r.topLeft(), r.bottomLeft())),
            (2, (r.topRight(), r.bottomRight())),
            (4, (r.topLeft(), r.topRight())),
            (8, (r.bottomLeft(), r.bottomRight())),
        ):
            if self.frame_bits & bit:
                painter.drawLine(a, b)


class ReportScene(QGraphicsScene):
    """All report pages stacked vertically; data bands repeated with fake rows."""

    def __init__(self, report: Node, marks: dict[str, str]):
        super().__init__()
        self.marks = marks
        self.object_rects: dict[str, QRectF] = {}
        y = 0.0
        for page in report.pages:
            y = self._page(page, y) + PAGE_GAP

    # -- layout -------------------------------------------------------------
    def _page(self, page: Node, top: float) -> float:
        width = _num(page, "PaperWidth", 210) * PX_PER_MM
        height = _num(page, "PaperHeight", 297) * PX_PER_MM
        left = _num(page, "LeftMargin", 10) * PX_PER_MM
        margin_top = _num(page, "TopMargin", 10) * PX_PER_MM
        margin_bottom = _num(page, "BottomMargin", 10) * PX_PER_MM

        sheet = self.addRect(
            QRectF(0, top, width, height), QPen(Qt.PenStyle.NoPen), QBrush(QColor("white"))
        )
        sheet.setZValue(-10)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 60))
        sheet.setGraphicsEffect(shadow)

        bands = [b for b in page.children if b.is_band and b.tag.startswith("Tfrx")]
        bands.sort(key=lambda b: _num(b, "Top"))
        footers = [b for b in bands if b.tag == "TfrxPageFooter"]
        y = top + margin_top
        for band in bands:
            if band in footers:
                continue
            for row in range(FAKE_ROWS if band.tag in DATA_BANDS else 1):
                y += self._band(band, left, y, row)
        footer_y = max(y, top + height - margin_bottom - sum(_num(f, "Height") for f in footers))
        for footer in footers:
            footer_y += self._band(footer, left, footer_y, 0)
        bottom = max(top + height, footer_y + margin_bottom)
        sheet.setRect(QRectF(0, top, width, bottom - top))
        self._mark(page, QRectF(0, top, width, bottom - top))
        return bottom

    def _band(self, band: Node, x: float, y: float, row: int) -> float:
        rect = QRectF(x + _num(band, "Left"), y, _num(band, "Width"), _num(band, "Height"))
        outline = self.addRect(rect, _pen(LABEL_COLOR, 0.6, Qt.PenStyle.DotLine))
        outline.setZValue(-5)
        if row == 0:
            label = QGraphicsSimpleTextItem(band.key)
            label.setFont(QFont("Segoe UI", 7))
            label.setBrush(QBrush(LABEL_COLOR))
            label.setPos(4, y + 1)
            self.addItem(label)
            self._mark(band, rect)
        for child in band.children:
            self._object(child, rect, row)
        return rect.height()

    def _object(self, node: Node, band: QRectF, row: int) -> None:
        if not node.named or "Left" not in node.attrs and node.tag != "TfrxTableObject":
            return
        x, y = band.x() + _num(node, "Left"), band.y() + _num(node, "Top")
        w, h = _num(node, "Width"), _num(node, "Height")
        align = node.attrs.get("Align", "baNone")
        if align in ("baWidth", "baClient"):
            x, w = band.x(), band.width()
        if align == "baClient":
            y, h = band.y(), band.height()
        elif align == "baBottom":
            y = band.bottom() - h
        elif align == "baRight":
            x = band.right() - w
        elif align == "baCenter":
            x = band.x() + (band.width() - w) / 2
        rect = QRectF(x, y, w, h)

        if node.tag == "TfrxTableObject":
            rect = self._table(node, QPointF(x, y), row)
        elif node.tag == "TfrxLineView":
            color = _color(
                node.attrs.get("Color") or node.attrs.get("Frame.Color"), QColor("black")
            )
            self.addLine(
                x,
                y,
                x + w,
                y + h,
                _pen(color or QColor("black"), max(0.5, _num(node, "Frame.Width", 1))),
            )
        elif node.tag == "TfrxShapeView":
            shape = BoxItem(rect, node, ellipse=node.attrs.get("Shape") == "skEllipse")
            shape.frame_bits = 15  # shapes always draw their outline
            self.addItem(shape)
        elif node.tag == "TfrxPictureView":
            pen = _pen(LABEL_COLOR, 0.8, Qt.PenStyle.DashLine)
            self.addRect(rect, pen)
            self.addLine(rect.left(), rect.top(), rect.right(), rect.bottom(), pen)
            self.addLine(rect.left(), rect.bottom(), rect.right(), rect.top(), pen)
        elif node.tag in ("TfrxMemoView", "TfrxSysMemoView"):
            text = fill(node.attrs.get("Text", ""), row)
            if node.attrs.get("AllowHTMLTags") == "True":
                text = _HTML_TAG.sub("", text)
            self.addItem(BoxItem(rect, node, text))
        else:  # barcodes, checkboxes, rich text, ...: honest placeholder
            self.addRect(rect, _pen(LABEL_COLOR, 0.8, Qt.PenStyle.DashLine))
            label = QGraphicsSimpleTextItem(node.tag.removeprefix("Tfrx"))
            label.setFont(QFont("Segoe UI", 7))
            label.setBrush(QBrush(LABEL_COLOR))
            label.setPos(rect.topLeft() + QPointF(2, 1))
            self.addItem(label)
        if row == 0:
            self._mark(node, rect)

    def _table(self, table: Node, origin: QPointF, row: int) -> QRectF:
        widths = [_num(c, "Width") for c in table.children if c.tag == "TfrxTableColumn"]
        y = origin.y()
        for table_row in (c for c in table.children if c.tag == "TfrxTableRow"):
            height, x = _num(table_row, "Height"), origin.x()
            for width, cell in zip(widths, table_row.children, strict=False):
                rect = QRectF(x, y, width, height)
                self.addItem(BoxItem(rect, cell, fill(cell.attrs.get("Text", ""), row)))
                if row == 0:
                    self._mark(cell, rect)
                x += width
            y += height
        return QRectF(origin.x(), origin.y(), sum(widths), y - origin.y())

    def _mark(self, node: Node, rect: QRectF) -> None:
        self.object_rects.setdefault(node.key, rect)
        kind = self.marks.get(node.key)
        if kind:
            color = QColor(MARK_COLORS[kind])
            pen = _pen(color, 1.6)
            fill_color = QColor(color)
            fill_color.setAlpha(28)
            item = self.addRect(rect.adjusted(-1, -1, 1, 1), pen, QBrush(fill_color))
            item.setZValue(5)


class PreviewView(QGraphicsView):
    """Zoomable view; emits zoomed() so a sibling view can follow."""

    zoomed = Signal(float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._focus: QGraphicsItem | None = None
        self.focus_color = QColor("#5B4BB7")

    def show_report(self, report: Node | None, marks: dict[str, str], placeholder: str) -> None:
        self._focus = None
        if report is None:
            scene = QGraphicsScene()
            hint = scene.addSimpleText(placeholder, QFont("Segoe UI", 11))
            hint.setBrush(QBrush(LABEL_COLOR))
        else:
            scene = ReportScene(report, marks)
        self._scene = scene  # keep a Python reference alive
        self.setScene(scene)
        self.setSceneRect(scene.itemsBoundingRect().adjusted(-24, -24, 24, 24))

    def focus_object(self, name: str | None) -> None:
        scene = self.scene()
        if self._focus is not None and self._focus.scene() is scene:
            scene.removeItem(self._focus)
        self._focus = None
        rect = getattr(scene, "object_rects", {}).get(name or "")
        if rect is None:
            return
        self._focus = scene.addRect(rect.adjusted(-4, -4, 4, 4), _pen(self.focus_color, 2.5))
        self._focus.setZValue(10)
        self.centerOn(rect.center())

    def apply_zoom(self, factor: float) -> None:
        self.scale(factor, factor)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            dy = event.angleDelta().y()
            if dy == 0:
                return super().wheelEvent(event)
            factor = 1.15 if dy > 0 else 1 / 1.15
            self.apply_zoom(factor)
            self.zoomed.emit(factor)
        else:
            super().wheelEvent(event)
