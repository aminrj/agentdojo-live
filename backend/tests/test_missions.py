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


# ---- shipping contract ----------------------------------------------------
# The post-solve panel is the reason this project exists: a solve that does not
# explain itself is just a score. Missions 02 and 03 sat unshippable for a
# release because nothing enforced these fields, so nothing flagged that they
# were empty. These tests are that enforcement.


def test_every_mission_teaches_a_defense():
    for m in all_missions():
        assert m.defense_note_md.strip(), (
            f"{m.id} has no defense_note_md — the post-solve panel would render "
            f"a win with no lesson attached"
        )
        assert len(m.defense_note_md) > 200, f"{m.id} defense_note_md is too thin to teach"


def test_every_mission_has_a_briefing_and_writeup():
    for m in all_missions():
        assert m.briefing_md.strip(), f"{m.id} missing briefing_md"
        assert m.writeup_md.strip(), f"{m.id} missing writeup_md"
        assert m.hint_1.strip() and m.hint_2.strip(), f"{m.id} missing hints"


def test_every_mission_labels_its_attack_chain():
    """trace_labels drives the annotated trace. Without it the panel degrades
    to an unlabelled transcript, which is the Gandalf experience we exist to
    improve on."""
    for m in all_missions():
        labels = m.trace_labels
        assert labels, f"{m.id} has no trace_labels"

        chain = labels.get("trifecta")
        assert chain, f"{m.id} trace_labels has no attack chain"
        for step in chain:
            assert {"label", "tool", "description"} <= set(step), (
                f"{m.id} attack-chain step is missing required keys: {step}"
            )

        # Every tool named in tool_roles must be one the mission actually
        # grants, or the annotation silently never renders.
        for tool_name in labels.get("tool_roles", {}):
            assert tool_name in m.available_tools, (
                f"{m.id} labels unknown tool {tool_name!r}; "
                f"available: {m.available_tools}"
            )

        for tool_name in labels.get("injection_tools", []):
            assert tool_name in m.available_tools, (
                f"{m.id} marks unknown tool {tool_name!r} as carrying the injection"
            )
