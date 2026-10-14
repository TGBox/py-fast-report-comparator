# py-fast-report-comparator

Vergleicht zwei FastReport-VCL-Vorlagen (`.fr3`) – z. B. Standardvorlage ↔ Kundenvorlage – und zeigt nur die bedeutsamen Unterschiede: als deutschen Satz erklärt, gefiltert nach Inhalt, Layout und Metadaten, mit einer Skizzen-Vorschau beider Vorlagen nebeneinander (gefüllt mit generischen Fake-Daten).

Details: [docs/SPEC.md](docs/SPEC.md)

## Voraussetzungen

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Setup & Ausführung

```bash
uv sync

# GUI starten (optional mit zwei Vorlagen)
uv run main
uv run main "testdata/Terminuebersicht_Terminübersicht.fr3" "testdata/Terminuebersicht_Terminübersicht Neu.fr3"

# Tests
uv run pytest -q

# Standalone-Exe mit PyInstaller bauen
uv run build
```

## Bedienung

| Aktion | Wie |
|---|---|
| Vorlage A / B öffnen | Werkzeugleiste oder `Strg+1` / `Strg+2`; oder Dateien ins Fenster ziehen (zwei Dateien = A und B, eine Datei rechts = B) |
| Unterschied ansehen | In der Liste anklicken – beide Vorschauen springen zum Objekt, Details (inkl. Zeilen-Diff bei Skript/SQL) unten links |
| Filtern | Häkchen *Inhalt*, *Layout*, *Metadaten* |
| Zoomen | `Strg` + Mausrad (beide Seiten zoomen mit) |
| Exakte Druckansicht | Schalter *Druckansicht* – rendert mit der echten FastReport-Engine (einmalig `delphi/FrxRender` bauen, siehe [README](delphi/FrxRender/README.md)) |
| Vollbild | `F11` |

Farben in der Vorschau: **grün** neu in B, **rot** entfernt in B, **gelb** geändert.

Bewusst nicht enthalten: pixelgenaues Rendering, Skriptausführung, Barcodes (Platzhalter), Seitenumbruch-/Gruppenlogik, Bearbeiten von Vorlagen.

## Projektstruktur

```
src/        main.py (Fenster) · preview.py (Vorschau) · printpreview.py (Druckansicht) · parser.py · differ.py · explain.py · fakedata.py · units.py
tests/      pytest, inkl. Golden-Tests gegen testdata/
docs/       SPEC.md, intent/
delphi/     FrxRender – Render-Hilfsprogramm mit der echten FastReport-Engine
tasks/      plan.md, todo.md
```
