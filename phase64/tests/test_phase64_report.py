import json

from phase64.reporting.phase64_report import write_phase64_report


def _valid_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase64_findings_or_reject",
        "policy_result": {"policy_status": "PASS", "reasons": []},
        "operator_finalize_package": {"status": "OPERATOR_FINALIZE_PACKAGE_READY"},
        "operator_finalize_controls": {"status": "OPERATOR_FINALIZE_CONTROLS_READY"},
        "operator_finalize_stop_conditions": {
            "status": "OPERATOR_FINALIZE_STOP_CONDITIONS_READY"
        },
        "operator_finalize_evidence_requirements": {
            "status": "OPERATOR_FINALIZE_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_operator_finalize": {"status": "MANUAL_GATE_OPERATOR_FINALIZE_READY"},
        "selected_decision": "REJECT",
    }


def test_write_phase64_report_fail_on_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("selected_decision")
    out = tmp_path / "phase64.json"
    result = write_phase64_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_write_phase64_report_pass(tmp_path) -> None:
    out = tmp_path / "phase64.json"
    result = write_phase64_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "64"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
