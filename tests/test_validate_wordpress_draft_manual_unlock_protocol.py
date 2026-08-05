import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_manual_unlock_protocol import run_validation, validate_protocol


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_protocol() -> dict:
    return {
        "phase": "Phase 6-9",
        "protocol_name": "wordpress_draft_manual_unlock_protocol_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "manual_unlock_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "unlock_currently_allowed": False,
        "real_write_enabled": False,
        "wordpress_write_executed": False,
        "unlock_scope": {
            "target": "single_wordpress_draft_only",
            "max_posts_on_first_unlock": 1,
            "target_post_status": "draft",
            "publish_forbidden_on_unlock": True,
            "update_existing_post_forbidden_on_unlock": True,
            "delete_post_forbidden_on_unlock": True
        },
        "reviewer_requirements": {
            "human_reviewer_required": True,
            "reviewer_identity_must_be_recorded": True,
            "reviewer_cannot_be_automated_agent": True,
            "review_decision_token": "APPROVE_MANUAL_UNLOCK_DRAFT_CREATE_ONLY",
            "review_expiry_minutes": 30,
            "review_timestamp_required": True
        },
        "evidence_checklist_before_unlock": [
            "phase6_1_through_6_8_all_PASS_confirmed",
            "readiness_result_is_READINESS_DESIGN_PASS",
            "final_go_no_go_reviewed_by_human",
            "warn_items_resolved_or_explicitly_overridden",
            "affiliate_tag_status_confirmed",
            "content_url_confirmed",
            "pr_disclosure_confirmed",
            "wordpress_user_role_confirmed",
            "application_password_active_confirmed",
            "no_forbidden_action_in_request",
            "secrets_env_non_edit_confirmed",
            "existing_post_impact_zero_confirmed"
        ],
        "unlock_decision_mapping": {
            "all_checklist_items_confirmed_and_human_approved": "UNLOCK_GRANTED_DRAFT_ONLY",
            "checklist_incomplete_or_warn_unresolved": "UNLOCK_BLOCKED_PENDING_REVIEW",
            "forbidden_action_detected": "UNLOCK_HARD_BLOCKED",
            "write_or_publish_detected": "UNLOCK_HARD_BLOCKED",
            "phase6_9_default": "UNLOCK_BLOCKED_DESIGN_ONLY"
        },
        "unlock_hard_block_conditions": [
            "human_review_missing == true",
            "human_review_expired == true",
            "review_decision_not_APPROVE_MANUAL_UNLOCK_DRAFT_CREATE_ONLY == true",
            "checklist_item_not_confirmed == true",
            "warn_unresolved_without_override == true",
            "wordpress_rest_post_attempted == true",
            "wordpress_rest_put_patch_attempted == true",
            "publish_attempted == true",
            "update_existing_post_attempted == true",
            "delete_post_attempted == true",
            "external_export_attempted == true",
            "github_actions_trigger_attempted == true",
            "slack_production_notification_attempted == true",
            "vps_self_builder_execution_attempted == true",
            "env_secret_credential_auto_edit_attempted == true"
        ],
        "post_unlock_evidence_spec": {
            "required_on_actual_unlock": True,
            "required_in_phase6_9": False,
            "future_required_fields": ["request_id", "reviewer_id", "draft_post_id"]
        },
        "re_lock_policy": {
            "auto_re_lock_after_single_use": True,
            "re_unlock_requires_new_full_review": True,
            "bulk_unlock_forbidden": True
        },
        "retry_policy": {
            "auto_retry_forbidden": True,
            "retry_on_failure": False,
            "manual_rerun_requires_new_review": True
        },
        "forbidden_actions": [
            "wordpress_rest_post",
            "wordpress_rest_put_patch",
            "publish_post",
            "update_existing_post",
            "delete_post",
            "bulk_posting",
            "external_export",
            "github_actions_trigger",
            "slack_production_notification",
            "cron_automation",
            "env_secret_auto_edit",
            "vps_self_builder_execution"
        ]
    }


def test_valid_protocol_pass():
    result = validate_protocol(base_protocol())
    assert result["status"] == "PASS"
    assert result["unlock_currently_allowed"] is False


def test_unlock_currently_allowed_true_aborts():
    p = base_protocol()
    p["unlock_currently_allowed"] = True
    result = validate_protocol(p)
    assert result["status"] == "ABORT"


def test_wrong_review_token_aborts():
    p = base_protocol()
    p["reviewer_requirements"]["review_decision_token"] = "APPROVE_DRAFT_CREATE_ONLY"
    result = validate_protocol(p)
    assert result["status"] == "ABORT"


def test_missing_checklist_item_aborts():
    p = base_protocol()
    p["evidence_checklist_before_unlock"].remove("existing_post_impact_zero_confirmed")
    result = validate_protocol(p)
    assert result["status"] == "ABORT"


def test_auto_relock_false_aborts():
    p = base_protocol()
    p["re_lock_policy"]["auto_re_lock_after_single_use"] = False
    result = validate_protocol(p)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "protocol.json"
        out = base / "result.json"
        write_json(inp, base_protocol())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["manual_unlock_status"] == "DESIGN_ONLY"
        assert saved["unlock_currently_allowed"] is False
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
