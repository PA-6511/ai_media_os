import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase9_2_publish_go_redecision_input_gate import run_validation

RUNBOOK_RESULT = ROOT / "exchange" / "logs" / "phase9_1_publish_go_redecision_manual_publish_runbook_generation_result.json"
OUT_JSON = ROOT / "exchange" / "logs" / "phase9_2_publish_go_redecision_input_gate_result.json"

VALID_GO_TOKEN = "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY"

ALL_CONFIRMED = {
    "phase9_1_runbook_reviewed_confirmed": True,
    "target_draft_id_confirmed": True,
    "target_status_draft_confirmed": True,
    "human_reviewer_confirmed": True,
    "token_constraints_confirmed": True,
    "no_go_scope_understood_confirmed": True,
    "manual_publish_only_confirmed": True,
    "publish_not_executed_in_phase9_2_confirmed": True,
}

SAFE_FLAGS = {
    "publish_allowed": False,
    "update_allowed": False,
    "delete_allowed": False,
    "export_allowed": False,
    "wordpress_post_enabled": False,
    "real_write_enabled": False,
    "wordpress_write_executed": False,
    "auto_post": False,
    "auto_update": False,
    "auto_delete": False,
    "auto_export": False,
    "github_actions_triggered": False,
    "slack_notification_executed": False,
    "vps_self_builder_executed": False,
    "env_or_secrets_modified": False,
}


def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _base_input(decision="KEEP_NO_GO", token="NONE", confirmation=None):
    return {
        "package_type": "phase9_2_publish_go_redecision_input_gate",
        "phase": "Phase 9-2",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "reviewer": "manual_human_reviewer",
        "reviewer_is_human": True,
        "decision": decision,
        "approval_token": token,
        "wordpress_draft_id": 110,
        "manual_confirmation": confirmation if confirmation is not None else {k: False for k in ALL_CONFIRMED},
        "review_notes": {"summary": "test", "fix_requests": []},
        "safety_flags": SAFE_FLAGS.copy(),
    }


def _run(input_data: dict) -> dict:
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        inp = td / "input.json"
        out = td / "result.json"
        _write(inp, input_data)
        result = run_validation(inp, out)
        return result


def test_keep_no_go_passes_without_confirmations():
    result = _run(_base_input("KEEP_NO_GO"))
    assert result["status"] == "PASS"
    assert result["decision"] == "KEEP_NO_GO"
    assert result["publish_candidate_unlocked_for_operator"] is False
    assert result["wordpress_publish_execution"] == "NO_GO"
    assert result["wordpress_write_executed"] is False


def test_go_passes_when_all_confirmed_and_token_valid():
    result = _run(_base_input("GO_PUBLISH_ONE_TIME_MANUAL_ONLY", VALID_GO_TOKEN, ALL_CONFIRMED))
    assert result["status"] == "PASS"
    assert result["decision"] == "GO_PUBLISH_ONE_TIME_MANUAL_ONLY"
    assert result["publish_candidate_unlocked_for_operator"] is True
    # publish は実行されていない
    assert result["wordpress_write_executed"] is False
    assert result["wordpress_publish_execution"] == "NO_GO"


def test_go_with_wrong_token_aborts():
    result = _run(_base_input("GO_PUBLISH_ONE_TIME_MANUAL_ONLY", "WRONG_TOKEN", ALL_CONFIRMED))
    assert result["status"] == "ABORT"
    assert result["publish_candidate_unlocked_for_operator"] is False


def test_go_with_incomplete_confirmation_aborts():
    incomplete = {**ALL_CONFIRMED, "target_draft_id_confirmed": False}
    result = _run(_base_input("GO_PUBLISH_ONE_TIME_MANUAL_ONLY", VALID_GO_TOKEN, incomplete))
    assert result["status"] == "ABORT"
    assert result["publish_candidate_unlocked_for_operator"] is False


def test_request_fix_is_warn():
    result = _run(_base_input("REQUEST_FIX"))
    assert result["status"] == "WARN"
    assert result["publish_candidate_unlocked_for_operator"] is False
    assert result["next_step"] == "request_fix"


def test_forbidden_flag_true_aborts():
    data = _base_input("KEEP_NO_GO")
    data["safety_flags"]["publish_allowed"] = True
    result = _run(data)
    assert result["status"] == "ABORT"
    assert result["publish_candidate_unlocked_for_operator"] is False
