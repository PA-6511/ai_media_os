import json
import tempfile
from pathlib import Path

from scripts.record_draft_candidate_approval_evidence import record_draft_candidate_approval_evidence


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_review_result() -> dict:
    return {
        "package_type": "wordpress_draft_candidate_review_result",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": "APPROVE_DRY_RUN_ONLY",
        "status": "PASS",
        "reason": "approved for draft candidate dry-run flow only",
        "next_step": "record_draft_candidate_approval_evidence",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
    }


def run_case(payload: dict, precreate_output: bool = False):
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "review_result.json"
        out = base / "evidence.json"
        write_json(inp, payload)

        if precreate_output:
            write_json(out, {"existing": True})

        result = record_draft_candidate_approval_evidence(inp, out)
        saved = None
        if out.exists():
            saved = json.loads(out.read_text(encoding="utf-8"))
        return result, saved


def test_pass_and_approve_generates_evidence():
    result, saved = run_case(base_review_result())
    assert result["status"] == "PASS"
    assert result["evidence_generated"] is True
    assert saved["package_type"] == "draft_candidate_approval_evidence"
    assert saved["phase"] == "Phase 5-5"


def test_request_fix_aborts():
    payload = base_review_result()
    payload["decision"] = "REQUEST_FIX"
    payload["status"] = "WARN"
    payload["next_step"] = "request_fix"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_status_warn_aborts():
    payload = base_review_result()
    payload["status"] = "WARN"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_execution_live_aborts():
    payload = base_review_result()
    payload["execution"] = "LIVE"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_aborts():
    payload = base_review_result()
    payload["auto_post"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_aborts():
    payload = base_review_result()
    payload["wordpress_write_executed"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_existing_evidence_aborts_without_overwrite():
    result, saved = run_case(base_review_result(), precreate_output=True)
    assert result["status"] == "ABORT"
    assert saved == {"existing": True}


def test_evidence_keeps_production_flags_false():
    result, saved = run_case(base_review_result())
    assert result["status"] == "PASS"
    assert saved["safety_flags"]["wordpress_write_executed"] is False
    assert saved["safety_flags"]["auto_post"] is False
    assert saved["safety_flags"]["auto_update"] is False
    assert saved["safety_flags"]["auto_delete"] is False
    assert saved["safety_flags"]["auto_export"] is False
    assert saved["safety_flags"]["github_actions_triggered"] is False
    assert saved["safety_flags"]["slack_notification_executed"] is False


def test_evidence_has_pass_dry_run_only_status():
    _, saved = run_case(base_review_result())
    assert saved["status"] == "PASS_DRY_RUN_ONLY"
