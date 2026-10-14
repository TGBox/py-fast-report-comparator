# py-fast-report-comparator

A python app to compare two fast report files against each other to see the differences in them more clearly.

## Voraussetzungen

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

- Qt 6 (wird automatisch über uv installiert)


## Setup & Ausführung

```bash
uv sync

# GUI starten
uv run main
# oder:
uv run py-fast-report-comparator

# Tests ausführen
uv run test

# Standalone-Exe mit PyInstaller bauen
uv run build
```

## Framework

Dieses Projekt verwendet **PySide6**.

## Projektstruktur

```
py-fast-report-comparator/
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── build.py
│   └── tools.py
├── tests/
│   └── test_main.py
├── pyproject.toml
└── README.md
```