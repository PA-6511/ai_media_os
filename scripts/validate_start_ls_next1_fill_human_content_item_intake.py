#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_VALIDATED_NO_EXECUTION"
STATUS_WAITING_VALIDATED = "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_VALIDATED_NO_EXECUTION"
STATUS_NOT_VALIDATED = "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_NOT_VALIDATED"

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
    parser.add_argument("--result", default="exchange/runtime/start_ls_next1_fill_human_content_item_intake_result.json")
    parser.add_argument("--lock", default="exchange/locks/start_ls_next1_fill_human_content_item_intake.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls_next1_fill_human_content_item_intake_result.json")
    parser.add_argument("--human-input-template", default="exchange/intake/start_ls_next1_fill_human_input.template.json")
    parser.add_argument("--human-input-record", default="exchange/intake/start_ls_next1_fill_human_input.json")
    parser.add_argument("--filled-intake-record", default="exchange/intake/start_ls_next1_filled_next_content_item_intake.json")
    parser.add_argument("--ls-next1-result", default="exchange/runtime/start_ls_next1_next_content_item_intake_result.json")
    parser.add_argument("--ls-reuse1-result", default="exchange/runtime/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls_next1_fill_human_content_item_intake_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls_next1_fill_human_content_item_intake_validation_report.md")
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


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEXT-1-FILL Human Content Item Intake Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- human_filled: {payload.get('human_filled', '')}",
        f"- human_confirmed: {payload.get('human_confirmed', '')}",
        f"- ready_for_ls_next_2: {payload.get('ready_for_ls_next_2', '')}",
        f"- execution_allowed: {payload.get('execution_allowed', '')}",
        f"- recommended_next_action: {payload.get('recommended_next_action', '')}",
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


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def missing_required_fields(payload: dict[str, Any]) -> list[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        v = payload.get(field)
        if v is None or (isinstance(v, str) and v.strip() == ""):
            missing.append(field)
    return missing


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    result = try_load_json(Path(args.result), errors)
    lock = try_load_json(Path(args.lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    human_input_template = try_load_json(Path(args.human_input_template), errors)
    human_input_record = try_load_json(Path(args.human_input_record), errors)
    filled_intake_record = try_load_json(Path(args.filled_intake_record), errors)
    ls_next1_result = try_load_json(Path(args.ls_next1_result), errors)
    ls_reuse1_result = try_load_json(Path(args.ls_reuse1_result), errors)

    next_phase = policy.get("next_phase", {})

    req(result == run_result, "run result mismatch", errors)
    req(human_input_template.get("document_type") == "START_LS_NEXT1_FILL_HUMAN_INPUT_TEMPLATE", "human input template mismatch", errors)
    req(human_input_record.get("document_type") == "START_LS_NEXT1_FILL_HUMAN_INPUT_RECORD", "human input record mismatch", errors)
    req(str(filled_intake_record.get("phase", "")) == "LS-NEXT-1-FILL", "filled intake record mismatch", errors)

    req(ls_next1_result.get("status") == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION", "LS-NEXT-1 status mismatch", errors)
    req(ls_reuse1_result.get("status") in (
        "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION",
        "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION",
    ), "LS-REUSE-1 status mismatch", errors)

    run_status = str(result.get("status", ""))
    if run_status == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION":
        req(result.get("production_status") == "WAITING_FOR_HUMAN_INPUT_NO_EXECUTION", "production_status mismatch", errors)
        expected_action = str(next_phase.get("recommended_next_action_if_missing", "WAIT_FOR_HUMAN_INPUT"))
        expected_validation_status = STATUS_WAITING_VALIDATED
    elif run_status == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_PASSED_NO_EXECUTION":
        req(result.get("production_status") == "NO_EXECUTION_HUMAN_INTAKE_FILLED", "production_status mismatch", errors)
        expected_action = str(next_phase.get("recommended_next_action_if_valid", "BEGIN_LS_NEXT_2_DRAFT_STATUS_AND_PAYLOAD_DRY_RUN"))
        expected_validation_status = STATUS_VALIDATED
    else:
        errors.append("status mismatch")
        expected_action = ""
        expected_validation_status = STATUS_NOT_VALIDATED

    req(str(result.get("recommended_next_action", "")) == expected_action, "recommended_next_action mismatch", errors)
    req(bool(result.get("execution_allowed", False)) is False, "execution_allowed=true", errors)

    # No-execution invariants
    must_false = [
        "auto_content_selection_allowed",
        "next_post_creation_allowed",
        "wordpress_api_call_executed",
        "credential_env_read_executed",
        "publish_executed_by_this_phase",
        "next_post_created",
        "next_post_selected_by_ai",
        "post119_update_executed",
        "post183_update_executed_by_this_phase",
        "external_api_call_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_false:
        req(bool(result.get(key, False)) is False, f"{key}=true", errors)

    target_post_id = result.get("target_post_id")
    if target_post_id is not None:
        req(isinstance(target_post_id, int), "target_post_id must be integer", errors)
        if isinstance(target_post_id, int):
            req(target_post_id > 0, "target_post_id must be positive", errors)
            req(target_post_id not in (119, 183), "target_post_id forbidden", errors)

    missing = missing_required_fields(result)
    if result.get("ready_for_ls_next_2", False):
        req(not missing, "ready_for_ls_next_2=true while missing fields", errors)

    if run_status == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION":
        req(bool(result.get("human_filled", True)) is False, "human_filled mismatch", errors)
        req(bool(result.get("human_confirmed", True)) is False, "human_confirmed mismatch", errors)
        req(bool(result.get("intake_registration_completed", True)) is False, "intake_registration_completed mismatch", errors)
        req(bool(result.get("ready_for_ls_next_2", True)) is False, "ready_for_ls_next_2 mismatch", errors)
    if run_status == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_PASSED_NO_EXECUTION":
        req(bool(result.get("human_filled", False)) is True, "human_filled mismatch", errors)
        req(bool(result.get("human_confirmed", False)) is True, "human_confirmed mismatch", errors)
        req(bool(result.get("intake_registration_completed", False)) is True, "intake_registration_completed mismatch", errors)
        req(bool(result.get("ready_for_ls_next_2", False)) is True, "ready_for_ls_next_2 mismatch", errors)

    lock_status = str(lock.get("status", ""))
    if run_status == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION":
        req(lock_status == "LSNEXT1_FILL_WAITING_FOR_HUMAN_INPUT_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    elif run_status == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_PASSED_NO_EXECUTION":
        req(lock_status == "LSNEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(lock.get("locked", False)) is True, "lock mismatch", errors)

    status = expected_validation_status if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-NEXT-1-FILL",
        "document_type": "START_LS_NEXT1_FILL_HUMAN_CONTENT_ITEM_INTAKE_VALIDATION_RESULT",
        "status": status,
        "run_status": run_status,
        "execution_mode": str(result.get("execution_mode", "")),
        "production_status": str(result.get("production_status", "")),
        "ls_next1_validated": bool(result.get("ls_next1_validated", False)),
        "ls_reuse1_validated": bool(result.get("ls_reuse1_validated", False)),
        "human_input_template_created": bool(result.get("human_input_template_created", False)),
        "human_input_record_exists": bool(result.get("human_input_record_exists", False)),
        "human_filled": bool(result.get("human_filled", False)),
        "human_confirmed": bool(result.get("human_confirmed", False)),
        "human_input_required": bool(result.get("human_input_required", False)),
        "intake_registration_completed": bool(result.get("intake_registration_completed", False)),
        "ready_for_ls_next_2": bool(result.get("ready_for_ls_next_2", False)),
        "execution_allowed": bool(result.get("execution_allowed", False)),
        "content_item_id": result.get("content_item_id", ""),
        "target_post_id": result.get("target_post_id"),
        "target_post_link": result.get("target_post_link", ""),
        "payload_title": result.get("payload_title", ""),
        "payload_asin": result.get("payload_asin", ""),
        "expected_pre_publish_status": result.get("expected_pre_publish_status", ""),
        "target_publish_status": result.get("target_publish_status", ""),
        "public_url": result.get("public_url", ""),
        "public_rest_url": result.get("public_rest_url", ""),
        "missing_required_human_fields": list(result.get("missing_required_human_fields", [])),
        "auto_content_selection_allowed": bool(result.get("auto_content_selection_allowed", False)),
        "next_post_creation_allowed": bool(result.get("next_post_creation_allowed", False)),
        "wordpress_api_call_executed": bool(result.get("wordpress_api_call_executed", False)),
        "credential_env_read_executed": bool(result.get("credential_env_read_executed", False)),
        "publish_executed_by_this_phase": bool(result.get("publish_executed_by_this_phase", False)),
        "next_post_created": bool(result.get("next_post_created", False)),
        "next_post_selected_by_ai": bool(result.get("next_post_selected_by_ai", False)),
        "post119_update_executed": bool(result.get("post119_update_executed", False)),
        "post183_update_executed_by_this_phase": bool(result.get("post183_update_executed_by_this_phase", False)),
        "external_api_call_executed": bool(result.get("external_api_call_executed", False)),
        "amazon_api_call_executed": bool(result.get("amazon_api_call_executed", False)),
        "pa_api_call_executed": bool(result.get("pa_api_call_executed", False)),
        "creators_api_call_executed": bool(result.get("creators_api_call_executed", False)),
        "x_api_call_executed": bool(result.get("x_api_call_executed", False)),
        "credential_value_output": bool(result.get("credential_value_output", False)),
        "credential_secret_output": bool(result.get("credential_secret_output", False)),
        "secret_length_output": bool(result.get("secret_length_output", False)),
        "secret_hash_output": bool(result.get("secret_hash_output", False)),
        "authorization_header_generated": bool(result.get("authorization_header_generated", False)),
        "authorization_header_output": bool(result.get("authorization_header_output", False)),
        "basic_auth_string_generated": bool(result.get("basic_auth_string_generated", False)),
        "basic_auth_string_output": bool(result.get("basic_auth_string_output", False)),
        "rollback_executed": bool(result.get("rollback_executed", False)),
        "unpublish_executed": bool(result.get("unpublish_executed", False)),
        "draft_revert_executed": bool(result.get("draft_revert_executed", False)),
        "locked": bool(result.get("locked", False)),
        "rerun_allowed": bool(result.get("rerun_allowed", False)),
        "publish_rerun_allowed": bool(result.get("publish_rerun_allowed", False)),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
