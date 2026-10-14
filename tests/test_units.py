from src.units import (
    color_text,
    delphi_date_text,
    font_style_text,
    frame_text,
    mm,
    parse_number,
    pt,
)


def test_parse_number_accepts_decimal_comma():
    assert parse_number("18,89765") == 18.89765


def test_parse_number_returns_none_for_text():
    assert parse_number("Arial") is None


def test_mm_converts_96_dpi_pixels():
    assert round(mm("37,7953"), 2) == 10.0


def test_pt_converts_negative_font_height():
    assert pt("-13") == 9.75


def test_color_text_names_common_and_system_colors():
    assert color_text("0") == "Schwarz"
    assert color_text("-16777208") == "Systemfarbe Fenstertext"
    assert color_text("536870911") == "keine"


def test_color_text_shows_rgb_hex_for_other_colors():
    # Delphi TColor is BGR: 0x00336699 -> r=99 g=66 b=33
    assert color_text(str(0x336699)) == "#996633"
    assert color_text("16711680") == "Blau"


def test_font_style_text_decodes_bitmask():
    assert font_style_text("0") == "normal"
    assert font_style_text("3") == "fett, kursiv"


def test_frame_text_decodes_bitmask():
    assert frame_text("0") == "kein Rahmen"
    assert frame_text("15") == "rundum"
    assert frame_text("8") == "unten"
    assert frame_text("3") == "links, rechts"


def test_delphi_date_text():
    assert delphi_date_text("46309,4551875926") == "14.10.2026 10:55"
