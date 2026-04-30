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


def test_seed_state_contains_canary():
    m = get("mission-01")
    state = m.seed_state("session1234567890")
    report = state["fs"]["quarterly-report.pdf.txt"]
    assert m.canary_for("session1234567890") in report


def test_all_missions_registered():
    ids = {m.id for m in all_missions()}
    assert {"mission-01", "mission-02", "mission-03", "mission-04"}.issubset(ids)


def test_each_mission_has_threat_class_and_difficulty():
    for m in all_missions():
        assert m.difficulty in {"easy", "medium", "hard"}
        assert m.threat_class, f"{m.id} missing threat_class"
