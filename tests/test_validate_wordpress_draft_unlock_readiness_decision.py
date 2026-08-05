import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_unlock_readiness_decision import run_validation, validate_decision


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_decision() -> dict:
    return {
        "phase": "Phase 6-7",
        "decision_name": "wordpress_draft_unlock_readiness_decision_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "decision_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "real_write_enabled": False,
        "readiness_result": "READINESS_DESIGN_PASS",
        "required_phase_checks": [
            "phase6_1_release_policy_validation_result.status == PASS",
            "phase6_2_preflight_gate_validation_result.status == PASS",
            "phase6_3_release_decision_rules_validation_result.status == PASS",
            "phase6_4_controlled_unlock_plan_validation_result.status == PASS",
            "phase6_5_execution_spec_validation_result.status == PASS",
            "phase6_6_pre_execution_rehearsal_validation_result.status == PASS"
        ],
        "warn_review_requirements": {
            "phase5_warn_handling_confirmed": True,
            "affiliate_tag_warn_handling_confirmed": True,
            "content_url_missing_warn_handling_confirmed": True,
            "explicit_human_override_required_for_warn": True
        },
        "readiness_logic": {
            "all_phase_checks_must_pass": True,
            "warn_handling_must_be_documented": True,
            "real_write_must_remain_disabled": True,
            "wordpress_write_executed_must_be_false": True,
            "result_when_all_conditions_met": "READINESS_DESIGN_PASS",
            "result_when_any_condition_missing": "READINESS_DESIGN_BLOCK"
        },
        "hard_block_conditions": [
            "phase_check_missing_or_failed == true",
            "warn_handling_not_confirmed == true",
            "real_write_enabled == true",
            "wordpress_write_executed == true",
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


def test_valid_readiness_pass():
    result = validate_decision(base_decision())
    assert result["status"] == "PASS"
    assert result["readiness_result"] == "READINESS_DESIGN_PASS"


def test_real_write_enabled_true_aborts():
    d = base_decision()
    d["real_write_enabled"] = True
    result = validate_decision(d)
    assert result["status"] == "ABORT"


def test_missing_phase_check_aborts():
    d = base_decision()
    d["required_phase_checks"].remove("phase6_6_pre_execution_rehearsal_validation_result.status == PASS")
    result = validate_decision(d)
    assert result["status"] == "ABORT"


def test_warn_handling_missing_aborts():
    d = base_decision()
    d["warn_review_requirements"]["affiliate_tag_warn_handling_confirmed"] = False
    result = validate_decision(d)
    assert result["status"] == "ABORT"


def test_bad_readiness_logic_result_aborts():
    d = base_decision()
    d["readiness_logic"]["result_when_all_conditions_met"] = "GO"
    result = validate_decision(d)
    assert result["status"] == "ABORT"


def test_run_validation_writes_output():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        inp = base / "decision.json"
        out = base / "result.json"
        write_json(inp, base_decision())

        result = run_validation(inp, out)
        assert out.exists()
        saved = json.loads(out.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["decision_status"] == "DESIGN_ONLY"
        assert saved["readiness_result"] == "READINESS_DESIGN_PASS"
        assert saved["production_status"] == "NO_GO"
        assert saved["wordpress_draft_creation"] == "NO_GO"
        assert saved["real_write_enabled"] is False
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
        assert result["status"] == "PASS"
