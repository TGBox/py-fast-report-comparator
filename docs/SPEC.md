# Spec: py-fast-report-comparator

Status: **Freigegeben 2026-10-14** · Intent: [docs/intent/fr3-comparator.md](intent/fr3-comparator.md)

## Objective

Daniel vergleicht im Support FastReport-VCL-Vorlagen (`.fr3`): Standardvorlage ↔ Kundenvorlage bzw. Standard ↔ Neuimplementierung. Ein Text-Diff des XML ist unbrauchbar (Design-Koordinaten, Float-Rauschen, Default-Attribute, Einzeiler mit `&#13;&#10;`). Die App zeigt nur die **bedeutsamen** Unterschiede, erklärt jeden in einem deutschen Satz und zeigt beide Vorlagen als Skizze mit Fake-Daten nebeneinander.

### User Stories

1. Ich wähle Datei A und B (Dialog oder Drag & Drop) und sehe sofort eine nach Seite → Band → Objekt gruppierte Liste der Unterschiede.
2. Jeder Eintrag ist ein deutscher Satz, z. B.
   - „Memo *Memo6* (Band *Header1*): 73,5 mm nach links verschoben, Breite 25,0 → 117,0 mm.“
   - „Text geändert: ‚Behandler‘ → ‚Behandlung‘.“
   - „Neu in B: Memo *praxisname* mit `[praxis."name"]`.“
   - „Entfernt in B: Memo *Eventsresourcename*.“
   - „Datenquelle *praxis* neu in B (SQL siehe Details).“
3. Ich kann filtern: **Inhalt** (Text, Ausdrücke, Datenfelder, Datasets, SQL, Skript, Sichtbarkeit, Events) / **Layout** (Position, Größe, Schrift, Rahmen, Farbe, Ausrichtung) / **Metadaten** (Autor, LastChange, …; standardmäßig ausgeblendet).
4. Skript (`ScriptText`) und SQL (`SQL.Text` der `TfrxFDQuery`) erscheinen als Zeilen-Diff.
5. Die Vorschau zeigt A und B nebeneinander (synchron gescrollt/gezoomt): Seiten in Papiergröße, Bänder gestapelt, Objekte an Originalposition, Platzhalter `[...]` mit Fake-Werten gefüllt, Datenbänder 3× wiederholt. Geänderte Objekte gelb, neue grün, entfernte rot umrandet.
6. Klick auf einen Listeneintrag springt in der Vorschau zum Objekt und hebt es hervor.

## Erkenntnisse aus `testdata/` (12 Dateien, 6 Paare)

- Struktur: `TfrxReport` → `TfrxDataPage` (`TfrxFDQuery` mit `SQL.Text`, `FieldDefs`, `Parameters`) + `TfrxReportPage` → Bänder (`PageHeader`, `ReportTitle`, `Header`, `GroupHeader`, `MasterData`, `DetailData`, `Child`, `ReportSummary`, `PageFooter`) → Objekte (`MemoView`, `LineView`, `ShapeView`, `PictureView`, `TableObject`→`TableRow`→`TableCell`→`MemoView`), dazu `Datasets`, `Variables`.
- Einheiten: Pixel bei 96 dpi (1 mm = 3,7795 px), Dezimalkomma (`'18,89765'`). Papier in mm (`PaperWidth`).
- Ausdrücke: `[Dataset."feld"]`, `<Dataset."feld">` innerhalb von Funktionen, `[Date]`, `[Page#]`, `[TotalPages]`, eigene Skriptfunktionen `[GetZuzahlungSumValue()]`, `iif(...)`.
- **Rauschen, das ignoriert/abgeschwächt werden muss** (an echten Paaren beobachtet):
  - `Top` von **Bändern** ist Designer-Position, nicht Druckposition → nur Höhe/Reihenfolge zählt.
  - Float-Rauschen (`18,89765` vs. `18,89767456`) → Toleranz 0,05 mm.
  - Attribute, die nur in einer Datei explizit auf ihrem Default stehen (`ContentScaleOptions.*="0"`) → als gleich werten.
  - `ReportOptions.LastChange`/`CreateDate` → Kategorie Metadaten.
- Farben: Delphi-`TColor` (BGR-Integer, negative Werte = Systemfarben, z. B. `-16777208` = clWindowText ≈ Schwarz). `Font.Style` ist Bitmaske (1 fett, 2 kursiv, 4 unterstrichen, 8 durchgestrichen). `Frame.Typ` Bitmaske (1 links, 2 rechts, 4 oben, 8 unten).

## Tech Stack

- Python ≥ 3.12, PySide6 (vorhanden). **Keine weiteren Laufzeit-Abhängigkeiten**: `xml.etree.ElementTree`, `difflib`, `dataclasses` aus der Standardbibliothek. Fake-Daten per eigener Tabelle (kein Faker).
- Vorschau mit `QGraphicsScene`/`QGraphicsView`.

## Commands

```bash
uv sync                       # Abhängigkeiten
uv run main                   # GUI starten
uv run main A.fr3 B.fr3       # GUI mit vorgeladenem Paar
uv run pytest -q              # Tests
uv run ruff check --fix src tests && uv run ruff format src tests
uv run build                  # PyInstaller-Exe
```

## Project Structure

```
src/
  main.py            → Hauptfenster, Worker-Thread, Theme (QSS), F11, QSettings, CLI-Argumente
  preview.py         → QGraphicsScene-Skizze einer Vorlage, Markierungen, Fokus, Zoom
  parser.py          → .fr3 → generischer Knotenbaum (kein Qt)
  differ.py          → Knotenbaum × Knotenbaum → list[Difference], Rauschregeln (kein Qt)
  explain.py         → Difference → deutscher Satz (kein Qt)
  fakedata.py        → [Ausdruck] → Fake-Wert (kein Qt)
  units.py           → px↔mm, Delphi-Farben/-Datum, Font-/Frame-Bitmasken (kein Qt)
tests/
  test_units.py, test_parser.py, test_differ.py, test_explain.py, test_fakedata.py
  test_testdata_pairs.py → Golden-Tests gegen testdata/
  test_ui_smoke.py       → Offscreen: alle 12 Dateien rendern, Fenster vergleicht ein Paar
docs/  SPEC.md, intent/
tasks/ plan.md, todo.md
```

Logik (parser/differ/explain/fakedata/units) ist Qt-frei und vollständig per pytest testbar.

## Code Style

```python
@dataclass(frozen=True)
class Difference:
    path: tuple[str, ...]          # ("Page1", "MasterData1", "Memo6")
    kind: Literal["added", "removed", "changed"]
    category: Literal["content", "layout", "meta"]
    prop: str | None = None        # "Left", "Text", ...
    old: str | None = None
    new: str | None = None


def px_to_mm(value: str) -> float:
    """Convert a FastReport pixel string ('18,89765') to millimetres."""
    return float(value.replace(",", ".")) / PX_PER_MM
```

Englische Bezeichner/Kommentare, deutsche UI-Texte, Typannotationen, Ruff (Zeilenlänge 100), `pathlib.Path`.

## Testing Strategy

- pytest, TDD (rot → grün → refactor) für alle Qt-freien Module.
- Unit-Tests mit kleinen Inline-XML-Fixtures pro Regel (Zuordnung, Toleranz, Band-Top-Ignorieren, Default-Gleichheit, Umbenennungs-Fallback, Erklärungssätze, Fake-Werte).
- Golden-Tests: für jedes der 6 Paare in `testdata/` erwartete Schlüssel-Unterschiede (z. B. Terminübersicht: `Memo3` Text „Behandler“→„Behandlung“, `praxis`-Query neu, `Eventsresourcename` entfernt) **und** erwartetes Nicht-Auftreten von Rauschen.
- Smoke-Test: alle 12 Dateien parsen + rendern ohne Exception (Preview-Szene offscreen, `QT_QPA_PLATFORM=offscreen`).
- UI wird manuell an den Testpaaren geprüft; keine Coverage-Quote, aber jede Diff-/Erklär-Regel hat einen Test.

## Boundaries

- **Always:** Tests vor jedem Commit grün, Ruff sauber, Logik Qt-frei halten, Parsen/Diffen im Worker-Thread, Dark+Light für jedes neue UI-Element.
- **Ask first:** neue Abhängigkeiten, Änderungen an `pyproject.toml`-Skripten/CI, Änderungen an diesem Spec-Umfang.
- **Never:** Vorlagen verändern oder zurückschreiben, Skripte ausführen, echte Patientendaten in Fake-Daten/Tests/Logs, `testdata/` modifizieren.

## Success Criteria

1. Alle 12 `testdata`-Dateien werden ohne Fehler geparst und gerendert.
2. Terminübersicht alt ↔ neu: Liste enthält die realen Änderungen (Texte, neue/entfernte Memos, neue Query `praxis`, Skript-Event `OnReportPrint`) und **keine** Einträge für Band-`Top`, Float-Rauschen < 0,05 mm oder Default-Attribute.
3. DINA4 ↔ Starkenburg: Ergebnis im Filter „Inhalt“ = genau die zwei Text-Änderungen (`Memo1`, `praxisplz1`).
4. Jeder Unterschied hat einen deutschen Satz mit Werten in mm/pt/Klartext (keine Rohwerte wie `-16777208` oder `Font.Style=2`).
5. Vorschau zeigt beide Vorlagen nebeneinander mit Fake-Daten; Klick in Liste → Objekt hervorgehoben; Markierungsfarben je Änderungsart.
6. Laden + Vergleichen eines Paares < 1 s, UI blockiert nicht.
7. F11 Vollbild, Fenstergeometrie per QSettings, Dark/Light umschaltbar.

## Entscheidungen (ehemals offene Fragen)

1. Umbenennungs-Fallback: Objekte gleichen Typs im gleichen Band mit ≥ 80 % Überlappung (Schnittfläche / größere Fläche) gelten als umbenannt.
2. `FieldDefs`, `Parameters`, `Variables`, `Datasets` und `Formats` werden **einzeln** gelistet (Schlüssel: `FieldName`, `Name`, `DataSetName`, Position).
3. Modell und Parser liegen zusammen in `src/parser.py` (generischer Knotenbaum statt eigener Klassen je Objekttyp) – weniger Code, deckt unbekannte Objekttypen automatisch ab.
