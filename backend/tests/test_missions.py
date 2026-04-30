"""Mission registry sanity tests."""

from app.missions import all_missions, get


def test_mission_01_registered():
    m = get("mission-01")
    assert m.id == "mission-01"
    assert "send_email" in m.available_tools


def test_canary_is_session_specific():
    m = get("mission-01")
    a = m.canary_for("aaaaaaaaXXXX")
    b = m.canary_for("bbbbbbbbYYYY")
    assert a != b
    assert a.startswith("FLAG-CANARY-")


def test_seed_filesystem_contains_canary():
    m = get("mission-01")
    fs = m.seed_filesystem("session1234567890")
    report = fs["quarterly-report.pdf.txt"]
    assert m.canary_for("session1234567890") in report


def test_at_least_one_mission():
    assert len(all_missions()) >= 1
