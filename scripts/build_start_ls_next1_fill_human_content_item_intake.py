#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_WAITING = "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
STATUS_PASSED = "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_FAILED_NO_EXECUTION"

LOCK_WAITING = "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_LOCKED_NO_EXECUTION"
LOCK_PASSED = "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_LOCKED_NO_EXECUTION"

REQUIRED_FIELDS = [
    "content_item_id",
    "target_post_id",
    "target_post_link",
    "payload_title",
    "payload_asin",
    "public_url",
    "public_rest_url",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_next1_fill_human_content_item_intake_policy.json")
    parser.add_argument("--ls-next1-result", default="exchange/runtime/start_ls_next1_next_content_item_intake_result.json")
    parser.add_argument("--ls-next1-lock", default="exchange/locks/start_ls_next1_next_content_item_intake.lock.json")
    parser.add_argument("--ls-next1-run-result", default="exchange/logs/start_ls_next1_next_content_item_intake_result.json")
    parser.add_argument("--ls-next1-validation-result", default="exchange/logs/start_ls_next1_next_content_item_intake_validation_result.json")
    parser.add_argument("--ls-next1-intake-template", default="exchange/intake/start_ls_next1_next_content_item_intake.template.json")
    parser.add_argument("--ls-next1-intake-record", default="exchange/intake/start_ls_next1_next_content_item_intake.json")
    parser.add_argument("--ls-reuse1-result", default="exchange/runtime/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--human-input-template-output", default="exchange/intake/start_ls_next1_fill_human_input.template.json")
    parser.add_argument("--human-input-record", default="exchange/intake/start_ls_next1_fill_human_input.json")
    parser.add_argument("--filled-intake-output", default="exchange/intake/start_ls_next1_filled_next_content_item_intake.json")
    parser.add_argument("--output", default="exchange/runtime/start_ls_next1_fill_human_content_item_intake_result.json")
    parser.add_argument("--lock-output", default="exchange/locks/start_ls_next1_fill_human_content_item_intake.lock.json")
    parser.add_argument("--report", default="reports/start_ls_next1_fill_human_content_item_intake_report.md")

    parser.add_argument("--create-human-input-template", action="store_true")
    parser.add_argument("--require-no-wordpress-api", action="store_true")
    parser.add_argument("--require-no-credential-read", action="store_true")
    parser.add_argument("--require-no-publish", action="store_true")
    parser.add_argument("--require-no-next-post-creation", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-post183-update", action="store_true")
    parser.add_argument("--forbid-auto-content-selection", action="store_true")
    parser.add_argument("--require-human-filled", action="store_true")
    parser.add_argument("--require-human-confirmed", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing file: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json: {path}")
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def human_input_template() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_TEMPLATE",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1-FILL",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "public_url": "",
        "public_rest_url": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "human_filled": False,
        "human_confirmed": False,
        "execution_allowed": False,
        "notes": "Fill this file manually. Do not let AI infer or guess these values.",
    }


def waiting_human_input_record() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEXT1_FILL_HUMAN_INPUT_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1-FILL",
        "status": "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "public_url": "",
        "public_rest_url": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "human_filled": False,
        "human_confirmed": False,
        "execution_allowed": False,
        "ready_for_ls_next_2": False,
        "missing_required_human_fields": list(REQUIRED_FIELDS),
        "errors": [],
    }


def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def compute_missing_fields(human: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_FIELDS:
        if is_missing(human.get(field)):
            missing.append(field)
    return missing


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEXT-1-FILL Human Content Item Intake Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- execution_mode: {payload['execution_mode']}",
        f"- production_status: {payload['production_status']}",
        f"- ls_next1_validated: {payload['ls_next1_validated']}",
        f"- ls_reuse1_validated: {payload['ls_reuse1_validated']}",
        f"- human_input_template_created: {payload['human_input_template_created']}",
        f"- human_input_record_exists: {payload['human_input_record_exists']}",
        f"- human_filled: {payload['human_filled']}",
        f"- human_confirmed: {payload['human_confirmed']}",
        f"- human_input_required: {payload['human_input_required']}",
        f"- intake_registration_completed: {payload['intake_registration_completed']}",
        f"- ready_for_ls_next_2: {payload['ready_for_ls_next_2']}",
        f"- execution_allowed: {payload['execution_allowed']}",
        f"- recommended_next_action: {payload['recommended_next_action']}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls_next1_result = try_load_json(Path(args.ls_next1_result), errors)
    ls_next1_lock = try_load_json(Path(args.ls_next1_lock), errors)
    ls_next1_run = try_load_json(Path(args.ls_next1_run_result), errors)
    ls_next1_validation = try_load_json(Path(args.ls_next1_validation_result), errors)
    _ls_next1_template = try_load_json(Path(args.ls_next1_intake_template), errors)
    _ls_next1_record = try_load_json(Path(args.ls_next1_intake_record), errors)
    ls_reuse1_result = try_load_json(Path(args.ls_reuse1_result), errors)

    req_prev = policy.get("required_previous_phase", {})
    req_next1 = req_prev.get("ls_next1", {})
    req_reuse = req_prev.get("ls_reuse1", {})
    human_policy = policy.get("human_input_policy", {})
    next_phase = policy.get("next_phase", {})

    req(args.create_human_input_template, "missing --create-human-input-template", errors)
    req(args.require_no_wordpress_api, "missing --require-no-wordpress-api", errors)
    req(args.require_no_credential_read, "missing --require-no-credential-read", errors)
    req(args.require_no_publish, "missing --require-no-publish", errors)
    req(args.require_no_next_post_creation, "missing --require-no-next-post-creation", errors)
    req(args.forbid_post119_update, "missing --forbid-post119-update", errors)
    req(args.forbid_post183_update, "missing --forbid-post183-update", errors)
    req(args.forbid_auto_content_selection, "missing --forbid-auto-content-selection", errors)

    req(ls_next1_result.get("status") == req_next1.get("required_run_status"), "LS-NEXT-1 status mismatch", errors)
    req(ls_next1_validation.get("status") == req_next1.get("required_validation_status"), "LS-NEXT-1 validation mismatch", errors)
    req(ls_next1_result == ls_next1_run, "LS-NEXT-1 run result mismatch", errors)
    req(ls_next1_result.get("production_status") == req_next1.get("required_production_status"), "LS-NEXT-1 production status mismatch", errors)
    req(bool(ls_next1_result.get("human_input_required", False)) is bool(req_next1.get("required_human_input_required", True)), "LS-NEXT-1 human_input_required mismatch", errors)
    req(bool(ls_next1_result.get("execution_allowed", True)) is bool(req_next1.get("required_execution_allowed", False)), "LS-NEXT-1 execution_allowed mismatch", errors)
    req(bool(ls_next1_result.get("ready_for_ls_next_2", True)) is bool(req_next1.get("required_ready_for_ls_next_2", False)), "LS-NEXT-1 ready_for_ls_next_2 mismatch", errors)
    req(bool(ls_next1_lock.get("locked", False)) is True, "LS-NEXT-1 lock mismatch", errors)

    reuse_status = str(ls_reuse1_result.get("status", ""))
    req(
        reuse_status in (
            str(req_reuse.get("required_validation_status", "")),
            "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION",
        ),
        "LS-REUSE-1 status mismatch",
        errors,
    )
    req(bool(ls_reuse1_result.get("reusable_template_built", False)) is bool(req_reuse.get("required_reusable_template_built", True)), "LS-REUSE-1 reusable_template_built mismatch", errors)

    template_created = False
    human_record_exists = Path(args.human_input_record).exists()

    if args.create_human_input_template and not Path(args.human_input_template_output).exists():
        write_json(Path(args.human_input_template_output), human_input_template())
    template_created = Path(args.human_input_template_output).exists()

    if not human_record_exists:
        write_json(Path(args.human_input_record), waiting_human_input_record())
        human_record_exists = True

    human_record = try_load_json(Path(args.human_input_record), errors)

    missing_fields = compute_missing_fields(human_record)
    human_filled = bool(human_record.get("human_filled", False))
    human_confirmed = bool(human_record.get("human_confirmed", False))

    invalid_human_errors: list[str] = []
    target_post_id = human_record.get("target_post_id")
    if target_post_id is not None:
        if not isinstance(target_post_id, int):
            invalid_human_errors.append("target_post_id must be integer")
        elif target_post_id <= 0:
            invalid_human_errors.append("target_post_id must be positive")
        elif target_post_id in (119, 183):
            invalid_human_errors.append("target_post_id forbidden")

    if human_record.get("expected_pre_publish_status", "draft") != "draft":
        invalid_human_errors.append("expected_pre_publish_status must be draft")
    if human_record.get("target_publish_status", "publish") != "publish":
        invalid_human_errors.append("target_publish_status must be publish")

    status = STATUS_WAITING
    production_status = "WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
    recommended_next_action = str(next_phase.get("recommended_next_action_if_missing", "WAIT_FOR_HUMAN_INPUT"))
    recommended_next_phase_options = ["LS-NEXT-1-FILL_AFTER_HUMAN_INPUT", "LS-MON-2"]

    intake_registration_completed = False
    ready_for_ls_next_2 = False
    human_input_required = True

    hard_error_count = len(errors)

    if not errors:
        if invalid_human_errors:
            errors.extend(invalid_human_errors)
            status = STATUS_FAILED
            production_status = "NO_EXECUTION_HUMAN_INTAKE_FILL_ONLY"
        else:
            require_hf = args.require_human_filled
            require_hc = args.require_human_confirmed
            should_wait = (
                (require_hf and not human_filled)
                or (require_hc and not human_confirmed)
                or bool(missing_fields)
            )
            if should_wait:
                status = STATUS_WAITING
                production_status = "WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
            else:
                status = STATUS_PASSED
                production_status = "NO_EXECUTION_HUMAN_INTAKE_FILLED"
                intake_registration_completed = True
                ready_for_ls_next_2 = bool(human_policy.get("ready_for_ls_next_2_if_valid", True))
                human_input_required = False
                recommended_next_action = str(next_phase.get("recommended_next_action_if_valid", "BEGIN_LS_NEXT_2_DRAFT_STATUS_AND_PAYLOAD_DRY_RUN"))
                recommended_next_phase_options = list(next_phase.get("recommended_next_phase_options", ["LS-NEXT-2_AFTER_HUMAN_INPUT", "LS-MON-2"]))

    filled_intake = {
        "document_type": "START_LS_NEXT1_FILLED_NEXT_CONTENT_ITEM_INTAKE_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1-FILL",
        "status": status,
        "content_item_id": human_record.get("content_item_id", ""),
        "target_post_id": human_record.get("target_post_id"),
        "target_post_link": human_record.get("target_post_link", ""),
        "payload_title": human_record.get("payload_title", ""),
        "payload_asin": human_record.get("payload_asin", ""),
        "expected_pre_publish_status": human_record.get("expected_pre_publish_status", "draft"),
        "target_publish_status": human_record.get("target_publish_status", "publish"),
        "public_url": human_record.get("public_url", ""),
        "public_rest_url": human_record.get("public_rest_url", ""),
        "human_filled": human_filled,
        "human_confirmed": human_confirmed,
        "execution_allowed": False,
        "ready_for_ls_next_2": ready_for_ls_next_2,
        "missing_required_human_fields": list(missing_fields),
        "errors": list(errors),
    }

    payload = {
        "phase": "LS-NEXT-1-FILL",
        "document_type": "START_LS_NEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_RESULT",
        "status": status,
        "execution_mode": "HUMAN_INPUT_REGISTRATION_ONLY_NO_EXECUTION",
        "production_status": production_status,
        "ls_next1_validated": ls_next1_validation.get("status") == req_next1.get("required_validation_status"),
        "ls_reuse1_validated": reuse_status in (
            str(req_reuse.get("required_validation_status", "")),
            "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION",
        ),
        "human_input_template_created": template_created,
        "human_input_record_exists": human_record_exists,
        "human_filled": human_filled,
        "human_confirmed": human_confirmed,
        "human_input_required": human_input_required,
        "intake_registration_completed": intake_registration_completed,
        "ready_for_ls_next_2": ready_for_ls_next_2,
        "execution_allowed": False,
        "content_item_id": human_record.get("content_item_id", ""),
        "target_post_id": human_record.get("target_post_id"),
        "target_post_link": human_record.get("target_post_link", ""),
        "payload_title": human_record.get("payload_title", ""),
        "payload_asin": human_record.get("payload_asin", ""),
        "expected_pre_publish_status": human_record.get("expected_pre_publish_status", "draft"),
        "target_publish_status": human_record.get("target_publish_status", "publish"),
        "public_url": human_record.get("public_url", ""),
        "public_rest_url": human_record.get("public_rest_url", ""),
        "missing_required_human_fields": list(missing_fields),
        "auto_content_selection_allowed": False,
        "next_post_creation_allowed": False,
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_put_executed": False,
        "wordpress_patch_executed": False,
        "wordpress_delete_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "publish_executed_by_this_phase": False,
        "next_post_created": False,
        "next_post_selected_by_ai": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "wordpress_new_post_executed": False,
        "wordpress_content_update_executed": False,
        "wordpress_title_update_executed": False,
        "wordpress_meta_update_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "credential_env_read_executed": False,
        "credential_values_loaded_for_output": False,
        "credential_values_persisted": False,
        "credential_values_logged": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "actual_publish_execution_runner_executed": False,
        "manual_publish_executed": False,
        "external_api_call_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "locked": status != STATUS_FAILED,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": recommended_next_action,
        "recommended_next_phase_options": recommended_next_phase_options,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    for key, expected in policy.get("must_remain_false_flags", {}).items():
        observed = bool(payload.get(key, False))
        if observed is not bool(expected):
            errors.append(f"{key} mismatch")

    if hard_error_count > 0:
        status = STATUS_FAILED
        payload["status"] = STATUS_FAILED
        payload["production_status"] = "NO_EXECUTION_HUMAN_INTAKE_FILL_ONLY"
        payload["locked"] = False
        payload["errors"] = list(errors)
    elif errors and status != STATUS_WAITING:
        status = STATUS_FAILED
        payload["status"] = STATUS_FAILED
        payload["production_status"] = "NO_EXECUTION_HUMAN_INTAKE_FILL_ONLY"
        payload["locked"] = False
        payload["errors"] = list(errors)

    if status == STATUS_WAITING:
        lock_status = LOCK_WAITING
    elif status == STATUS_PASSED:
        lock_status = LOCK_PASSED
    else:
        lock_status = STATUS_FAILED

    lock_payload = {
        "phase": "LS-NEXT-1-FILL",
        "document_type": "START_LS_NEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_LOCK",
        "status": lock_status,
        "locked": status != STATUS_FAILED,
        "human_input_template_created": template_created,
        "human_input_record_exists": human_record_exists,
        "human_filled": human_filled,
        "human_confirmed": human_confirmed,
        "human_input_required": payload["human_input_required"],
        "intake_registration_completed": payload["intake_registration_completed"],
        "ready_for_ls_next_2": payload["ready_for_ls_next_2"],
        "execution_allowed": False,
        "target_post_id": payload["target_post_id"],
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "next_post_created": False,
        "next_post_selected_by_ai": False,
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "publish_executed_by_this_phase": False,
        "rollback_executed": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": payload["recommended_next_action"],
        "recommended_next_phase_options": payload["recommended_next_phase_options"],
    }

    write_json(Path(args.filled_intake_output), filled_intake)
    write_json(Path(args.output), payload)
    write_json(Path(args.lock_output), lock_payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
