"""Parse FastReport VCL (.fr3) templates into a generic, diffable node tree."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# Business key of list entries, by container tag.
_ITEM_KEYS = {
    "Datasets": "DataSetName",
    "FieldDefs": "FieldName",
    "Parameters": "Name",
    "Variables": "Name",
}


@dataclass(eq=False)
class Node:
    tag: str
    key: str
    attrs: dict[str, str]
    named: bool
    children: list[Node] = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False)

    @property
    def path(self) -> tuple[str, ...]:
        """Keys from the top-level element (page, data page, ...) down to this node."""
        keys: list[str] = []
        node: Node | None = self
        while node is not None and node.parent is not None:
            keys.append(node.key)
            node = node.parent
        return tuple(reversed(keys))

    @property
    def is_band(self) -> bool:
        return self.parent is not None and self.parent.tag == "TfrxReportPage"

    @property
    def pages(self) -> list[Node]:
        return [c for c in self.children if c.tag == "TfrxReportPage"]

    def walk(self) -> Iterator[Node]:
        """All descendants in document order (excluding self)."""
        for child in self.children:
            yield child
            yield from child.walk()

    def find(self, name: str) -> Node | None:
        return next((n for n in self.walk() if n.named and n.key == name), None)

    def named_owner(self) -> Node | None:
        """This node if it has a Name, otherwise the nearest named ancestor."""
        node: Node | None = self
        while node is not None and not node.named:
            node = node.parent
        return node


def _build(element: ET.Element, parent: Node | None, index: int) -> Node:
    attrs = dict(element.attrib)
    name = attrs.get("Name") if element.tag != "item" else None
    if name:
        key = name
    elif element.tag == "item" and parent is not None:
        key = attrs.get(_ITEM_KEYS.get(parent.tag, ""), "") or f"#{index}"
    else:
        key = element.tag
    node = Node(element.tag, key, attrs, named=bool(name), parent=parent)
    node.children = [_build(child, node, i) for i, child in enumerate(element, start=1)]
    return node


def parse_report(source: str | bytes | Path) -> Node:
    """Parse .fr3 XML given as text, bytes or file path."""
    if isinstance(source, Path):
        root = ET.parse(source).getroot()
    else:
        root = ET.fromstring(source)
    return _build(root, None, 0)
