from src.differ import diff_reports
from src.parser import parse_report


def report(memo_attrs: str = "", band_attrs: str = 'Top="10"', extra: str = "") -> str:
    return f"""<TfrxReport ScriptText.Text="begin end.">
      <TfrxReportPage Name="Page1">
        <TfrxMasterData Name="MasterData1" {band_attrs} Height="40" Width="700">
          <TfrxMemoView Name="Memo1" Left="0" Top="0" Width="100" Height="20" {memo_attrs}/>
          {extra}
        </TfrxMasterData>
      </TfrxReportPage>
    </TfrxReport>"""


def diff(a: str, b: str):
    return diff_reports(parse_report(a), parse_report(b))


def test_identical_reports_have_no_differences():
    assert diff(report(), report()) == []


def test_changed_text_is_content():
    [d] = diff(report('Text="Behandler"'), report('Text="Behandlung"'))
    assert (d.kind, d.category, d.prop, d.old, d.new) == (
        "changed",
        "content",
        "Text",
        "Behandler",
        "Behandlung",
    )
    assert d.path == ("Page1", "MasterData1", "Memo1")


def test_moved_object_is_layout():
    b = report().replace('Name="Memo1" Left="0"', 'Name="Memo1" Left="37,7953"')
    [d] = diff(report(), b)
    assert (d.category, d.prop) == ("layout", "Left")


def test_band_top_is_ignored():
    assert diff(report(band_attrs='Top="10"'), report(band_attrs='Top="324,5"')) == []


def test_float_noise_below_tolerance_is_ignored():
    a = report().replace('Height="20"', 'Height="18,89765"')
    b = report().replace('Height="20"', 'Height="18,89767456"')
    assert diff(a, b) == []


def test_missing_attribute_equals_explicit_zero():
    assert diff(report(), report('ContentScaleOptions.Constraints.MaxIterationValue="0"')) == []


def test_missing_boolean_is_reported():
    [d] = diff(report(), report('Visible="False"'))
    assert (d.prop, d.old, d.new) == ("Visible", None, "False")


def test_added_and_removed_objects():
    extra_a = '<TfrxMemoView Name="Old" Left="300" Top="0" Width="50" Height="20"/>'
    extra_b = '<TfrxLineView Name="New" Left="500" Top="0" Width="50" Height="0"/>'
    result = {(d.kind, d.path[-1]) for d in diff(report(extra=extra_a), report(extra=extra_b))}
    assert result == {("removed", "Old"), ("added", "New")}


def test_renamed_object_is_matched_by_overlap():
    extra_a = '<TfrxMemoView Name="Eventsname" Left="300" Top="0" Width="50" Height="20" Text="a"/>'
    extra_b = '<TfrxMemoView Name="Memo9" Left="301" Top="0" Width="50" Height="20" Text="b"/>'
    result = diff(report(extra=extra_a), report(extra=extra_b))
    kinds = {(d.kind, d.prop) for d in result}
    assert kinds == {("renamed", None), ("changed", "Left"), ("changed", "Text")}
    renamed = next(d for d in result if d.kind == "renamed")
    assert (renamed.old, renamed.new) == ("Eventsname", "Memo9")


def test_object_moved_to_other_band():
    a = report(extra='<TfrxMemoView Name="X" Left="300" Top="0" Width="5" Height="5"/>')
    b = a.replace('<TfrxMemoView Name="X" Left="300" Top="0" Width="5" Height="5"/>', "").replace(
        "</TfrxReportPage>",
        '<TfrxPageFooter Name="PageFooter1" Height="20" Width="700">'
        '<TfrxMemoView Name="X" Left="300" Top="0" Width="5" Height="5"/>'
        "</TfrxPageFooter></TfrxReportPage>",
    )
    result = {(d.kind, d.path[-1], d.prop) for d in diff(a, b)}
    assert ("added", "PageFooter1", None) in result
    assert ("changed", "X", "Band") in result


def test_script_change_is_content_on_report():
    a = report()
    b = a.replace("begin end.", "begin x := 1; end.")
    [d] = diff(a, b)
    assert (d.path, d.prop, d.category) == ((), "ScriptText.Text", "content")


def test_meta_category():
    a = report().replace("<TfrxReport ", '<TfrxReport ReportOptions.LastChange="1" ')
    b = report().replace("<TfrxReport ", '<TfrxReport ReportOptions.LastChange="2" ')
    [d] = diff(a, b)
    assert d.category == "meta"


def test_items_are_compared_individually():
    def with_fields(fields: str) -> str:
        return report(extra=f"<FieldDefs>{fields}</FieldDefs>")

    a = with_fields('<item FieldName="ort" Size="40"/><item FieldName="plz"/>')
    b = with_fields('<item FieldName="ort" Size="60"/><item FieldName="email"/>')
    result = {(d.kind, d.path[-1], d.prop) for d in diff(a, b)}
    assert result == {
        ("changed", "ort", "Size"),
        ("removed", "plz", None),
        ("added", "email", None),
    }


def test_display_format_entries_are_layout():
    a = report(
        extra='<TfrxMemoView Name="M" Left="300" Top="0" Width="5" Height="5">'
        "<Formats><item/><item/></Formats></TfrxMemoView>"
    )
    b = a.replace("<item/><item/>", "<item/>")
    [d] = diff(a, b)
    assert (d.kind, d.category) == ("removed", "layout")


def test_added_object_carries_its_text():
    extra = '<TfrxMemoView Name="New" Left="300" Top="0" Width="5" Height="5" Text="Hallo"/>'
    [d] = diff(report(), report(extra=extra))
    assert (d.kind, d.new) == ("added", "Hallo")
