import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_pre_execution_rehearsal import run_validation, validate_rehearsal


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_rehearsal() -> dict:
    return {
        "phase": "Phase 6-6",
        "rehearsal_name": "wordpress_draft_pre_execution_rehearsal_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "rehearsal_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "rehearsal_enabled": True,
        "real_write_enabled": False,
        "rehearsal_scope": {
            "target_operation": "single_wordpress_draft_creation_rehearsal",
            "max_posts_per_run": 1,
            "target_post_status": "draft",
            "simulate_only": True,
            "wordpress_rest_call_must_be_skipped": True
        },
        "required_inputs": [
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
        "preconditions": [
            "phase6_1_release_policy_validation_result.status == PASS",
            "phase6_2_preflight_gate_validation_result.status == PASS",
            "phase6_3_release_decision_rules_validation_result.status == PASS",
            "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
            "phase6_5_execution_spec_validation_result.status == PASS",
            "execution_enabled == false",
            "wordpress_write_executed == false"
        ],
        "rehearsal_sequence": [
            {"step": 1, "name": "load_inputs_and_schema_check", "stop_on_failure": True},
            {"step": 2, "name": "phase_gate_and_policy_check", "stop_on_failure": True},
            {"step": 3, "name": "human_review_and_expiry_check", "stop_on_failure": True},
            {"step": 4, "name": "wordpress_permission_and_scope_check", "stop_on_failure": True},
            {"step": 5, "name": "payload_simulation_without_send", "stop_on_failure": True},
            {"step": 6, "name": "evidence_dry_record_and_signoff", "stop_on_failure": True}
        ],
        "evidence_requirements": {
            "required_in_phase6_6": True,
            "store_as_simulation_only": True,
            "required_fields": [
                "request_id",
                "candidate_id",
                "reviewer_id",
                "decision_token",
                "simulated_payload_hash",
                "simulated_at",
                "result_status",
                "write_api_called"
            ]
        },
        "stop_conditions": [
            "missing_required_input == true",
            "precondition_not_met == true",
            "human_review_missing_or_expired == true",
            "affiliate_check_unresolved_warn == true",
            "content_url_missing == true",
            "pr_disclosure_missing == true",
            "wordpress_role_not_allowed == true",
            "wordpress_rest_post_attempted == true",
            "wordpress_rest_put_patch_attempted == true",
            "publish_attempted == true",
            "update_existing_post_attempted == true",
            "delete_post_attempted == true",
            "cron_change_attempted == true",
            "github_actions_trigger_attempted == true",
            "slack_production_notification_attempted == true",
            "vps_self_builder_execution_attempted == true",
            "env_secret_credential_auto_edit_attempted == true"
        ],
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


def test_valid_rehearsal_pass():
    result = validate_rehearsal(base_rehearsal())
    assert result["status"] == "PASS"
    assert result["real_write_enabled"] is False


def test_real_write_enabled_true_aborts():
    r = base_rehearsal()
    r["real_write_enabled"] = True
    result = validate_rehearsal(r)
    assert result["status"] == "ABORT"


def test_rehearsal_step_order_invalid_aborts():
    r = base_rehearsal()
    r["rehearsal_sequence"][4]["name"] = "unexpected_step"
    result = validate_rehearsal(r)
    assert result["status"] == "ABORT"


def test_missing_precondition_aborts():
    r = base_rehearsal()
    r["preconditions"].remove("phase6_5_execution_spec_validation_result.status == PASS")
    result = validate_rehearsal(r)
    assert result["status"] == "ABORT"


def test_evidence_required_false_aborts():
    r = base_rehearsal()
    r["evidence_requirements"]["required_in_phase6_6"] = False
    result = validate_rehearsal(r)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "rehearsal.json"
        out = base / "result.json"
        write_json(inp, base_rehearsal())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["rehearsal_status"] == "DESIGN_ONLY"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
