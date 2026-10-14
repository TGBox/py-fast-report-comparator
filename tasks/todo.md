# Tasks

## Phase 1: Kern (Qt-frei, TDD)
- [x] T1 `units.py` – px→mm, Font-Höhe→pt, Delphi-Farben, Font-Style/Frame-Bitmasken, Delphi-Datum → Klartext
  - Verify: `uv run pytest tests/test_units.py`
- [x] T2 `parser.py` – `.fr3` → Knotenbaum, Pfad (Seite → Band → Objekt), Item-Schlüssel
  - Verify: `uv run pytest tests/test_parser.py`, alle 12 testdata-Dateien parsen
- [x] T3 `differ.py` – added/removed/changed, Kategorien, Rauschregeln, Umbenennungs-Fallback, Items einzeln
  - Verify: `uv run pytest tests/test_differ.py`
- [x] T4 `explain.py` – deutscher Satz je Unterschied
  - Verify: `uv run pytest tests/test_explain.py`
- [x] T5 Golden-Tests gegen testdata (Erfolgskriterien 2–4)
  - Verify: `uv run pytest tests/test_testdata_pairs.py`
- [x] T6 `fakedata.py` – `[Ausdruck]` → generischer Fake-Wert
  - Verify: `uv run pytest tests/test_fakedata.py`

### Checkpoint: Kern komplett, alle Tests grün ✔ (55 Tests)

## Phase 2: Oberfläche
- [x] T7 `ui/preview.py` – Seite(n) als QGraphicsScene, Markierungen, Fokus auf Objekt
- [x] T8 `ui/main_window.py` – Dateiwahl/Drag&Drop, Worker-Thread, Unterschiedsbaum, Filter, Detail-/Zeilen-Diff, Vorschau A|B synchron
- [x] T9 Theme Dark/Light, F11, QSettings, CLI-Argumente
  - Verify: `uv run main testdata/…alt.fr3 testdata/…neu.fr3` manuell; Offscreen-Smoke-Test rendert alle 12 Dateien

### Checkpoint: Erfolgskriterien 1–7 manuell abgenommen
- [ ] `uv run pytest` inkl. `test_ui_smoke.py` auf Windows grün (Qt im Entwicklungs-Container nicht verfügbar)
- [ ] Daniel prüft Vorschau und Liste an echten Paaren
