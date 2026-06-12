"""Authority-matrix asymmetry rule on the Opus veto (items 1+2, 2026-06-12).

The veto is a filter, not a third opinion:
- may suppress findings, never create them (creation already blocked in
  _run_opus_veto_pass — strays are logged + dropped);
- may downgrade severity, never upgrade it (enforced in
  _apply_veto_actions);
- every drop / downgrade / blocked-upgrade emits a disagreement-log
  event (the extraction-quality signal).
"""

from app.services.validation.tiered_validation import _apply_veto_actions


def _finding(severity: str = "major", title: str = "Port mismatch") -> dict:
    return {"rule": "UCP600-20", "title": title, "message": title, "severity": severity}


def test_drop_removes_finding_and_emits_event():
    events = []
    out = _apply_veto_actions(
        [_finding()],
        [{"source": "deterministic", "index": 0, "action": "drop", "reason": "same UN/LOCODE"}],
        "deterministic",
        events_out=events,
    )
    assert out == []
    assert len(events) == 1
    assert events[0]["event"] == "veto_drop"
    assert events[0]["source_layer"] == "deterministic"
    assert events[0]["reason"] == "same UN/LOCODE"


def test_downgrade_is_applied_and_logged():
    events = []
    out = _apply_veto_actions(
        [_finding(severity="major")],
        [{"source": "ai", "index": 0, "action": "modify", "updated_severity": "minor", "reason": "cosmetic"}],
        "ai",
        events_out=events,
    )
    assert out[0]["severity"] == "minor"
    assert events[0]["event"] == "veto_downgrade"
    assert events[0]["severity_from"] == "major"
    assert events[0]["severity_to"] == "minor"


def test_upgrade_is_blocked_original_severity_kept():
    events = []
    out = _apply_veto_actions(
        [_finding(severity="minor")],
        [{"source": "ai", "index": 0, "action": "modify", "updated_severity": "critical", "reason": "looks bad"}],
        "ai",
        events_out=events,
    )
    assert out[0]["severity"] == "minor"  # upgrade ignored
    assert events[0]["event"] == "veto_upgrade_blocked"
    assert events[0]["severity_kept"] == "minor"
    assert events[0]["severity_attempted"] == "critical"


def test_unknown_severity_word_is_blocked():
    events = []
    out = _apply_veto_actions(
        [_finding(severity="major")],
        [{"source": "ai", "index": 0, "action": "modify", "updated_severity": "catastrophic"}],
        "ai",
        events_out=events,
    )
    assert out[0]["severity"] == "major"
    assert events[0]["event"] == "veto_upgrade_blocked"


def test_equal_rank_relabel_is_allowed():
    # warning and minor share a rank — relabeling across vocabularies is
    # not an upgrade.
    events = []
    out = _apply_veto_actions(
        [_finding(severity="warning")],
        [{"source": "deterministic", "index": 0, "action": "modify", "updated_severity": "minor"}],
        "deterministic",
        events_out=events,
    )
    assert out[0]["severity"] == "minor"
    assert events[0]["event"] == "veto_relabel"


def test_confirm_is_noop_with_no_events():
    events = []
    out = _apply_veto_actions(
        [_finding()],
        [{"source": "ai", "index": 0, "action": "confirm"}],
        "ai",
        events_out=events,
    )
    assert out[0]["severity"] == "major"
    assert events == []


def test_title_modify_without_severity_keeps_severity():
    events = []
    out = _apply_veto_actions(
        [_finding(severity="major")],
        [{"source": "ai", "index": 0, "action": "modify", "updated_title": "Clearer title"}],
        "ai",
        events_out=events,
    )
    assert out[0]["title"] == "Clearer title"
    assert out[0]["severity"] == "major"


def test_events_out_none_does_not_crash():
    out = _apply_veto_actions(
        [_finding()],
        [{"source": "ai", "index": 0, "action": "drop"}],
        "ai",
    )
    assert out == []
