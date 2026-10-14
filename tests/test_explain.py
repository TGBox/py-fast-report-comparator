from src.differ import Difference
from src.explain import explain, format_value


def changed(prop: str, old: str | None, new: str | None, tag: str = "TfrxMemoView") -> Difference:
    return Difference(("Page1", "MasterData1", "Memo6"), "changed", "layout", tag, prop, old, new)


def test_horizontal_move_in_mm_with_direction():
    text = explain(changed("Left", "283,46475", "3,77953005"))
    assert text == "74,0 mm nach links verschoben (Links: 75,0 mm → 1,0 mm)."


def test_vertical_move():
    assert explain(changed("Top", "0", "37,7953")).startswith("10,0 mm nach unten verschoben")


def test_size_change():
    assert explain(changed("Width", "94,48825", "442,20500644")) == "Breite: 25,0 mm → 117,0 mm."


def test_font_size_in_points():
    assert explain(changed("Font.Height", "-13", "-16")) == "Schriftgröße: 9,75 pt → 12 pt."


def test_font_style_and_colors_are_readable():
    assert explain(changed("Font.Style", "2", "1")) == "Schriftstil: kursiv → fett."
    assert explain(changed("Font.Color", "0", "-16777208")) == (
        "Schriftfarbe: Schwarz → Systemfarbe Fenstertext."
    )


def test_frame():
    assert explain(changed("Frame.Typ", "8", "0")) == "Rahmen: unten → kein Rahmen."


def test_text_change_quotes_values():
    assert explain(changed("Text", "Behandler", "Behandlung")) == (
        "Text geändert: „Behandler“ → „Behandlung“."
    )


def test_missing_value_is_called_default():
    assert explain(changed("Visible", None, "False")) == "Sichtbar: Standard → nein."


def test_multiline_script_change_counts_lines():
    d = Difference(
        (),
        "changed",
        "content",
        "TfrxReport",
        "ScriptText.Text",
        "begin\r\nend.",
        "begin\r\n  x := 1;\r\n  y := 2;\r\nend.",
    )
    assert explain(d) == "Skript geändert: 2 Zeilen hinzugefügt, 0 entfernt."


def test_band_move():
    assert explain(changed("Band", "GroupHeader1", "PageHeader1")) == (
        "In anderes Band verschoben: GroupHeader1 → PageHeader1."
    )


def test_added_memo_shows_its_text():
    d = Difference(
        ("Page1", "PageHeader1", "praxisname"),
        "added",
        "content",
        "TfrxMemoView",
        new='[praxis."name"]',
    )
    assert explain(d) == 'Neu in B: Textfeld „praxisname“ mit Inhalt „[praxis."name"]“.'


def test_removed_field_definition():
    d = Difference(("Data", "praxis", "FieldDefs", "plz"), "removed", "content", "item")
    assert explain(d) == "Entfernt in B: Feld „plz“."


def test_renamed():
    d = Difference(
        ("Page1", "MasterData1", "Memo9"),
        "renamed",
        "content",
        "TfrxMemoView",
        old="Eventsname",
        new="Memo9",
    )
    assert explain(d) == "Umbenannt: „Eventsname“ → „Memo9“ (an gleicher Stelle)."


def test_format_value_alignment_and_dates():
    assert format_value("HAlign", "haCenter") == "zentriert"
    assert format_value("ReportOptions.LastChange", "46309,4551875926") == "14.10.2026 10:55"
