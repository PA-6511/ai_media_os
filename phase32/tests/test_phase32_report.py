import json
from pathlib import Path

from phase32.reporting.phase32_report import write_phase32_report


def test_phase32_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase32.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase32_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_preflight_package": {
            "status": "MANUAL_DRY_RUN_PREFLIGHT_PACKAGE_READY"
        },
        "preflight_controls": {"status": "PREFLIGHT_CONTROLS_READY"},
        "preflight_stop_conditions": {"status": "PREFLIGHT_STOP_CONDITIONS_READY"},
        "preflight_evidence_requirements": {
            "status": "PREFLIGHT_EVIDENCE_REQUIREMENTS_READY"
        },
        "manual_gate_preflight": {"status": "MANUAL_GATE_PREFLIGHT_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase32_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "32"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
