#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError


STATUS_EXECUTED = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTED_ONE_SHOT_DRAFT_ONLY"
STATUS_NOT_READY = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"
STATUS_NOT_READY_MISSING_FINAL = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_FINAL_EXECUTE_NOW"
STATUS_NOT_READY_MISSING_EXECUTE = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY_MISSING_EXECUTE_NOW_FLAG"
STATUS_FAILED = "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED"

REQUIRED_FINAL_LABEL = "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_asin(content: str) -> str:
    marker = "amazon.co.jp/dp/"
    if marker not in content:
        return ""
    return content.split(marker, 1)[1].split("?")[0].split('"')[0]


def extract_payload(ls6c_payload: dict[str, Any], errors: list[str]) -> tuple[str, str, str, int, str]:
    payloads = ls6c_payload.get("payloads", [])
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)
    max_items = int(ls6c_payload.get("max_items", 0))
    require(max_items == 1, "max_items must be 1", errors)
    require(ls6c_payload.get("payload_count") == 1, "payload_count must be 1", errors)

    title = ""
    asin = ""
    post_status = ""
    content = ""
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        title = str(item.get("title", ""))
        post_status = str(item.get("post_status", ""))
        content = str(item.get("content", ""))
        asin = parse_asin(content)

    require(title == "2.5次元の誘惑", "payload title mismatch", errors)
    require(asin == "B07X2G67B4", "payload ASIN mismatch", errors)
    require(post_status == "draft", "post_status must be draft", errors)

    return title, asin, post_status, max_items, content


def safe_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def resolve_required_final_label(policy: dict[str, Any]) -> str:
    primary = safe_value(policy, "actual_execution_policy", "required_confirm_final_label")
    fallback = safe_value(policy, "required_previous_phase", "ls6oc0", "required_label")
    if isinstance(primary, str) and primary:
        return primary
    if isinstance(fallback, str) and fallback:
        return fallback
    return REQUIRED_FINAL_LABEL


def get_confirmation_label(final_confirmation: dict[str, Any]) -> str:
    label = (
        safe_value(final_confirmation, "confirmation_label")
        or safe_value(final_confirmation, "confirm_final_label")
        or safe_value(final_confirmation, "final_execute_now_label")
        or safe_value(final_confirmation, "label")
        or ""
    )
    return str(label)


def build_label_mismatch_error(
    *,
    cli_label: str,
    confirmation_label: str,
    confirmation_decision_required_label: str,
    ready_result_confirmation_label: str,
    policy_required_label: str,
) -> str:
    return (
        "final execute-now confirmation label mismatch:\n"
        f"cli_label={cli_label}\n"
        f"confirmation_label={confirmation_label}\n"
        f"confirmation_decision_required_label={confirmation_decision_required_label}\n"
        f"ready_result_confirmation_label={ready_result_confirmation_label}\n"
        f"policy_required_label={policy_required_label}"
    )


def validate_final_execute_now_labels(
    *,
    cli_label: str,
    final_confirmation: dict[str, Any],
    final_ready: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    canonical_required_label = resolve_required_final_label(policy)
    confirmation_label = get_confirmation_label(final_confirmation)
    confirmation_decision_required_label = str(
        safe_value(final_confirmation, "decision", "required_confirm_final_label") or ""
    )
    ready_result_confirmation_label = str(final_ready.get("confirmation_label") or "")
    cli_label_stripped = cli_label.strip()

    if (
        cli_label_stripped == canonical_required_label
        and confirmation_label == canonical_required_label
        and confirmation_decision_required_label == canonical_required_label
        and ready_result_confirmation_label == canonical_required_label
    ):
        return []

    return [
        build_label_mismatch_error(
            cli_label=cli_label_stripped,
            confirmation_label=confirmation_label,
            confirmation_decision_required_label=confirmation_decision_required_label,
            ready_result_confirmation_label=ready_result_confirmation_label,
            policy_required_label=canonical_required_label,
        )
    ]


def build_execution_result(
    *,
    status: str,
    title: str,
    asin: str,
    requested_status: str,
    returned_status: str,
    new_post_id: int,
    new_post_link: str,
    created_count: int,
    max_items: int,
    credential_env_read_executed: bool,
    wordpress_api_call_executed: bool,
    wordpress_write_executed: bool,
    wordpress_draft_creation_executed: bool,
    actual_wordpress_go_consumed_by_this_phase: bool,
    final_execute_now_consumed_by_this_phase: bool,
    one_shot_actual_execution_lock_consumed_by_this_phase: bool,
    runner_executed: bool,
    actual_execution_executed: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6O-C-1",
        "document_type": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_EXECUTION_RESULT",
        "status": status,
        "payload_title": title,
        "payload_asin": asin,
        "requested_post_status": requested_status,
        "returned_post_status": returned_status,
        "new_post_id": new_post_id,
        "new_post_link": new_post_link,
        "wordpress_api_call_executed": wordpress_api_call_executed,
        "wordpress_write_executed": wordpress_write_executed,
        "wordpress_draft_creation_executed": wordpress_draft_creation_executed,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "max_items": max_items,
        "created_count": created_count,
        "credential_env_read_executed": credential_env_read_executed,
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "runtime_freeze_active": True,
        "runtime_freeze_restored": False,
        "actual_wordpress_go_consumed_by_this_phase": actual_wordpress_go_consumed_by_this_phase,
        "final_execute_now_consumed_by_this_phase": final_execute_now_consumed_by_this_phase,
        "one_shot_actual_execution_lock_consumed_by_this_phase": one_shot_actual_execution_lock_consumed_by_this_phase,
        "runner_executed": runner_executed,
        "actual_execution_executed": actual_execution_executed,
        "errors": errors,
    }


def build_consumption_lock(*, new_post_id: int, title: str, asin: str) -> dict[str, Any]:
    return {
        "phase": "LS-6O-C-1",
        "document_type": "ACTUAL_EXECUTION_CONSUMPTION_LOCK",
        "status": "ACTUAL_EXECUTION_CONSUMED_ONE_SHOT_LOCKS",
        "locked": True,
        "rerun_allowed": False,
        "actual_wordpress_go_consumed": True,
        "final_execute_now_consumed": True,
        "one_shot_actual_execution_lock_consumed": True,
        "created_count": 1,
        "new_post_id": new_post_id,
        "payload_title": title,
        "payload_asin": asin,
        "post_status": "draft",
        "runtime_freeze_restored": False,
        "next_phase": {
            "phase": "LS-6P",
            "requires_post_id_verification": True,
            "requires_runtime_freeze_restore": True,
        },
    }


def build_run_result(
    *,
    status: str,
    production_status: str,
    execution_result: dict[str, Any] | None,
    errors: list[str],
) -> dict[str, Any]:
    created_count = int(execution_result.get("created_count", 0)) if execution_result else 0
    return {
        "phase": "LS-6O-C-1",
        "status": status,
        "execution_mode": "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONE_SHOT_ONLY",
        "production_status": production_status,
        "payload_title": execution_result.get("payload_title", "") if execution_result else "",
        "payload_asin": execution_result.get("payload_asin", "") if execution_result else "",
        "requested_post_status": execution_result.get("requested_post_status", "") if execution_result else "",
        "returned_post_status": execution_result.get("returned_post_status", "") if execution_result else "",
        "new_post_id": int(execution_result.get("new_post_id", 0)) if execution_result else 0,
        "new_post_link": execution_result.get("new_post_link", "") if execution_result else "",
        "created_count": created_count,
        "max_items": int(execution_result.get("max_items", 0)) if execution_result else 0,
        "credential_env_read_executed": bool(execution_result and execution_result.get("credential_env_read_executed")),
        "credential_value_output": False,
        "credential_value_persisted": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_output": False,
        "wordpress_api_call_executed": bool(execution_result and execution_result.get("wordpress_api_call_executed")),
        "wordpress_write_executed": bool(execution_result and execution_result.get("wordpress_write_executed")),
        "wordpress_draft_creation_executed": bool(execution_result and execution_result.get("wordpress_draft_creation_executed")),
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "actual_wordpress_go_consumed_by_this_phase": bool(execution_result and execution_result.get("actual_wordpress_go_consumed_by_this_phase")),
        "final_execute_now_consumed_by_this_phase": bool(execution_result and execution_result.get("final_execute_now_consumed_by_this_phase")),
        "one_shot_actual_execution_lock_consumed_by_this_phase": bool(execution_result and execution_result.get("one_shot_actual_execution_lock_consumed_by_this_phase")),
        "runtime_freeze_active": bool(execution_result and execution_result.get("runtime_freeze_active")),
        "runtime_freeze_restored": False,
        "runner_executed": bool(execution_result and execution_result.get("runner_executed")),
        "actual_execution_executed": bool(execution_result and execution_result.get("actual_execution_executed")),
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6P",
            "execution_allowed": False,
            "requires_post_id_verification": True,
            "requires_draft_status_verification": True,
            "requires_runtime_freeze_restore": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6O-C-1 Actual WordPress One-shot Draft Creation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- requested_post_status: {result['requested_post_status']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- new_post_id: {result['new_post_id']}",
        f"- new_post_link: {result['new_post_link']}",
        f"- created_count: {result['created_count']}",
        f"- max_items: {result['max_items']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- actual_wordpress_go_consumed_by_this_phase: {result['actual_wordpress_go_consumed_by_this_phase']}",
        f"- final_execute_now_consumed_by_this_phase: {result['final_execute_now_consumed_by_this_phase']}",
        f"- one_shot_actual_execution_lock_consumed_by_this_phase: {result['one_shot_actual_execution_lock_consumed_by_this_phase']}",
        f"- runtime_freeze_restored: {result['runtime_freeze_restored']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_policy.json")
    parser.add_argument("--final-execute-now-ready-result", default="exchange/logs/start_ls6oc0_final_execute_now_confirmation_ready_result.json")
    parser.add_argument("--final-execute-now-confirmation", default="exchange/human_review/start_ls6oc0_final_execute_now_confirmation.json")
    parser.add_argument("--ls6ob-preflight-result", default="exchange/runtime/start_ls6ob_actual_execution_runner_final_preflight_result.json")
    parser.add_argument("--ls6ob-run-result", default="exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_result.json")
    parser.add_argument("--ls6ob-validation-result", default="exchange/logs/start_ls6ob_actual_execution_runner_final_preflight_gate_validation_result.json")
    parser.add_argument("--ls6oa-ready-result", default="exchange/logs/start_ls6oa_actual_wordpress_one_shot_draft_creation_go_gate_ready_result.json")
    parser.add_argument("--ls6oa-go", default="exchange/human_review/start_ls6oa_actual_wordpress_one_shot_draft_creation_go.json")
    parser.add_argument("--one-shot-lock", default="exchange/locks/start_ls6n_one_shot_actual_execution.lock.json")
    parser.add_argument("--ls6n-final-preflight", default="exchange/runtime/start_ls6n_final_execution_preflight_result.json")
    parser.add_argument("--credential-presence-result", default="exchange/runtime/start_ls6m_credential_presence_check_result.json")
    parser.add_argument("--runtime-freeze-state", default="exchange/runtime/start_ls6m_runtime_freeze_active_state.json")
    parser.add_argument("--runtime-freeze-lock", default="exchange/locks/start_ls6m_runtime_freeze_active.lock.json")
    parser.add_argument("--ls6i-validation-result", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_validation_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--ls6b-lock", default="exchange/locks/start_ls6b_wordpress_one_shot_draft_creation.lock.json")
    parser.add_argument("--credential-env", default="/etc/ai-media-os/credential.env")
    parser.add_argument("--execution-output", default="exchange/runtime/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_result.json")
    parser.add_argument("--consumption-lock-output", default="exchange/locks/start_ls6oc1_actual_execution_consumption.lock.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--report", default="reports/start_ls6oc1_actual_wordpress_one_shot_draft_creation_report.md")
    parser.add_argument("--execute-now", action="store_true")
    parser.add_argument("--confirm-final-label", default="")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = load_json(Path(args.policy))

    final_ready_path = Path(args.final_execute_now_ready_result)
    final_confirmation_path = Path(args.final_execute_now_confirmation)

    if not final_ready_path.exists() or not final_confirmation_path.exists():
        run_result = build_run_result(
            status=STATUS_NOT_READY_MISSING_FINAL,
            production_status="NO_GO",
            execution_result=None,
            errors=["LS-6O-C-0 final execute-now confirmation is missing"],
        )
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    if not args.execute_now:
        run_result = build_run_result(
            status=STATUS_NOT_READY_MISSING_EXECUTE,
            production_status="NO_GO",
            execution_result=None,
            errors=["--execute-now is required for actual execution"],
        )
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    final_ready = load_json(final_ready_path)
    final_confirmation = load_json(final_confirmation_path)
    ls6ob_preflight = load_json(Path(args.ls6ob_preflight_result))
    ls6ob_run = load_json(Path(args.ls6ob_run_result))
    ls6ob_validation = load_json(Path(args.ls6ob_validation_result))
    ls6oa_ready = load_json(Path(args.ls6oa_ready_result))
    ls6oa_go = load_json(Path(args.ls6oa_go))
    one_shot_lock = load_json(Path(args.one_shot_lock))
    ls6n_final_preflight = load_json(Path(args.ls6n_final_preflight))
    credential_presence = load_json(Path(args.credential_presence_result))
    runtime_freeze_state = load_json(Path(args.runtime_freeze_state))
    runtime_freeze_lock = load_json(Path(args.runtime_freeze_lock))
    ls6i_validation = load_json(Path(args.ls6i_validation_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))
    ls6b_lock = load_json(Path(args.ls6b_lock))

    label_errors = validate_final_execute_now_labels(
        cli_label=args.confirm_final_label,
        final_confirmation=final_confirmation,
        final_ready=final_ready,
        policy=policy,
    )
    if label_errors:
        run_result = build_run_result(
            status=STATUS_NOT_READY,
            production_status="NO_GO",
            execution_result=None,
            errors=label_errors,
        )
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    require(policy.get("phase") == "LS-6O-C-1", "policy phase mismatch", errors)
    require(final_ready.get("status") == "LS6OC0_FINAL_EXECUTE_NOW_CONFIRMATION_READY_NO_EXECUTION", "LS-6O-C-0 ready status mismatch", errors)
    require(final_ready.get("confirmation_label") == resolve_required_final_label(policy), "LS-6O-C-0 ready confirmation_label mismatch", errors)
    require(get_confirmation_label(final_confirmation) == resolve_required_final_label(policy), "LS-6O-C-0 confirmation label mismatch", errors)
    require(
        safe_value(final_confirmation, "decision", "required_confirm_final_label") == resolve_required_final_label(policy),
        "LS-6O-C-0 confirmation decision required label mismatch",
        errors,
    )

    require(ls6ob_preflight.get("status") == "ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE", "LS-6O-B preflight status mismatch", errors)
    require(ls6ob_run.get("status") == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_PASSED_NO_WRITE", "LS-6O-B run status mismatch", errors)
    require(ls6ob_validation.get("status") == "LS6OB_ACTUAL_EXECUTION_RUNNER_FINAL_PREFLIGHT_VALIDATED_NO_WRITE", "LS-6O-B validation status mismatch", errors)

    require(ls6oa_ready.get("status") == "LS6OA_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_READY_NO_EXECUTION", "LS-6O-A status mismatch", errors)
    require(ls6oa_go.get("go_label") == "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_GO_ONLY", "LS-6O-A go_label mismatch", errors)
    require(safe_value(ls6oa_go, "decision", "actual_wordpress_go_consumed") is False, "actual GO already consumed", errors)

    require(one_shot_lock.get("one_shot_actual_execution_lock_active") is True, "one-shot lock active must be true", errors)
    require(one_shot_lock.get("one_shot_actual_execution_lock_consumed") is False, "one-shot lock consumed must be false", errors)
    require(ls6n_final_preflight.get("status") == "FINAL_EXECUTION_PREFLIGHT_PASSED_NO_WORDPRESS_WRITE", "LS-6N final preflight status mismatch", errors)

    require(credential_presence.get("required_keys_present") is True, "credential presence required_keys_present must be true", errors)
    require(credential_presence.get("required_keys_non_empty") is True, "credential presence required_keys_non_empty must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_active") is True, "runtime freeze active must be true", errors)
    require(runtime_freeze_state.get("runtime_freeze_restored") is False, "runtime freeze restored must be false", errors)
    require(runtime_freeze_lock.get("locked") is True, "runtime freeze lock must be true", errors)

    require(ls6i_validation.get("status") == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_AND_VALIDATED_PREFLIGHT_ONLY_NO_EXECUTION", "LS-6I validation status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6b_lock.get("rerun_allowed") is False, "LS-6B rerun_allowed must be false", errors)

    title, asin, requested_status, max_items, content = extract_payload(ls6c_payload, errors)

    if errors:
        execution_result = build_execution_result(
            status="ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY",
            title=title,
            asin=asin,
            requested_status=requested_status,
            returned_status="",
            new_post_id=0,
            new_post_link="",
            created_count=0,
            max_items=max_items if max_items > 0 else 1,
            credential_env_read_executed=False,
            wordpress_api_call_executed=False,
            wordpress_write_executed=False,
            wordpress_draft_creation_executed=False,
            actual_wordpress_go_consumed_by_this_phase=False,
            final_execute_now_consumed_by_this_phase=False,
            one_shot_actual_execution_lock_consumed_by_this_phase=False,
            runner_executed=False,
            actual_execution_executed=False,
            errors=errors,
        )
        run_result = build_run_result(
            status=STATUS_NOT_READY,
            production_status="NO_GO",
            execution_result=execution_result,
            errors=errors,
        )
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    credential_path = Path(args.credential_env)
    env = parse_env_file(credential_path)

    base_url = env.get("WORDPRESS_BASE_URL", "")
    username = env.get("WORDPRESS_USERNAME", "")
    app_password = env.get("WORDPRESS_APP_PASSWORD", "")

    credential_errors: list[str] = []
    require(bool(base_url), "WORDPRESS_BASE_URL missing", credential_errors)
    require(bool(username), "WORDPRESS_USERNAME missing", credential_errors)
    require(bool(app_password), "WORDPRESS_APP_PASSWORD missing", credential_errors)

    if credential_errors:
        execution_result = build_execution_result(
            status="ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED",
            title=title,
            asin=asin,
            requested_status=requested_status,
            returned_status="",
            new_post_id=0,
            new_post_link="",
            created_count=0,
            max_items=max_items,
            credential_env_read_executed=True,
            wordpress_api_call_executed=False,
            wordpress_write_executed=False,
            wordpress_draft_creation_executed=False,
            actual_wordpress_go_consumed_by_this_phase=False,
            final_execute_now_consumed_by_this_phase=False,
            one_shot_actual_execution_lock_consumed_by_this_phase=False,
            runner_executed=True,
            actual_execution_executed=True,
            errors=credential_errors,
        )
        write_json(Path(args.execution_output), execution_result)
        run_result = build_run_result(
            status=STATUS_FAILED,
            production_status="EXECUTION_FAILED",
            execution_result=execution_result,
            errors=credential_errors,
        )
        write_json(Path(args.output), run_result)
        write_report(run_result, Path(args.report))
        print(json.dumps(run_result, ensure_ascii=False, indent=2))
        return 0

    endpoint = base_url.rstrip("/") + "/wp-json/wp/v2/posts"
    body = {
        "title": title,
        "content": content,
        "status": "draft",
    }

    auth_token = base64.b64encode(f"{username}:{app_password}".encode("utf-8")).decode("ascii")
    req = request.Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_token}",
        },
        method="POST",
    )

    api_errors: list[str] = []
    response_payload: dict[str, Any] = {}

    try:
        with request.urlopen(req, timeout=30) as resp:
            status_code = int(getattr(resp, "status", 0) or 0)
            raw = resp.read().decode("utf-8")
            response_payload = json.loads(raw) if raw else {}
            if status_code not in (200, 201):
                api_errors.append(f"WordPress API returned unexpected status code: {status_code}")
    except HTTPError as exc:
        api_errors.append(f"WordPress API HTTPError: {exc.code}")
    except URLError as exc:
        api_errors.append(f"WordPress API URLError: {exc.reason}")
    except Exception as exc:  # pragma: no cover
        api_errors.append(f"WordPress API error: {exc.__class__.__name__}")

    returned_status = str(response_payload.get("status", ""))
    new_post_id_raw = response_payload.get("id", 0)
    new_post_link = str(response_payload.get("link", ""))

    try:
        new_post_id = int(new_post_id_raw)
    except (TypeError, ValueError):
        new_post_id = 0

    if returned_status != "draft":
        api_errors.append("WordPress returned post status is not draft")
    if new_post_id < 1:
        api_errors.append("WordPress returned invalid new_post_id")

    success = not api_errors

    execution_result = build_execution_result(
        status="ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATED_DRAFT_ONLY" if success else "ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED",
        title=title,
        asin=asin,
        requested_status="draft",
        returned_status=returned_status,
        new_post_id=new_post_id,
        new_post_link=new_post_link,
        created_count=1 if success else 0,
        max_items=1,
        credential_env_read_executed=True,
        wordpress_api_call_executed=True,
        wordpress_write_executed=True,
        wordpress_draft_creation_executed=True,
        actual_wordpress_go_consumed_by_this_phase=success,
        final_execute_now_consumed_by_this_phase=success,
        one_shot_actual_execution_lock_consumed_by_this_phase=success,
        runner_executed=True,
        actual_execution_executed=True,
        errors=api_errors,
    )
    write_json(Path(args.execution_output), execution_result)

    if success:
        consumption = build_consumption_lock(new_post_id=new_post_id, title=title, asin=asin)
        write_json(Path(args.consumption_lock_output), consumption)

    run_result = build_run_result(
        status=STATUS_EXECUTED if success else STATUS_FAILED,
        production_status="ONE_SHOT_DRAFT_CREATED" if success else "EXECUTION_FAILED",
        execution_result=execution_result,
        errors=api_errors,
    )

    write_json(Path(args.output), run_result)
    write_report(run_result, Path(args.report))
    print(json.dumps(run_result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
