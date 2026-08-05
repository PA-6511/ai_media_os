import json
from pathlib import Path

from scripts import validate_start_ls6b_wordpress_one_shot_draft_creation_result as validator


def write_json(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def success_result() -> dict:
    return {
        "phase": "LS-6B",
        "status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN",
        "execution_mode": "ONE_SHOT_WRITE_ALLOWED",
        "production_status": "LIMITED_GO_DRAFT_ONLY",
        "approval_label": "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY",
        "approval_is_actual": True,
        "post_id": 123,
        "post_status": "draft",
        "max_items": 1,
        "payload_count": 1,
        "wordpress_api_call_executed": True,
        "wordpress_write_executed": True,
        "wordpress_draft_creation_executed": True,
        "publish_executed": False,
        "future_schedule_executed": False,
        "existing_post_update_executed": False,
        "delete_executed": False,
        "amazon_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_token_consumed": True,
        "freeze_after_run_executed": True,
        "safe_stop": False,
        "next_phase": {
            "phase": "LS-7",
            "execution_allowed": False,
            "requires_human_review": True,
            "manual_publish_only": True,
        },
    }


def preflight_result() -> dict:
    return {
        "phase": "LS-6B",
        "status": "LS6B_ONE_SHOT_DRAFT_CREATION_PREFLIGHT_PASS_NO_EXECUTION",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "approval_token_consumed": False,
    }


def safe_stop_result() -> dict:
    return {
        "phase": "LS-6B",
        "status": "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP",
        "safe_stop": True,
        "publish_executed": False,
        "future_schedule_executed": False,
        "existing_post_update_executed": False,
        "delete_executed": False,
    }


def test_success_validated():
    status, errors = validator.validate_result(success_result())
    assert status == "LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED"
    assert errors == []


def test_preflight_validated():
    status, errors = validator.validate_result(preflight_result())
    assert status == "LS6B_PREFLIGHT_RESULT_VALIDATED_NO_EXECUTION"
    assert errors == []


def test_safe_stop_recorded():
    status, errors = validator.validate_result(safe_stop_result())
    assert status == "LS6B_SAFE_STOP_RESULT_RECORDED"
    assert errors == []


def test_publish_true_fails():
    result = success_result()
    result["publish_executed"] = True
    status, _ = validator.validate_result(result)
    assert status == "LS6B_RESULT_VALIDATION_FAILED"


def test_post_status_publish_fails():
    result = success_result()
    result["post_status"] = "publish"
    status, _ = validator.validate_result(result)
    assert status == "LS6B_RESULT_VALIDATION_FAILED"


def test_success_with_token_false_fails():
    result = success_result()
    result["approval_token_consumed"] = False
    status, _ = validator.validate_result(result)
    assert status == "LS6B_RESULT_VALIDATION_FAILED"


def test_next_phase_execution_allowed_true_fails():
    result = success_result()
    result["next_phase"]["execution_allowed"] = True
    status, _ = validator.validate_result(result)
    assert status == "LS6B_RESULT_VALIDATION_FAILED"


def test_secret_flag_true_fails():
    result = success_result()
    result["credential_secret_output"] = True
    status, _ = validator.validate_result(result)
    assert status == "LS6B_RESULT_VALIDATION_FAILED"
