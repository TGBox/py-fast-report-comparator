# FrxRender – exakte Druckansicht

Kleines Konsolenprogramm, das eine `.fr3`-Vorlage mit der echten FastReport-VCL-Engine als PDF ausgibt. Die Python-App nutzt es für die **Druckansicht**.

## Bauen (einmalig)

1. In Delphi 12 `delphi/FrxRender/FrxRender.dpr` öffnen (die `.dproj` legt Delphi selbst an).
2. Zielplattform wie beim ReportDesigner wählen (Win32 oder Win64), Konfiguration **Release**.
3. Kompilieren. Die App findet die Exe automatisch unter `delphi/FrxRender/<Plattform>/<Konfiguration>/FrxRender.exe`, alternativ über die Umgebungsvariable `FRX_RENDER_EXE`.

Voraussetzungen: FastReport VCL 2025 im Bibliothekspfad (wie beim ReportDesigner) und `cur-delphi` neben diesem Repo (für `Library\FastReportAddFunctions.pas`).

## Test von Hand

```bat
FrxRender.exe "..\..\testdata\Terminuebersicht_Terminübersicht.fr3" fake.db out.pdf
```

`fake.db` erzeugt die App (je Abfrage eine Tabelle mit generischen Werten). Bei Fehlern steht die Meldung in `out.pdf.error.txt`.

## Grenzen

- Das SQL der Vorlage wird **nicht** ausgeführt; jede Abfrage liefert ihre Fake-Zeilen. Datenabhängige Logik (z. B. Filter im SQL) wirkt daher nicht.
- Bilder aus dem Upload-Verzeichnis (z. B. Praxislogo) fehlen.
- `PValue(...)` liefert ohne Formular `no parent`.
