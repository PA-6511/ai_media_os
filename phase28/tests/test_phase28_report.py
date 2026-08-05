import json
from pathlib import Path

from phase28.reporting.phase28_report import write_phase28_report


def test_phase28_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase28.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase28_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "manual_dry_run_gate": {"status": "MANUAL_DRY_RUN_GATE_READY"},
        "approval_input_schema": {"status": "APPROVAL_INPUT_SCHEMA_READY"},
        "evidence_storage_spec": {"status": "EVIDENCE_STORAGE_SPEC_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase28_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "28"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
