"""Compare two parsed .fr3 reports and return the meaningful differences."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.parser import Node
from src.units import PX_PER_MM, parse_number

Kind = Literal["added", "removed", "changed", "renamed"]
Category = Literal["content", "layout", "meta"]

GEOMETRY = {"Left", "Top", "Width", "Height"}
TOLERANCE_PX = 0.05 * PX_PER_MM
RENAME_MIN_OVERLAP = 0.8

_META = {
    "Version",
    "IniFile",
    "DotMatrixReport",
    "HGuides.Text",
    "VGuides.Text",
    "LargeDesignHeight",
}
_META_PREFIXES = ("ReportOptions.", "PreviewOptions.", "PrintOptions.", "EngineOptions.")
_DESIGNER_ONLY_TAGS = {"TfrxDataPage", "TfrxFDQuery"}  # their geometry is designer-only
_LAYOUT = GEOMETRY | {
    "HAlign",
    "VAlign",
    "Align",
    "Color",
    "WordWrap",
    "WordBreak",
    "ParentFont",
    "Rotation",
    "Shape",
    "Curve",
    "Diagonal",
    "AutoWidth",
    "Center",
    "Stretched",
    "KeepAspectRatio",
    "Transparent",
    "TransparentColor",
    "HightQuality",
    "FillType",
    "Columns",
    "ColumnWidth",
    "ColumnGap",
    "ColumnPositions.Text",
    "GapX",
    "GapY",
    "LineSpacing",
    "CharSpacing",
    "ParagraphGap",
    "Underlines",
    "MinWidth",
    "MaxWidth",
    "MinHeight",
    "MaxHeight",
    "AutoSize",
    "TopMargin",
    "BottomMargin",
    "LeftMargin",
    "RightMargin",
    "PaperWidth",
    "PaperHeight",
    "PaperSize",
    "Orientation",
    "MirrorMode",
    "ShiftMode",
    "StretchMode",
    "AllowVectorExport",
}
_LAYOUT_PREFIXES = (
    "Font.",
    "Frame.",
    "Fill.",
    "FillGap.",
    "Highlight.Font.",
    "Highlight.Fill.",
    "Highlight.Frame.",
    "ContentScaleOptions.",
)


@dataclass(frozen=True)
class Difference:
    path: tuple[str, ...]  # e.g. ("Page1", "MasterData1", "Memo6"); () = report itself
    kind: Kind
    category: Category
    tag: str
    prop: str | None = None
    old: str | None = None
    new: str | None = None
    obj_a: str | None = None  # name of the affected named object in A (for preview marks)
    obj_b: str | None = None


def category_of(tag: str, prop: str) -> Category:
    if prop in _META or prop.startswith(_META_PREFIXES):
        return "meta"
    if tag in _DESIGNER_ONLY_TAGS and prop in GEOMETRY:
        return "meta"
    if prop in _LAYOUT or prop.startswith(_LAYOUT_PREFIXES):
        return "layout"
    return "content"


def _is_text(prop: str) -> bool:
    return prop == "Text" or prop.endswith(".Text") or prop in {"Expression", "Value"}


def _same(prop: str, old: str | None, new: str | None, is_band: bool) -> bool:
    if old == new or (prop == "Top" and is_band):
        return True
    if _is_text(prop):
        return (old or "") == (new or "")
    if old is None or new is None:  # a missing attribute means "default"; zero is the default
        present = new if old is None else old
        return present == "" or parse_number(present) == 0
    a, b = parse_number(old), parse_number(new)
    if a is None or b is None:
        return False
    return abs(a - b) <= (TOLERANCE_PX if prop in GEOMETRY else 0) + 1e-9


def _owner_name(node: Node | None) -> str | None:
    owner = node.named_owner() if node else None
    return owner.key if owner else None


def _node_category(node: Node, prop: str = "") -> Category:
    if "Formats" in node.path:  # display formats follow their expressions: formatting only
        return "layout"
    return category_of(node.tag, prop) if prop else "content"


def _entry(node: Node, kind: Kind, side: str) -> Difference:
    summary = node.attrs.get("Text") or node.attrs.get("SQL.Text")
    return Difference(
        node.path,
        kind,
        _node_category(node),
        node.tag,
        old=summary if side == "a" else None,
        new=summary if side == "b" else None,
        obj_a=_owner_name(node) if side == "a" else None,
        obj_b=_owner_name(node) if side == "b" else None,
    )


def _compare_attrs(a: Node, b: Node, out: list[Difference]) -> None:
    for prop in sorted(a.attrs.keys() | b.attrs.keys()):
        if prop == "Name":
            continue
        old, new = a.attrs.get(prop), b.attrs.get(prop)
        if not _same(prop, old, new, b.is_band):
            out.append(
                Difference(
                    b.path,
                    "changed",
                    _node_category(b, prop),
                    b.tag,
                    prop,
                    old,
                    new,
                    _owner_name(a),
                    _owner_name(b),
                )
            )


def _compare_unnamed_children(a: Node, b: Node, out: list[Difference]) -> None:
    """Containers and list items have no Name: match them by key below a matched parent."""
    kids_a = {c.key: c for c in a.children if not c.named}
    kids_b = {c.key: c for c in b.children if not c.named}
    for key, child_b in kids_b.items():
        child_a = kids_a.get(key)
        if child_a is None:
            out.append(_entry(child_b, "added", "b"))
        else:
            _compare_attrs(child_a, child_b, out)
            _compare_unnamed_children(child_a, child_b, out)
    out.extend(_entry(c, "removed", "a") for k, c in kids_a.items() if k not in kids_b)


def _rect(node: Node) -> tuple[float, float, float, float]:
    left, top, width, height = (
        parse_number(node.attrs.get(p)) or 0.0 for p in ("Left", "Top", "Width", "Height")
    )
    return left, top, left + width, top + height


def _overlap(a: Node, b: Node) -> float:
    """Intersection area divided by the larger area (lines get a 1 px thickness)."""
    ax1, ay1, ax2, ay2 = _rect(a)
    bx1, by1, bx2, by2 = _rect(b)
    w = min(ax2, bx2) - max(ax1, bx1)
    h = min(ay2, by2) - max(ay1, by1)
    if w < 0 or h < 0:
        return 0.0
    area = max(max(ax2 - ax1, 1) * max(ay2 - ay1, 1), max(bx2 - bx1, 1) * max(by2 - by1, 1))
    return max(w, 1) * max(h, 1) / area


def _match_renamed(only_a: list[Node], only_b: list[Node]) -> dict[Node, Node]:
    pairs: dict[Node, Node] = {}
    free_b = list(only_b)
    for node_a in only_a:
        candidates = [
            (_overlap(node_a, node_b), node_b)
            for node_b in free_b
            if node_b.tag == node_a.tag and _owner_name(node_b.parent) == _owner_name(node_a.parent)
        ]
        score, best = max(candidates, key=lambda c: c[0], default=(0.0, None))
        if best is not None and score >= RENAME_MIN_OVERLAP:
            pairs[node_a] = best
            free_b.remove(best)
    return pairs


def diff_reports(a: Node, b: Node) -> list[Difference]:
    out: list[Difference] = []
    _compare_attrs(a, b, out)
    _compare_unnamed_children(a, b, out)

    named_a = {n.key: n for n in a.walk() if n.named}
    named_b = {n.key: n for n in b.walk() if n.named}
    pairs = {named_a[k]: named_b[k] for k in named_a.keys() & named_b.keys()}
    only_a = [n for k, n in named_a.items() if k not in named_b]
    only_b = [n for k, n in named_b.items() if k not in named_a]
    renamed = _match_renamed(only_a, only_b)
    pairs |= renamed
    a_by_b = {nb: na for na, nb in pairs.items()}

    # Emit in document order of B, then everything that only exists in A.
    for node_b in named_b.values():
        node_a = a_by_b.get(node_b)
        if node_a is None:
            if node_b.parent not in a_by_b and node_b.parent.named:
                continue  # parent itself was added: report only the top-most new object
            out.append(_entry(node_b, "added", "b"))
            continue
        if node_a in renamed:
            out.append(
                Difference(
                    node_b.path,
                    "renamed",
                    "content",
                    node_b.tag,
                    None,
                    node_a.key,
                    node_b.key,
                    node_a.key,
                    node_b.key,
                )
            )
        parent_a, parent_b = _owner_name(node_a.parent), _owner_name(node_b.parent)
        if parent_a != parent_b:
            out.append(
                Difference(
                    node_b.path,
                    "changed",
                    "content",
                    node_b.tag,
                    "Band",
                    parent_a,
                    parent_b,
                    node_a.key,
                    node_b.key,
                )
            )
        _compare_attrs(node_a, node_b, out)
        _compare_unnamed_children(node_a, node_b, out)

    matched_a = set(pairs)
    for node_a in named_a.values():
        if node_a in matched_a:
            continue
        if node_a.parent.named and node_a.parent not in matched_a:
            continue
        out.append(_entry(node_a, "removed", "a"))
    return out
