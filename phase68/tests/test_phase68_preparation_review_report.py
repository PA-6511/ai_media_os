import json

from phase68.reporting.phase68_preparation_review_report import (
    write_phase68_preparation_review_report,
)


def _valid_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "execute_allowed": False,
        "next_step": "fix_phase68_findings_or_reject",
        "policy_result": {"policy_status": "PASS", "reasons": []},
        "preparation_review_package": {"status": "PREPARATION_REVIEW_PACKAGE_READY"},
        "review_controls": {"status": "REVIEW_CONTROLS_READY"},
        "review_evidence_checks": {"status": "REVIEW_EVIDENCE_CHECKS_READY"},
        "manual_review_gate": {"status": "MANUAL_REVIEW_GATE_READY"},
        "selected_decision": "REJECT",
    }


def test_report_fails_when_missing_key(tmp_path) -> None:
    payload = _valid_payload()
    payload.pop("selected_decision")
    out = tmp_path / "phase68.json"
    result = write_phase68_preparation_review_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert "missing keys" in result["reason"]


def test_report_fails_when_can_execute_true(tmp_path) -> None:
    payload = _valid_payload()
    payload["can_execute"] = True
    out = tmp_path / "phase68.json"
    result = write_phase68_preparation_review_report(payload, str(out))
    assert result["status"] == "FAIL"
    assert result["reason"] == "can_execute must be False"


def test_report_pass(tmp_path) -> None:
    out = tmp_path / "phase68.json"
    result = write_phase68_preparation_review_report(_valid_payload(), str(out))
    assert result["status"] == "PASS"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["phase"] == "68"
    assert data["human_approval_required"] is True
