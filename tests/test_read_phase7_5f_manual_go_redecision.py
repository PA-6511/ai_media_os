import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from read_phase7_5f_manual_go_redecision import read_manual_go_redecision


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_payload(decision="KEEP_FREEZE"):
    return {
        "package_type": "phase7_5f_manual_go_redecision",
        "phase": "Phase 7-5F",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "reviewer": "human_reviewer",
        "reviewer_is_human": True,
        "decision": decision,
        "approval_token": "NONE",
        "manual_confirmation": {
            "payload_title_and_content_reviewed": False,
            "content_url_validity_confirmed": False,
            "affiliate_tag_confirmed": False,
            "pr_disclosure_confirmed": False,
            "wordpress_editor_role_confirmed": False,
            "status_draft_only_confirmed": False,
            "manual_delete_procedure_confirmed": False,
            "approval_token_expiry_confirmed": False,
        },
        "token_constraints": {
            "one_time_only": True,
            "expires_minutes": 30,
            "post_status": "draft",
            "post_count_limit": 1,
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
        },
        "safety_flags": {
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


def run_case(payload):
    with tempfile.TemporaryDirectory() as td:
        input_path = Path(td) / "decision.json"
        output_path = Path(td) / "result.json"
        write_json(input_path, payload)
        result = read_manual_go_redecision(input_path, output_path)
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        return result, saved


def test_keep_freeze_passes_without_all_confirmations():
    result, saved = run_case(base_payload("KEEP_FREEZE"))
    assert result["status"] == "PASS"
    assert saved["decision"] == "KEEP_FREEZE"
    assert saved["phase7_5c_execution_unlocked_for_operator"] is False
    assert saved["wordpress_write_executed"] is False


def test_manual_go_passes_when_all_confirmed_and_token_valid():
    payload = base_payload("MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME")
    payload["approval_token"] = "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
    for key in payload["manual_confirmation"]:
        payload["manual_confirmation"][key] = True

    result, saved = run_case(payload)

    assert result["status"] == "PASS"
    assert saved["phase7_5c_execution_unlocked_for_operator"] is True
    assert saved["wordpress_draft_creation"] == "PENDING_MANUAL_ONE_TIME_EXECUTION"
    assert saved["wordpress_write_executed"] is False


def test_manual_go_aborts_if_any_confirmation_false():
    payload = base_payload("MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME")
    payload["approval_token"] = "MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME"
    for key in payload["manual_confirmation"]:
        payload["manual_confirmation"][key] = True
    payload["manual_confirmation"]["affiliate_tag_confirmed"] = False

    result, saved = run_case(payload)

    assert result["status"] == "ABORT"
    assert saved["wordpress_write_executed"] is False


def test_wrong_token_aborts():
    payload = base_payload("MANUAL_GO_SINGLE_DRAFT_CREATE_ONE_TIME")
    payload["approval_token"] = "APPROVE_SINGLE_DRAFT_CREATE_LIVE"

    for key in payload["manual_confirmation"]:
        payload["manual_confirmation"][key] = True

    result, _ = run_case(payload)

    assert result["status"] == "ABORT"


def test_publish_allowed_true_aborts():
    payload = base_payload("KEEP_FREEZE")
    payload["token_constraints"]["publish_allowed"] = True

    result, _ = run_case(payload)

    assert result["status"] == "ABORT"


def test_non_human_reviewer_aborts():
    payload = base_payload("KEEP_FREEZE")
    payload["reviewer"] = "ai_agent_reviewer"

    result, _ = run_case(payload)

    assert result["status"] == "ABORT"
