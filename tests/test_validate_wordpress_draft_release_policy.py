import json
import tempfile
from pathlib import Path

from scripts.validate_wordpress_draft_release_policy import run_validation, validate_policy


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def base_policy() -> dict:
    return {
        "phase": "Phase 6-1",
        "policy_name": "wordpress_real_draft_limited_release_design",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "policy_status": "DESIGN_ONLY",
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "release_constraints": {
            "single_item_only": True,
            "draft_only": True,
            "non_public_only": True,
            "requires_human_approval": True,
            "requires_quality_validation": True,
            "requires_affiliate_url_check": True,
            "requires_pr_label_check": True,
            "max_items_per_run": 1,
        },
        "pre_abort_conditions": ["execution!=DRY_RUN"],
        "write_preflight_required_checks": ["draft_candidate_review_result.status == PASS"],
        "post_write_evidence_spec": {"required": False, "note": "design-only"},
        "forbidden_during_phase6_1": [
            "wordpress_rest_post",
            "wordpress_rest_put_patch",
            "publish_post",
            "update_existing_post",
            "delete_post",
            "bulk_posting",
            "cron_automation",
            "github_actions_trigger",
            "slack_production_notification",
            "vps_self_builder_execution",
            "env_secret_auto_edit",
        ],
    }


def test_valid_policy_passes():
    result = validate_policy(base_policy())
    assert result["status"] == "PASS"
    assert result["production_status"] == "NO_GO"


def test_execution_live_aborts():
    p = base_policy()
    p["execution"] = "LIVE"
    result = validate_policy(p)
    assert result["status"] == "ABORT"


def test_wordpress_draft_creation_yes_aborts():
    p = base_policy()
    p["wordpress_draft_creation"] = "GO"
    result = validate_policy(p)
    assert result["status"] == "ABORT"


def test_max_items_not_one_aborts():
    p = base_policy()
    p["release_constraints"]["max_items_per_run"] = 2
    result = validate_policy(p)
    assert result["status"] == "ABORT"


def test_missing_forbidden_action_aborts():
    p = base_policy()
    p["forbidden_during_phase6_1"].remove("wordpress_rest_post")
    result = validate_policy(p)
    assert result["status"] == "ABORT"


def test_run_validation_writes_result_file():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        policy_path = base / "policy.json"
        result_path = base / "result.json"
        write_json(policy_path, base_policy())

        result = run_validation(policy_path, result_path)
        assert result_path.exists()
        saved = json.loads(result_path.read_text(encoding="utf-8"))
        assert saved["status"] == "PASS"
        assert saved["wordpress_write_executed"] is False
        assert saved["auto_post"] is False
        assert saved["auto_update"] is False
        assert saved["auto_delete"] is False
        assert saved["auto_export"] is False
