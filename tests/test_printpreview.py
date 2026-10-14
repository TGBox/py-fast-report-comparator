import sqlite3
from pathlib import Path

from src.parser import parse_report
from src.printpreview import RenderError, build_fake_db, find_renderer, render_command

XML = """<TfrxReport>
  <TfrxDataPage Name="Data">
    <TfrxFDQuery Name="praxis" SQL.Text="select * from praxis">
      <FieldDefs><item FieldName="name" FieldType="fftString"/><item FieldName="plz"/></FieldDefs>
    </TfrxFDQuery>
    <TfrxFDQuery Name="Patienten" SQL.Text="select ...">
      <Parameters><item Name="id" DataType="ftWideString" Expression="&lt;id&gt;"/></Parameters>
      <FieldDefs><item FieldName="p_name" FieldType="fftString"/></FieldDefs>
    </TfrxFDQuery>
    <TfrxFDQuery Name="events" SQL.Text="select ...">
      <FieldDefs>
        <item FieldName="start" FieldType="fftDateTime"/>
        <item FieldName="betrag" FieldType="fftNumeric"/>
        <item FieldName="abgesagt" FieldType="fftBoolean"/>
      </FieldDefs>
    </TfrxFDQuery>
    <TfrxFDQuery Name="leer"/>
  </TfrxDataPage>
  <TfrxReportPage Name="Page1">
    <TfrxMasterData Name="MasterData1" DataSetName="Patienten"/>
    <TfrxDetailData Name="DetailData1" DataSetName="events"/>
  </TfrxReportPage>
</TfrxReport>"""


def rows(db: Path, table: str) -> list[tuple]:
    with sqlite3.connect(db) as con:
        return con.execute(f'SELECT * FROM "{table}"').fetchall()


def columns(db: Path, table: str) -> list[tuple[str, str]]:
    with sqlite3.connect(db) as con:
        return [(c[1], c[2]) for c in con.execute(f'PRAGMA table_info("{table}")')]


def test_one_table_per_query_with_typed_columns(tmp_path: Path = Path("build/t1")):
    db = build_fake_db(parse_report(XML), tmp_path / "fake.db")
    assert columns(db, "praxis") == [("name", "TEXT"), ("plz", "TEXT")]
    assert columns(db, "events") == [
        ("start", "DATETIME"),
        ("betrag", "REAL"),
        ("abgesagt", "BOOLEAN"),
    ]


def test_fake_values_are_generic_and_typed(tmp_path: Path = Path("build/t2")):
    db = build_fake_db(parse_report(XML), tmp_path / "fake.db")
    assert rows(db, "praxis") == [("Praxis Beispiel", "12345")]
    start, betrag, abgesagt = rows(db, "events")[0]
    assert start == "2026-01-01 09:00:00"
    assert betrag == 123.45
    assert abgesagt == 0


def test_single_record_lookup_by_id_gets_one_row(tmp_path: Path = Path("build/t6")):
    xml = XML.replace('<TfrxDetailData Name="DetailData1" DataSetName="events"/>', "")
    db = build_fake_db(parse_report(xml), tmp_path / "fake.db")
    assert len(rows(db, "Patienten")) == 1  # has parameter "id": one record


def test_list_bands_get_several_rows_masters_with_detail_one(tmp_path: Path = Path("build/t3")):
    db = build_fake_db(parse_report(XML), tmp_path / "fake.db")
    assert len(rows(db, "events")) == 3  # detail band: a list
    assert len(rows(db, "Patienten")) == 1  # master with detail below: one record


def test_query_without_fields_still_gets_a_table(tmp_path: Path = Path("build/t4")):
    db = build_fake_db(parse_report(XML), tmp_path / "fake.db")
    assert rows(db, "leer") == [(None,)]


def test_render_command():
    cmd = render_command(Path("C:/r/FrxRender.exe"), Path("a.fr3"), Path("f.db"), Path("o.pdf"))
    assert [Path(c).name for c in cmd] == ["FrxRender.exe", "a.fr3", "f.db", "o.pdf"]


def test_find_renderer_prefers_explicit_path(tmp_path: Path = Path("build/t5")):
    exe = tmp_path / "FrxRender.exe"
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_bytes(b"")
    assert find_renderer(str(exe), candidates=()) == exe
    assert find_renderer(str(tmp_path / "missing.exe"), candidates=()) is None
    assert find_renderer(None, candidates=(tmp_path / "x.exe", exe)) == exe


def test_render_error_is_an_exception():
    assert issubclass(RenderError, Exception)
