import json
from pathlib import Path

from phase29.reporting.phase29_report import write_phase29_report


def test_phase29_report_writes_required_fields(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "phase29.json"
    payload = {
        "readiness_status": "NOT_READY",
        "can_execute": False,
        "next_step": "fix_phase29_findings_or_reject",
        "policy_result": {"policy_status": "FAIL"},
        "rehearsal_gate_input": {"status": "REHEARSAL_GATE_INPUT_READY"},
        "rehearsal_gate_checklist": {"status": "REHEARSAL_GATE_CHECKLIST_READY"},
        "rehearsal_evidence_gate": {"status": "REHEARSAL_EVIDENCE_GATE_READY"},
        "selected_decision": "REJECT",
    }

    result = write_phase29_report(payload, str(output))
    assert result["status"] == "PASS"
    assert output.exists()

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["phase"] == "29"
    assert data["mode"] == "DRY_RUN"
    assert data["human_approval_required"] is True
