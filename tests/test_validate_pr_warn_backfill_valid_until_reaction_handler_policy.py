import json
from pathlib import Path

from scripts.validate_pr_warn_backfill_valid_until_reaction_handler_policy import validate

POLICY_PATH = Path("config/pr_warn_backfill_valid_until_reaction_handler_policy.json")

def test_policy_file_exists_and_valid_json():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert policy["phase"] == "PR_WARN_BACKFILL_PHASE1Y_VALID_UNTIL_REACTION_HANDLER_POLICY"

def test_policy_validator_passes():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert validate(policy) == []

def test_write_and_live_are_never_allowed():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert policy["wordpress_write_allowed"] is False
    assert policy["approved_true_allowed"] is False
    assert policy["live_execution_allowed"] is False
    assert policy["wordpress_post_put_patch_delete_allowed"] is False

def test_busy_fallback_is_read_only_revalidation():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert policy["busy_fallback_enabled"] is True
    assert policy["busy_fallback_action"] == "READ_ONLY_REVALIDATION"
    assert policy["wordpress_get_allowed_only_during_revalidation"] is True

def test_soft_expiry_and_reaction_timeout_are_fixed():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    assert policy["soft_expiry_threshold_minutes"] == 10
    assert policy["reaction_timeout_minutes"] == 2

def test_active_approval_refresh_constraints_are_safe():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    constraints = policy["auto_active_approval_refresh_constraints"]
    assert constraints["approved_must_remain_false"] is True
    assert constraints["wordpress_live_write_allowed_must_remain_false"] is True
    assert constraints["created_for_execution_must_remain_false"] is True
    assert constraints["allowed_changed_fields_must_equal"] == ["content"]
    assert constraints["max_live_updates_must_equal"] == 1

def test_design_only_implementation_status_is_false():
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    status = policy["implementation_status"]
    assert status["reaction_monitor_created"] is False
    assert status["notification_sender_created"] is False
    assert status["auto_revalidation_runner_created"] is False
    assert status["wordpress_api_called_in_this_phase"] is False
    assert status["wordpress_write_executed"] is False
    assert status["live_execution_executed"] is False
    assert status["approved_true_created"] is False
