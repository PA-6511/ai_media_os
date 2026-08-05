import json
from pathlib import Path

from phase51.reporting.phase51_report import write_phase51_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase51_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "readiness_review_package": {"status": "READINESS_REVIEW_PACKAGE_READY"},
        "readiness_review_controls": {"status": "READINESS_REVIEW_CONTROLS_READY"},
        "readiness_review_stop_conditions": {"status": "READINESS_REVIEW_STOP_CONDITIONS_READY"},
        "readiness_review_evidence_requirements": {
            "status": "READINESS_REVIEW_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_readiness_review": {"status": "MANUAL_GATE_READINESS_REVIEW_READY"},
        "selected_decision": "REJECT",
    }


def test_phase51_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase51.json"
    result = write_phase51_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase51_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase51.json"
    write_phase51_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "51"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
