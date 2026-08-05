import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from read_phase8_7_publish_go_no_go_decision import read_publish_go_no_go_decision


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def phase8_6_payload() -> dict:
    return {
        "status": "PASS",
        "target_draft_id": 110,
    }


def phase8_2_payload() -> dict:
    return {
        "status": "PASS",
        "decision": "APPROVE",
    }


def base_payload(decision="KEEP_NO_GO"):
    return {
        "package_type": "phase8_7_publish_go_no_go_decision",
        "phase": "Phase 8-7",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "reviewer": "manual_human_reviewer",
        "reviewer_is_human": True,
        "decision": decision,
        "approval_token": "NONE",
        "wordpress_draft_id": 110,
        "manual_confirmation": {
            "phase8_6_readiness_pass_confirmed": True,
            "target_draft_id_confirmed": True,
            "target_status_draft_confirmed": True,
            "human_reviewer_confirmed": True,
            "token_constraints_confirmed": True,
            "no_go_scope_understood_confirmed": True,
            "manual_publish_only_confirmed": True,
            "publish_not_executed_in_phase8_7_confirmed": True,
        },
        "review_notes": {
            "summary": "ok",
            "fix_requests": [],
        },
        "safety_flags": {
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
        },
    }


def run_case(payload, p86=None, p82=None):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        input_path = td / "input.json"
        output_path = td / "result.json"
        p86_path = td / "phase8_6.json"
        p82_path = td / "phase8_2.json"

        write_json(input_path, payload)
        write_json(p86_path, p86 or phase8_6_payload())
        write_json(p82_path, p82 or phase8_2_payload())

        import read_phase8_7_publish_go_no_go_decision as mod

        old_p86 = mod.PHASE8_6_RESULT
        old_p82 = mod.PHASE8_2_RESULT
        mod.PHASE8_6_RESULT = p86_path
        mod.PHASE8_2_RESULT = p82_path
        try:
            result = read_publish_go_no_go_decision(input_path, output_path)
        finally:
            mod.PHASE8_6_RESULT = old_p86
            mod.PHASE8_2_RESULT = old_p82

        saved = json.loads(output_path.read_text(encoding="utf-8"))
        return result, saved


def test_keep_no_go_passes():
    result, saved = run_case(base_payload("KEEP_NO_GO"))
    assert result["status"] == "PASS"
    assert saved["publish_candidate_unlocked_for_operator"] is False
    assert saved["wordpress_publish_execution"] == "NO_GO"


def test_go_passes_when_all_confirmed_and_token_valid():
    payload = base_payload("GO_PUBLISH_ONE_TIME_MANUAL_ONLY")
    payload["approval_token"] = "APPROVE_PUBLISH_ONE_TIME_MANUAL_ONLY"

    result, saved = run_case(payload)

    assert result["status"] == "PASS"
    assert saved["publish_candidate_unlocked_for_operator"] is True
    assert saved["wordpress_write_executed"] is False


def test_request_fix_warn():
    result, saved = run_case(base_payload("REQUEST_FIX"))
    assert result["status"] == "WARN"
    assert saved["publish_candidate_unlocked_for_operator"] is False


def test_non_human_reviewer_aborts():
    payload = base_payload("KEEP_NO_GO")
    payload["reviewer_is_human"] = False

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_draft_id_mismatch_aborts():
    payload = base_payload("KEEP_NO_GO")
    payload["wordpress_draft_id"] = 999

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_forbidden_flag_true_aborts():
    payload = base_payload("KEEP_NO_GO")
    payload["safety_flags"]["publish_allowed"] = True

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"
