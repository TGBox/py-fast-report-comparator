from datetime import date

from src.fakedata import fake_field, fill

TODAY = date(2026, 10, 14)


def test_patient_name_fields():
    assert fake_field("patienten", "p_vname") == "Max"
    assert fake_field("patienten", "p_name") == "Mustermann"
    assert fake_field("Events", "patient") == "Max Mustermann"


def test_rows_vary_values():
    assert fake_field("patienten", "p_name", row=1) != fake_field("patienten", "p_name", row=0)


def test_practice_name_is_a_practice():
    assert fake_field("praxis", "name") == "Praxis Beispiel"


def test_address_contact_date_money():
    assert fake_field("praxis", "plz") == "12345"
    assert fake_field("praxis", "ort") == "Musterstadt"
    assert fake_field("praxis", "strasse") == "Musterstraße"
    assert fake_field("praxis", "email") == "info@beispiel.de"
    assert fake_field("termine", "datum") == "01.01.2026"
    assert fake_field("summe", "brutto") == "123,45"


def test_unknown_field_gets_placeholder():
    assert fake_field("x", "qwertz") == "‹qwertz›"


def test_fill_replaces_bracket_expressions():
    text = 'Telefon: [praxis."telefon1"]\r\n[praxis."plz"] [praxis."ort"]'
    assert fill(text) == "Telefon: 0123 456789\r\n12345 Musterstadt"


def test_fill_handles_builtins_and_functions():
    assert fill("Seite [Page#] von [TotalPages#], [Date]", today=TODAY) == (
        "Seite 1 von 1, 14.10.2026"
    )
    assert fill("[formatfloat('#,0.00',<summe.\"brutto\">)] EUR") == "123,45 EUR"
    assert fill("[GetZuzahlungSumValue()]") == "‹GetZuzahlungSumValue()›"
