#!/usr/bin/env python3
"""Phase 8-SVC-2: Credential Ready route validator-only entrypoint.

This script runs report/validator scripts only.
It never calls WordPress APIs directly, never creates/publishes drafts,
and keeps NO_GO + DRY_RUN guardrails.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_JSON = ROOT / "exchange/logs/phase8_svc_2_credential_ready_route_no_execution_result.json"
OVERALL_REPORT_JSON = ROOT / "exchange/logs/phase8_36_to_8_40_trial_route_overall_report.json"
EXPECTED_OVERALL_STATUS = "PHASE8_36_TO_8_40_TRIAL_ROUTE_READY_FOR_FIRST_ONE_ITEM_TRIAL_NO_EXECUTION"

# validator/report only route (no execution script that performs WP write actions)
DEFAULT_COMMANDS = [
    ["scripts/generate_phase8_29_credential_readiness_recheck_no_secret_leak_gate_report.py"],
    ["scripts/validate_phase8_29_credential_readiness_recheck_no_secret_leak_gate.py"],
    ["scripts/generate_phase8_30_final_operator_rerun_handoff_report.py"],
    ["scripts/generate_phase8_30_final_preflight_before_single_controlled_draft_creation_report.py"],
    ["scripts/validate_phase8_30_final_preflight_before_single_controlled_draft_creation.py"],
    ["scripts/generate_phase8_31_human_execution_approval_validation_handoff_report.py"],
    ["scripts/validate_phase8_31_human_execution_approval_validation_handoff.py"],
    ["scripts/validate_phase8_31_secret_safe_credential_procedure.py"],
    ["scripts/generate_phase8_29_to_8_31_pre_execution_approval_pack_overall_report.py"],
    ["scripts/generate_phase8_35_final_pre_execution_confirmation_report.py"],
    ["scripts/validate_phase8_35_final_pre_execution_confirmation.py"],
    ["scripts/generate_phase8_35_final_ready_blocked_rerun_decision.py"],
    ["scripts/generate_phase8_36_one_shot_draft_creation_dry_run_handoff_report.py"],
    ["scripts/validate_phase8_36_one_shot_draft_creation_dry_run_handoff.py"],
    ["scripts/validate_phase8_37_credential_ready_revalidation.py"],
    ["scripts/generate_phase8_38_first_one_item_trial_preflight_report.py"],
    ["scripts/validate_phase8_38_first_one_item_trial_preflight.py"],
    ["scripts/generate_phase8_39_manual_rerun_command_bundle.py"],
    ["scripts/run_phase8_39_abort_rollback_freeze_simulation.py"],
    ["scripts/generate_phase8_40_post_rerun_branch_decision.py"],
    ["scripts/generate_phase8_36_to_8_40_trial_route_overall_report.py"],
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_command(script: str) -> dict:
    command = [sys.executable, script]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "script": script,
        "returncode": completed.returncode,
        "stdout_tail": "\n".join(completed.stdout.strip().splitlines()[-10:]),
        "stderr_tail": "\n".join(completed.stderr.strip().splitlines()[-10:]),
    }


def _read_overall_status(path: Path | None = None) -> str | None:
    if path is None:
        path = OVERALL_REPORT_JSON
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload.get("overall_status")


def run_route(
    commands: Iterable[list[str]] | None = None,
    output_json_path: Path = OUTPUT_JSON,
) -> dict:
    if commands is None:
        commands = DEFAULT_COMMANDS

    base = {
        "phase": "8-SVC-2",
        "phase_name": "validator-only no-execution entrypoint",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "publish_allowed": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
        "systemctl_edit_executed": False,
        "systemctl_restart_executed": False,
        "credential_env_created": False,
        "checked_at": _now_iso(),
    }

    step_results: list[dict] = []
    all_success = True

    for item in commands:
        script = item[0]
        result = _run_command(script)
        step_results.append(result)
        if result["returncode"] != 0:
            all_success = False

    overall_status = _read_overall_status()
    ready_reached = overall_status == EXPECTED_OVERALL_STATUS

    if all_success and ready_reached:
        status = "SVC2_VALIDATOR_ROUTE_PASS_READY_REACHED_NO_EXECUTION"
        next_step = "NEXT_STEP_SVC3_UNIT_FILE_PLACEMENT_DESIGN_ONLY"
    elif all_success:
        status = "SVC2_VALIDATOR_ROUTE_PASS_READY_NOT_REACHED_NO_EXECUTION"
        next_step = "NEXT_STEP_FIX_CREDENTIAL_READINESS_THEN_RERUN_SVC2"
    else:
        status = "SVC2_VALIDATOR_ROUTE_FAIL_SCRIPT_ERROR_NO_EXECUTION"
        next_step = "NEXT_STEP_FIX_FAILED_SCRIPT_AND_RERUN_SVC2"

    result = {
        **base,
        "status": status,
        "scripts_total": len(step_results),
        "scripts_success": sum(1 for r in step_results if r["returncode"] == 0),
        "scripts_failed": sum(1 for r in step_results if r["returncode"] != 0),
        "overall_report_status": overall_status,
        "expected_overall_report_status": EXPECTED_OVERALL_STATUS,
        "ready_reached": ready_reached,
        "step_results": step_results,
        "next_step": next_step,
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> int:
    result = run_route()
    summary = {
        "phase": result["phase"],
        "status": result["status"],
        "scripts_total": result["scripts_total"],
        "scripts_failed": result["scripts_failed"],
        "overall_report_status": result["overall_report_status"],
        "ready_reached": result["ready_reached"],
        "next_step": result["next_step"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result["scripts_failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
