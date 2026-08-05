import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from read_phase8_2_manual_pre_publish_review import read_manual_pre_publish_review


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def phase8_1_payload() -> dict:
    return {
        "package_type": "phase8_1_pre_publish_review_design_validation_result",
        "phase": "Phase 8-1",
        "status": "PASS",
    }


def phase7_6_payload() -> dict:
    return {
        "package_type": "phase7_6_wordpress_draft_creation_overall_completion_report",
        "phase": "Phase 7-6",
        "status": "PASS",
        "wordpress_draft_id": 110,
        "created_post_status": "draft",
    }


def base_payload(decision="APPROVE"):
    return {
        "package_type": "phase8_2_manual_pre_publish_review",
        "phase": "Phase 8-2",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "reviewer": "manual_human_reviewer",
        "reviewer_is_human": True,
        "decision": decision,
        "wordpress_draft_id": 110,
        "manual_confirmation": {
            "title_reviewed": True,
            "content_reviewed": True,
            "pr_disclosure_confirmed": True,
            "links_valid_confirmed": True,
            "affiliate_tag_confirmed": True,
            "category_confirmed": True,
            "tags_confirmed": True,
            "publish_block_conditions_checked": True,
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


def run_case(payload, p81=None, p76=None):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        input_path = td / "input.json"
        output_path = td / "result.json"
        p81_path = td / "phase8_1.json"
        p76_path = td / "phase7_6.json"

        write_json(input_path, payload)
        write_json(p81_path, p81 or phase8_1_payload())
        write_json(p76_path, p76 or phase7_6_payload())

        # monkeypatch globals by importing module attributes dynamically
        import read_phase8_2_manual_pre_publish_review as mod

        old_p81 = mod.PHASE8_1_RESULT
        old_p76 = mod.PHASE7_6_RESULT
        mod.PHASE8_1_RESULT = p81_path
        mod.PHASE7_6_RESULT = p76_path
        try:
            result = read_manual_pre_publish_review(input_path, output_path)
        finally:
            mod.PHASE8_1_RESULT = old_p81
            mod.PHASE7_6_RESULT = old_p76

        saved = json.loads(output_path.read_text(encoding="utf-8"))
        return result, saved


def test_approve_passes_when_all_confirmed():
    result, saved = run_case(base_payload("APPROVE"))
    assert result["status"] == "PASS"
    assert saved["wordpress_draft_id"] == 110
    assert saved["wordpress_publish_execution"] == "NO_GO"


def test_request_fix_warn():
    result, saved = run_case(base_payload("REQUEST_FIX"))
    assert result["status"] == "WARN"
    assert saved["next_step"] == "request_fix_and_re_review"


def test_reject_warn():
    result, saved = run_case(base_payload("REJECT"))
    assert result["status"] == "WARN"
    assert saved["next_step"] == "reject_and_keep_draft"


def test_non_human_reviewer_aborts():
    payload = base_payload("APPROVE")
    payload["reviewer_is_human"] = False

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_draft_id_mismatch_aborts():
    payload = base_payload("APPROVE")
    payload["wordpress_draft_id"] = 999

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"


def test_forbidden_flag_true_aborts():
    payload = base_payload("APPROVE")
    payload["safety_flags"]["publish_allowed"] = True

    result, _ = run_case(payload)
    assert result["status"] == "ABORT"
