#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASSED = "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_FAILED_NO_EXECUTION"
STATUS_LOCKED = "LSREUSE1_START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_LOCKED_NO_EXECUTION"

LS6AU_VALIDATION_PATH = "exchange/logs/start_ls6au_post_publish_verification_published_evidence_validation_result.json"
LS6AT_VALIDATION_PATH = "exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_result.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_reuse1_reusable_publish_chain_template_policy.json")
    parser.add_argument("--ls-mon1-result", default="exchange/runtime/start_ls_mon1_post183_published_state_monitor_result.json")
    parser.add_argument("--ls-mon1-lock", default="exchange/locks/start_ls_mon1_post183_published_state_monitor.lock.json")
    parser.add_argument("--ls-mon1-validation-result", default="exchange/logs/start_ls_mon1_post183_published_state_monitor_validation_result.json")
    parser.add_argument("--ls-close1-result", default="exchange/runtime/start_ls_close1_one_shot_publish_chain_closure_result.json")
    parser.add_argument("--ls-close1-lock", default="exchange/locks/start_ls_close1_one_shot_publish_chain_closure.lock.json")
    parser.add_argument("--ls-close1-validation-result", default="exchange/logs/start_ls_close1_one_shot_publish_chain_closure_validation_result.json")
    parser.add_argument("--ls6au-result", default="exchange/runtime/start_ls6au_post_publish_verification_published_evidence_result.json")
    parser.add_argument("--ls6at-result", default="exchange/runtime/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json")
    parser.add_argument("--output", default="exchange/runtime/start_ls_reuse1_reusable_publish_chain_template_result.json")
    parser.add_argument("--lock-output", default="exchange/locks/start_ls_reuse1_reusable_publish_chain_template.lock.json")
    parser.add_argument("--report", default="reports/start_ls_reuse1_reusable_publish_chain_template_report.md")
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
        "# LS-REUSE-1 Reusable Publish Chain Template Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- execution_mode: {payload['execution_mode']}",
        f"- production_status: {payload['production_status']}",
        f"- source_post_id: {payload['source_post_id']}",
        f"- reusable_template_built: {payload['reusable_template_built']}",
        f"- input_schema_created: {payload['input_schema_created']}",
        f"- phase_map_created: {payload['phase_map_created']}",
        f"- item_template_created: {payload['item_template_created']}",
        f"- safety_contract_created: {payload['safety_contract_created']}",
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


def must_have_path(outputs: dict[str, Any], key: str, errors: list[str]) -> Path | None:
    raw = outputs.get(key)
    if not isinstance(raw, str) or not raw.strip():
        errors.append(f"missing output path: {key}")
        return None
    return Path(raw)


def build_input_schema() -> dict[str, Any]:
    return {
        "schema_name": "START_LS_REUSABLE_PUBLISH_CHAIN_INPUT_SCHEMA",
        "schema_version": "1.0.0",
        "required_fields": [
            "content_item_id",
            "target_post_id",
            "target_post_link",
            "payload_title",
            "payload_asin",
            "expected_pre_publish_status",
            "target_publish_status",
            "public_url",
            "public_rest_url",
            "human_review_required",
            "execution_allowed_initially",
        ],
        "field_definitions": {
            "content_item_id": {
                "type": "string",
                "description": "Stable identifier for the next content item.",
            },
            "target_post_id": {
                "type": "integer",
                "description": "Existing WordPress draft post ID. Must not be 119. Must be explicitly confirmed before execution.",
            },
            "target_post_link": {
                "type": "string",
                "description": "Public or preview link for the target post.",
            },
            "payload_title": {
                "type": "string",
                "description": "Human-readable content title.",
            },
            "payload_asin": {
                "type": "string",
                "description": "ASIN or affiliate content identifier.",
            },
            "expected_pre_publish_status": {
                "type": "string",
                "allowed_values": ["draft"],
            },
            "target_publish_status": {
                "type": "string",
                "allowed_values": ["publish"],
            },
            "public_url": {"type": "string"},
            "public_rest_url": {"type": "string"},
            "human_review_required": {
                "type": "boolean",
                "required_value": True,
            },
            "execution_allowed_initially": {
                "type": "boolean",
                "required_value": False,
            },
        },
        "forbidden_values": {
            "target_post_id": [119],
        },
    }


def build_phase_map() -> dict[str, Any]:
    return {
        "phase_map_name": "START_LS_REUSABLE_PUBLISH_CHAIN_PHASE_MAP",
        "schema_version": "1.0.0",
        "source_chain": "post_id_183_start_ls_one_shot_publish_chain",
        "reusable_sequence": [
            {
                "phase_group": "intake",
                "phase": "LS-NEXT-1",
                "purpose": "Register next content item using the reusable input schema.",
                "execution_allowed": False,
            },
            {
                "phase_group": "draft_review",
                "phase": "LS-NEXT-2",
                "purpose": "Build or verify next draft payload in dry-run mode.",
                "execution_allowed": False,
            },
            {
                "phase_group": "human_review",
                "phase": "LS-NEXT-3",
                "purpose": "Human review for next content item.",
                "execution_allowed": False,
            },
            {
                "phase_group": "preflight",
                "phase": "LS-NEXT-4",
                "purpose": "Final preflight for target draft post.",
                "execution_allowed": False,
            },
            {
                "phase_group": "separated_publish_execution",
                "phase": "LS-NEXT-PUBLISH",
                "purpose": "Separated actual publish execution for confirmed target post ID only.",
                "execution_allowed": "requires_explicit_human_approval",
            },
            {
                "phase_group": "post_publish_verification",
                "phase": "LS-NEXT-VERIFY",
                "purpose": "Post-publish verification and published evidence.",
                "execution_allowed": False,
            },
            {
                "phase_group": "closure",
                "phase": "LS-NEXT-CLOSE",
                "purpose": "Close next item publish chain.",
                "execution_allowed": False,
            },
            {
                "phase_group": "monitor",
                "phase": "LS-NEXT-MON",
                "purpose": "GET-only published state monitoring.",
                "execution_allowed": False,
            },
        ],
        "global_safety_rules": {
            "post119_update_forbidden": True,
            "credential_secret_output_forbidden": True,
            "authorization_header_output_forbidden": True,
            "rerun_forbidden_after_publish": True,
            "human_approval_required_for_actual_publish": True,
            "publish_execution_must_be_separated": True,
        },
    }


def build_item_template() -> dict[str, Any]:
    return {
        "template_name": "START_LS_REUSABLE_PUBLISH_CHAIN_ITEM_TEMPLATE",
        "schema_version": "1.0.0",
        "content_item_id": "",
        "target_post_id": None,
        "target_post_link": "",
        "payload_title": "",
        "payload_asin": "",
        "expected_pre_publish_status": "draft",
        "target_publish_status": "publish",
        "public_url": "",
        "public_rest_url": "",
        "human_review_required": True,
        "execution_allowed_initially": False,
        "post119_update_forbidden": True,
        "credential_env_read_allowed_initially": False,
        "wordpress_write_allowed_initially": False,
        "actual_publish_requires_separated_phase": True,
        "actual_publish_requires_explicit_human_approval": True,
        "post_publish_verification_required": True,
        "chain_closure_required": True,
        "get_only_monitor_required": True,
    }


def build_safety_contract() -> dict[str, Any]:
    return {
        "contract_name": "START_LS_REUSABLE_PUBLISH_CHAIN_SAFETY_CONTRACT",
        "schema_version": "1.0.0",
        "always_forbidden": {
            "post119_update": True,
            "credential_value_output": True,
            "credential_value_persisted": True,
            "secret_length_output": True,
            "secret_hash_output": True,
            "authorization_header_output": True,
            "basic_auth_string_output": True,
            "unscoped_wordpress_write": True,
            "multi_post_update": True,
            "publish_without_separated_phase": True,
            "publish_without_explicit_human_approval": True,
            "rerun_after_publish_without_new_phase": True,
        },
        "required_boundaries": {
            "pre_publish_status_check": True,
            "post_publish_status_check": True,
            "post_publish_verification": True,
            "closure_registration": True,
            "get_only_monitor": True,
            "rollback_readiness_record": True,
        },
        "default_state": {
            "wordpress_api_call_allowed": False,
            "credential_env_read_allowed": False,
            "publish_allowed": False,
            "next_item_creation_allowed": False,
        },
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    ls_mon1_result = try_load_json(Path(args.ls_mon1_result), errors)
    ls_mon1_lock = try_load_json(Path(args.ls_mon1_lock), errors)
    ls_mon1_validation = try_load_json(Path(args.ls_mon1_validation_result), errors)
    ls_close1_result = try_load_json(Path(args.ls_close1_result), errors)
    ls_close1_lock = try_load_json(Path(args.ls_close1_lock), errors)
    ls_close1_validation = try_load_json(Path(args.ls_close1_validation_result), errors)
    ls6au_result = try_load_json(Path(args.ls6au_result), errors)
    ls6at_result = try_load_json(Path(args.ls6at_result), errors)
    ls6au_validation = try_load_json(Path(LS6AU_VALIDATION_PATH), errors)
    ls6at_validation = try_load_json(Path(LS6AT_VALIDATION_PATH), errors)

    source_chain = policy.get("source_chain", {})
    req_prev = policy.get("required_previous_phase", {})
    req_mon1 = req_prev.get("ls_mon1", {})
    req_close1 = req_prev.get("ls_close1", {})
    req_ls6au = req_prev.get("ls6au", {})
    req_ls6at = req_prev.get("ls6at", {})
    outputs = policy.get("outputs", {})

    input_schema_path = must_have_path(outputs, "input_schema", errors)
    phase_map_path = must_have_path(outputs, "phase_map", errors)
    item_template_path = must_have_path(outputs, "item_template", errors)
    safety_contract_path = must_have_path(outputs, "safety_contract", errors)

    req(policy.get("phase") == "LS-REUSE-1", "policy.phase mismatch", errors)
    req(ls_mon1_validation.get("status") == req_mon1.get("required_validation_status"), "LS-MON-1 validation status mismatch", errors)
    req(ls_mon1_result.get("production_status") == req_mon1.get("required_production_status"), "LS-MON-1 production status mismatch", errors)
    req(int(ls_mon1_result.get("post_id", 0)) == int(req_mon1.get("required_post_id", 0)), "LS-MON-1 post_id mismatch", errors)
    req(bool(ls_mon1_result.get("public_url_reachable", False)) is bool(req_mon1.get("required_public_url_reachable", True)), "LS-MON-1 public_url_reachable mismatch", errors)
    req(str(ls_mon1_result.get("public_rest_returned_post_status", "")) == str(req_mon1.get("required_public_rest_status", "")), "LS-MON-1 public_rest status mismatch", errors)
    req(bool(ls_mon1_lock.get("locked", False)) is True, "LS-MON-1 lock mismatch", errors)

    req(ls_close1_validation.get("status") == req_close1.get("required_validation_status"), "LS-CLOSE-1 validation status mismatch", errors)
    req(str(ls_close1_result.get("completion_status", "")) == str(req_close1.get("required_completion_status", "")), "LS-CLOSE-1 completion mismatch", errors)
    req(bool(ls_close1_lock.get("locked", False)) is True, "LS-CLOSE-1 lock mismatch", errors)

    req(ls6au_validation.get("status") == req_ls6au.get("required_validation_status"), "LS-6AU status mismatch", errors)
    req(str(ls6au_result.get("production_status", "")) == str(req_ls6au.get("required_production_status", "")), "LS-6AU production mismatch", errors)

    req(ls6at_validation.get("status") == req_ls6at.get("required_validation_status"), "LS-6AT status mismatch", errors)
    req(str(ls6at_result.get("production_status", "")) == str(req_ls6at.get("required_production_status", "")), "LS-6AT production mismatch", errors)

    req(int(source_chain.get("source_post_id", 0)) == int(ls_mon1_result.get("post_id", 0)), "source post_id mismatch", errors)

    input_schema_created = False
    phase_map_created = False
    item_template_created = False
    safety_contract_created = False

    if input_schema_path is not None:
        write_json(input_schema_path, build_input_schema())
        input_schema_created = input_schema_path.exists()
    if phase_map_path is not None:
        write_json(phase_map_path, build_phase_map())
        phase_map_created = phase_map_path.exists()
    if item_template_path is not None:
        write_json(item_template_path, build_item_template())
        item_template_created = item_template_path.exists()
    if safety_contract_path is not None:
        write_json(safety_contract_path, build_safety_contract())
        safety_contract_created = safety_contract_path.exists()

    req(input_schema_created, "input schema not created", errors)
    req(phase_map_created, "phase map not created", errors)
    req(item_template_created, "item template not created", errors)
    req(safety_contract_created, "safety contract not created", errors)

    status = STATUS_PASSED if not errors else STATUS_FAILED

    payload = {
        "phase": "LS-REUSE-1",
        "document_type": "START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_RESULT",
        "status": status,
        "execution_mode": "TEMPLATE_BUILD_ONLY_NO_EXECUTION",
        "production_status": "NO_EXECUTION_REUSE_TEMPLATE_ONLY",
        "source_post_id": int(source_chain.get("source_post_id", 0)),
        "source_post_link": str(source_chain.get("source_post_link", "")),
        "source_payload_title": str(source_chain.get("source_title", "")),
        "source_payload_asin": str(source_chain.get("source_asin", "")),
        "ls_mon1_validated": ls_mon1_validation.get("status") == req_mon1.get("required_validation_status"),
        "ls_close1_validated": ls_close1_validation.get("status") == req_close1.get("required_validation_status"),
        "ls6au_validated": ls6au_validation.get("status") == req_ls6au.get("required_validation_status"),
        "ls6at_validated": ls6at_validation.get("status") == req_ls6at.get("required_validation_status"),
        "reusable_template_built": all([input_schema_created, phase_map_created, item_template_created, safety_contract_created]),
        "input_schema_created": input_schema_created,
        "phase_map_created": phase_map_created,
        "item_template_created": item_template_created,
        "safety_contract_created": safety_contract_created,
        "parameterized_fields": [
            "content_item_id",
            "target_post_id",
            "target_post_link",
            "payload_title",
            "payload_asin",
            "expected_pre_publish_status",
            "target_publish_status",
            "public_url",
            "public_rest_url",
            "evidence_paths",
        ],
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
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "next_post_created": False,
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
        "locked": status == STATUS_PASSED,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "ls6oc1_rerun_executed": False,
        "recommended_next_action": str(policy.get("next_phase", {}).get("recommended_next_action", "BEGIN_NEXT_CONTENT_ITEM_WITH_REUSABLE_TEMPLATE_OR_CONTINUE_MONITORING")),
        "recommended_next_phase_options": list(policy.get("next_phase", {}).get("recommended_next_phase_options", ["LS-NEXT-1", "LS-MON-2", "LS-REUSE-2"])),
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
        "phase": "LS-REUSE-1",
        "document_type": "START_LS_REUSABLE_PUBLISH_CHAIN_TEMPLATE_LOCK",
        "status": STATUS_LOCKED if status == STATUS_PASSED else status,
        "locked": status == STATUS_PASSED,
        "source_post_id": int(source_chain.get("source_post_id", 0)),
        "reusable_template_built": payload["reusable_template_built"],
        "input_schema_created": payload["input_schema_created"],
        "phase_map_created": payload["phase_map_created"],
        "item_template_created": payload["item_template_created"],
        "safety_contract_created": payload["safety_contract_created"],
        "template_execution_allowed_by_this_phase": False,
        "next_item_creation_allowed_by_this_phase": False,
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "publish_executed_by_this_phase": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "next_post_created": False,
        "rollback_executed": False,
        "unpublish_executed": False,
        "draft_revert_executed": False,
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
