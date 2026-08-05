import json
from pathlib import Path

from phase53.reporting.phase53_report import write_phase53_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase53_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "final_go_review_package": {"status": "FINAL_GO_REVIEW_PACKAGE_READY"},
        "final_go_review_controls": {"status": "FINAL_GO_REVIEW_CONTROLS_READY"},
        "final_go_review_stop_conditions": {"status": "FINAL_GO_REVIEW_STOP_CONDITIONS_READY"},
        "final_go_review_evidence_requirements": {
            "status": "FINAL_GO_REVIEW_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_final_go_review": {"status": "MANUAL_GATE_FINAL_GO_REVIEW_READY"},
        "selected_decision": "REJECT",
    }


def test_phase53_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase53.json"
    result = write_phase53_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase53_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase53.json"
    write_phase53_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "53"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
