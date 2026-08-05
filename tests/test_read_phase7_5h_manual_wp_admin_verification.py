import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from read_phase7_5h_manual_wp_admin_verification import read_manual_wp_admin_verification


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def phase7_5c_payload() -> dict:
    return {
        "package_type": "phase7_5c_single_draft_create_live_result",
        "phase": "Phase 7-5C",
        "status": "PASS",
        "wordpress_write_executed": True,
        "relocked_after_execution": True,
        "created_post_id": 110,
        "wordpress_draft_id": 110,
        "created_post_status": "draft",
    }


def phase7_5g_payload() -> dict:
    return {
        "package_type": "phase7_5g_post_draft_creation_verification_report",
        "phase": "Phase 7-5G",
        "status": "PASS",
        "wordpress_draft_id": 110,
        "created_post_status": "draft",
        "wordpress_write_executed": True,
        "relocked_after_execution": True,
    }


def base_payload(decision="KEEP"):
    return {
        "package_type": "phase7_5h_manual_wp_admin_verification",
        "phase": "Phase 7-5H",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "reviewer": "manual_human_reviewer",
        "reviewer_is_human": True,
        "decision": decision,
        "wordpress_draft_id": 110,
        "manual_confirmation": {
            "post_id_exists_confirmed": True,
            "status_is_draft_confirmed": True,
            "not_published_confirmed": True,
            "title_matches_expected_confirmed": True,
            "content_sanity_checked_confirmed": True,
            "manual_delete_if_unneeded_confirmed": True,
        },
        "safety_flags": {
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
            "wordpress_post_enabled": False,
            "real_write_enabled": False,
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


def run_case(payload, p75c=None, p75g=None):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        input_path = td / "input.json"
        output_path = td / "result.json"
        phase7_5c_path = td / "phase7_5c.json"
        phase7_5g_path = td / "phase7_5g.json"

        write_json(input_path, payload)
        write_json(phase7_5c_path, p75c or phase7_5c_payload())
        write_json(phase7_5g_path, p75g or phase7_5g_payload())

        result = read_manual_wp_admin_verification(input_path, output_path)
        saved = json.loads(output_path.read_text(encoding="utf-8"))
        return result, saved


def test_keep_passes_when_all_confirmed():
    result, saved = run_case(base_payload("KEEP"))
    assert result["status"] == "PASS"
    assert saved["wordpress_draft_id"] == 110
    assert saved["created_post_status"] == "draft"


def test_manual_delete_passes_when_all_confirmed():
    result, saved = run_case(base_payload("MANUAL_DELETE"))
    assert result["status"] == "PASS"
    assert saved["next_step"] == "manual_delete_in_wp_admin_if_unneeded"


def test_request_fix_is_warn():
    result, saved = run_case(base_payload("REQUEST_FIX"))
    assert result["status"] == "WARN"
    assert saved["wordpress_write_executed"] is True


def test_non_human_reviewer_aborts():
    payload = base_payload("KEEP")
    payload["reviewer_is_human"] = False

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_draft_id_mismatch_aborts():
    payload = base_payload("KEEP")
    payload["wordpress_draft_id"] = 999

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_forbidden_flag_true_aborts():
    payload = base_payload("KEEP")
    payload["safety_flags"]["publish_allowed"] = True

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"
