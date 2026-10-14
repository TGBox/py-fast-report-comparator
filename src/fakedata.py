"""Generic, obviously fake values for FastReport expressions (never real patient data)."""

import re
from datetime import date

_EXPRESSION = re.compile(r"\[([^\[\]]+)\]")
_FIELD = re.compile(r'(\w+)\."([^"]+)"')

# (substring of the lower-cased field name, values per row) – first match wins.
_RULES: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
    (("vname", "vorname", "firstname"), ("Max", "Erika", "Paul")),
    (("patient",), ("Max Mustermann", "Erika Musterfrau", "Paul Beispiel")),
    (("inhaber", "arzt", "therapeut"), ("Dr. Anna Beispiel",)),
    (("resource", "behandler"), ("Behandler A", "Behandler B", "Raum 1")),
    (("strasse", "street"), ("Musterstraße", "Beispielweg", "Hauptstraße")),
    (("hausnummer", "hnr"), ("1", "12a", "7")),
    (("plz", "zip"), ("12345", "54321", "10115")),
    (("ort", "city", "stadt"), ("Musterstadt", "Beispielhausen", "Neustadt")),
    (("telefon", "phone", "fax", "mobil", "handy", "tel"), ("0123 456789",)),
    (("kasse", "kostentraeger"), ("Musterkasse",)),
    (("email", "mail"), ("info@beispiel.de",)),
    (("website", "homepage", "url"), ("www.beispiel.de",)),
    (("uhrzeit", "zeiten"), ("09:00 – 09:30", "10:00 – 10:45", "14:15 – 15:00")),
    (("start", "beginn"), ("09:00",)),
    (("ende", "end"), ("09:30",)),
    (
        ("datum", "date", "_am", "geburt", "birth", "created", "erstellt"),
        ("01.01.2026", "02.01.2026", "15.03.2026"),
    ),
    (
        ("brutto", "netto", "betrag", "summe", "preis", "zuzahlung", "bezahlt", "gebuehr"),
        ("123,45", "67,80", "10,00"),
    ),
    (("nr", "nummer", "id"), ("1001", "1002", "1003")),
    (("title", "titel", "bezeichnung", "leistung"), ("Beispieltermin", "Kontrolle", "Therapie")),
    (("description", "bemerkung", "hinweis", "text", "notiz"), ("Beispieltext",)),
    (("anzahl", "count", "menge", "einheit"), ("2", "1", "3")),
    (("namenszusatz", "zusatz"), ("Gemeinschaftspraxis",)),
    (("name", "nachname"), ("Mustermann", "Musterfrau", "Beispiel")),
]
_BUILTINS = {"page": "1", "page#": "1", "totalpages": "1", "totalpages#": "1", "time": "12:00"}


def fake_field(dataset: str, field: str, row: int = 0) -> str:
    name = field.lower()
    if name == "name" and dataset.lower() == "praxis":
        return "Praxis Beispiel"
    for needles, values in _RULES:
        if any(n in name for n in needles):
            return values[row % len(values)]
    return f"‹{field}›"


def _evaluate(expression: str, row: int, today: date) -> str:
    key = expression.strip().lower()
    if key == "date":
        return today.strftime("%d.%m.%Y")
    if key in ("line", "line#"):
        return str(row + 1)
    if key in _BUILTINS:
        return _BUILTINS[key]
    field = _FIELD.search(expression)
    if field:
        return fake_field(field.group(1), field.group(2), row)
    return f"‹{expression.strip()}›"


def fill(text: str, row: int = 0, today: date | None = None) -> str:
    """Replace every [expression] in a memo text with a fake value."""
    today = today or date.today()
    return _EXPRESSION.sub(lambda m: _evaluate(m.group(1), row, today), text)
