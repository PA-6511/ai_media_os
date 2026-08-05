import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_phase10_4_manual_unlock_candidate_validation_design_report import (
    generate_report,
)


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_10_3() -> dict:
    return {
        "package_type": "phase10_3_manual_redecision_record_and_final_lock_gate_design_report",
        "phase": "Phase 10-3",
        "status": "PASS",
        "current_decision": "KEEP_NO_GO",
        "phase9_2_decision": "KEEP_NO_GO",
        "wordpress_draft_id": 110,
        "target_draft_status": "draft",
        "publish_candidate_unlocked_for_operator": False,
        "wordpress_publish_execution": "NO_GO",
        "wordpress_write_executed": False,
        "production_status": "NO_GO",
        "manual_redecision_record_design": {
            "allowed_decisions": [
                "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
                "KEEP_NO_GO",
                "REQUEST_FIX",
                "ABORT",
            ]
        },
        "final_lock_gate_design": {
            "required_token": "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY",
            "token_expiry_minutes": 30,
            "max_publish_count": 1,
            "publish_execution_in_phase10_3": "NO_GO",
            "wordpress_write_executed_in_phase10_3": False,
        },
        "decision_gate_matrix": [
            {
                "decision": "GO_PUBLISH_ONE_TIME_MANUAL_ONLY",
                "gate_result": "UNLOCK_CANDIDATE",
                "publish_execution_in_phase10_3": "NO_GO",
            }
        ],
    }


def _run(p10_3: dict) -> tuple[dict, dict, str]:
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        i10_3 = tdp / "p10_3.json"
        out_json = tdp / "p10_4.json"
        out_md = tdp / "p10_4.md"

        _write(i10_3, p10_3)

        result = generate_report(i10_3, out_json, out_md)
        report = json.loads(out_json.read_text(encoding="utf-8"))
        md = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
        return result, report, md


def test_phase10_4_pass_with_phase10_3_input():
    result, report, _ = _run(_base_10_3())

    assert result["status"] == "PASS"
    assert report["status"] == "PASS"
    assert report["phase10_4_design_status"] == "PASS"
    assert report["current_decision"] == "KEEP_NO_GO"
    assert report["publish_candidate_unlocked_for_operator"] is False
    assert report["wordpress_publish_execution"] == "NO_GO"
    assert report["wordpress_write_executed"] is False
    assert report["manual_unlock_candidate_validation_design"]["validation_checks_count"] == 8


def test_phase10_4_aborts_when_phase10_3_not_pass():
    p10_3 = _base_10_3()
    p10_3["status"] = "ABORT"

    result, report, _ = _run(p10_3)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_4_aborts_when_decision_mismatch():
    p10_3 = _base_10_3()
    p10_3["current_decision"] = "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, report, _ = _run(p10_3)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_4_aborts_when_publish_candidate_unlocked_true():
    p10_3 = _base_10_3()
    p10_3["publish_candidate_unlocked_for_operator"] = True

    result, report, _ = _run(p10_3)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_4_aborts_on_draft_mismatch():
    p10_3 = _base_10_3()
    p10_3["wordpress_draft_id"] = 999

    result, report, _ = _run(p10_3)

    assert result["status"] == "ABORT"
    assert report["status"] == "ABORT"


def test_phase10_4_generates_markdown_on_pass():
    _, report, md = _run(_base_10_3())

    assert report["status"] == "PASS"
    assert "Phase 10-4" in md
    assert "VALID_UNLOCK_CANDIDATE" in md
    assert "NO_GO" in md
    assert "validation_checks_count: 8" in md
