#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6AS_ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6as_actual_publish_execution_runner_final_command_policy.json",
    )
    parser.add_argument(
        "--template",
        default="exchange/human_review/start_ls6as_actual_publish_execution_runner_final_command.template.json",
    )
    parser.add_argument(
        "--final-command",
        default="exchange/human_review/start_ls6as_actual_publish_execution_runner_final_command.json",
    )
    parser.add_argument(
        "--ls6ar-credential-preflight-result",
        default="exchange/runtime/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--ls6ar-credential-preflight-lock",
        default="exchange/locks/start_ls6ar_actual_publish_execution_runner_credential_preflight.lock.json",
    )
    parser.add_argument(
        "--ls6ar-run-result",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_result.json",
    )
    parser.add_argument(
        "--ls6ar-validation-result",
        default="exchange/logs/start_ls6ar_actual_publish_execution_runner_credential_preflight_validation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6as_actual_publish_execution_runner_final_command_ready_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6as_actual_publish_execution_runner_final_command_ready_report.md",
    )
    parser.add_argument("--allow-template", action="store_true")
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
        "# LS-6AS Actual Publish Execution Runner Final Command Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- command_status: {payload.get('command_status', '')}",
        f"- post_id: {payload.get('post_id', 0)}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {err}" for err in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def bool_val(value: Any) -> bool:
    return bool(value)


def get_doc_value(source_doc: dict[str, Any], key: str) -> Any:
    if key in source_doc:
        return source_doc.get(key)
    final_command = source_doc.get("final_command", {})
    if key in final_command:
        return final_command.get(key)
    current_phase_execution = source_doc.get("current_phase_execution", {})
    if key in current_phase_execution:
        return current_phase_execution.get(key)
    return None


def validate_ls6ar_prerequisites(
    policy: dict[str, Any],
    preflight_result: dict[str, Any],
    preflight_lock: dict[str, Any],
    run_result: dict[str, Any],
    validation_result: dict[str, Any],
    errors: list[str],
) -> None:
    required = policy.get("required_previous_phase", {}).get("ls6ar", {})

    req(policy.get("phase") == "LS-6AS", "policy.phase mismatch", errors)

    req(
        preflight_result.get("status") == required.get("required_run_status"),
        "LS-6AR run status mismatch",
        errors,
    )
    req(
        validation_result.get("status") == required.get("required_validation_status"),
        "LS-6AR validation status mismatch",
        errors,
    )
    req(run_result.get("status") == required.get("required_run_status"), "LS-6AR run log status mismatch", errors)

    req(preflight_result.get("post_id") == required.get("required_post_id"), "post_id mismatch", errors)
    req(preflight_result.get("returned_post_status") == required.get("required_returned_post_status"), "returned_post_status mismatch", errors)

    req(
        bool_val(preflight_result.get("actual_publish_execution_runner_credential_preflight_ready"))
        is bool(required.get("required_credential_preflight_ready")),
        "credential_preflight_ready mismatch",
        errors,
    )
    req(
        bool_val(preflight_result.get("actual_publish_execution_runner_credential_preflight_consumed"))
        is bool(required.get("required_credential_preflight_consumed")),
        "credential_preflight_consumed mismatch",
        errors,
    )
    req(
        bool_val(preflight_result.get("actual_publish_execution_runner_final_boundary_ready"))
        is bool(required.get("required_final_boundary_ready")),
        "final_boundary_ready mismatch",
        errors,
    )
    req(
        bool_val(preflight_result.get("actual_publish_execution_runner_final_boundary_consumed"))
        is bool(required.get("required_final_boundary_consumed")),
        "final_boundary_consumed mismatch",
        errors,
    )
    req(
        bool_val(preflight_result.get("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase"))
        is bool(required.get("required_boundary_allows_execution_by_this_phase")),
        "boundary_allows_execution_by_this_phase mismatch",
        errors,
    )

    req(
        bool_val(preflight_result.get("credential_env_read_executed"))
        is bool(required.get("required_credential_env_read_executed")),
        "credential_env_read_executed mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("credential_env_exists"))
        is bool(required.get("required_credential_env_exists")),
        "credential_env_exists mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("credential_env_readable"))
        is bool(required.get("required_credential_env_readable")),
        "credential_env_readable mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("credential_env_permission_checked"))
        is bool(required.get("required_credential_env_permission_checked")),
        "credential_env_permission_checked mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("credential_required_keys_present"))
        is bool(required.get("required_credential_required_keys_present")),
        "credential_required_keys_present mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("credential_required_keys_non_empty"))
        is bool(required.get("required_credential_required_keys_non_empty")),
        "credential_required_keys_non_empty mismatch in LS-6AR source",
        errors,
    )

    req(
        bool_val(preflight_result.get("credential_value_output"))
        is (not bool(required.get("required_no_credential_value_output"))),
        "credential_value_output mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("credential_value_persisted"))
        is (not bool(required.get("required_no_credential_value_persisted"))),
        "credential_value_persisted mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("secret_length_output"))
        is (not bool(required.get("required_no_secret_length_output"))),
        "secret_length_output mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("secret_hash_output"))
        is (not bool(required.get("required_no_secret_hash_output"))),
        "secret_hash_output mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("authorization_header_generated"))
        is (not bool(required.get("required_no_authorization_header_generated"))),
        "authorization_header_generated mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("basic_auth_string_generated"))
        is (not bool(required.get("required_no_basic_auth_string_generated"))),
        "basic_auth_string_generated mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("wordpress_api_call_executed"))
        is (not bool(required.get("required_no_wordpress_api_call"))),
        "wordpress_api_call_executed mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("publish_executed"))
        is (not bool(required.get("required_no_publish"))),
        "publish_executed mismatch in LS-6AR source",
        errors,
    )
    req(
        bool_val(preflight_result.get("actual_publish_execution_runner_executed"))
        is (not bool(required.get("required_no_runner_execution"))),
        "actual_publish_execution_runner_executed mismatch in LS-6AR source",
        errors,
    )

    req(
        bool_val(preflight_result.get("publish_execution_still_blocked"))
        is bool(required.get("required_publish_execution_still_blocked")),
        "publish_execution_still_blocked mismatch in LS-6AR source",
        errors,
    )

    req(preflight_lock.get("locked") is True, "LS-6AR lock mismatch", errors)


def validate_target(policy: dict[str, Any], source_doc: dict[str, Any], errors: list[str]) -> None:
    target = policy.get("target_post", {})
    doc_target = source_doc.get("target_post", {})
    req(doc_target.get("post_id") == target.get("post_id"), "document target post_id mismatch", errors)
    req(doc_target.get("post_link") == target.get("post_link"), "document target post_link mismatch", errors)
    req(doc_target.get("title") == target.get("title"), "document target title mismatch", errors)
    req(doc_target.get("asin") == target.get("asin"), "document target asin mismatch", errors)
    req(
        doc_target.get("expected_current_status") == target.get("expected_current_status"),
        "document target expected_current_status mismatch",
        errors,
    )


def validate_source_doc(
    policy: dict[str, Any],
    source_doc: dict[str, Any],
    allow_template: bool,
    errors: list[str],
) -> None:
    final_command = source_doc.get("final_command", {})

    if allow_template:
        req(
            source_doc.get("document_type") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_TEMPLATE",
            "template document_type mismatch",
            errors,
        )
        req(source_doc.get("command_status") == "TEMPLATE_NOT_CONFIRMED", "template command_status mismatch", errors)
        req(
            final_command.get("actual_publish_execution_runner_final_command_label", "") == "",
            "template final command label must be empty",
            errors,
        )
    else:
        req(
            source_doc.get("document_type") == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND",
            "final command document_type mismatch",
            errors,
        )
        req(
            source_doc.get("command_status")
            == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION",
            "final command status mismatch",
            errors,
        )

    final_policy = policy.get("final_command_policy", {})

    required_label = str(final_policy.get("actual_publish_execution_runner_final_command_label", ""))
    if not allow_template:
        req(
            final_command.get("actual_publish_execution_runner_final_command_label") == required_label,
            "wrong final command label",
            errors,
        )
    req(
        final_command.get("required_actual_publish_execution_runner_final_command_label") == required_label,
        "required final command label mismatch",
        errors,
    )

    req(
        bool_val(get_doc_value(source_doc, "actual_publish_execution_runner_final_command_consumed"))
        is bool(final_policy.get("actual_publish_execution_runner_final_command_consumed")),
        "final command consumed mismatch",
        errors,
    )
    req(
        bool_val(get_doc_value(source_doc, "actual_publish_execution_runner_final_command_allows_execution_by_this_phase"))
        is bool(final_policy.get("actual_publish_execution_runner_final_command_allows_execution_by_this_phase")),
        "final command allows_execution mismatch",
        errors,
    )
    req(
        bool_val(get_doc_value(source_doc, "actual_publish_execution_runner_final_command_approved_for_later_separated_phase"))
        is bool(final_policy.get("actual_publish_execution_runner_final_command_approved_for_later_separated_phase")),
        "approved_for_later_separated_phase mismatch",
        errors,
    )
    req(
        bool_val(get_doc_value(source_doc, "actual_publish_execution_runner_separate_publish_execution_phase_required"))
        is bool(final_policy.get("actual_publish_execution_runner_separate_publish_execution_phase_required")),
        "separate publish execution phase required mismatch",
        errors,
    )

    must_false = policy.get("must_remain_false_flags", {})
    for key, expected in must_false.items():
        value = get_doc_value(source_doc, key)
        if value is not None:
            req(bool_val(value) is bool(expected), f"{key} mismatch", errors)


def build_payload(
    policy: dict[str, Any],
    source_doc: dict[str, Any],
    preflight_result: dict[str, Any],
    errors: list[str],
    allow_template: bool,
) -> dict[str, Any]:
    target = policy.get("target_post", {})
    final = source_doc.get("final_command", {})
    current = source_doc.get("current_phase_execution", {})
    next_phase_policy = policy.get("next_phase", {})
    final_policy = policy.get("final_command_policy", {})

    if errors:
        status = STATUS_NOT_READY
    elif allow_template:
        status = STATUS_TEMPLATE_READY
    else:
        status = STATUS_READY

    return {
        "phase": "LS-6AS",
        "status": status,
        "execution_mode": str(policy.get("execution_mode", "")),
        "production_status": str(policy.get("production_status", "")),
        "post_id": int(target.get("post_id", 0)),
        "post_link": str(target.get("post_link", "")),
        "payload_title": str(target.get("title", "")),
        "payload_asin": str(target.get("asin", "")),
        "returned_post_status": str(preflight_result.get("returned_post_status", "")),
        "ls6ar_credential_preflight_validated": bool(
            final.get("ls6ar_credential_preflight_validated", False)
        ),
        "actual_publish_execution_runner_final_command_recorded": (
            source_doc.get("command_status")
            == "ACTUAL_PUBLISH_EXECUTION_RUNNER_FINAL_COMMAND_RECORDED_NO_PUBLISH_EXECUTION"
        ),
        "command_status": str(source_doc.get("command_status", "")),
        "actual_publish_execution_runner_final_command_label": str(
            final.get("actual_publish_execution_runner_final_command_label", "")
        ),
        "actual_publish_execution_runner_final_command_consumed": bool(
            final.get("actual_publish_execution_runner_final_command_consumed", False)
        ),
        "actual_publish_execution_runner_final_command_allows_execution_by_this_phase": bool(
            final.get("actual_publish_execution_runner_final_command_allows_execution_by_this_phase", False)
        ),
        "actual_publish_execution_runner_final_command_approved_for_later_separated_phase": bool(
            final.get("actual_publish_execution_runner_final_command_approved_for_later_separated_phase", False)
        ),
        "actual_publish_execution_runner_separate_publish_execution_phase_required": bool(
            final.get("actual_publish_execution_runner_separate_publish_execution_phase_required", False)
        ),
        "actual_publish_execution_runner_credential_preflight_ready": bool(
            final.get("actual_publish_execution_runner_credential_preflight_ready", False)
        ),
        "actual_publish_execution_runner_credential_preflight_consumed": bool(
            final.get("actual_publish_execution_runner_credential_preflight_consumed", False)
        ),
        "actual_publish_execution_runner_final_boundary_ready": bool(
            final.get("actual_publish_execution_runner_final_boundary_ready", False)
        ),
        "actual_publish_execution_runner_final_boundary_consumed": bool(
            final.get("actual_publish_execution_runner_final_boundary_consumed", False)
        ),
        "actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase": bool(
            final.get("actual_publish_execution_runner_final_boundary_allows_execution_by_this_phase", False)
        ),
        "ls6ar_credential_env_read_executed": bool(
            preflight_result.get("credential_env_read_executed", False)
        ),
        "credential_env_read_executed_by_this_phase": bool(
            final.get("credential_env_read_executed_by_this_phase", False)
        ),
        "credential_env_read_executed": bool(final.get("credential_env_read_executed", False)),
        "credential_values_loaded_for_output": bool(final.get("credential_values_loaded_for_output", False)),
        "credential_values_persisted": bool(final.get("credential_values_persisted", False)),
        "credential_values_logged": bool(final.get("credential_values_logged", False)),
        "credential_value_output": bool(final.get("credential_value_output", False)),
        "credential_value_persisted": bool(final.get("credential_value_persisted", False)),
        "credential_secret_output": bool(final.get("credential_secret_output", False)),
        "secret_length_output": bool(final.get("secret_length_output", False)),
        "secret_hash_output": bool(final.get("secret_hash_output", False)),
        "authorization_header_generated": bool(final.get("authorization_header_generated", False)),
        "authorization_header_output": bool(final.get("authorization_header_output", False)),
        "basic_auth_string_generated": bool(final.get("basic_auth_string_generated", False)),
        "basic_auth_string_output": bool(final.get("basic_auth_string_output", False)),
        "wordpress_api_call_executed": bool(current.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(current.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(current.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(current.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(current.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(current.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(
            current.get("wordpress_write_executed_by_this_phase", False)
        ),
        "wordpress_publish_executed": bool(current.get("wordpress_publish_executed", False)),
        "publish_executed": bool(current.get("publish_executed", False)),
        "future_schedule_executed": bool(current.get("future_schedule_executed", False)),
        "delete_executed": bool(current.get("delete_executed", False)),
        "post119_update_executed": bool(current.get("post119_update_executed", False)),
        "actual_publish_execution_runner_network_call_enabled": bool(
            current.get("actual_publish_execution_runner_network_call_enabled", False)
        ),
        "actual_publish_execution_runner_credential_read_enabled": bool(
            current.get("actual_publish_execution_runner_credential_read_enabled", False)
        ),
        "actual_publish_execution_runner_publish_enabled": bool(
            current.get("actual_publish_execution_runner_publish_enabled", False)
        ),
        "actual_publish_execution_runner_execution_enabled": bool(
            current.get("actual_publish_execution_runner_execution_enabled", False)
        ),
        "actual_publish_execution_runner_executed": bool(
            current.get("actual_publish_execution_runner_executed", False)
        ),
        "manual_publish_executed": bool(current.get("manual_publish_executed", False)),
        "actual_publish_execution_allowed_by_this_phase": bool(
            final.get("actual_publish_execution_allowed_by_this_phase", False)
        ),
        "actual_runner_execution_allowed_by_this_phase": bool(
            final.get("actual_runner_execution_allowed_by_this_phase", False)
        ),
        "manual_publish_allowed_by_this_phase": bool(
            final.get("manual_publish_allowed_by_this_phase", False)
        ),
        "manual_publish_execution_allowed_by_this_phase": bool(
            final.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "rerun_allowed": bool(current.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(current.get("ls6oc1_rerun_executed", False)),
        "requires_separate_publish_execution_phase": bool(
            final.get(
                "requires_separate_publish_execution_phase",
                final_policy.get("requires_separate_publish_execution_phase", False),
            )
        ),
        "requires_actual_publish_execution_runner_separated_execution": bool(
            final.get(
                "requires_actual_publish_execution_runner_separated_execution",
                final_policy.get("requires_actual_publish_execution_runner_separated_execution", False),
            )
        ),
        "publish_execution_still_blocked": bool(
            final.get(
                "publish_execution_still_blocked",
                final_policy.get("publish_execution_still_blocked", False),
            )
        ),
        "next_phase": {
            "phase": str(next_phase_policy.get("phase", "")),
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": bool(
                next_phase_policy.get("manual_publish_execution_allowed_by_this_phase", False)
            ),
            "actual_publish_execution_allowed_by_this_phase": bool(
                next_phase_policy.get("actual_publish_execution_allowed_by_this_phase", False)
            ),
            "actual_runner_execution_allowed_by_this_phase": bool(
                next_phase_policy.get("actual_runner_execution_allowed_by_this_phase", False)
            ),
            "requires_separate_publish_execution_phase": bool(
                next_phase_policy.get("requires_separate_publish_execution_phase", False)
            ),
            "requires_actual_publish_execution_runner_separated_execution": bool(
                next_phase_policy.get("requires_actual_publish_execution_runner_separated_execution", False)
            ),
            "publish_execution_still_blocked": bool(
                next_phase_policy.get("publish_execution_still_blocked", False)
            ),
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    template = try_load_json(Path(args.template), errors)
    final_command = try_load_json(Path(args.final_command), errors)
    preflight_result = try_load_json(Path(args.ls6ar_credential_preflight_result), errors)
    preflight_lock = try_load_json(Path(args.ls6ar_credential_preflight_lock), errors)
    run_result = try_load_json(Path(args.ls6ar_run_result), errors)
    validation_result = try_load_json(Path(args.ls6ar_validation_result), errors)

    source_doc = template if args.allow_template else final_command

    validate_ls6ar_prerequisites(
        policy,
        preflight_result,
        preflight_lock,
        run_result,
        validation_result,
        errors,
    )

    validate_target(policy, source_doc, errors)
    validate_source_doc(policy, source_doc, args.allow_template, errors)

    payload = build_payload(policy, source_doc, preflight_result, errors, args.allow_template)

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
