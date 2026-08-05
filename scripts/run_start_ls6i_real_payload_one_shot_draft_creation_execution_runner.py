#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def parse_asin(content: str) -> str:
    marker = "amazon.co.jp/dp/"
    if marker not in content:
        return ""
    return content.split(marker, 1)[1].split("?")[0].split('"')[0]


def build_result(status: str, errors: list[str], *, payload_ready: bool, payload_title: str, payload_asin: str, payload_post_status: str, payload_content_format: str, actual_execute_approval: bool, execute_approval_label: str, final_preflight_passed: bool, runner_plan_ready: bool, runner_execution_allowed: bool) -> dict[str, Any]:
    return {
        "phase": "LS-6I",
        "status": status,
        "execution_mode": "RUNNER_IMPLEMENTATION_PREFLIGHT_ONLY",
        "production_status": "NO_GO",
        "runner_implemented": True,
        "runner_preflight_passed": status == "LS6I_EXECUTION_RUNNER_IMPLEMENTED_PREFLIGHT_ONLY_NO_EXECUTION",
        "actual_execution_allowed": False,
        "separate_execution_command_required": True,
        "execute_option_implemented": False,
        "payload_ready": payload_ready,
        "payload_title": payload_title,
        "payload_asin": payload_asin,
        "payload_post_status": payload_post_status,
        "payload_content_format": payload_content_format,
        "max_items": 1,
        "actual_execute_approval": actual_execute_approval,
        "execute_approval_label": execute_approval_label,
        "execute_approval_label_consumed": False,
        "final_preflight_passed": final_preflight_passed,
        "runner_plan_ready": runner_plan_ready,
        "runner_execution_allowed": runner_execution_allowed,
        "wordpress_api_call_allowed_by_this_phase": False,
        "wordpress_write_allowed_by_this_phase": False,
        "wordpress_draft_creation_allowed_by_this_phase": False,
        "credential_env_read_allowed_by_this_phase": False,
        "manual_publish_allowed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "future_schedule_executed": False,
        "delete_executed": False,
        "credential_env_read_executed": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "approval_token_consumed": False,
        "approval_label_consumed": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "ls6b_rerun_executed": False,
        "next_phase": {
            "phase": "LS-6J",
            "execution_allowed": False,
            "requires_separate_execution_command": True,
            "requires_ls6i_runner_preflight_pass": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6I Real Payload One-shot Draft Creation Execution Runner Preflight Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- runner_implemented: {result['runner_implemented']}",
        f"- runner_preflight_passed: {result['runner_preflight_passed']}",
        f"- actual_execution_allowed: {result['actual_execution_allowed']}",
        f"- separate_execution_command_required: {result['separate_execution_command_required']}",
        f"- execute_option_implemented: {result['execute_option_implemented']}",
        f"- payload_ready: {result['payload_ready']}",
        f"- payload_title: {result['payload_title']}",
        f"- payload_asin: {result['payload_asin']}",
        f"- payload_post_status: {result['payload_post_status']}",
        f"- max_items: {result['max_items']}",
        f"- actual_execute_approval: {result['actual_execute_approval']}",
        f"- execute_approval_label: {result['execute_approval_label']}",
        f"- execute_approval_label_consumed: {result['execute_approval_label_consumed']}",
        f"- final_preflight_passed: {result['final_preflight_passed']}",
        f"- runner_plan_ready: {result['runner_plan_ready']}",
        f"- runner_execution_allowed: {result['runner_execution_allowed']}",
        f"- wordpress_api_call_allowed_by_this_phase: {result['wordpress_api_call_allowed_by_this_phase']}",
        f"- wordpress_write_allowed_by_this_phase: {result['wordpress_write_allowed_by_this_phase']}",
        f"- wordpress_draft_creation_allowed_by_this_phase: {result['wordpress_draft_creation_allowed_by_this_phase']}",
        f"- credential_env_read_allowed_by_this_phase: {result['credential_env_read_allowed_by_this_phase']}",
        f"- manual_publish_allowed: {result['manual_publish_allowed']}",
        f"- wordpress_api_call_executed: {result['wordpress_api_call_executed']}",
        f"- wordpress_write_executed: {result['wordpress_write_executed']}",
        f"- wordpress_draft_creation_executed: {result['wordpress_draft_creation_executed']}",
        f"- post119_update_executed: {result['post119_update_executed']}",
        f"- publish_executed: {result['publish_executed']}",
        f"- credential_env_read_executed: {result['credential_env_read_executed']}",
        f"- approval_token_consumed: {result['approval_token_consumed']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- execute_approval_label_consumed: {result['execute_approval_label_consumed']}",
        f"- runner_executed: {result['runner_executed']}",
        f"- actual_execution_executed: {result['actual_execution_executed']}",
        f"- ls6b_rerun_executed: {result['ls6b_rerun_executed']}",
        "",
        "## Next Phase",
        f"- phase: {result['next_phase']['phase']}",
        f"- execution_allowed: {result['next_phase']['execution_allowed']}",
        f"- requires_separate_execution_command: {result['next_phase']['requires_separate_execution_command']}",
        f"- requires_ls6i_runner_preflight_pass: {result['next_phase']['requires_ls6i_runner_preflight_pass']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend([f"- {e}" for e in result["errors"]])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_policy.json")
    parser.add_argument("--ls6h-approved-result", default="exchange/logs/start_ls6h_real_payload_one_shot_draft_creation_execute_approval_gate_approved_result.json")
    parser.add_argument("--ls6h-approval", default="exchange/human_review/start_ls6h_real_payload_one_shot_draft_creation_execute_approval.json")
    parser.add_argument("--ls6g-result", default="exchange/logs/start_ls6g_real_payload_one_shot_draft_creation_final_preflight_gate_result.json")
    parser.add_argument("--ls6f-runner-plan", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_plan.json")
    parser.add_argument("--ls6f-result", default="exchange/logs/start_ls6f_real_payload_one_shot_draft_runner_prep_result.json")
    parser.add_argument("--ls6c-payload", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    parser.add_argument("--ls6c-result", default="exchange/logs/start_ls6c_real_draft_payload_rebuild_dry_run_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_preflight_result.json")
    parser.add_argument("--report", default="reports/start_ls6i_real_payload_one_shot_draft_creation_execution_runner_preflight_report.md")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.execute:
        raise SystemExit("--execute is not supported in LS-6I preflight-only runner")

    errors: list[str] = []

    policy = load_json(Path(args.policy))
    ls6h_result = load_json(Path(args.ls6h_approved_result))
    ls6h_approval = load_json(Path(args.ls6h_approval))
    ls6g_result = load_json(Path(args.ls6g_result))
    ls6f_plan = load_json(Path(args.ls6f_runner_plan))
    ls6f_result = load_json(Path(args.ls6f_result))
    ls6c_payload = load_json(Path(args.ls6c_payload))
    ls6c_result = load_json(Path(args.ls6c_result))

    require(policy.get("phase") == "LS-6I", "policy phase must be LS-6I", errors)
    require(policy.get("execution_mode") == "RUNNER_IMPLEMENTATION_PREFLIGHT_ONLY", "policy execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_GO", "policy production_status mismatch", errors)

    require(ls6h_result.get("status") == "LS6H_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_APPROVED_NO_EXECUTION", "LS-6H status mismatch", errors)
    actual_execute_approval = ls6h_result.get("actual_execute_approval") is True
    require(actual_execute_approval, "LS-6H actual_execute_approval must be true", errors)
    execute_approval_label = str(ls6h_result.get("execute_approval_label", ""))
    require(execute_approval_label == "APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE_ONLY", "LS-6H execute_approval_label mismatch", errors)
    require(ls6h_result.get("execute_approval_label_consumed") is False, "LS-6H execute_approval_label_consumed must be false", errors)
    require(
        ls6h_approval.get("execute_approval_status") == "HUMAN_APPROVED_FOR_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_EXECUTE",
        "LS-6H approval execute_approval_status mismatch",
        errors,
    )

    require(ls6g_result.get("status") == "LS6G_REAL_PAYLOAD_ONE_SHOT_DRAFT_CREATION_FINAL_PREFLIGHT_PASSED_NO_EXECUTION", "LS-6G status mismatch", errors)
    final_preflight_passed = ls6g_result.get("final_preflight_passed") is True
    require(final_preflight_passed, "LS-6G final_preflight_passed must be true", errors)
    require(ls6g_result.get("execution_allowed") is False, "LS-6G execution_allowed must be false", errors)

    require(ls6f_plan.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F runner plan status mismatch", errors)
    require(ls6f_result.get("status") == "LS6F_REAL_PAYLOAD_ONE_SHOT_DRAFT_RUNNER_PREP_READY_NO_EXECUTION", "LS-6F result status mismatch", errors)
    runner_plan_ready = ls6f_plan.get("runner_plan_ready") is True and ls6f_result.get("runner_plan_ready") is True
    require(runner_plan_ready, "LS-6F runner_plan_ready must be true", errors)
    runner_execution_allowed = ls6f_plan.get("runner_execution_allowed") is True or ls6f_result.get("runner_execution_allowed") is True
    require(not runner_execution_allowed, "LS-6F runner_execution_allowed must be false", errors)
    require(ls6f_plan.get("runner_executed") is False, "LS-6F plan runner_executed must be false", errors)
    require(ls6f_result.get("runner_executed") is False, "LS-6F result runner_executed must be false", errors)

    require(ls6c_result.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILD_DRY_RUN_READY", "LS-6C result status mismatch", errors)
    require(ls6c_payload.get("status") == "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY", "LS-6C payload status mismatch", errors)
    payload_ready = ls6c_payload.get("payload_ready") is True
    require(payload_ready, "LS-6C payload_ready must be true", errors)
    require(ls6c_payload.get("payload_count") == 1, "LS-6C payload_count must be 1", errors)
    require(ls6c_payload.get("max_items") == 1, "LS-6C max_items must be 1", errors)

    payload_title = ""
    payload_asin = ""
    payload_post_status = ""
    payload_content_format = ""
    payloads = ls6c_payload.get("payloads")
    require(isinstance(payloads, list) and len(payloads) == 1, "LS-6C payloads must contain one item", errors)
    if isinstance(payloads, list) and len(payloads) == 1:
        item = payloads[0]
        payload_title = str(item.get("title", ""))
        payload_post_status = str(item.get("post_status", ""))
        payload_content_format = str(item.get("content_format", ""))
        payload_asin = parse_asin(str(item.get("content", "")))
        require(payload_title == "2.5次元の誘惑", "LS-6C title mismatch", errors)
        require(payload_asin == "B07X2G67B4", "LS-6C asin mismatch", errors)
        require(payload_post_status == "draft", "LS-6C post_status must be draft", errors)
        require(payload_content_format == "html", "LS-6C content_format must be html", errors)
        require(item.get("markdown_link_present") is False, "LS-6C markdown_link_present must be false", errors)
        require(item.get("html_link_present") is True, "LS-6C html_link_present must be true", errors)
        require(item.get("sample_content_detected") is False, "LS-6C sample_content_detected must be false", errors)

    status = "LS6I_EXECUTION_RUNNER_IMPLEMENTED_PREFLIGHT_ONLY_NO_EXECUTION" if not errors else "LS6I_EXECUTION_RUNNER_IMPLEMENTATION_PREFLIGHT_NOT_READY"
    result = build_result(
        status,
        errors,
        payload_ready=payload_ready,
        payload_title=payload_title,
        payload_asin=payload_asin,
        payload_post_status=payload_post_status,
        payload_content_format=payload_content_format,
        actual_execute_approval=actual_execute_approval,
        execute_approval_label=execute_approval_label,
        final_preflight_passed=final_preflight_passed,
        runner_plan_ready=runner_plan_ready,
        runner_execution_allowed=False,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
