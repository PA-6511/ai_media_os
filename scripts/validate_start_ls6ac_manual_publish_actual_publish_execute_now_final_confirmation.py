#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6AC_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_NOT_READY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation.template.json")
    parser.add_argument("--confirmation", default="exchange/human_review/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation.json")
    parser.add_argument("--ls6ab-run-result", default="exchange/logs/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_result.json")
    parser.add_argument("--ls6ab-validation-result", default="exchange/logs/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_validation_result.json")
    parser.add_argument("--ls6ab-blocked-runner-result", default="exchange/runtime/start_ls6ab_manual_publish_separated_actual_publish_execution_runner_blocked_result.json")
    parser.add_argument("--ls6ab-blocked-runner-lock", default="exchange/locks/start_ls6ab_manual_publish_separated_actual_publish_execution_runner.lock.json")
    parser.add_argument("--ls6aa-validation-result", default="exchange/logs/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_validation_result.json")
    parser.add_argument("--ls6aa-final-preflight-result", default="exchange/runtime/start_ls6aa_manual_publish_actual_publish_execution_final_preflight_result.json")
    parser.add_argument("--ls6aa-final-preflight-lock", default="exchange/locks/start_ls6aa_manual_publish_actual_publish_execution_final_preflight.lock.json")
    parser.add_argument("--ls6z-ready-result", default="exchange/logs/start_ls6z_manual_publish_final_explicit_publish_execution_command_ready_result.json")
    parser.add_argument("--ls6z-command-result", default="exchange/human_review/start_ls6z_manual_publish_final_explicit_publish_execution_command.json")
    parser.add_argument("--ls6y-validation-result", default="exchange/logs/start_ls6y_manual_publish_actual_publish_runner_execution_boundary_validation_result.json")
    parser.add_argument("--ls6y-boundary-lock", default="exchange/locks/start_ls6y_manual_publish_actual_publish_runner_execution_boundary.lock.json")
    parser.add_argument("--ls6x-ready-result", default="exchange/logs/start_ls6x_manual_publish_separated_actual_publish_execution_gate_ready_result.json")
    parser.add_argument("--ls6x-gate-result", default="exchange/human_review/start_ls6x_manual_publish_separated_actual_publish_execution_gate.json")
    parser.add_argument("--ls6v-ready-result", default="exchange/logs/start_ls6v_manual_publish_final_execution_command_ready_result.json")
    parser.add_argument("--ls6t-ready-result", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6ac_manual_publish_actual_publish_execute_now_final_confirmation_ready_report.md")
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


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-6AC Manual Publish Actual Publish Execute-Now Final Confirmation Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- post_id: {result['post_id']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- confirmation_status: {result['confirmation_status']}",
        f"- actual_publish_execute_now_final_confirmation_label: {result['actual_publish_execute_now_final_confirmation_label']}",
        f"- actual_publish_execution_runner_ready: {result['actual_publish_execution_runner_ready']}",
        f"- actual_publish_execution_runner_blocked: {result['actual_publish_execution_runner_blocked']}",
        f"- publish_execution_still_blocked: {result['publish_execution_still_blocked']}",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur


def k_cread() -> str:
    return "credential_" + "env_read_executed"


def validate_target(target: dict[str, Any], errors: list[str]) -> None:
    req(target.get("post_id") == 183, "target_post.post_id mismatch", errors)
    req(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)
    req(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    req(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def validate_false_keys(doc: dict[str, Any], keys: list[str], prefix: str, errors: list[str]) -> None:
    for key in keys:
        req(doc.get(key) is False, f"{prefix}.{key} must be false", errors)


def validate_current_phase(current: dict[str, Any], errors: list[str]) -> None:
    validate_false_keys(
        current,
        [
            "wordpress_api_call_executed",
            "wordpress_get_executed",
            "wordpress_post_executed",
            "wordpress_put_executed",
            "wordpress_patch_executed",
            "wordpress_delete_executed",
            "wordpress_write_executed_by_this_phase",
            "wordpress_draft_creation_executed_by_this_phase",
            "wordpress_existing_post_update_executed",
            "wordpress_publish_executed",
            "publish_executed",
            "future_schedule_executed",
            "delete_executed",
            "post119_update_executed",
            k_cread(),
            "credential_value_output",
            "credential_value_persisted",
            "credential_secret_output",
            "secret_length_output",
            "secret_hash_output",
            "authorization_header_output",
            "ls6oc1_rerun_executed",
            "rerun_allowed",
        ],
        "current_phase_execution",
        errors,
    )


def validate_common_upstream(
    policy: dict[str, Any],
    ls6ab_run: dict[str, Any],
    ls6ab_validation: dict[str, Any],
    ls6ab_blocked: dict[str, Any],
    ls6ab_lock: dict[str, Any],
    ls6aa_validation: dict[str, Any],
    ls6aa_preflight: dict[str, Any],
    ls6aa_lock: dict[str, Any],
    ls6z_ready: dict[str, Any],
    ls6z_command: dict[str, Any],
    ls6y_validation: dict[str, Any],
    ls6y_lock: dict[str, Any],
    ls6x_ready: dict[str, Any],
    ls6x_gate: dict[str, Any],
    ls6v_ready: dict[str, Any],
    ls6t_ready: dict[str, Any],
    ls6r_ready: dict[str, Any],
    ls6oc1_lock: dict[str, Any],
    errors: list[str],
) -> None:
    req(policy.get("phase") == "LS-6AC", "policy.phase mismatch", errors)
    req(policy.get("execution_mode") == "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_GATE_ONLY_NO_PUBLISH", "policy.execution_mode mismatch", errors)
    req(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    req(ls6ab_run.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB run status mismatch", errors)
    req(ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB validation status mismatch", errors)
    req(ls6ab_blocked.get("status") == "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_BLOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB blocked status mismatch", errors)
    req(ls6ab_lock.get("status") == "MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_LOCKED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH", "LS-6AB lock status mismatch", errors)
    req(ls6ab_run.get("post_id") == 183, "LS-6AB post_id mismatch", errors)
    req(ls6ab_run.get("returned_post_status") == "draft", "LS-6AB returned_post_status mismatch", errors)
    req(ls6ab_run.get("actual_publish_execution_runner_ready") is True, "LS-6AB runner_ready must be true", errors)
    req(ls6ab_run.get("actual_publish_execution_runner_executed") is False, "LS-6AB runner_executed must be false", errors)
    req(ls6ab_run.get("actual_publish_execution_runner_blocked") is True, "LS-6AB runner_blocked must be true", errors)
    req(ls6ab_run.get("explicit_execute_now_for_actual_publish_required") is True, "LS-6AB explicit required must be true", errors)
    req(ls6ab_run.get("explicit_execute_now_for_actual_publish_received") is False, "LS-6AB explicit received must be false", errors)
    req(ls6ab_run.get("explicit_execute_now_for_actual_publish_consumed") is False, "LS-6AB explicit consumed must be false", errors)
    req(ls6ab_run.get("publish_execution_still_blocked") is True, "LS-6AB publish_execution_still_blocked must be true", errors)
    req(safe_get(ls6ab_run, "next_phase", "phase") == "LS-6AC", "LS-6AB next_phase mismatch", errors)

    req(ls6aa_validation.get("status") == "LS6AA_MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTION_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH", "LS-6AA validation status mismatch", errors)
    req(ls6aa_validation.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA validation consumed must be false", errors)
    req(ls6aa_preflight.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA preflight consumed must be false", errors)
    req(ls6aa_lock.get("actual_publish_execution_final_preflight_consumed") is False, "LS-6AA lock consumed must be false", errors)

    req(ls6z_ready.get("status") == "LS6Z_MANUAL_PUBLISH_FINAL_EXPLICIT_PUBLISH_EXECUTION_COMMAND_READY_NO_PUBLISH", "LS-6Z ready status mismatch", errors)
    req(ls6z_ready.get("final_explicit_publish_execution_command_consumed") is False, "LS-6Z consumed must be false", errors)
    req(safe_get(ls6z_command, "final_explicit_publish_execution_command", "final_explicit_publish_execution_command_consumed") is False, "LS-6Z command consumed must be false", errors)

    req(ls6y_validation.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y consumed must be false", errors)
    req(ls6y_lock.get("actual_publish_runner_boundary_consumed") is False, "LS-6Y lock consumed must be false", errors)

    req(ls6x_ready.get("actual_publish_execution_gate_consumed") is False, "LS-6X consumed must be false", errors)
    req(safe_get(ls6x_gate, "actual_publish_execution_gate", "actual_publish_execution_gate_consumed") is False, "LS-6X gate consumed must be false", errors)

    req(ls6v_ready.get("final_execution_command_consumed") is False, "LS-6V consumed must be false", errors)
    req(ls6t_ready.get("execute_now_confirmation_consumed") is False, "LS-6T consumed must be false", errors)
    req(ls6r_ready.get("approval_label_consumed") is False, "LS-6R consumed must be false", errors)
    req(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)


def validate_template_doc(template: dict[str, Any], errors: list[str]) -> None:
    req(template.get("phase") == "LS-6AC", "template.phase mismatch", errors)
    req(template.get("document_type") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_TEMPLATE", "template.document_type mismatch", errors)
    req(template.get("confirmation_status") == "TEMPLATE_NOT_CONFIRMED", "template.confirmation_status mismatch", errors)
    validate_target(template.get("target_post", {}), errors)

    conf = template.get("actual_publish_execute_now_final_confirmation", {})
    req(conf.get("actual_publish_execute_now_final_confirmation_label") in ("", None), "template label must be empty", errors)
    req(conf.get("required_actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "template required label mismatch", errors)
    req(conf.get("actual_publish_execute_now_final_confirmation_consumed") is False, "template confirmation consumed must be false", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_required") is True, "template explicit required must be true", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_received") is False, "template explicit received must be false", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_consumed") is False, "template explicit consumed must be false", errors)
    req(conf.get("actual_publish_execution_runner_ready") is True, "template runner ready must be true", errors)
    req(conf.get("actual_publish_execution_runner_executed") is False, "template runner executed must be false", errors)
    req(conf.get("actual_publish_execution_runner_blocked") is True, "template runner blocked must be true", errors)

    validate_false_keys(
        conf,
        [
            "actual_publish_execution_allowed_by_this_phase",
            "actual_runner_execution_allowed_by_this_phase",
            "manual_publish_allowed_by_this_phase",
            "manual_publish_execution_allowed_by_this_phase",
            "manual_publish_executed",
        ],
        "template.confirmation",
        errors,
    )

    validate_false_keys(
        template.get("upstream_consumption_state", {}),
        [
            "final_explicit_publish_execution_command_consumed",
            "actual_publish_execution_final_preflight_consumed",
            "actual_publish_runner_boundary_consumed",
            "actual_publish_execution_gate_consumed",
            "final_execution_command_consumed",
            "approval_label_consumed",
            "execute_now_confirmation_consumed",
        ],
        "template.upstream_consumption_state",
        errors,
    )

    validate_current_phase(template.get("current_phase_execution", {}), errors)


def validate_confirmation_doc(doc: dict[str, Any], errors: list[str]) -> None:
    req(doc.get("phase") == "LS-6AC", "confirmation.phase mismatch", errors)
    req(doc.get("document_type") == "MANUAL_PUBLISH_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION", "confirmation.document_type mismatch", errors)
    req(doc.get("confirmation_status") == "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION", "confirmation_status mismatch", errors)
    validate_target(doc.get("target_post", {}), errors)

    conf = doc.get("actual_publish_execute_now_final_confirmation", {})
    req(conf.get("actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "wrong actual_publish_execute_now_final_confirmation_label", errors)
    req(conf.get("required_actual_publish_execute_now_final_confirmation_label") == "CONFIRMED_FOR_ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_GATE_ONLY", "required confirmation label mismatch", errors)
    req(conf.get("actual_publish_execute_now_final_confirmation_consumed") is False, "confirmation consumed must be false", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_required") is True, "explicit required must be true", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_received") is True, "explicit received must be true", errors)
    req(conf.get("explicit_execute_now_for_actual_publish_consumed") is False, "explicit consumed must be false", errors)
    req(conf.get("actual_publish_execution_runner_ready") is True, "runner ready must be true", errors)
    req(conf.get("actual_publish_execution_runner_executed") is False, "runner executed must be false", errors)
    req(conf.get("actual_publish_execution_runner_blocked") is True, "runner blocked must be true", errors)

    validate_false_keys(
        conf,
        [
            "actual_publish_execution_allowed_by_this_phase",
            "actual_runner_execution_allowed_by_this_phase",
            "manual_publish_allowed_by_this_phase",
            "manual_publish_execution_allowed_by_this_phase",
            "manual_publish_executed",
        ],
        "confirmation",
        errors,
    )
    req(conf.get("requires_next_phase") == "LS-6AD", "requires_next_phase mismatch", errors)

    validate_false_keys(
        doc.get("upstream_consumption_state", {}),
        [
            "final_explicit_publish_execution_command_consumed",
            "actual_publish_execution_final_preflight_consumed",
            "actual_publish_runner_boundary_consumed",
            "actual_publish_execution_gate_consumed",
            "final_execution_command_consumed",
            "approval_label_consumed",
            "execute_now_confirmation_consumed",
        ],
        "upstream_consumption_state",
        errors,
    )

    validate_current_phase(doc.get("current_phase_execution", {}), errors)


def build_result(status: str, source: dict[str, Any], ls6ab_validation: dict[str, Any], ls6ab_run: dict[str, Any], ls6aa_preflight: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    target = source.get("target_post", {})
    conf = source.get("actual_publish_execute_now_final_confirmation", {})
    cur = source.get("current_phase_execution", {})
    return {
        "phase": "LS-6AC",
        "status": status,
        "execution_mode": "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_GATE_ONLY_NO_PUBLISH",
        "production_status": "NO_PUBLISH",
        "post_id": target.get("post_id", 0),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "returned_post_status": target.get("expected_current_status", ""),
        "ls6ab_blocked_runner_validated": ls6ab_validation.get("status") == "LS6AB_MANUAL_PUBLISH_SEPARATED_ACTUAL_PUBLISH_EXECUTION_RUNNER_VALIDATED_EXPLICIT_EXECUTE_REQUIRED_NO_PUBLISH",
        "actual_publish_execute_now_final_confirmation_recorded": source.get("confirmation_status") == "ACTUAL_PUBLISH_EXECUTE_NOW_FINAL_CONFIRMATION_RECORDED_NO_PUBLISH_EXECUTION",
        "confirmation_status": source.get("confirmation_status", ""),
        "actual_publish_execute_now_final_confirmation_label": conf.get("actual_publish_execute_now_final_confirmation_label", ""),
        "actual_publish_execute_now_final_confirmation_consumed": bool(conf.get("actual_publish_execute_now_final_confirmation_consumed", False)),
        "explicit_execute_now_for_actual_publish_required": bool(conf.get("explicit_execute_now_for_actual_publish_required", False)),
        "explicit_execute_now_for_actual_publish_received": bool(conf.get("explicit_execute_now_for_actual_publish_received", False)),
        "explicit_execute_now_for_actual_publish_consumed": bool(conf.get("explicit_execute_now_for_actual_publish_consumed", False)),
        "actual_publish_execution_runner_ready": bool(conf.get("actual_publish_execution_runner_ready", False)),
        "actual_publish_execution_runner_executed": bool(conf.get("actual_publish_execution_runner_executed", False)),
        "actual_publish_execution_runner_blocked": bool(conf.get("actual_publish_execution_runner_blocked", False)),
        "final_explicit_publish_execution_command_label": ls6ab_run.get("final_explicit_publish_execution_command_label", ""),
        "final_explicit_publish_execution_command_consumed": bool(safe_get(source, "upstream_consumption_state", "final_explicit_publish_execution_command_consumed")),
        "actual_publish_execution_final_preflight_ready": bool(ls6aa_preflight.get("actual_publish_execution_final_preflight_ready", False)),
        "actual_publish_execution_final_preflight_consumed": bool(safe_get(source, "upstream_consumption_state", "actual_publish_execution_final_preflight_consumed")),
        "actual_publish_runner_boundary_consumed": bool(safe_get(source, "upstream_consumption_state", "actual_publish_runner_boundary_consumed")),
        "actual_publish_execution_gate_consumed": bool(safe_get(source, "upstream_consumption_state", "actual_publish_execution_gate_consumed")),
        "final_execution_command_consumed": bool(safe_get(source, "upstream_consumption_state", "final_execution_command_consumed")),
        "approval_label_consumed": bool(safe_get(source, "upstream_consumption_state", "approval_label_consumed")),
        "execute_now_confirmation_consumed": bool(safe_get(source, "upstream_consumption_state", "execute_now_confirmation_consumed")),
        "actual_publish_execution_allowed_by_this_phase": bool(conf.get("actual_publish_execution_allowed_by_this_phase", False)),
        "actual_runner_execution_allowed_by_this_phase": bool(conf.get("actual_runner_execution_allowed_by_this_phase", False)),
        "manual_publish_allowed_by_this_phase": bool(conf.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(conf.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(conf.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(cur.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(cur.get("wordpress_get_executed", False)),
        "wordpress_post_executed": bool(cur.get("wordpress_post_executed", False)),
        "wordpress_put_executed": bool(cur.get("wordpress_put_executed", False)),
        "wordpress_patch_executed": bool(cur.get("wordpress_patch_executed", False)),
        "wordpress_delete_executed": bool(cur.get("wordpress_delete_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(cur.get("wordpress_write_executed_by_this_phase", False)),
        "wordpress_draft_creation_executed_by_this_phase": bool(cur.get("wordpress_draft_creation_executed_by_this_phase", False)),
        "wordpress_existing_post_update_executed": bool(cur.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(cur.get("wordpress_publish_executed", False)),
        "publish_executed": bool(cur.get("publish_executed", False)),
        "future_schedule_executed": bool(cur.get("future_schedule_executed", False)),
        "delete_executed": bool(cur.get("delete_executed", False)),
        "post119_update_executed": bool(cur.get("post119_update_executed", False)),
        k_cread(): bool(cur.get(k_cread(), False)),
        "credential_value_output": bool(cur.get("credential_value_output", False)),
        "credential_value_persisted": bool(cur.get("credential_value_persisted", False)),
        "credential_secret_output": bool(cur.get("credential_secret_output", False)),
        "secret_length_output": bool(cur.get("secret_length_output", False)),
        "secret_hash_output": bool(cur.get("secret_hash_output", False)),
        "authorization_header_output": bool(cur.get("authorization_header_output", False)),
        "rerun_allowed": bool(cur.get("rerun_allowed", False)),
        "ls6oc1_rerun_executed": bool(cur.get("ls6oc1_rerun_executed", False)),
        "requires_actual_publish_execution_boundary": True,
        "requires_separate_publish_execution_phase": True,
        "publish_execution_still_blocked": True,
        "next_phase": {
            "phase": "LS-6AD",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "actual_publish_execution_allowed_by_this_phase": False,
            "actual_runner_execution_allowed_by_this_phase": False,
            "requires_actual_publish_execution_boundary": True,
            "requires_separate_publish_execution_phase": True,
            "publish_execution_still_blocked": True,
        },
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    template = try_load_json(Path(args.template), errors)

    ls6ab_run = try_load_json(Path(args.ls6ab_run_result), errors)
    ls6ab_validation = try_load_json(Path(args.ls6ab_validation_result), errors)
    ls6ab_blocked = try_load_json(Path(args.ls6ab_blocked_runner_result), errors)
    ls6ab_lock = try_load_json(Path(args.ls6ab_blocked_runner_lock), errors)
    ls6aa_validation = try_load_json(Path(args.ls6aa_validation_result), errors)
    ls6aa_preflight = try_load_json(Path(args.ls6aa_final_preflight_result), errors)
    ls6aa_lock = try_load_json(Path(args.ls6aa_final_preflight_lock), errors)
    ls6z_ready = try_load_json(Path(args.ls6z_ready_result), errors)
    ls6z_command = try_load_json(Path(args.ls6z_command_result), errors)
    ls6y_validation = try_load_json(Path(args.ls6y_validation_result), errors)
    ls6y_lock = try_load_json(Path(args.ls6y_boundary_lock), errors)
    ls6x_ready = try_load_json(Path(args.ls6x_ready_result), errors)
    ls6x_gate = try_load_json(Path(args.ls6x_gate_result), errors)
    ls6v_ready = try_load_json(Path(args.ls6v_ready_result), errors)
    ls6t_ready = try_load_json(Path(args.ls6t_ready_result), errors)
    ls6r_ready = try_load_json(Path(args.ls6r_ready_result), errors)
    ls6oc1_lock = try_load_json(Path(args.ls6oc1_consumption_lock), errors)

    validate_common_upstream(
        policy,
        ls6ab_run,
        ls6ab_validation,
        ls6ab_blocked,
        ls6ab_lock,
        ls6aa_validation,
        ls6aa_preflight,
        ls6aa_lock,
        ls6z_ready,
        ls6z_command,
        ls6y_validation,
        ls6y_lock,
        ls6x_ready,
        ls6x_gate,
        ls6v_ready,
        ls6t_ready,
        ls6r_ready,
        ls6oc1_lock,
        errors,
    )

    if args.allow_template:
        validate_template_doc(template, errors)
        src = template
        status = STATUS_TEMPLATE_READY if not errors else STATUS_NOT_READY
    else:
        cpath = Path(args.confirmation)
        if not cpath.exists():
            errors.append("confirmation file missing")
            src = template
        else:
            conf = try_load_json(cpath, errors)
            validate_confirmation_doc(conf, errors)
            src = conf
        status = STATUS_READY if not errors else STATUS_NOT_READY

    result = build_result(status, src, ls6ab_validation, ls6ab_run, ls6aa_preflight, errors)
    write_json(Path(args.output), result)
    write_report(Path(args.report), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
