#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_DIAGNOSED = "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_DIAGNOSED_NO_EXECUTION"
STATUS_MISMATCH = "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_MISMATCH_FOUND_NO_EXECUTION"
STATUS_FIXED = "LS6OC1_FIX_A_FINAL_EXECUTE_NOW_LABEL_COMPATIBILITY_FIXED_NO_EXECUTION"
EXPECTED_LABEL = "FINAL_EXECUTE_NOW_FOR_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_ONLY"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmation", default="exchange/human_review/start_ls6oc0_final_execute_now_confirmation.json")
    parser.add_argument("--ready-result", default="exchange/logs/start_ls6oc0_final_execute_now_confirmation_ready_result.json")
    parser.add_argument("--policy", default="config/start_ls6oc1_actual_wordpress_one_shot_draft_creation_execution_policy.json")
    parser.add_argument("--previous-run-result", default="exchange/logs/start_ls6oc1_actual_wordpress_one_shot_draft_creation_result.json")
    parser.add_argument("--runner-script", default="scripts/run_start_ls6oc1_actual_wordpress_one_shot_draft_creation.py")
    parser.add_argument("--output", default="exchange/logs/start_ls6oc1_fix_a_final_execute_now_label_compatibility_diagnosis_result.json")
    parser.add_argument("--report", default="reports/start_ls6oc1_fix_a_final_execute_now_label_compatibility_diagnosis_report.md")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_module(script_path: Path):
    spec = importlib.util.spec_from_file_location("ls6oc1_runner", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_result(
    *,
    status: str,
    confirmation_label: str,
    confirmation_decision_required_label: str,
    ready_result_confirmation_label: str,
    policy_required_previous_label: str,
    policy_actual_execution_required_label: str,
    label_compatibility_passed: bool,
    runner_patch_required: bool,
    runner_patch_applied: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6O-C-1-FIX-A",
        "status": status,
        "execution_mode": "NO_EXECUTION_DIAGNOSIS_ONLY",
        "production_status": "NO_GO",
        "expected_label": EXPECTED_LABEL,
        "confirmation_label": confirmation_label,
        "confirmation_decision_required_label": confirmation_decision_required_label,
        "ready_result_confirmation_label": ready_result_confirmation_label,
        "policy_required_previous_label": policy_required_previous_label,
        "policy_actual_execution_required_label": policy_actual_execution_required_label,
        "label_compatibility_passed": label_compatibility_passed,
        "runner_patch_required": runner_patch_required,
        "runner_patch_applied": runner_patch_applied,
        "credential_env_read_executed": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "actual_wordpress_go_consumed_by_this_phase": False,
        "final_execute_now_consumed_by_this_phase": False,
        "one_shot_actual_execution_lock_consumed_by_this_phase": False,
        "runtime_freeze_restored": False,
        "runner_executed": False,
        "actual_execution_executed": False,
        "next_action": "safe_to_retry_after_review" if label_compatibility_passed else "keep_no_execution_and_fix_inputs",
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6O-C-1 FIX-A Final Execute-Now Label Compatibility Diagnosis Report",
        "",
        f"- status: {result['status']}",
        f"- expected_label: {result['expected_label']}",
        f"- confirmation_label: {result['confirmation_label']}",
        f"- confirmation_decision_required_label: {result['confirmation_decision_required_label']}",
        f"- ready_result_confirmation_label: {result['ready_result_confirmation_label']}",
        f"- policy_required_previous_label: {result['policy_required_previous_label']}",
        f"- policy_actual_execution_required_label: {result['policy_actual_execution_required_label']}",
        f"- label_compatibility_passed: {result['label_compatibility_passed']}",
        f"- runner_patch_required: {result['runner_patch_required']}",
        f"- runner_patch_applied: {result['runner_patch_applied']}",
        f"- next_action: {result['next_action']}",
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
    errors: list[str] = []

    confirmation = load_json(Path(args.confirmation))
    ready_result = load_json(Path(args.ready_result))
    policy = load_json(Path(args.policy))
    previous_run_result = load_json(Path(args.previous_run_result))
    runner_module = load_module(Path(args.runner_script))

    confirmation_label = str(confirmation.get("confirmation_label") or "")
    confirmation_decision_required_label = str(
        confirmation.get("decision", {}).get("required_confirm_final_label") or ""
    )
    ready_result_confirmation_label = str(ready_result.get("confirmation_label") or "")
    policy_required_previous_label = str(
        policy.get("required_previous_phase", {}).get("ls6oc0", {}).get("required_label") or ""
    )
    policy_actual_execution_required_label = str(
        policy.get("actual_execution_policy", {}).get("required_confirm_final_label") or ""
    )

    require(confirmation_label == EXPECTED_LABEL, "confirmation.confirmation_label mismatch", errors)
    require(
        confirmation_decision_required_label == EXPECTED_LABEL,
        "confirmation.decision.required_confirm_final_label mismatch",
        errors,
    )
    require(ready_result_confirmation_label == EXPECTED_LABEL, "ready_result.confirmation_label mismatch", errors)
    require(policy_required_previous_label == EXPECTED_LABEL, "policy.required_previous_phase.ls6oc0.required_label mismatch", errors)
    require(
        policy_actual_execution_required_label == EXPECTED_LABEL,
        "policy.actual_execution_policy.required_confirm_final_label mismatch",
        errors,
    )
    require(
        previous_run_result.get("status") == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY",
        "previous_run_result.status must be LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY",
        errors,
    )
    require(previous_run_result.get("wordpress_api_call_executed") is False, "previous run shows wordpress_api_call_executed=true", errors)
    require(previous_run_result.get("credential_env_read_executed") is False, "previous run shows credential_env_read_executed=true", errors)
    require(previous_run_result.get("wordpress_write_executed") is False, "previous run shows wordpress_write_executed=true", errors)
    require(previous_run_result.get("actual_execution_executed") is False, "previous run shows actual_execution_executed=true", errors)
    require(previous_run_result.get("actual_wordpress_go_consumed_by_this_phase") is False, "previous run shows actual GO consumed", errors)
    require(previous_run_result.get("final_execute_now_consumed_by_this_phase") is False, "previous run shows final execute-now consumed", errors)
    require(previous_run_result.get("one_shot_actual_execution_lock_consumed_by_this_phase") is False, "previous run shows one-shot lock consumed", errors)

    runner_patch_required = (
        previous_run_result.get("status") == "LS6OC1_ACTUAL_WORDPRESS_ONE_SHOT_DRAFT_CREATION_NOT_READY"
        and any("label mismatch" in str(item) for item in previous_run_result.get("errors", []))
        and confirmation_label == EXPECTED_LABEL
        and confirmation_decision_required_label == EXPECTED_LABEL
        and ready_result_confirmation_label == EXPECTED_LABEL
        and policy_required_previous_label == EXPECTED_LABEL
        and policy_actual_execution_required_label == EXPECTED_LABEL
    )

    helper_errors = runner_module.validate_final_execute_now_labels(
        cli_label=f"  {EXPECTED_LABEL}  ",
        final_confirmation=confirmation,
        final_ready=ready_result,
        policy=policy,
    )
    mismatch_check = runner_module.validate_final_execute_now_labels(
        cli_label="WRONG_LABEL",
        final_confirmation=confirmation,
        final_ready=ready_result,
        policy=policy,
    )
    runner_patch_applied = helper_errors == [] and bool(mismatch_check)

    label_compatibility_passed = not errors and runner_patch_applied
    if errors:
        status = STATUS_MISMATCH
    elif runner_patch_required and runner_patch_applied:
        status = STATUS_FIXED
    else:
        status = STATUS_DIAGNOSED

    result = build_result(
        status=status,
        confirmation_label=confirmation_label,
        confirmation_decision_required_label=confirmation_decision_required_label,
        ready_result_confirmation_label=ready_result_confirmation_label,
        policy_required_previous_label=policy_required_previous_label,
        policy_actual_execution_required_label=policy_actual_execution_required_label,
        label_compatibility_passed=label_compatibility_passed,
        runner_patch_required=runner_patch_required,
        runner_patch_applied=runner_patch_applied,
        errors=errors,
    )
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())