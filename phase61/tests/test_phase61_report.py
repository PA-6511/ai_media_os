import json

from phase61.reporting.phase61_report import write_phase61_report


def _valid_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase61_findings_or_reject",
        "policy_result": {"policy_status": "PASS", "reasons": []},
        "operator_checklist_package": {"status": "OPERATOR_CHECKLIST_PACKAGE_READY"},
        "operator_checklist_controls": {"status": "OPERATOR_CHECKLIST_CONTROLS_READY"},
        "operator_checklist_stop_conditions": {
            "status": "OPERATOR_CHECKLIST_STOP_CONDITIONS_READY"
        },
        "operator_checklist_evidence_requirements": {
            "status": "OPERATOR_CHECKLIST_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_operator_checklist": {"status": "MANUAL_GATE_OPERATOR_CHECKLIST_READY"},
        "selected_decision": "REJECT",
    }


def test_write_phase61_report_fail_on_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("selected_decision")
    out = tmp_path / "phase61.json"
    result = write_phase61_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_write_phase61_report_pass(tmp_path) -> None:
    out = tmp_path / "phase61.json"
    result = write_phase61_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "61"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
