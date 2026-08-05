#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_PASS = "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE"
STATUS_NOT_READY = "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY"
STATUS_NOT_READY_MISSING_GO = "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_NOT_READY_MISSING_ACTUAL_GO"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def parse_asin(content: str) -> str:
    marker = "amazon.co.jp/dp/"
    if marker not in content:
        return ""
    return content.split(marker, 1)[1].split("?")[0].split('"')[0]


def build_preflight_result(*, title: str, asin: str, post_status: str, max_items: int) -> dict[str, Any]:
    return {
        "phase": "LS-6O-B",
        "document_type": "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_RESULT",
        "status": "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE",
        "runner_final_preflight_passed": True,
        "actual_wordpress_go_ready": True,
        "actual_wordpress_go_consumed": False,
        "payload_ready": True,
        "payload_title": title,
        "payload_asin": asin,
        "payload_post_status": post_status,
        "max_items": max_items,
        "one_shot_actual_execution_lock_active": True,
        "one_shot_actual_execution_lock_consumed": False,
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
        "actual_wordpress_go_consumed_by_this_phase": False,
        "one_shot_actual_execution_lock_consumed_by_this_phase": False,
        "runtime_freeze_restored_by_this_phase": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "errors": [],
    }


def build_run_result(*, status: str, payload_ready: bool, title: str, asin: str, post_status: str, max_items: int, go_ready: bool, errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6O-B",
        "status": status,
        "execution_mode": "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY",
        "production_status": "NO_GO",
        "actual_wordpress_go_ready": go_ready,
        "actual_wordpress_go_consumed": False,
        "runner_final_preflight_passed": status == STATUS_PASS,
        "payload_ready": payload_ready,
        "payload_title": title,
        "payload_asin": asin,
        "payload_post_status": post_status,
        "max_items": max_items,
        "one_shot_actual_execution_lock_active": status == STATUS_PASS,
        "one_shot_actual_execution_lock_consumed": False,
        "runtime_freeze_active": status == STATUS_PASS,
        "runtime_freeze_applied": status == STATUS_PASS,
        "runtime_freeze_restored": False,
        "credential_presence_check_validated": status == STATUS_PASS,
        "actual_execution_allowed": False,
        "manual_publish_allowed": False,
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
        "actual_wordpress_go_consumed_by_this_phase": False,
        "one_shot_actual_execution_lock_consumed_by_this_phase": False,
        "runtime_freeze_restored_by_this_phase": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6O-C",
            "execution_allowed": False,
            "requires_ls6ob_runner_final_preflight_pass": True,
            "requires_final_human_execute_now": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6O-B Actual Execution Runner Final Preflight Gate Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- actual_wordpress_go_ready: {result['actual_wordpress_go_ready']}",
        f"- actual_wordpress_go_consumed: {result['actual_wordpress_go_consumed']}",
        f"- runner_final_preflight_passed: {result['runner_final_preflight_passed']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- max_items: {result['max_items']}",
        f"- one_shot_actual_execution_lock_active: {result['one_shot_actual_execution_lock_active']}",
        f"- one_shot_actual_execution_lock_consumed: {result['one_shot_actual_execution_lock_consumed']}",
        f"- runtime_freeze_active: {result['runtime_freeze_active']}",
        f"- runtime_freeze_applied: {result['runtime_freeze_applied']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_ls6ob_runner_final_preflight_pass: {result['next_phase']['requires_ls6ob_runner_final_preflight_pass']}",
        f"- requires_final_human_execute_now: {result['next_phase']['requires_final_human_execute_now']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6ob_actual_execution_runner_final_preflight_policy.json")
    parser.add_argument("--ls6oa-ready-result", default="exchange/logs/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_ready_result.json")
    parser.add_argument("--ls6oa-go", default="exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.json")
    parser.add_argument("--ls6n-run-result", default="exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_result.json")
    parser.add_argument("--ls6n-validation-result", default="exchange/logs/start_ls6n_one_shot_actual_execution_lock_and_final_preflight_gate_validation_result.json")
    parser.add_argument("--one-shot-lock", default="exchange/locks/start_ls6n_one_shot_actual_execution.lock.json")
    parser.add_argument("--final-execution-preflight", default="exchange/runtime/start_ls6n_final_execution_preflight_result.json")
    parser.add_argument("--ls6m-validation-result", default="exchange/logs/start_ls6m_credential_presence_check_and_runtime_freeze_apply_gate_validation_result.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--preflight-output", default="exchange/runtime/start_ls6ob_actual_execution_runner_final_preflight_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_result.json")
    parser.add_argument("--report", default="reports/start_ls6ob_actual_execution_runner_final_preflight_gate_report.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    missing_go = False

    policy = load_json(Path(args.policy))

    ls6oa_ready_path = Path(args.ls6oa_ready_result)
    ls6oa_go_path = Path(args.ls6oa_go)
    if not ls6oa_ready_path.exists() or not ls6oa_go_path.exists():
        missing_go = True
    ls6oa_ready = load_json(ls6oa_ready_path) if ls6oa_ready_path.exists() else {}
    ls6oa_go = load_json(ls6oa_go_path) if ls6oa_go_path.exists() else {}

    ls6n_run = load_json(Path(args.ls6n_run_result))
    ls6n_validation = load_json(Path(args.ls6n_validation_result))
    one_shot_lock = load_json(Path(args.one_shot_lock))
    final_execution_preflight = load_json(Path(args.final_execution_preflight))
    ls6m_validation = load_json(Path(args.ls6m_validation_result))
    credential_presence = load_json(Path(args.credential_presence_result))
    runtime_freeze_state = load_json(Path(args.runtime_freeze_state))
    runtime_freeze_lock = load_json(Path(args.runtime_freeze_lock))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    require(policy.get("phase") == "LS-6O-B", "policy phase must be LS-6O-B", errors)
    require(policy.get("execution_mode") == "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    require(ls6oa_ready.get("status") == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION", "LS-6O-A ready status mismatch", errors)
    require(ls6oa_go.get("go_label") == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY", "LS-6O-A go label mismatch", errors)
    require(ls6oa_go.get("go_status") == "HUMAN_CONFIRMED_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO", "LS-6O-A go status mismatch", errors)
    require(ls6oa_go.get("decision", {}).get("actual_wordpress_go_consumed") is False, "LS-6O-A go consumed must be false", errors)

    require(ls6n_run.get("status") == "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_PASSED_NO_WORDPRESS_WRITE", "LS-6N run status mismatch", errors)
    require(ls6n_validation.get("status") == "LS6N_ONE_SHOT_ACTUAL_EXECUTION_LOCK_AND_FINAL_PREFLIGHT_GATE_VALIDATED_NO_WORDPRESS_WRITE", "LS-6N validation status mismatch", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_active") is True, "one-shot lock active must be true", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_consumed") is False, "one-shot lock consumed must be false", errors)
    require(final_execution_preflight.get("status") == "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE", "LS-6N final execution preflight status mismatch", errors)

    require(ls6m_validation.get("status") == "LS6M_CREDENTIAL_PRESENCE_CHECK_AND_RUNTIME_FREEZE_APPLY_GATE_VALIDATED_NO_WORDPRESS_WRITE", "LS-6M validation status mismatch", errors)
    require(credential_presence.get("required_keys_present") is True, "credential presence required_keys_present must be true", errors)
    require(credential_presence.get("required_keys_non_empty") is True, "credential presence required_keys_non_empty must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_active") is True, "runtime_freeze_active must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_applied") is True, "runtime_freeze_applied must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_restored") is False, "runtime_freeze_restored must be false", errors)

    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I validation status mismatch", errors)

    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(int(ls6c_payload.get("max_items", 0)) == 1, "LS-6C max_items must be 1", errors)

    payload_ready = ls6c_payload.get("payload_ready") is True
    title = ""
    asin = ""
    post_status = ""
    max_items = int(ls6c_payload.get("max_items", 1))
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

    if missing_go:
        status = STATUS_NOT_READY_MISSING_GO
        if not ls6oa_ready_path.exists():
            errors.append("LS-6O-A ready result is missing")
        if not ls6oa_go_path.exists():
            errors.append("LS-6O-A actual go file is missing")
    elif errors:
        status = STATUS_NOT_READY
    else:
        status = STATUS_PASS

    if status == STATUS_PASS:
        preflight_result = build_preflight_result(
            title=title,
            asin=asin,
            post_status=post_status,
            max_items=max_items,
        )
        write_json(Path(args.preflight_output), preflight_result)

    run_result = build_run_result(
        status=status,
        payload_ready=payload_ready,
        title=title,
        asin=asin,
        post_status=post_status,
        max_items=max_items,
        go_ready=(status == STATUS_PASS),
        errors=errors,
    )
    write_json(Path(args.output), run_result)
    write_report(run_result, Path(args.report))
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
