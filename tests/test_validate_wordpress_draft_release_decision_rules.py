import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_release_decision_rules import run_validation, validate_rules


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_rules() -> dict:
    return {
        "phase": "Phase 6-3",
        "rules_name": "wordpress_draft_release_final_decision_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "rules_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "activation_target": {
            "decision_token": "APPROVE_DRAFT_CREATE_ONLY",
            "currently_allowed": False,
            "note": "reserved"
        },
        "prerequisites_for_activation": [
            "phase5_overall_completion_status in [PASS_DRY_RUN_ONLY, PASS_DRY_RUN_ONLY_WITH_WARN]",
            "phase6_1_design_validation_result.status == PASS",
            "phase6_2_preflight_gate_validation_result.status == PASS",
            "human_review_final_decision == APPROVE_DRAFT_CREATE_ONLY",
            "post_count_limit == 1",
            "post_status == draft",
            "wordpress_write_executed == false"
        ],
        "warn_handling_rules": {
            "phase5_warn_requires_explicit_human_override": True,
            "phase5_warn_without_override_is_block": True,
            "quality_warn_requires_human_review": True
        },
        "hard_stop_conditions": [
            "affiliate_tag_unverified == true",
            "content_url_missing == true",
            "pr_label_missing == true",
            "post_count_limit != 1",
            "post_status != draft",
            "wordpress_user_role_not_allowed == true",
            "human_review_missing == true",
            "human_review_decision_not_APPROVE_DRAFT_CREATE_ONLY == true",
            "secrets_or_env_auto_edit_detected == true",
            "wordpress_rest_execute_before_gate == true",
            "publish_request_detected == true",
            "update_request_detected == true",
            "delete_request_detected == true",
            "export_request_detected == true",
            "vps_self_builder_execution_enabled == true"
        ],
        "wordpress_permission_requirements": {
            "allowed_roles": ["editor", "administrator"],
            "application_password_required": True,
            "token_scope_limited": True,
            "username_must_be_dedicated": True
        },
        "final_human_review_requirements": {
            "required": True,
            "decision_must_be": "APPROVE_DRAFT_CREATE_ONLY",
            "decision_expiry_minutes": 30,
            "reviewer_identity_required": True,
            "review_timestamp_required": True
        },
        "post_execution_evidence_requirements": {
            "required": False,
            "note": "design-only",
            "future_required_fields": ["draft_post_id"]
        },
        "retry_policy": {
            "retry_on_failure": False,
            "auto_retry_forbidden": True,
            "manual_requeue_requires_new_review": True
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


def test_valid_rules_pass():
    result = validate_rules(base_rules())
    assert result["status"] == "PASS"
    assert result["production_status"] == "NO_GO"


def test_currently_allowed_true_aborts():
    r = base_rules()
    r["activation_target"]["currently_allowed"] = True
    result = validate_rules(r)
    assert result["status"] == "ABORT"


def test_execution_live_aborts():
    r = base_rules()
    r["execution"] = "LIVE"
    result = validate_rules(r)
    assert result["status"] == "ABORT"


def test_missing_hard_stop_aborts():
    r = base_rules()
    r["hard_stop_conditions"].remove("content_url_missing == true")
    result = validate_rules(r)
    assert result["status"] == "ABORT"


def test_invalid_review_decision_rule_aborts():
    r = base_rules()
    r["final_human_review_requirements"]["decision_must_be"] = "APPROVE_DRY_RUN_ONLY"
    result = validate_rules(r)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "rules.json"
        out = base / "result.json"
        write_json(inp, base_rules())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
