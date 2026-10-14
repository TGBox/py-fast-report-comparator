"""Turn a Difference into one readable German sentence."""

from __future__ import annotations

import difflib

from src.differ import GEOMETRY, Difference
from src.units import color_text, delphi_date_text, font_style_text, frame_text, mm, pt

OBJECT_NAMES = {
    "TfrxReport": "Bericht",
    "TfrxReportPage": "Seite",
    "TfrxDataPage": "Datenseite",
    "TfrxFDQuery": "Datenabfrage",
    "TfrxMemoView": "Textfeld",
    "TfrxLineView": "Linie",
    "TfrxShapeView": "Form",
    "TfrxPictureView": "Bild",
    "TfrxBarCodeView": "Barcode",
    "TfrxCheckBoxView": "Checkbox",
    "TfrxRichView": "RTF-Text",
    "TfrxSubreport": "Unterbericht",
    "TfrxTableObject": "Tabelle",
    "TfrxTableColumn": "Tabellenspalte",
    "TfrxTableRow": "Tabellenzeile",
    "TfrxTableCell": "Tabellenzelle",
    "TfrxPageHeader": "Seitenkopf",
    "TfrxPageFooter": "Seitenfuß",
    "TfrxReportTitle": "Berichtstitel",
    "TfrxReportSummary": "Berichtsabschluss",
    "TfrxHeader": "Kopfband",
    "TfrxFooter": "Fußband",
    "TfrxMasterData": "Datenband",
    "TfrxDetailData": "Detailband",
    "TfrxSubdetailData": "Unterdetailband",
    "TfrxGroupHeader": "Gruppenkopf",
    "TfrxGroupFooter": "Gruppenfuß",
    "TfrxChild": "Unterband",
    "TfrxColumnHeader": "Spaltenkopf",
    "TfrxColumnFooter": "Spaltenfuß",
    "TfrxOverlay": "Overlay",
    "Datasets": "Datenquellen-Liste",
    "Variables": "Variablen-Liste",
    "FieldDefs": "Felddefinitionen",
    "Parameters": "Parameter-Liste",
    "Formats": "Anzeigeformate",
}
_ITEM_NAMES = {
    "Datasets": "Datenquellen-Verknüpfung",
    "FieldDefs": "Feld",
    "Parameters": "Parameter",
    "Variables": "Variable",
    "Formats": "Anzeigeformat",
}
PROP_NAMES = {
    "Left": "Links",
    "Top": "Oben",
    "Width": "Breite",
    "Height": "Höhe",
    "Font.Height": "Schriftgröße",
    "Font.Name": "Schriftart",
    "Font.Style": "Schriftstil",
    "Font.Color": "Schriftfarbe",
    "Font.Charset": "Zeichensatz",
    "Frame.Typ": "Rahmen",
    "Frame.Color": "Rahmenfarbe",
    "Frame.Width": "Rahmenstärke",
    "Fill.BackColor": "Hintergrundfarbe",
    "Color": "Farbe",
    "HAlign": "Horizontale Ausrichtung",
    "VAlign": "Vertikale Ausrichtung",
    "Align": "Ausrichtung im Band",
    "Visible": "Sichtbar",
    "WordWrap": "Zeilenumbruch",
    "AllowHTMLTags": "HTML-Tags erlaubt",
    "DataSet": "Datenquelle",
    "DataSetName": "Datenquelle",
    "DataField": "Datenfeld",
    "DisplayFormat.FormatStr": "Anzeigeformat",
    "DisplayFormat.Kind": "Formatart",
    "Highlight.Condition": "Hervorhebungsbedingung",
    "StretchMode": "Dehnungsmodus",
    "ShiftMode": "Verschiebemodus",
    "PaperWidth": "Papierbreite",
    "PaperHeight": "Papierhöhe",
    "PaperSize": "Papierformat",
    "TopMargin": "Rand oben",
    "BottomMargin": "Rand unten",
    "LeftMargin": "Rand links",
    "RightMargin": "Rand rechts",
    "Columns": "Spalten",
    "Child": "Unterband",
    "StartNewPage": "Neue Seite beginnen",
    "Stretched": "Dehnbar",
    "PrintOnFirstPage": "Auf erster Seite drucken",
    "PrintOnLastPage": "Auf letzter Seite drucken",
    "ReportOptions.LastChange": "Zuletzt geändert",
    "ReportOptions.CreateDate": "Erstellt",
    "ReportOptions.Author": "Autor",
    "Expression": "Ausdruck",
    "Value": "Wert",
    "FieldType": "Feldtyp",
    "Condition": "Bedingung",
    "FillType": "Füllart",
    "Size": "Größe",
    "DataType": "Datentyp",
    "Shape": "Formtyp",
}
_MM_PROPS = {
    "PaperWidth",
    "PaperHeight",
    "TopMargin",
    "BottomMargin",
    "LeftMargin",
    "RightMargin",
}  # already stored in millimetres
_ENUMS = {
    "haLeft": "links",
    "haCenter": "zentriert",
    "haRight": "rechts",
    "haBlock": "Blocksatz",
    "vaTop": "oben",
    "vaCenter": "mittig",
    "vaBottom": "unten",
    "baNone": "keine",
    "baLeft": "links",
    "baRight": "rechts",
    "baCenter": "zentriert",
    "baWidth": "volle Breite",
    "baBottom": "unten",
    "baClient": "ganzes Band",
    "True": "ja",
    "False": "nein",
}
_PAPER_SIZES = {"9": "A4", "11": "A5", "70": "A6", "256": "benutzerdefiniert"}
_MULTILINE_PROPS = {"ScriptText.Text": "Skript", "SQL.Text": "SQL"}


def _num(value: float, decimals: int = 2) -> str:
    text = f"{value:.{decimals}f}".rstrip("0").rstrip(".") if decimals else f"{value:.0f}"
    return text.replace(".", ",")


def _mm_text(value: float) -> str:
    return f"{value + 0.0:.1f} mm".replace(".", ",").replace("-0,0", "0,0")


def _short(text: str, limit: int = 80) -> str:
    text = text.replace("\r\n", " ⏎ ").replace("\n", " ⏎ ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_value(prop: str, value: str | None) -> str:
    """Render a raw attribute value for humans."""
    if value is None:
        return "Standard"
    if prop in GEOMETRY:
        return _mm_text(mm(value))
    if prop in _MM_PROPS:
        return _mm_text(float(value.replace(",", ".")))
    if prop.endswith("Font.Height"):
        return f"{_num(pt(value))} pt"
    if prop.endswith("Font.Style"):
        return font_style_text(value)
    if prop.endswith("Frame.Typ"):
        return frame_text(value)
    if prop.endswith("Color"):
        return color_text(value)
    if prop.startswith("ReportOptions.") and prop.endswith("Date") or prop.endswith("LastChange"):
        return delphi_date_text(value)
    if prop == "PaperSize":
        return _PAPER_SIZES.get(value, value)
    return _ENUMS.get(value, f"„{_short(value)}“" if value else "leer")


def object_label(d: Difference) -> str:
    key = d.path[-1] if d.path else ""
    if d.tag == "item":
        container = d.path[-2] if len(d.path) > 1 else ""
        return f"{_ITEM_NAMES.get(container, 'Eintrag')} „{key}“"
    return f"{OBJECT_NAMES.get(d.tag, d.tag)} „{key}“" if key else OBJECT_NAMES.get(d.tag, d.tag)


def prop_label(prop: str) -> str:
    if prop.startswith("Highlight."):
        return f"Hervorhebung, {prop_label(prop.removeprefix('Highlight.'))}"
    return PROP_NAMES.get(prop, prop)


def _move(d: Difference) -> str:
    delta = mm(d.new or "0") - mm(d.old or "0")
    if d.prop == "Left":
        direction = "rechts" if delta > 0 else "links"
    else:
        direction = "unten" if delta > 0 else "oben"
    return (
        f"{_mm_text(abs(delta))} nach {direction} verschoben "
        f"({PROP_NAMES[d.prop]}: {format_value(d.prop, d.old)} → "
        f"{format_value(d.prop, d.new)})."
    )


def _multiline(d: Difference) -> str:
    added = removed = 0
    for line in difflib.ndiff((d.old or "").splitlines(), (d.new or "").splitlines()):
        added += line.startswith("+ ")
        removed += line.startswith("- ")
    return f"{_MULTILINE_PROPS[d.prop]} geändert: {added} Zeilen hinzugefügt, {removed} entfernt."


def explain(d: Difference) -> str:
    if d.kind == "added":
        extra = f" mit Inhalt „{_short(d.new)}“" if d.new else ""
        return f"Neu in B: {object_label(d)}{extra}."
    if d.kind == "removed":
        extra = f" (Inhalt war „{_short(d.old)}“)" if d.old else ""
        return f"Entfernt in B: {object_label(d)}{extra}."
    if d.kind == "renamed":
        return f"Umbenannt: „{d.old}“ → „{d.new}“ (an gleicher Stelle)."

    prop = d.prop or ""
    if prop in ("Left", "Top") and d.old is not None and d.new is not None:
        return _move(d)
    if prop in _MULTILINE_PROPS:
        return _multiline(d)
    if prop == "Band":
        return f"In anderes Band verschoben: {d.old} → {d.new}."
    if prop == "Text":
        return f"Text geändert: {format_value(prop, d.old)} → {format_value(prop, d.new)}."
    if prop.startswith("On"):
        return f"Ereignis {prop}: {d.old or 'keins'} → {d.new or 'keins'}."
    return f"{prop_label(prop)}: {format_value(prop, d.old)} → {format_value(prop, d.new)}."
