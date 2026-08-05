import json
import tempfile
from pathlib import Path

from scripts.read_wordpress_draft_candidate_review import read_wordpress_draft_candidate_review


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_review(decision: str = "APPROVE_DRY_RUN_ONLY") -> dict:
    return {
        "package_type": "wordpress_draft_candidate_review",
        "source": "human_operator",
        "target": "core_consensus_ai",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "human_approval_required": True,
        "decision": decision,
        "reason": "test",
        "wordpress_write_executed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
    }


def run_case(payload: dict):
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "review.json"
        out = base / "result.json"
        write_json(inp, payload)
        result = read_wordpress_draft_candidate_review(inp, out)
        saved = json.loads(out.read_text(encoding="utf-8"))
        return result, saved


def test_approve_dry_run_only_pass():
    result, saved = run_case(base_review("APPROVE_DRY_RUN_ONLY"))
    assert result["status"] == "PASS"
    assert saved["next_step"] == "record_draft_candidate_approval_evidence"


def test_request_fix_warn():
    result, saved = run_case(base_review("REQUEST_FIX"))
    assert result["status"] == "WARN"
    assert saved["next_step"] == "request_fix"


def test_reject_fail():
    result, saved = run_case(base_review("REJECT"))
    assert result["status"] == "FAIL"
    assert saved["next_step"] == "stop"


def test_abort_abort():
    result, saved = run_case(base_review("ABORT"))
    assert result["status"] == "ABORT"
    assert saved["next_step"] == "abort"


def test_unknown_decision_abort():
    result, _ = run_case(base_review("APPROVE_LIVE"))
    assert result["status"] == "ABORT"


def test_execution_live_abort():
    payload = base_review()
    payload["execution"] = "LIVE"
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_auto_post_true_abort():
    payload = base_review()
    payload["auto_post"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_wordpress_write_executed_true_abort():
    payload = base_review()
    payload["wordpress_write_executed"] = True
    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_result_file_generated_and_production_flags_false():
    result, saved = run_case(base_review("APPROVE_DRY_RUN_ONLY"))
    assert result["status"] == "PASS"
    assert saved["wordpress_write_executed"] is False
    assert saved["auto_post"] is False
    assert saved["auto_update"] is False
    assert saved["auto_delete"] is False
    assert saved["auto_export"] is False
