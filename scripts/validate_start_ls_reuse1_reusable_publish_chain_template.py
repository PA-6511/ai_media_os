#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATED_NO_EXECUTION"
STATUS_NOT_VALIDATED = "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_NOT_VALIDATED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_reuse1_reusable_publish_chain_template_policy.json")
    parser.add_argument("--template-result", default="exchange/runtime/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--template-lock", default="exchange/locks/start_ls_reuse1_reusable_publish_chain_template.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--input-schema", default="config/start_ls_reusable_publish_chain_input_schema.json")
    parser.add_argument("--phase-map", default="config/start_ls_reusable_publish_chain_phase_map.json")
    parser.add_argument("--item-template", default="exchange/templates/start_ls_reusable_publish_chain_item.template.json")
    parser.add_argument("--safety-contract", default="exchange/templates/start_ls_reusable_publish_chain_safety_contract.json")
    parser.add_argument("--ls-mon1-result", default="exchange/runtime/start_ls_mon1_post183_published_state_monitor_result.json")
    parser.add_argument("--ls-close1-result", default="exchange/runtime/start_ls_close1_one_shot_publish_chain_closure_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls_reuse1_reusable_publish_chain_template_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls_reuse1_reusable_publish_chain_template_validation_report.md")
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
        "# LS-REUSE-1 Reusable Publish Chain Template Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- source_post_id: {payload.get('source_post_id', '')}",
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
    template_result = try_load_json(Path(args.template_result), errors)
    template_lock = try_load_json(Path(args.template_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    input_schema = try_load_json(Path(args.input_schema), errors)
    phase_map = try_load_json(Path(args.phase_map), errors)
    item_template = try_load_json(Path(args.item_template), errors)
    safety_contract = try_load_json(Path(args.safety_contract), errors)
    ls_mon1_result = try_load_json(Path(args.ls_mon1_result), errors)
    ls_close1_result = try_load_json(Path(args.ls_close1_result), errors)

    source_chain = policy.get("source_chain", {})
    next_phase = policy.get("next_phase", {})

    req(template_result.get("status") == "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION", "status mismatch", errors)
    req(template_result == run_result, "run result mismatch", errors)
    req(template_result.get("production_status") == "NO_EXECUTION_REUSE_TEMPLATE_ONLY", "production_status mismatch", errors)
    req(int(template_result.get("source_post_id", 0)) == int(source_chain.get("source_post_id", 0)), "source_post_id mismatch", errors)

    req(bool(template_result.get("reusable_template_built", False)) is True, "reusable_template_built mismatch", errors)
    req(bool(template_result.get("input_schema_created", False)) is True, "input_schema_created mismatch", errors)
    req(bool(template_result.get("phase_map_created", False)) is True, "phase_map_created mismatch", errors)
    req(bool(template_result.get("item_template_created", False)) is True, "item_template_created mismatch", errors)
    req(bool(template_result.get("safety_contract_created", False)) is True, "safety_contract_created mismatch", errors)

    req(bool(template_result.get("template_execution_allowed_by_this_phase", True)) is False, "template_execution_allowed mismatch", errors)
    req(bool(template_result.get("next_item_creation_allowed_by_this_phase", True)) is False, "next_item_creation_allowed mismatch", errors)

    must_be_false = [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_post_executed",
        "wordpress_write_executed_by_this_phase",
        "publish_executed_by_this_phase",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_generated",
        "authorization_header_output",
        "basic_auth_string_generated",
        "basic_auth_string_output",
        "post119_update_executed",
        "post183_update_executed_by_this_phase",
        "next_post_created",
        "rollback_executed",
        "unpublish_executed",
        "draft_revert_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_be_false:
        req(bool(template_result.get(key, False)) is False, f"{key} must be false", errors)

    req(template_lock.get("status") == "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(template_lock.get("locked", False)) is True, "lock mismatch", errors)

    req(ls_mon1_result.get("phase") == "LS-MON-1", "source monitor phase mismatch", errors)
    req(bool(ls_mon1_result.get("post_publish_state_monitor_ok", False)) is True, "source monitor checkpoint mismatch", errors)
    req(ls_close1_result.get("completion_status") == source_chain.get("source_completion_status"), "source completion status mismatch", errors)

    req(input_schema.get("schema_name") == "START_LS_REUSABLE_PUBLISH_CHAIN_INPUT_SCHEMA", "input schema name mismatch", errors)
    required_fields = list(input_schema.get("required_fields", []))
    req("target_post_id" in required_fields, "input schema missing target_post_id", errors)
    req("human_review_required" in required_fields, "input schema missing human_review_required", errors)
    forbidden_ids = list(input_schema.get("forbidden_values", {}).get("target_post_id", []))
    req(119 in forbidden_ids, "input schema missing forbidden post_id 119", errors)

    seq = list(phase_map.get("reusable_sequence", []))
    phases = [str(item.get("phase", "")) for item in seq]
    req("LS-NEXT-PUBLISH" in phases, "phase map missing LS-NEXT-PUBLISH", errors)
    publish_items = [item for item in seq if item.get("phase") == "LS-NEXT-PUBLISH"]
    req(bool(publish_items), "phase map publish phase missing", errors)
    if publish_items:
        req(str(publish_items[0].get("execution_allowed", "")) == "requires_explicit_human_approval", "phase map publish boundary mismatch", errors)

    always_forbidden = safety_contract.get("always_forbidden", {})
    req(bool(always_forbidden.get("post119_update", False)) is True, "safety contract missing post119 forbidden", errors)
    req(bool(always_forbidden.get("publish_without_explicit_human_approval", False)) is True, "safety contract missing human approval boundary", errors)

    req(str(template_result.get("recommended_next_action", "")) == str(next_phase.get("recommended_next_action", "")), "recommended_next_action mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-REUSE-1",
        "document_type": "START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_VALIDATION_RESULT",
        "status": status,
        "run_status": str(template_result.get("status", "")),
        "execution_mode": str(template_result.get("execution_mode", "")),
        "production_status": str(template_result.get("production_status", "")),
        "source_post_id": int(template_result.get("source_post_id", 0)),
        "source_post_link": str(template_result.get("source_post_link", "")),
        "source_payload_title": str(template_result.get("source_payload_title", "")),
        "source_payload_asin": str(template_result.get("source_payload_asin", "")),
        "ls_mon1_validated": bool(template_result.get("ls_mon1_validated", False)),
        "ls_close1_validated": bool(template_result.get("ls_close1_validated", False)),
        "ls6au_validated": bool(template_result.get("ls6au_validated", False)),
        "ls6at_validated": bool(template_result.get("ls6at_validated", False)),
        "reusable_template_built": bool(template_result.get("reusable_template_built", False)),
        "input_schema_created": bool(template_result.get("input_schema_created", False)),
        "phase_map_created": bool(template_result.get("phase_map_created", False)),
        "item_template_created": bool(template_result.get("item_template_created", False)),
        "safety_contract_created": bool(template_result.get("safety_contract_created", False)),
        "parameterized_fields": list(template_result.get("parameterized_fields", [])),
        "template_execution_allowed_by_this_phase": bool(template_result.get("template_execution_allowed_by_this_phase", False)),
        "next_item_creation_allowed_by_this_phase": bool(template_result.get("next_item_creation_allowed_by_this_phase", False)),
        "wordpress_api_call_executed": bool(template_result.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(template_result.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(template_result.get("wordpress_post_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(template_result.get("wordpress_write_executed_by_this_phase", False)),
        "publish_executed_by_this_phase": bool(template_result.get("publish_executed_by_this_phase", False)),
        "credential_env_read_executed": bool(template_result.get("credential_env_read_executed", False)),
        "credential_value_output": bool(template_result.get("credential_value_output", False)),
        "credential_secret_output": bool(template_result.get("credential_secret_output", False)),
        "secret_length_output": bool(template_result.get("secret_length_output", False)),
        "secret_hash_output": bool(template_result.get("secret_hash_output", False)),
        "authorization_header_generated": bool(template_result.get("authorization_header_generated", False)),
        "authorization_header_output": bool(template_result.get("authorization_header_output", False)),
        "basic_auth_string_generated": bool(template_result.get("basic_auth_string_generated", False)),
        "basic_auth_string_output": bool(template_result.get("basic_auth_string_output", False)),
        "post119_update_executed": bool(template_result.get("post119_update_executed", False)),
        "post183_update_executed_by_this_phase": bool(template_result.get("post183_update_executed_by_this_phase", False)),
        "next_post_created": bool(template_result.get("next_post_created", False)),
        "rollback_executed": bool(template_result.get("rollback_executed", False)),
        "unpublish_executed": bool(template_result.get("unpublish_executed", False)),
        "draft_revert_executed": bool(template_result.get("draft_revert_executed", False)),
        "locked": bool(template_result.get("locked", False)),
        "rerun_allowed": bool(template_result.get("rerun_allowed", False)),
        "publish_rerun_allowed": bool(template_result.get("publish_rerun_allowed", False)),
        "recommended_next_action": str(template_result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(template_result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
