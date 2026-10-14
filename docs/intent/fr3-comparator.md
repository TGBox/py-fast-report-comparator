# Intent: py-fast-report-comparator

Bestätigt am 2026-10-14.

- **Ergebnis:** PySide6-Desktop-App, die zwei .fr3-Vorlagen (FastReport VCL) lädt, alle Unterschiede auflistet und jeden als verständlichen deutschen Satz erklärt.
- **Nutzer:** Daniel allein — vergleicht Standardvorlagen mit Kundenvorlagen und Neuimplementierungen.
- **Diff-Logik:** Regelbasiert, ohne KI. Zuordnung über `Name`, Positions-Fallback bei Umbenennung. Gruppiert nach Seite → Band. Filter Kosmetik vs. Inhalt. Skript als Zeilen-Diff.
- **Vorschau:** Beide Vorlagen nebeneinander als „ehrliche Skizze“ an Originalposition, Datenbänder mit ein paar Fake-Zeilen, Änderungen farbig markiert, Klick in Liste springt zum Objekt.
- **Fake-Daten:** Generische Werte aus dem Feldnamen abgeleitet, Platzhalter `‹Feldname›` für Unbekanntes.
- **Erfolg:** Bei einem echten Kunden-/Standard-Paar ist in < 1 Minute klar, was sich wirklich geändert hat — ohne XML zu lesen.
- **Rahmen:** Bestehender Stack und Regeln (uv, Ruff, pytest, Dark/Light, F11, QSettings, Worker-Thread).
- **Nicht im Umfang:** Pixelgenaues Rendering, Skriptausführung, echte Barcodes, Seitenumbruch-/Gruppenlogik, Bearbeiten/Mergen, > 2 Dateien, KI-Erklärungen, Report-Export.
