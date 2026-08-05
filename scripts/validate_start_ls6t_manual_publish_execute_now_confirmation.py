#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6T_MANUAL_PUBLISH_EXECUTE_NOW_CONFIRMATION_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6t_manual_publish_execute_now_confirmation_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.template.json")
    parser.add_argument("--confirmation", default="exchange/human_review/start_ls6t_manual_publish_execute_now_confirmation.json")
    parser.add_argument("--ls6s-validation-result", default="exchange/logs/start_ls6s_manual_publish_final_preflight_validation_result.json")
    parser.add_argument("--ls6s-final-preflight-result", default="exchange/runtime/start_ls6s_manual_publish_final_preflight_result.json")
    parser.add_argument("--ls6s-final-preflight-lock", default="exchange/locks/start_ls6s_manual_publish_final_preflight.lock.json")
    parser.add_argument("--ls6r-ready-result", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--ls6r-approval-result", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6oc1-consumption-lock", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6t_manual_publish_execute_now_confirmation_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6t_manual_publish_execute_now_confirmation_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def validate_common(
    policy: dict[str, Any],
    ls6s_validation: dict[str, Any],
    ls6s_preflight: dict[str, Any],
    ls6s_lock: dict[str, Any],
    ls6r_ready: dict[str, Any],
    ls6r_approval: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6oc1_lock: dict[str, Any],
    errors: list[str],
) -> None:
    require(policy.get("phase") == "LS-6T", "policy.phase mismatch", errors)
    require(policy.get("execution_mode") == "EXECUTE_NOW_CONFIRMATION_GATE_ONLY", "policy.execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    require(ls6s_validation.get("status") == safe_get(policy, "required_previous_phase", "ls6s", "required_validation_status"), "LS-6S validation status mismatch", errors)
    require(ls6s_preflight.get("status") == "MANUAL_PUBLISH_FINAL_PREFLIGHT_PASSED_NO_PUBLISH", "LS-6S final preflight status mismatch", errors)
    require(ls6s_lock.get("status") == "MANUAL_PUBLISH_FINAL_PREFLIGHT_LOCKED_NO_PUBLISH", "LS-6S lock status mismatch", errors)
    require(ls6s_preflight.get("returned_post_status") == "draft", "LS-6S returned_post_status mismatch", errors)
    require(ls6s_validation.get("approval_label") == safe_get(policy, "required_previous_phase", "ls6s", "required_approval_label"), "LS-6S approval_label mismatch", errors)
    require(ls6s_validation.get("approval_label_consumed") is False, "LS-6S approval_label_consumed must be false", errors)
    require(ls6s_validation.get("manual_publish_executed") is False, "LS-6S manual_publish_executed must be false", errors)
    require(ls6s_validation.get("separate_execute_now_confirmation_required") is True, "LS-6S separate_execute_now_confirmation_required must be true", errors)
    require(ls6s_validation.get("publish_execution_still_blocked") is True, "LS-6S publish_execution_still_blocked must be true", errors)
    require(safe_get(ls6s_validation, "next_phase", "phase") == "LS-6T", "LS-6S next_phase.phase mismatch", errors)

    require(ls6r_ready.get("status") == safe_get(policy, "required_previous_phase", "ls6r", "required_ready_status"), "LS-6R ready status mismatch", errors)
    require(ls6r_ready.get("approval_label_consumed") is False, "LS-6R approval_label_consumed must be false", errors)
    require(ls6r_ready.get("manual_publish_executed") is False, "LS-6R manual_publish_executed must be false", errors)
    require(safe_get(ls6r_approval, "approval", "approval_label_consumed") is False, "LS-6R approval result label consumed mismatch", errors)

    require(ls6p_lock.get("locked") is True, "LS-6P lock must be true", errors)
    require(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)
    require(ls6oc1_lock.get("rerun_allowed") is False, "LS-6O-C-1 rerun_allowed must be false", errors)


def validate_target_post(target: dict[str, Any], errors: list[str]) -> None:
    require(to_int(target.get("post_id")) == 183, "target_post.post_id mismatch", errors)
    require(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)
    require(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    require(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def validate_current_phase_flags(data: dict[str, Any], errors: list[str]) -> None:
    keys = [
        "wordpress_api_call_executed",
        "wordpress_get_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "wordpress_existing_post_update_executed",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "approval_label_consumed",
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]
    for key in keys:
        require(bool(data.get(key, False)) is False, f"current_phase_execution.{key} must be false", errors)


def validate_template(template_doc: dict[str, Any], errors: list[str]) -> None:
    require(template_doc.get("confirmation_status") == "TEMPLATE_NOT_CONFIRMED", "template confirmation_status mismatch", errors)
    conf = template_doc.get("confirmation", {})
    require(conf.get("execute_now_confirmation_label") in ("", None), "template execute_now_confirmation_label must be empty", errors)
    require(conf.get("required_execute_now_confirmation_label") == "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY", "template required label mismatch", errors)
    require(conf.get("execute_now_confirmation_consumed") is False, "template execute_now_confirmation_consumed must be false", errors)
    require(conf.get("manual_publish_allowed_by_this_phase") is False, "template manual_publish_allowed_by_this_phase must be false", errors)
    require(conf.get("manual_publish_execution_allowed_by_this_phase") is False, "template manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(conf.get("manual_publish_executed") is False, "template manual_publish_executed must be false", errors)


def validate_confirmation(confirmation_doc: dict[str, Any], errors: list[str]) -> None:
    require(confirmation_doc.get("confirmation_status") == "CONFIRMED_NO_PUBLISH_EXECUTION", "confirmation_status mismatch", errors)
    conf = confirmation_doc.get("confirmation", {})
    require(conf.get("execute_now_confirmation_label") == "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY", "execute_now_confirmation_label mismatch", errors)
    require(conf.get("required_execute_now_confirmation_label") == "CONFIRMED_FOR_MANUAL_PUBLISH_EXECUTE_NOW_GATE_ONLY", "required_execute_now_confirmation_label mismatch", errors)
    require(conf.get("execute_now_confirmation_consumed") is False, "execute_now_confirmation_consumed must be false", errors)
    require(conf.get("manual_publish_allowed_by_this_phase") is False, "manual_publish_allowed_by_this_phase must be false", errors)
    require(conf.get("manual_publish_execution_allowed_by_this_phase") is False, "manual_publish_execution_allowed_by_this_phase must be false", errors)
    require(conf.get("manual_publish_executed") is False, "manual_publish_executed must be false", errors)
    require(conf.get("requires_next_phase") == "LS-6U", "requires_next_phase mismatch", errors)


def build_result(
    *,
    status: str,
    target: dict[str, Any],
    confirmation: dict[str, Any],
    current_phase_execution: dict[str, Any],
    ls6s_validation: dict[str, Any],
    ls6s_preflight: dict[str, Any],
    ls6r_ready: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6oc1_lock: dict[str, Any],
    recorded: bool,
    errors: list[str],
) -> dict[str, Any]:
    execute_label = confirmation.get("execute_now_confirmation_label", "")
    conf_status = "CONFIRMED_NO_PUBLISH_EXECUTION" if recorded else "TEMPLATE_NOT_CONFIRMED"
    return {
        "phase": "LS-6T",
        "status": status,
        "execution_mode": "EXECUTE_NOW_CONFIRMATION_GATE_ONLY",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(target.get("post_id")),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "draft_verified": bool(ls6s_validation.get("draft_verified", False)),
        "returned_post_status": ls6s_preflight.get("returned_post_status", ""),
        "ls6s_final_preflight_validated": ls6s_validation.get("status") == "LS6S_MANUAL_PUBLISH_FINAL_PREFLIGHT_VALIDATED_NO_PUBLISH",
        "ls6r_approval_verified": ls6r_ready.get("status") == "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH",
        "manual_publish_execute_now_confirmation_recorded": recorded,
        "confirmation_status": conf_status,
        "execute_now_confirmation_label": execute_label,
        "execute_now_confirmation_consumed": bool(confirmation.get("execute_now_confirmation_consumed", False)),
        "approval_label": ls6s_validation.get("approval_label", ""),
        "approval_label_consumed": bool(current_phase_execution.get("approval_label_consumed", False)),
        "manual_publish_allowed_by_this_phase": bool(confirmation.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(confirmation.get("manual_publish_execution_allowed_by_this_phase", False)),
        "manual_publish_executed": bool(confirmation.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(current_phase_execution.get("wordpress_api_call_executed", False)),
        "wordpress_get_executed": bool(current_phase_execution.get("wordpress_get_executed", False)),
        "wordpress_write_executed": bool(current_phase_execution.get("wordpress_write_executed", False)),
        "wordpress_draft_creation_executed": bool(current_phase_execution.get("wordpress_draft_creation_executed", False)),
        "wordpress_existing_post_update_executed": bool(current_phase_execution.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(current_phase_execution.get("wordpress_publish_executed", False)),
        "publish_executed": bool(current_phase_execution.get("publish_executed", False)),
        "future_schedule_executed": bool(current_phase_execution.get("future_schedule_executed", False)),
        "delete_executed": bool(current_phase_execution.get("delete_executed", False)),
        "post119_update_executed": bool(current_phase_execution.get("post119_update_executed", False)),
        "credential_env_read_executed": bool(current_phase_execution.get("credential_env_read_executed", False)),
        "credential_value_output": bool(current_phase_execution.get("credential_value_output", False)),
        "credential_value_persisted": bool(current_phase_execution.get("credential_value_persisted", False)),
        "credential_secret_output": bool(current_phase_execution.get("credential_secret_output", False)),
        "secret_length_output": bool(current_phase_execution.get("secret_length_output", False)),
        "secret_hash_output": bool(current_phase_execution.get("secret_hash_output", False)),
        "authorization_header_output": bool(current_phase_execution.get("authorization_header_output", False)),
        "rerun_allowed": bool(ls6p_lock.get("rerun_allowed", ls6oc1_lock.get("rerun_allowed", False))),
        "ls6oc1_rerun_executed": bool(current_phase_execution.get("ls6oc1_rerun_executed", False)),
        "publish_execution_still_blocked": bool(ls6s_validation.get("publish_execution_still_blocked", False)),
        "next_phase": {
            "phase": "LS-6U",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "requires_execution_runner_boundary_preflight": True,
            "requires_final_execute_command": True,
            "publish_execution_still_blocked": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6T Manual Publish Execute-Now Confirmation Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- confirmation_status: {result['confirmation_status']}",
        f"- execute_now_confirmation_label: {result['execute_now_confirmation_label']}",
        f"- execute_now_confirmation_consumed: {result['execute_now_confirmation_consumed']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- manual_publish_allowed_by_this_phase: {result['manual_publish_allowed_by_this_phase']}",
        f"- manual_publish_execution_allowed_by_this_phase: {result['manual_publish_execution_allowed_by_this_phase']}",
        f"- manual_publish_executed: {result['manual_publish_executed']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    template_doc = load_json(Path(args.template))
    conf_path = Path(args.confirmation)
    conf_doc = load_json(conf_path) if conf_path.exists() else None

    ls6s_validation = load_json(Path(args.ls6s_validation_result))
    ls6s_preflight = load_json(Path(args.ls6s_final_preflight_result))
    ls6s_lock = load_json(Path(args.ls6s_final_preflight_lock))
    ls6r_ready = load_json(Path(args.ls6r_ready_result))
    ls6r_approval = load_json(Path(args.ls6r_approval_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6oc1_lock = load_json(Path(args.ls6oc1_consumption_lock))

    errors: list[str] = []
    validate_common(policy, ls6s_validation, ls6s_preflight, ls6s_lock, ls6r_ready, ls6r_approval, ls6p_lock, ls6oc1_lock, errors)

    source = template_doc if args.allow_template else (conf_doc or {})
    validate_target_post(source.get("target_post", {}), errors)

    if args.allow_template:
        validate_template(template_doc, errors)
        validate_current_phase_flags(template_doc.get("current_phase_execution", {}), errors)
        confirmation_data = template_doc.get("confirmation", {})
        current_phase_execution = template_doc.get("current_phase_execution", {})
        recorded = False
    else:
        require(conf_doc is not None, "confirmation file missing", errors)
        if conf_doc is None:
            confirmation_data = {}
            current_phase_execution = {}
            recorded = False
        else:
            validate_confirmation(conf_doc, errors)
            validate_current_phase_flags(conf_doc.get("current_phase_execution", {}), errors)
            confirmation_data = conf_doc.get("confirmation", {})
            current_phase_execution = conf_doc.get("current_phase_execution", {})
            recorded = True

    status = STATUS_NOT_READY
    if not errors:
        status = STATUS_TEMPLATE_READY if args.allow_template else STATUS_READY

    result = build_result(
        status=status,
        target=source.get("target_post", {}),
        confirmation=confirmation_data,
        current_phase_execution=current_phase_execution,
        ls6s_validation=ls6s_validation,
        ls6s_preflight=ls6s_preflight,
        ls6r_ready=ls6r_ready,
        ls6p_lock=ls6p_lock,
        ls6oc1_lock=ls6oc1_lock,
        recorded=recorded,
        errors=errors,
    )

    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
