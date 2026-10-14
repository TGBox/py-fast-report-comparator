# Implementation Plan: py-fast-report-comparator

Spec: [docs/SPEC.md](../docs/SPEC.md)

## Overview
Qt-freier Kern (Parser → Differ → Erklärung, Fake-Daten) per TDD, darauf eine PySide6-Oberfläche mit Unterschiedsliste und zwei synchronen Skizzen-Vorschauen.

## Architecture Decisions
- **Generischer Knotenbaum** (`Node(tag, name, attrs, children)`) statt typisierter Klassen: jedes `.fr3`-Element bleibt diffbar, auch unbekannte Objekttypen.
- **Zuordnung über `Name`** (in FastReport reportweit eindeutig), Listen-`item`s über fachlichen Schlüssel, Umbenennung über Überlappung.
- **Rauschregeln zentral im Differ** (Band-`Top`, Toleranz 0,05 mm, fehlend ≙ `0`/leer). Bool-Defaults werden bewusst *nicht* gleichgesetzt (Default je Property unterschiedlich).
- **Erklärung getrennt vom Diff** (`explain.py`), damit Wortlaut ohne Diff-Logik testbar ist.
- **Keine neuen Abhängigkeiten.** Tests laufen mit pytest; die Tests sind reine `assert`-Funktionen.

## Task List
Siehe [todo.md](todo.md).

## Risks and Mitigations
| Risiko | Impact | Mitigation |
|---|---|---|
| Unbekannte Properties werden falsch kategorisiert | Mittel | Default-Kategorie „Inhalt“ (lieber zu viel zeigen), Layout/Meta-Listen explizit |
| Vorschau weicht stark vom Druck ab (Band-Logik) | Mittel | Spec erlaubt Skizze; Bänder in Designer-Reihenfolge, Datenbänder 3× |
| PySide6/pytest im Entwicklungs-Container nicht installierbar (PyPI gesperrt) | Hoch | Kern mit eigenem Mini-Runner getestet; UI per `py_compile` geprüft, Endabnahme durch Daniel mit `uv run` |
