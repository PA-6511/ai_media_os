import json
from pathlib import Path

from phase52.reporting.phase52_report import write_phase52_report


def _base_payload() -> dict:
    return {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase52_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "go_live_review_package": {"status": "GO_LIVE_REVIEW_PACKAGE_READY"},
        "go_live_review_controls": {"status": "GO_LIVE_REVIEW_CONTROLS_READY"},
        "go_live_review_stop_conditions": {"status": "GO_LIVE_REVIEW_STOP_CONDITIONS_READY"},
        "go_live_review_evidence_requirements": {
            "status": "GO_LIVE_REVIEW_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_go_live_review": {"status": "MANUAL_GATE_GO_LIVE_REVIEW_READY"},
        "selected_decision": "REJECT",
    }


def test_phase52_report_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase52.json"
    result = write_phase52_report(_base_payload(), str(output))
    assert result["status"] == "PASS"
    assert output.exists()


def test_phase52_report_contains_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "phase52.json"
    write_phase52_report(_base_payload(), str(output))
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "52"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
