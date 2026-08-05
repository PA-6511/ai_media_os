import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_creation_execution_spec import run_validation, validate_spec


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_spec() -> dict:
    return {
        "phase": "Phase 6-5",
        "spec_name": "wordpress_draft_creation_execution_spec_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "spec_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "execution_enabled": False,
        "target_scope": {
            "operation": "create_single_wordpress_draft",
            "max_posts_per_run": 1,
            "target_post_status": "draft",
            "existing_post_impact_must_be_zero": True
        },
        "input_contract": {
            "required_fields": [
                "request_id",
                "candidate_id",
                "title",
                "body_markdown",
                "content_url",
                "pr_disclosure",
                "affiliate_check_result",
                "human_review_decision",
                "reviewer_id",
                "reviewed_at"
            ],
            "constraints": [
                "title_non_empty",
                "body_markdown_non_empty"
            ]
        },
        "execution_sequence": [
            {"step": 1, "name": "load_and_validate_inputs", "stop_on_failure": True},
            {"step": 2, "name": "validate_phase_gates", "stop_on_failure": True},
            {"step": 3, "name": "validate_human_review_freshness", "stop_on_failure": True},
            {"step": 4, "name": "validate_wordpress_permission", "stop_on_failure": True},
            {"step": 5, "name": "dry_run_payload_build_only", "stop_on_failure": True},
            {"step": 6, "name": "record_planned_evidence_schema", "stop_on_failure": True}
        ],
        "gates_before_any_write": {
            "required": True,
            "checks": [
                "phase6_1_release_policy_validation_result.status == PASS",
                "phase6_2_preflight_gate_validation_result.status == PASS",
                "phase6_3_release_decision_rules_validation_result.status == PASS",
                "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
                "unlock_currently_allowed == false in phase6_5",
                "wordpress_write_executed == false"
            ]
        },
        "evidence_spec": {
            "required_in_phase6_5": False,
            "future_required_fields": ["request_id", "draft_post_id"]
        },
        "immediate_stop_conditions": [
            "input_validation_failed == true",
            "required_phase_gate_missing == true",
            "human_review_missing_or_expired == true",
            "wordpress_role_not_allowed == true",
            "secrets_env_auto_edit_detected == true",
            "publish_request_detected == true",
            "update_request_detected == true",
            "delete_request_detected == true",
            "wordpress_rest_post_requested == true",
            "wordpress_rest_put_patch_requested == true",
            "cron_change_requested == true",
            "github_actions_trigger_requested == true",
            "slack_production_notification_requested == true",
            "vps_self_builder_execution_enabled == true"
        ],
        "retry_policy": {
            "retry_on_failure": False,
            "auto_retry_forbidden": True,
            "manual_requeue_requires_new_review": True
        },
        "runtime_restrictions": {
            "wordpress_rest_post_forbidden": True,
            "wordpress_rest_put_patch_forbidden": True,
            "publish_forbidden": True,
            "update_existing_post_forbidden": True,
            "delete_post_forbidden": True,
            "cron_change_forbidden": True,
            "github_actions_trigger_forbidden": True,
            "slack_production_notification_forbidden": True,
            "vps_self_builder_execution_forbidden": True,
            "env_secret_credential_auto_edit_forbidden": True
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


def test_valid_spec_pass():
    result = validate_spec(base_spec())
    assert result["status"] == "PASS"
    assert result["execution_enabled"] is False


def test_execution_enabled_true_aborts():
    s = base_spec()
    s["execution_enabled"] = True
    result = validate_spec(s)
    assert result["status"] == "ABORT"


def test_max_posts_not_one_aborts():
    s = base_spec()
    s["target_scope"]["max_posts_per_run"] = 2
    result = validate_spec(s)
    assert result["status"] == "ABORT"


def test_sequence_order_invalid_aborts():
    s = base_spec()
    s["execution_sequence"][2]["name"] = "unexpected_step"
    result = validate_spec(s)
    assert result["status"] == "ABORT"


def test_missing_stop_condition_aborts():
    s = base_spec()
    s["immediate_stop_conditions"].remove("wordpress_rest_post_requested == true")
    result = validate_spec(s)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "spec.json"
        out = base / "result.json"
        write_json(inp, base_spec())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["spec_status"] == "DESIGN_ONLY"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
