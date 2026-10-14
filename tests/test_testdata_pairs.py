"""Golden tests against the real template pairs in testdata/ (spec success criteria 2-4)."""

from pathlib import Path

import pytest

if not Path("testdata").is_dir():  # testdata/ holds real templates and is git-ignored
    pytest.skip("testdata/ fehlt", allow_module_level=True)

from src.differ import diff_reports
from src.explain import explain
from src.parser import parse_report

TESTDATA = Path("testdata")
PAIRS = [
    (
        "Terminerinnerung_Terminerinnerung DINA4.fr3",
        "Terminerinnerung_Terminerinnerung DINA4 - Starkenburg.fr3",
    ),
    (
        "Terminerinnerung_Terminerinnerung DINA5.fr3",
        "Terminerinnerung_Terminerinnerung DINA5 - Starkenburg.fr3",
    ),
    (
        "Terminerinnerung_Terminerinnerung DINA6.fr3",
        "Terminerinnerung_Terminerinnerung DINA6 - Starkenburg.fr3",
    ),
    (
        "Terminerinnerung_Terminerinnerung(Bon).fr3",
        "Terminerinnerung_Terminerinnerung(Bon) - Starkenburg.fr3",
    ),
    ("Terminuebersicht_Terminübersicht.fr3", "Terminuebersicht_Terminübersicht Neu.fr3"),
    ("Faktura_Quittung-Blanko-DINA6.fr3", "Faktura_Quittung-Neu2.fr3"),
]


def diff_pair(a: str, b: str):
    return diff_reports(parse_report(TESTDATA / a), parse_report(TESTDATA / b))


def test_dina4_customer_variant_has_exactly_two_content_changes():
    content = [d for d in diff_pair(*PAIRS[0]) if d.category == "content"]
    assert {(d.path[-1], d.prop) for d in content} == {("Memo1", "Text"), ("praxisplz1", "Text")}


def test_terminuebersicht_lists_the_real_changes():
    found = {(d.kind, d.path[-1] if d.path else "", d.prop) for d in diff_pair(*PAIRS[4])}
    assert ("changed", "Memo3", "Text") in found
    assert ("added", "praxis", None) in found
    assert ("removed", "Eventsresourcename", None) in found
    assert ("changed", "", "OnReportPrint") in found


def test_no_noise_in_any_pair():
    for a, b in PAIRS:
        for d in diff_pair(a, b):
            assert not (
                d.prop == "Top"
                and d.path[-1].startswith(("PageHeader", "MasterData", "ReportTitle", "Child"))
            ), d
            assert not (d.prop or "").startswith("ContentScaleOptions."), d


def test_every_difference_is_explained_without_raw_codes():
    for a, b in PAIRS:
        for d in diff_pair(a, b):
            text = explain(d)
            assert text.endswith("."), text
            assert "-16777208" not in text and "Font." not in text and "Frame." not in text, text
