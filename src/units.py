"""Conversions from raw FastReport VCL attribute values to readable German text."""

from datetime import datetime, timedelta

PX_PER_MM = 96 / 25.4

_NAMED_COLORS = {
    0x000000: "Schwarz",
    0xFFFFFF: "Weiß",
    0x0000FF: "Rot",
    0x008000: "Grün",
    0xFF0000: "Blau",
    0x808080: "Grau",
    0xC0C0C0: "Silber",
}
# Delphi system colours are 0xFF0000xx (negative as signed int32).
_SYSTEM_COLORS = {
    0x05: "Fensterhintergrund",
    0x08: "Fenstertext",
    0x0F: "Schaltflächenfläche",
    0x12: "Schaltflächentext",
}
_CL_NONE = 0x1FFFFFFF
_FONT_STYLES = ((1, "fett"), (2, "kursiv"), (4, "unterstrichen"), (8, "durchgestrichen"))
_FRAME_LINES = ((1, "links"), (2, "rechts"), (4, "oben"), (8, "unten"))


def parse_number(value: str | None) -> float | None:
    """Parse a FastReport number ('18,89765'); None if the value is not numeric."""
    if value is None:
        return None
    try:
        return float(value.replace(",", "."))
    except ValueError:
        return None


def mm(value: str) -> float:
    """Pixels (96 dpi) as stored in .fr3 -> millimetres."""
    return (parse_number(value) or 0.0) / PX_PER_MM


def pt(font_height: str) -> float:
    """Delphi Font.Height (negative pixel height at 96 dpi) -> points."""
    return abs(parse_number(font_height) or 0.0) * 72 / 96


def color_rgb(value: str) -> tuple[int, int, int] | None:
    """Delphi TColor -> (r, g, b); None for clNone. System colours map to black/white."""
    n = int(parse_number(value) or 0) & 0xFFFFFFFF
    if n == _CL_NONE:
        return None
    if n & 0xFF000000:
        return (255, 255, 255) if (n & 0xFF) in (0x05, 0x0F) else (0, 0, 0)
    return n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF


def color_text(value: str) -> str:
    n = int(parse_number(value) or 0) & 0xFFFFFFFF
    if n == _CL_NONE:
        return "keine"
    if n & 0xFF000000:
        return f"Systemfarbe {_SYSTEM_COLORS.get(n & 0xFF, hex(n & 0xFF))}"
    if n in _NAMED_COLORS:
        return _NAMED_COLORS[n]
    r, g, b = n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF
    return f"#{r:02X}{g:02X}{b:02X}"


def _bits(value: str, names: tuple[tuple[int, str], ...]) -> list[str]:
    n = int(parse_number(value) or 0)
    return [name for bit, name in names if n & bit]


def font_style_text(value: str) -> str:
    return ", ".join(_bits(value, _FONT_STYLES)) or "normal"


def frame_text(value: str) -> str:
    lines = _bits(value, _FRAME_LINES)
    if not lines:
        return "kein Rahmen"
    return "rundum" if len(lines) == 4 else ", ".join(lines)


def delphi_date_text(value: str) -> str:
    """Delphi TDateTime (days since 1899-12-30) -> 'dd.mm.yyyy hh:mm'."""
    days = parse_number(value) or 0.0
    return (datetime(1899, 12, 30) + timedelta(days=days)).strftime("%d.%m.%Y %H:%M")
