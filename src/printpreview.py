"""Exact print preview: fake SQLite data + the real FastReport engine (FrxRender.exe)."""

from __future__ import annotations

import os
import sqlite3
import subprocess
from collections.abc import Iterable
from pathlib import Path

from src.fakedata import fake_field
from src.parser import Node

REPO = Path(__file__).resolve().parent.parent
_BUILD = REPO / "delphi" / "FrxRender"
DEFAULT_CANDIDATES = tuple(
    _BUILD / platform / config / "FrxRender.exe"
    for config in ("Release", "Debug")
    for platform in ("Win32", "Win64")
)
LIST_ROWS = 3
_SQL_TYPES = {"fftNumeric": "REAL", "fftDateTime": "DATETIME", "fftBoolean": "BOOLEAN"}


class RenderError(Exception):
    """FrxRender.exe is missing or could not render the template."""


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _row_counts(report: Node) -> dict[str, int]:
    """Lists get several rows; single-record lookups and masters with details get one."""
    bands = [n for n in report.walk() if n.tag.endswith(("MasterData", "DetailData"))]
    has_detail = any(b.tag != "TfrxMasterData" for b in bands)
    counts: dict[str, int] = {}
    for band in bands:
        name = band.attrs.get("DataSetName", "").lower()
        is_master = band.tag == "TfrxMasterData"
        counts[name] = 1 if is_master and has_detail else LIST_ROWS
    for query in (n for n in report.walk() if n.tag == "TfrxFDQuery"):
        params = {p.key.lower() for p in query.walk() if p.parent.tag == "Parameters"}
        if "id" in params:
            counts[query.key.lower()] = 1
    return counts


def _fake_value(dataset: str, field: str, field_type: str, row: int) -> object:
    if field_type == "fftNumeric":
        return (123.45, 67.80, 10.00)[row % 3]
    if field_type == "fftDateTime":
        return f"2026-01-{row + 1:02d} {9 + row:02d}:00:00"
    if field_type == "fftBoolean":
        return 0
    return fake_field(dataset, field, row)


def build_fake_db(report: Node, path: Path) -> Path:
    """One table per TfrxFDQuery (named like the query) filled with generic fake rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    counts = _row_counts(report)
    with sqlite3.connect(path) as con:
        for query in (n for n in report.walk() if n.tag == "TfrxFDQuery"):
            fields = [
                (f.key, f.attrs.get("FieldType", "fftString"))
                for f in query.walk()
                if f.tag == "item" and f.parent.tag == "FieldDefs"
            ] or [("leer", "fftString")]
            columns = ", ".join(f"{_quote(n)} {_SQL_TYPES.get(t, 'TEXT')}" for n, t in fields)
            con.execute(f"CREATE TABLE {_quote(query.key)} ({columns})")
            marks = ", ".join("?" * len(fields))
            for row in range(counts.get(query.key.lower(), 1)):
                values = [
                    None if n == "leer" and len(fields) == 1 else _fake_value(query.key, n, t, row)
                    for n, t in fields
                ]
                con.execute(f"INSERT INTO {_quote(query.key)} VALUES ({marks})", values)
    return path


def find_renderer(
    explicit: str | None = None, candidates: Iterable[Path] = DEFAULT_CANDIDATES
) -> Path | None:
    """Explicit setting, then $FRX_RENDER_EXE, then the Delphi build folders."""
    for option in (explicit, os.environ.get("FRX_RENDER_EXE")):
        if option:
            return Path(option) if Path(option).is_file() else None
    return next((c for c in candidates if c.is_file()), None)


def render_command(exe: Path, fr3: Path, db: Path, pdf: Path) -> list[str]:
    return [str(exe), str(fr3), str(db), str(pdf)]


def render_pdf(exe: Path, fr3: Path, report: Node, work_dir: Path) -> Path:
    """Render one template with the real engine; returns the PDF path."""
    work_dir.mkdir(parents=True, exist_ok=True)
    db = build_fake_db(report, work_dir / f"{fr3.stem}.db")
    pdf = work_dir / f"{fr3.stem}.pdf"
    error_file = Path(f"{pdf}.error.txt")
    pdf.unlink(missing_ok=True)
    error_file.unlink(missing_ok=True)
    try:
        result = subprocess.run(
            render_command(exe, fr3, db, pdf), capture_output=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RenderError(f"FrxRender.exe konnte nicht ausgeführt werden: {error}") from error
    if result.returncode != 0 or not pdf.is_file():
        detail = (
            error_file.read_text(encoding="utf-8", errors="replace")
            if error_file.is_file()
            else result.stderr.decode("cp1252", "replace")
        )
        raise RenderError(f"„{fr3.name}“ konnte nicht gedruckt werden: {detail.strip()}")
    return pdf
