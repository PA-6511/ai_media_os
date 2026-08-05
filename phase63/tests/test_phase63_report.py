import json

from phase63.reporting.phase63_report import write_phase63_report


def _valid_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase63_findings_or_reject",
        "policy_result": {"policy_status": "PASS", "reasons": []},
        "operator_signoff_package": {"status": "OPERATOR_SIGNOFF_PACKAGE_READY"},
        "operator_signoff_controls": {"status": "OPERATOR_SIGNOFF_CONTROLS_READY"},
        "operator_signoff_stop_conditions": {
            "status": "OPERATOR_SIGNOFF_STOP_CONDITIONS_READY"
        },
        "operator_signoff_evidence_requirements": {
            "status": "OPERATOR_SIGNOFF_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_operator_signoff": {"status": "MANUAL_GATE_OPERATOR_SIGNOFF_READY"},
        "selected_decision": "REJECT",
    }


def test_write_phase63_report_fail_on_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("selected_decision")
    out = tmp_path / "phase63.json"
    result = write_phase63_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_write_phase63_report_pass(tmp_path) -> None:
    out = tmp_path / "phase63.json"
    result = write_phase63_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "63"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
