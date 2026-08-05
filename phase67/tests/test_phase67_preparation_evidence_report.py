import json

from phase67.reporting.phase67_preparation_evidence_report import (
    write_phase67_preparation_evidence_report,
)


def _valid_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "execute_allowed": False,
        "next_step": "fix_phase67_findings_or_reject",
        "policy_result": {"policy_status": "PASS", "reasons": []},
        "preparation_evidence_package": {"status": "PREPARATION_EVIDENCE_PACKAGE_READY"},
        "preparation_controls": {"status": "PREPARATION_CONTROLS_READY"},
        "preparation_evidence_requirements": {
            "status": "PREPARATION_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_preparation_gate": {"status": "MANUAL_PREPARATION_GATE_READY"},
        "selected_decision": "REJECT",
    }


def test_report_fails_when_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("selected_decision")
    out = tmp_path / "phase67.json"
    result = write_phase67_preparation_evidence_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_report_fails_when_can_execute_true(tmp_path) -> None:
    payload = _valid_payload()
    payload["can_execute"] = True
    out = tmp_path / "phase67.json"
    result = write_phase67_preparation_evidence_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert result["reason"] == "can_execute must be False"


def test_report_pass(tmp_path) -> None:
    out = tmp_path / "phase67.json"
    result = write_phase67_preparation_evidence_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "67"
    assert data["human_approval_required"] is True
