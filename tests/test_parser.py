from pathlib import Path

from src.parser import parse_report

XML = """<?xml version="1.0" encoding="utf-8"?>
<TfrxReport Version="2025.1.7" ScriptText.Text="begin&#13;&#10;end.">
  <Datasets><item DataSet="praxis" DataSetName="praxis"/></Datasets>
  <TfrxDataPage Name="Data">
    <TfrxFDQuery Name="praxis" SQL.Text="select 1">
      <FieldDefs><item FieldName="ort" FieldType="fftString"/></FieldDefs>
    </TfrxFDQuery>
  </TfrxDataPage>
  <TfrxReportPage Name="Page1">
    <TfrxMasterData Name="MasterData1" Top="10" Height="20">
      <TfrxMemoView Name="Memo1" Left="0" Top="0" Width="10" Height="10" Text="[praxis.&#34;ort&#34;]">
        <Formats><item/><item/></Formats>
      </TfrxMemoView>
    </TfrxMasterData>
  </TfrxReportPage>
</TfrxReport>"""


def test_parse_keeps_attributes_with_decoded_line_breaks():
    report = parse_report(XML)
    assert report.attrs["ScriptText.Text"] == "begin\r\nend."


def test_named_elements_are_keyed_by_name_and_know_their_path():
    report = parse_report(XML)
    memo = report.find("Memo1")
    assert memo.tag == "TfrxMemoView"
    assert memo.path == ("Page1", "MasterData1", "Memo1")
    assert memo.attrs["Text"] == '[praxis."ort"]'


def test_items_are_keyed_by_their_business_key():
    report = parse_report(XML)
    keys = [n.key for n in report.walk() if n.tag == "item"]
    assert keys == ["praxis", "ort", "#1", "#2"]


def test_band_detection():
    report = parse_report(XML)
    assert report.find("MasterData1").is_band
    assert not report.find("Memo1").is_band


def test_pages_lists_report_pages_only():
    report = parse_report(XML)
    assert [p.key for p in report.pages] == ["Page1"]


def test_all_testdata_files_parse():
    if not Path("testdata").is_dir():
        return  # testdata/ is git-ignored; covered locally
    files = sorted(Path("testdata").glob("*.fr3"))
    assert len(files) == 12
    for f in files:
        report = parse_report(f)
        assert report.pages, f.name
