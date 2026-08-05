import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from record_dry_run_approval_evidence import record_dry_run_approval_evidence


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_result():
    return {
        "package_type": "human_decision_result",
        "source": "read_human_review_decision",
        "target": "core_consensus_ai",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": "APPROVE_DRY_RUN_ONLY",
        "status": "PASS",
        "reason": "approved for DRY_RUN evidence only",
        "next_step": "record_dry_run_evidence",
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "wordpress_write_executed": False,
        "slack_notification_executed": False,
        "github_actions_triggered": False,
    }


def run_case(payload, precreate_output=False):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = Path(tmpdir) / "human_decision_result.json"
        output_path = Path(tmpdir) / "dry_run_approval_evidence.json"
        write_json(input_path, payload)

        if precreate_output:
            write_json(output_path, {"existing": True})

        result = record_dry_run_approval_evidence(input_path, output_path)

        saved = None
        if output_path.exists():
            saved = json.loads(output_path.read_text(encoding="utf-8"))

        return result, saved


def test_approve_dry_run_only_pass_generates_evidence():
    result, saved = run_case(base_result())
    assert result["status"] == "PASS"
    assert result["evidence_generated"] is True
    assert saved["package_type"] == "dry_run_approval_evidence"
    assert saved["phase"] == "Phase 4-7"


def test_request_fix_aborts():
    payload = base_result()
    payload["decision"] = "REQUEST_FIX"
    payload["status"] = "WARN"
    payload["next_step"] = "request_fix"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_status_warn_aborts():
    payload = base_result()
    payload["status"] = "WARN"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_execution_live_aborts():
    payload = base_result()
    payload["execution"] = "LIVE"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    payload = base_result()
    payload["auto_post"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    payload = base_result()
    payload["wordpress_write_executed"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_existing_evidence_aborts_without_overwrite():
    result, saved = run_case(base_result(), precreate_output=True)
    assert result["status"] == "ABORT"
    assert saved == {"existing": True}


def test_generated_evidence_keeps_production_flags_false():
    _, saved = run_case(base_result())
    assert saved["safety_flags"]["auto_post"] is False
    assert saved["safety_flags"]["auto_update"] is False
    assert saved["safety_flags"]["auto_delete"] is False
    assert saved["safety_flags"]["auto_export"] is False
    assert saved["safety_flags"]["wordpress_write_executed"] is False
    assert saved["safety_flags"]["slack_notification_executed"] is False
    assert saved["safety_flags"]["github_actions_triggered"] is False


def test_evidence_contains_phase_4_7():
    _, saved = run_case(base_result())
    assert saved["phase"] == "Phase 4-7"
