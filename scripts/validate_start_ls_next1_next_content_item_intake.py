#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_VALIDATED_NO_EXECUTION"
STATUS_NOT_VALIDATED = "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_NOT_VALIDATED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_next1_next_content_item_intake_policy.json")
    parser.add_argument("--intake-result", default="exchange/runtime/start_ls_next1_next_content_item_intake_result.json")
    parser.add_argument("--intake-lock", default="exchange/locks/start_ls_next1_next_content_item_intake.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls_next1_next_content_item_intake_result.json")
    parser.add_argument("--intake-template", default="exchange/intake/start_ls_next1_next_content_item_intake.template.json")
    parser.add_argument("--intake-record", default="exchange/intake/start_ls_next1_next_content_item_intake.json")
    parser.add_argument("--ls-reuse1-result", default="exchange/runtime/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--input-schema", default="config/start_ls_reusable_publish_chain_input_schema.json")
    parser.add_argument("--phase-map", default="config/start_ls_reusable_publish_chain_phase_map.json")
    parser.add_argument("--item-template", default="exchange/templates/start_ls_reusable_publish_chain_item.template.json")
    parser.add_argument("--safety-contract", default="exchange/templates/start_ls_reusable_publish_chain_safety_contract.json")
    parser.add_argument("--output", default="exchange/logs/start_ls_next1_next_content_item_intake_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls_next1_next_content_item_intake_validation_report.md")
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
        "# LS-NEXT-1 Next Content Item Intake Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- human_input_required: {payload.get('human_input_required', '')}",
        f"- execution_allowed: {payload.get('execution_allowed', '')}",
        f"- recommended_next_action: {payload.get('recommended_next_action', '')}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {item}" for item in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    intake_result = try_load_json(Path(args.intake_result), errors)
    intake_lock = try_load_json(Path(args.intake_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    intake_template = try_load_json(Path(args.intake_template), errors)
    intake_record = try_load_json(Path(args.intake_record), errors)
    ls_reuse1_result = try_load_json(Path(args.ls_reuse1_result), errors)
    input_schema = try_load_json(Path(args.input_schema), errors)
    phase_map = try_load_json(Path(args.phase_map), errors)
    item_template = try_load_json(Path(args.item_template), errors)
    safety_contract = try_load_json(Path(args.safety_contract), errors)

    intake_policy = policy.get("intake_policy", {})
    next_phase = policy.get("next_phase", {})

    req(intake_result.get("status") == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION", "status mismatch", errors)
    req(intake_result == run_result, "run result mismatch", errors)
    req(intake_result.get("production_status") == "NO_EXECUTION_NEXT_ITEM_INTAKE_ONLY", "production_status mismatch", errors)

    req(bool(intake_result.get("ls_reuse1_validated", False)) is True, "ls_reuse1_validated mismatch", errors)
    req(bool(intake_result.get("reusable_template_available", False)) is True, "reusable_template_available mismatch", errors)
    req(bool(intake_result.get("input_schema_available", False)) is True, "input_schema_available mismatch", errors)
    req(bool(intake_result.get("phase_map_available", False)) is True, "phase_map_available mismatch", errors)
    req(bool(intake_result.get("item_template_available", False)) is True, "item_template_available mismatch", errors)
    req(bool(intake_result.get("safety_contract_available", False)) is True, "safety_contract_available mismatch", errors)
    req(bool(intake_result.get("intake_template_created", False)) is True, "intake_template_created mismatch", errors)
    req(bool(intake_result.get("intake_record_created", False)) is True, "intake_record_created mismatch", errors)
    req(bool(intake_result.get("intake_registration_completed", True)) is False, "intake_registration_completed mismatch", errors)

    req(bool(intake_result.get("human_input_required", False)) is True, "human_input_required mismatch", errors)
    req(bool(intake_result.get("human_review_required", False)) is True, "human_review_required mismatch", errors)
    req(bool(intake_result.get("execution_allowed_initially", True)) is False, "execution_allowed_initially mismatch", errors)
    req(bool(intake_result.get("execution_allowed", True)) is False, "execution_allowed mismatch", errors)
    req(bool(intake_result.get("ready_for_ls_next_2", True)) is False, "ready_for_ls_next_2 mismatch", errors)

    target_post_id = intake_result.get("target_post_id")
    if target_post_id is not None:
        req(target_post_id not in (119, 183), "target_post_id forbidden", errors)

    req(bool(intake_result.get("auto_content_selection_allowed", True)) is False, "auto_content_selection_allowed mismatch", errors)
    req(bool(intake_result.get("next_post_creation_allowed", True)) is False, "next_post_creation_allowed mismatch", errors)

    must_false = [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_write_executed_by_this_phase",
        "publish_executed_by_this_phase",
        "next_post_created",
        "next_post_selected_by_ai",
        "post119_update_executed",
        "post183_update_executed_by_this_phase",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_generated",
        "authorization_header_output",
        "basic_auth_string_generated",
        "basic_auth_string_output",
        "rollback_executed",
        "unpublish_executed",
        "draft_revert_executed",
        "external_api_call_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_false:
        req(bool(intake_result.get(key, False)) is False, f"{key} must be false", errors)

    req(intake_template.get("document_type") == "START_LS_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE", "intake template doc type mismatch", errors)
    req(intake_record.get("document_type") == "START_LS_NEXT_CONTENT_ITEM_INTAKE_RECORD", "intake record doc type mismatch", errors)

    req(ls_reuse1_result.get("status") == "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION", "LS-REUSE-1 status mismatch", errors)
    req(input_schema.get("schema_name") == "START_LS_REUSABLE_PUBLISH_CHAIN_INPUT_SCHEMA", "input schema mismatch", errors)
    phases = [str(item.get("phase", "")) for item in list(phase_map.get("reusable_sequence", []))]
    req("LS-NEXT-PUBLISH" in phases, "phase map missing LS-NEXT-PUBLISH", errors)
    req(item_template.get("template_name") == "START_LS_REUSABLE_PUBLISH_CHAIN_ITEM_TEMPLATE", "item template mismatch", errors)
    req("always_forbidden" in safety_contract, "safety contract mismatch", errors)

    req(str(intake_result.get("recommended_next_action", "")) == str(next_phase.get("recommended_next_action", "")), "recommended_next_action mismatch", errors)

    req(intake_lock.get("status") == "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(intake_lock.get("locked", False)) is True, "lock mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-NEXT-1",
        "document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_VALIDATION_RESULT",
        "status": status,
        "run_status": str(intake_result.get("status", "")),
        "execution_mode": str(intake_result.get("execution_mode", "")),
        "production_status": str(intake_result.get("production_status", "")),
        "ls_reuse1_validated": bool(intake_result.get("ls_reuse1_validated", False)),
        "reusable_template_available": bool(intake_result.get("reusable_template_available", False)),
        "input_schema_available": bool(intake_result.get("input_schema_available", False)),
        "phase_map_available": bool(intake_result.get("phase_map_available", False)),
        "item_template_available": bool(intake_result.get("item_template_available", False)),
        "safety_contract_available": bool(intake_result.get("safety_contract_available", False)),
        "intake_template_created": bool(intake_result.get("intake_template_created", False)),
        "intake_record_created": bool(intake_result.get("intake_record_created", False)),
        "intake_registration_completed": bool(intake_result.get("intake_registration_completed", False)),
        "human_input_required": bool(intake_result.get("human_input_required", False)),
        "human_review_required": bool(intake_result.get("human_review_required", False)),
        "execution_allowed_initially": bool(intake_result.get("execution_allowed_initially", False)),
        "execution_allowed": bool(intake_result.get("execution_allowed", False)),
        "ready_for_ls_next_2": bool(intake_result.get("ready_for_ls_next_2", False)),
        "content_item_id": intake_result.get("content_item_id", ""),
        "target_post_id": intake_result.get("target_post_id"),
        "target_post_link": intake_result.get("target_post_link", ""),
        "payload_title": intake_result.get("payload_title", ""),
        "payload_asin": intake_result.get("payload_asin", ""),
        "expected_pre_publish_status": intake_result.get("expected_pre_publish_status", ""),
        "target_publish_status": intake_result.get("target_publish_status", ""),
        "public_url": intake_result.get("public_url", ""),
        "public_rest_url": intake_result.get("public_rest_url", ""),
        "missing_required_human_fields": list(intake_result.get("missing_required_human_fields", [])),
        "auto_content_selection_allowed": bool(intake_result.get("auto_content_selection_allowed", False)),
        "next_post_creation_allowed": bool(intake_result.get("next_post_creation_allowed", False)),
        "template_execution_allowed_by_this_phase": bool(intake_result.get("template_execution_allowed_by_this_phase", False)),
        "next_item_creation_allowed_by_this_phase": bool(intake_result.get("next_item_creation_allowed_by_this_phase", False)),
        "wordpress_api_call_executed": bool(intake_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(intake_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(intake_result.get("wordpress_post_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(intake_result.get("wordpress_write_executed_by_this_phase", False)),
        "publish_executed_by_this_phase": bool(intake_result.get("publish_executed_by_this_phase", False)),
        "next_post_created": bool(intake_result.get("next_post_created", False)),
        "next_post_selected_by_ai": bool(intake_result.get("next_post_selected_by_ai", False)),
        "post119_update_executed": bool(intake_result.get("post119_update_executed", False)),
        "post183_update_executed_by_this_phase": bool(intake_result.get("post183_update_executed_by_this_phase", False)),
        "credential_env_read_executed": bool(intake_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(intake_result.get("credential_value_output", False)),
        "credential_secret_output": bool(intake_result.get("credential_secret_output", False)),
        "secret_length_output": bool(intake_result.get("secret_length_output", False)),
        "secret_hash_output": bool(intake_result.get("secret_hash_output", False)),
        "authorization_header_generated": bool(intake_result.get("authorization_header_generated", False)),
        "authorization_header_output": bool(intake_result.get("authorization_header_output", False)),
        "basic_auth_string_generated": bool(intake_result.get("basic_auth_string_generated", False)),
        "basic_auth_string_output": bool(intake_result.get("basic_auth_string_output", False)),
        "rollback_executed": bool(intake_result.get("rollback_executed", False)),
        "unpublish_executed": bool(intake_result.get("unpublish_executed", False)),
        "draft_revert_executed": bool(intake_result.get("draft_revert_executed", False)),
        "external_api_call_executed": bool(intake_result.get("external_api_call_executed", False)),
        "amazon_api_call_executed": bool(intake_result.get("amazon_api_call_executed", False)),
        "pa_api_call_executed": bool(intake_result.get("pa_api_call_executed", False)),
        "creators_api_call_executed": bool(intake_result.get("creators_api_call_executed", False)),
        "x_api_call_executed": bool(intake_result.get("x_api_call_executed", False)),
        "locked": bool(intake_result.get("locked", False)),
        "rerun_allowed": bool(intake_result.get("rerun_allowed", False)),
        "publish_rerun_allowed": bool(intake_result.get("publish_rerun_allowed", False)),
        "recommended_next_action": str(intake_result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(intake_result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
