#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_FAILED_NO_EXECUTION"
STATUS_LOCKED = "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE_LOCKED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_next1_next_content_item_intake_policy.json")
    parser.add_argument("--ls-reuse1-result", default="exchange/runtime/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--ls-reuse1-lock", default="exchange/locks/start_ls_reuse1_reusable_publish_chain_template.lock.json")
    parser.add_argument("--ls-reuse1-run-result", default="exchange/logs/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--ls-reuse1-validation-result", default="exchange/logs/start_ls_reuse1_reusable_publish_chain_template_validation_result.json")
    parser.add_argument("--input-schema", default="config/start_ls_reusable_publish_chain_input_schema.json")
    parser.add_argument("--phase-map", default="config/start_ls_reusable_publish_chain_phase_map.json")
    parser.add_argument("--item-template", default="exchange/templates/start_ls_reusable_publish_chain_item.template.json")
    parser.add_argument("--safety-contract", default="exchange/templates/start_ls_reusable_publish_chain_safety_contract.json")
    parser.add_argument("--intake-template-output", default="exchange/intake/start_ls_next1_next_content_item_intake.template.json")
    parser.add_argument("--intake-record-output", default="exchange/intake/start_ls_next1_next_content_item_intake.json")
    parser.add_argument("--output", default="exchange/runtime/start_ls_next1_next_content_item_intake_result.json")
    parser.add_argument("--lock-output", default="exchange/locks/start_ls_next1_next_content_item_intake.lock.json")
    parser.add_argument("--report", default="reports/start_ls_next1_next_content_item_intake_report.md")

    parser.add_argument("--create-intake-template", action="store_true")
    parser.add_argument("--require-human-input", action="store_true")
    parser.add_argument("--require-no-wordpress-api", action="store_true")
    parser.add_argument("--require-no-credential-read", action="store_true")
    parser.add_argument("--require-no-publish", action="store_true")
    parser.add_argument("--require-no-next-post-creation", action="store_true")
    parser.add_argument("--forbid-post119-update", action="store_true")
    parser.add_argument("--forbid-post183-update", action="store_true")
    parser.add_argument("--forbid-auto-content-selection", action="store_true")
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
        "# LS-NEXT-1 Next Content Item Intake Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- execution_mode: {payload['execution_mode']}",
        f"- production_status: {payload['production_status']}",
        f"- ls_reuse1_validated: {payload['ls_reuse1_validated']}",
        f"- intake_template_created: {payload['intake_template_created']}",
        f"- intake_record_created: {payload['intake_record_created']}",
        f"- human_input_required: {payload['human_input_required']}",
        f"- execution_allowed: {payload['execution_allowed']}",
        f"- recommended_next_action: {payload['recommended_next_action']}",
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


def build_intake_template() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_TEMPLATE",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "public_url": "",
        "public_rest_url": "",
        "evidence_paths": {},
        "human_input_required": True,
        "human_review_required": True,
        "execution_allowed_initially": False,
        "execution_allowed": False,
        "target_post_id_119_forbidden": True,
        "target_post_id_183_forbidden_for_next_item": True,
        "auto_content_selection_allowed": False,
        "next_post_creation_allowed": False,
        "wordpress_write_allowed": False,
        "credential_env_read_allowed": False,
        "publish_allowed": False,
        "actual_publish_requires_separated_phase": True,
        "actual_publish_requires_explicit_human_approval": True,
        "post_publish_verification_required": True,
        "chain_closure_required": True,
        "get_only_monitor_required": True,
    }


def build_intake_record() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEXT-1",
        "status": "LSNEXT1_NEXT_CONTENT_ITEM_INTAKE_WAITING_FOR_HUMAN_INPUT",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "public_url": "",
        "public_rest_url": "",
        "evidence_paths": {},
        "human_input_required": True,
        "human_review_required": True,
        "execution_allowed_initially": False,
        "execution_allowed": False,
        "intake_registration_completed": False,
        "intake_template_created": True,
        "ready_for_ls_next_2": False,
        "missing_required_human_fields": [
            "content_item_id",
            "target_post_id",
            "target_post_link",
            "payload_title",
            "payload_asin",
            "public_url",
            "public_rest_url",
        ],
        "errors": [],
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls_reuse1_result = try_load_json(Path(args.ls_reuse1_result), errors)
    ls_reuse1_lock = try_load_json(Path(args.ls_reuse1_lock), errors)
    ls_reuse1_run = try_load_json(Path(args.ls_reuse1_run_result), errors)
    ls_reuse1_validation = try_load_json(Path(args.ls_reuse1_validation_result), errors)
    input_schema = try_load_json(Path(args.input_schema), errors)
    phase_map = try_load_json(Path(args.phase_map), errors)
    item_template = try_load_json(Path(args.item_template), errors)
    safety_contract = try_load_json(Path(args.safety_contract), errors)

    req_prev = policy.get("required_previous_phase", {}).get("ls_reuse1", {})
    intake_policy = policy.get("intake_policy", {})

    req(policy.get("phase") == "LS-NEXT-1", "policy.phase mismatch", errors)
    req(ls_reuse1_result.get("status") == req_prev.get("required_run_status"), "LS-REUSE-1 status mismatch", errors)
    req(ls_reuse1_validation.get("status") == req_prev.get("required_validation_status"), "LS-REUSE-1 validation mismatch", errors)
    req(ls_reuse1_result == ls_reuse1_run, "LS-REUSE-1 run result mismatch", errors)
    req(ls_reuse1_result.get("production_status") == req_prev.get("required_production_status"), "LS-REUSE-1 production mismatch", errors)
    req(int(ls_reuse1_result.get("source_post_id", 0)) == int(req_prev.get("required_source_post_id", 0)), "LS-REUSE-1 source_post_id mismatch", errors)
    req(bool(ls_reuse1_result.get("reusable_template_built", False)) is bool(req_prev.get("required_reusable_template_built", True)), "LS-REUSE-1 reusable_template_built mismatch", errors)
    req(bool(ls_reuse1_result.get("input_schema_created", False)) is bool(req_prev.get("required_input_schema_created", True)), "LS-REUSE-1 input_schema_created mismatch", errors)
    req(bool(ls_reuse1_result.get("phase_map_created", False)) is bool(req_prev.get("required_phase_map_created", True)), "LS-REUSE-1 phase_map_created mismatch", errors)
    req(bool(ls_reuse1_result.get("item_template_created", False)) is bool(req_prev.get("required_item_template_created", True)), "LS-REUSE-1 item_template_created mismatch", errors)
    req(bool(ls_reuse1_result.get("safety_contract_created", False)) is bool(req_prev.get("required_safety_contract_created", True)), "LS-REUSE-1 safety_contract_created mismatch", errors)
    req(bool(ls_reuse1_lock.get("locked", False)) is True, "LS-REUSE-1 lock mismatch", errors)

    req(bool(input_schema), "input schema unavailable", errors)
    req(bool(phase_map), "phase map unavailable", errors)
    req(bool(item_template), "item template unavailable", errors)
    req(bool(safety_contract), "safety contract unavailable", errors)

    req(args.create_intake_template, "missing --create-intake-template", errors)
    req(args.require_human_input, "missing --require-human-input", errors)
    req(args.require_no_wordpress_api, "missing --require-no-wordpress-api", errors)
    req(args.require_no_credential_read, "missing --require-no-credential-read", errors)
    req(args.require_no_publish, "missing --require-no-publish", errors)
    req(args.require_no_next_post_creation, "missing --require-no-next-post-creation", errors)
    req(args.forbid_post119_update, "missing --forbid-post119-update", errors)
    req(args.forbid_post183_update, "missing --forbid-post183-update", errors)
    req(args.forbid_auto_content_selection, "missing --forbid-auto-content-selection", errors)

    intake_template_created = False
    intake_record_created = False
    intake_registration_completed = False

    if not errors:
        write_json(Path(args.intake_template_output), build_intake_template())
        write_json(Path(args.intake_record_output), build_intake_record())
        intake_template_created = Path(args.intake_template_output).exists()
        intake_record_created = Path(args.intake_record_output).exists()

    status = STATUS_PASSED if not errors else STATUS_FAILED

    payload = {
        "phase": "LS-NEXT-1",
        "document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_RESULT",
        "status": status,
        "execution_mode": "INTAKE_TEMPLATE_AND_GATE_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_NEXT_ITEM_INTAKE_ONLY",
        "ls_reuse1_validated": ls_reuse1_validation.get("status") == req_prev.get("required_validation_status"),
        "reusable_template_available": bool(ls_reuse1_result),
        "input_schema_available": bool(input_schema),
        "phase_map_available": bool(phase_map),
        "item_template_available": bool(item_template),
        "safety_contract_available": bool(safety_contract),
        "intake_template_created": intake_template_created,
        "intake_record_created": intake_record_created,
        "intake_registration_completed": intake_registration_completed,
        "human_input_required": bool(intake_policy.get("human_input_required", True)),
        "human_review_required": bool(intake_policy.get("human_review_required", True)),
        "execution_allowed_initially": bool(intake_policy.get("execution_allowed_initially", False)),
        "execution_allowed": False,
        "ready_for_ls_next_2": False,
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "public_url": "",
        "public_rest_url": "",
        "missing_required_human_fields": [
            "content_item_id",
            "target_post_id",
            "target_post_link",
            "payload_title",
            "payload_asin",
            "public_url",
            "public_rest_url",
        ],
        "auto_content_selection_allowed": False,
        "next_post_creation_allowed": False,
        "template_execution_allowed_by_this_phase": False,
        "next_item_creation_allowed_by_this_phase": False,
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
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
        "external_api_call_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "locked": status == STATUS_PASSED,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": str(policy.get("next_phase", {}).get("recommended_next_action", "FILL_NEXT_CONTENT_ITEM_INTAKE_OR_CONTINUE_MONITORING")),
        "recommended_next_phase_options": list(policy.get("next_phase", {}).get("recommended_next_phase_options", ["LS-NEXT-1-FILL", "LS-MON-2", "LS-NEXT-2_AFTER_HUMAN_INPUT"])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    for key, expected in policy.get("must_remain_false_flags", {}).items():
        observed = bool(payload.get(key, False))
        req(observed is bool(expected), f"{key} mismatch", errors)

    status = STATUS_PASSED if not errors else STATUS_FAILED
    payload["status"] = status
    payload["locked"] = status == STATUS_PASSED
    payload["errors"] = list(errors)

    lock_payload = {
        "phase": "LS-NEXT-1",
        "document_type": "START_LS_NEXT_CONTENT_ITEM_INTAKE_LOCK",
        "status": STATUS_LOCKED if status == STATUS_PASSED else status,
        "locked": status == STATUS_PASSED,
        "intake_template_created": payload["intake_template_created"],
        "intake_record_created": payload["intake_record_created"],
        "intake_registration_completed": payload["intake_registration_completed"],
        "human_input_required": payload["human_input_required"],
        "execution_allowed": payload["execution_allowed"],
        "ready_for_ls_next_2": payload["ready_for_ls_next_2"],
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

    write_json(Path(args.output), payload)
    write_json(Path(args.lock_output), lock_payload)
    write_report(Path(args.report), payload)

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
