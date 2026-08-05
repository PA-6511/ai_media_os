#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_PASS = "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_TEMPLATE_PASS_NO_ACTUAL_GO"
STATUS_NOT_READY = "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_NOT_READY"
STATUS_READY = "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION"
STATUS_GATE_NOT_READY = "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_GATE_NOT_READY"


REQUIRED_CHECKLIST_KEYS = [
    "ls6n_lock_and_final_preflight_pass_checked",
    "one_shot_actual_execution_lock_active_checked",
    "one_shot_actual_execution_lock_not_consumed_checked",
    "runtime_freeze_active_checked",
    "credential_presence_validated_checked",
    "target_payload_title_checked",
    "target_payload_asin_checked",
    "post_status_draft_checked",
    "max_items_one_checked",
    "no_publish_checked",
    "no_existing_post_update_checked",
    "no_post119_update_checked",
    "no_schedule_checked",
    "no_delete_checked",
    "single_execution_only_checked",
    "next_phase_still_no_write_checked",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_asin(content: str) -> str:
    marker = "amazon.co.jp/dp/"
    if marker not in content:
        return ""
    return content.split(marker, 1)[1].split("?")[0].split('"')[0]


def validate_policy(policy: dict[str, Any], errors: list[str]) -> None:
    require(policy.get("phase") == "LS-6O-A", "policy phase must be LS-6O-A", errors)
    require(policy.get("execution_mode") == "EXPLICIT_HUMAN_GO_GATE_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    go_policy = policy.get("explicit_human_go_policy", {})
    require(go_policy.get("actual_go_file_auto_create_allowed") is False, "actual_go_file_auto_create_allowed must be false", errors)
    require(go_policy.get("human_actual_execution_go_required") is True, "human_actual_execution_go_required must be true", errors)
    require(go_policy.get("actual_execution_allowed_by_this_phase") is False, "actual_execution_allowed_by_this_phase must be false", errors)
    require(go_policy.get("wordpress_api_call_allowed_by_this_phase") is False, "wordpress_api_call_allowed_by_this_phase must be false", errors)
    require(go_policy.get("wordpress_write_allowed_by_this_phase") is False, "wordpress_write_allowed_by_this_phase must be false", errors)
    require(go_policy.get("wordpress_draft_creation_allowed_by_this_phase") is False, "wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(go_policy.get("credential_env_read_allowed_by_this_phase") is False, "credential_env_read_allowed_by_this_phase must be false", errors)
    require(go_policy.get("one_shot_actual_execution_lock_consumed_by_this_phase") is False, "one_shot_actual_execution_lock_consumed_by_this_phase must be false", errors)

    safety = policy.get("current_phase_safety_flags", {})
    for key, value in safety.items():
        require(value is False, f"current_phase_safety_flags.{key} must be false", errors)


def validate_previous_chain(
    *,
    ls6n_run: dict[str, Any],
    ls6n_validation: dict[str, Any],
    one_shot_lock: dict[str, Any],
    final_preflight: dict[str, Any],
    ls6m_validation: dict[str, Any],
    credential_presence: dict[str, Any],
    runtime_state: dict[str, Any],
    runtime_lock: dict[str, Any],
    ls6l_ready: dict[str, Any],
    ls6j_ready: dict[str, Any],
    ls6i_validation: dict[str, Any],
    ls6c_payload: dict[str, Any],
    ls6c_result: dict[str, Any],
    ls6b_lock: dict[str, Any],
    errors: list[str],
) -> tuple[bool, str, str, str, int]:
    require(ls6n_run.get("status") == "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE", "LS-6N run status mismatch", errors)
    require(ls6n_validation.get("status") == "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_VALIDATED_NO_WORDPRESS_WRITE", "LS-6N validation status mismatch", errors)

    require(one_shot_lock.get("locked") is True, "one-shot lock locked must be true", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_created") is True, "one-shot lock created must be true", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_active") is True, "one-shot lock active must be true", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_consumed") is False, "one-shot lock consumed must be false", errors)
    require(one_shot_lock.get("rerun_allowed") is False, "one-shot lock rerun_allowed must be false", errors)

    require(final_preflight.get("status") == "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE", "final preflight status mismatch", errors)
    require(final_preflight.get("final_execution_preflight_passed") is True, "final_execution_preflight_passed must be true", errors)
    require(final_preflight.get("actual_execution_allowed") is False, "final preflight actual_execution_allowed must be false", errors)
    require(final_preflight.get("wordpress_write_allowed_by_this_phase") is False, "final preflight wordpress_write_allowed_by_this_phase must be false", errors)

    require(ls6m_validation.get("status") == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE", "LS-6M validation status mismatch", errors)
    require(credential_presence.get("required_keys_present") is True, "credential presence required_keys_present must be true", errors)
    require(credential_presence.get("required_keys_non_empty") is True, "credential presence required_keys_non_empty must be true", errors)
    require(runtime_state.get("runtime_freeze_active") is True, "runtime_freeze_active must be true", errors)
    require(runtime_state.get("runtime_freeze_applied") is True, "runtime_freeze_applied must be true", errors)
    require(runtime_state.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false", errors)
    require(runtime_lock.get("locked") is True, "runtime freeze lock locked must be true", errors)

    require(ls6l_ready.get("status") == "LS6L_RUNTIME_FREEZE_AND_CREDENTIAL_READ_BOUNDARY_FINAL_CONFIRMATION_READY_NO_EXECUTION", "LS-6L status mismatch", errors)
    require(ls6j_ready.get("status") == "LS6J_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_SEPARATE_EXECUTION_COMMAND_READY_NO_EXECUTION", "LS-6J status mismatch", errors)
    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I status mismatch", errors)

    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)

    payload_ready = ls6c_payload.get("payload_ready") is True
    require(payload_ready, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    max_items = int(ls6c_payload.get("max_items", 0))
    require(max_items == 1, "LS-6C max_items must be 1", errors)

    title = ""
    asin = ""
    post_status = ""
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        post_status = str(item.get("post_status", ""))
        asin = parse_asin(str(item.get("content", "")))
        require(title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(asin == "B07X2G67B4", "LS-6C asin mismatch", errors)
        require(post_status == "draft", "LS-6C post_status must be draft", errors)

    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B rerun_allowed must be false", errors)

    return payload_ready, title, asin, post_status, max_items


def validate_template(template: dict[str, Any], errors: list[str]) -> None:
    require(template.get("go_status") == "TEMPLATE_NOT_ACTUAL_GO", "template go_status mismatch", errors)
    require(template.get("go_label") == "NOT_GO_YET", "template go_label mismatch", errors)


def validate_actual_go(go: dict[str, Any], errors: list[str]) -> None:
    require(go.get("phase") == "LS-6O-A", "actual go phase mismatch", errors)
    require(go.get("go_type") == "HUMAN_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO", "actual go go_type mismatch", errors)
    require(go.get("go_status") == "HUMAN_CONFIRMED_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO", "actual go go_status mismatch", errors)
    require(go.get("go_label") == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY", "actual go go_label mismatch", errors)

    checklist = go.get("go_checklist", {})
    for key in REQUIRED_CHECKLIST_KEYS:
        require(checklist.get(key) in [True, "TRUE", "CHECKED", "checked"], f"actual go checklist {key} must be checked", errors)

    decision = go.get("decision", {})
    require(decision.get("human_actual_wordpress_one_shot_draft_creation_go_granted") is True, "actual go decision grant must be true", errors)
    require(decision.get("actual_wordpress_go_consumed") is False, "actual go consumed must be false", errors)
    require(decision.get("wordpress_write_allowed_by_this_phase") is False, "actual go decision wordpress_write_allowed_by_this_phase must be false", errors)
    require(decision.get("wordpress_draft_creation_allowed_by_this_phase") is False, "actual go decision wordpress_draft_creation_allowed_by_this_phase must be false", errors)
    require(decision.get("actual_execution_allowed_by_this_phase") is False, "actual go decision actual_execution_allowed_by_this_phase must be false", errors)
    require(decision.get("credential_env_read_allowed_by_this_phase") is False, "actual go decision credential_env_read_allowed_by_this_phase must be false", errors)
    require(decision.get("one_shot_actual_execution_lock_consumed_by_this_phase") is False, "actual go decision lock consumed by this phase must be false", errors)

    current = go.get("current_phase_execution", {})
    for key in [
        "credential_env_read_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "runtime_freeze_restored",
        "one_shot_actual_execution_lock_consumed",
        "runner_executed",
        "actual_execution_executed",
    ]:
        require(current.get(key) is False, f"actual go current_phase_execution.{key} must be false", errors)


def build_result(
    *,
    status: str,
    actual_wordpress_go: bool,
    payload_ready: bool,
    payload_title: str,
    payload_asin: str,
    payload_post_status: str,
    max_items: int,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6O-A",
        "status": status,
        "execution_mode": "EXPLICIT_HUMAN_GO_GATE_ONLY",
        "production_status": "NO_GO",
        "actual_wordpress_go": actual_wordpress_go,
        "actual_wordpress_go_consumed": False,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "max_items": max_items,
        "ls6n_lock_and_final_preflight_passed": True,
        "one_shot_actual_execution_lock_active": True,
        "one_shot_actual_execution_lock_consumed": False,
        "final_execution_preflight_passed": True,
        "runtime_freeze_active": True,
        "runtime_freeze_applied": True,
        "runtime_freeze_restored": False,
        "credential_presence_check_validated": True,
        "actual_execution_allowed": False,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "credential_env_read_allowed_by_this_phase": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "execute_approval_label_consumed": False,
        "separate_execution_command_consumed": False,
        "final_runtime_confirmation_consumed": False,
        "one_shot_actual_execution_lock_consumed_by_this_phase": False,
        "runtime_freeze_restored_by_this_phase": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6O-B",
            "execution_allowed": False,
            "requires_ls6oa_actual_go_ready": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6O-A Explicit Human GO Gate Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- actual_wordpress_go: {result['actual_wordpress_go']}",
        f"- actual_wordpress_go_consumed: {result['actual_wordpress_go_consumed']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- max_items: {result['max_items']}",
        f"- one_shot_actual_execution_lock_active: {result['one_shot_actual_execution_lock_active']}",
        f"- one_shot_actual_execution_lock_consumed: {result['one_shot_actual_execution_lock_consumed']}",
        f"- final_execution_preflight_passed: {result['final_execution_preflight_passed']}",
        f"- runtime_freeze_active: {result['runtime_freeze_active']}",
        f"- runtime_freeze_applied: {result['runtime_freeze_applied']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- credential_presence_check_validated: {result['credential_presence_check_validated']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_ls6oa_actual_go_ready: {result['next_phase']['requires_ls6oa_actual_go_ready']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.template.json")
    parser.add_argument("--go", default="exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.json")
    parser.add_argument("--ls6n-run-result", default="exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_result.json")
    parser.add_argument("--ls6n-validation-result", default="exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_validation_result.json")
    parser.add_argument("--one-shot-lock", default="exchange/locks/start_ls6n_one_shot_actual_execution.lock.json")
    parser.add_argument("--final-preflight-result", default="exchange/runtime/start_ls6n_final_execution_preflight_result.json")
    parser.add_argument("--ls6m-validation-result", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_validation_result.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--ls6l-ready-result", default="exchange/logs/start_ls6l_runtime_freeze_and_credential_read_boundary_final_confirmation_ready_result.json")
    parser.add_argument("--ls6j-ready-result", default="exchange/logs/start_ls6j_real_payload_one_shot_draft_creation_separate_execution_command_gate_ready_result.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_not_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_not_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    template = load_json(Path(args.template))
    ls6n_run = load_json(Path(args.ls6n_run_result))
    ls6n_validation = load_json(Path(args.ls6n_validation_result))
    one_shot_lock = load_json(Path(args.one_shot_lock))
    final_preflight = load_json(Path(args.final_preflight_result))
    ls6m_validation = load_json(Path(args.ls6m_validation_result))
    credential_presence = load_json(Path(args.credential_presence_result))
    runtime_state = load_json(Path(args.runtime_freeze_state))
    runtime_lock = load_json(Path(args.runtime_freeze_lock))
    ls6l_ready = load_json(Path(args.ls6l_ready_result))
    ls6j_ready = load_json(Path(args.ls6j_ready_result))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    errors: list[str] = []
    validate_policy(policy, errors)
    payload_ready, payload_title, payload_asin, payload_post_status, max_items = validate_previous_chain(
        ls6n_run=ls6n_run,
        ls6n_validation=ls6n_validation,
        one_shot_lock=one_shot_lock,
        final_preflight=final_preflight,
        ls6m_validation=ls6m_validation,
        credential_presence=credential_presence,
        runtime_state=runtime_state,
        runtime_lock=runtime_lock,
        ls6l_ready=ls6l_ready,
        ls6j_ready=ls6j_ready,
        ls6i_validation=ls6i_validation,
        ls6c_payload=ls6c_payload,
        ls6c_result=ls6c_result,
        ls6b_lock=ls6b_lock,
        errors=errors,
    )
    validate_template(template, errors)

    go_path = Path(args.go)
    actual_go = False

    if errors:
        status = STATUS_GATE_NOT_READY
    else:
        if go_path.exists():
            go_data = load_json(go_path)
            go_errors: list[str] = []
            validate_actual_go(go_data, go_errors)
            if go_errors:
                errors.extend(go_errors)
                status = STATUS_GATE_NOT_READY
            else:
                actual_go = True
                status = STATUS_READY
        else:
            status = STATUS_TEMPLATE_PASS if args.allow_template else STATUS_NOT_READY

    result = build_result(
        status=status,
        actual_wordpress_go=actual_go,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        max_items=max_items,
        errors=errors,
    )

    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
