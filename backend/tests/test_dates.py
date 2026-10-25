from datetime import date

from odin.services.timeline import fmt_date


def test_fmt_date_matches_ui_format():
    assert fmt_date(date(2026, 11, 2)) == "2 Nov 2026"
    assert fmt_date(date(2026, 12, 31)) == "31 Dec 2026"
