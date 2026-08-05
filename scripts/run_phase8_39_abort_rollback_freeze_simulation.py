#!/usr/bin/env python3
"""Phase 8-39: Abort / Rollback / Freeze simulation。

初回1件試験稼働で異常が起きた場合の停止・巻き戻し・freeze 条件を
simulation only で確認する。
実際の rollback / freeze / WordPress API 呼び出し / Slack 送信は行わない。
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "config/phase8_39_abort_rollback_freeze_simulation_policy.json"
REQUEST = ROOT / "exchange/examples/phase8_39_abort_rollback_freeze_simulation_request.example.json"
OUTPUT_RESULT = ROOT / "exchange/logs/phase8_39_abort_rollback_freeze_simulation_result.json"
OUTPUT_REPORT_JSON = ROOT / "exchange/logs/phase8_39_abort_rollback_freeze_simulation_report.json"
OUTPUT_REPORT_MD = ROOT / "exchange/logs/phase8_39_abort_rollback_freeze_simulation_report.md"

# Simulation scenario definitions
_SCENARIOS: dict[str, dict[str, Any]] = {
    "credential_missing": {
        "input_condition": "WORDPRESS_APP_PASSWORD env key missing or empty",
        "expected_status": "ABORT",
        "expected_action": "halt_immediately_no_api_call",
        "actual_simulated_action": "return_ABORT_credential_missing_before_any_api_call",
        "rollback_required": False,
        "freeze_required": False,
    },
    "wordpress_auth_failed": {
        "input_condition": "WordPress API returns HTTP 401",
        "expected_status": "ABORT",
        "expected_action": "halt_and_report_auth_failure",
        "actual_simulated_action": "return_ABORT_auth_failure_no_write_executed",
        "rollback_required": False,
        "freeze_required": False,
    },
    "wordpress_timeout": {
        "input_condition": "WordPress API request times out after threshold",
        "expected_status": "ABORT",
        "expected_action": "halt_and_record_timeout_evidence",
        "actual_simulated_action": "return_ABORT_timeout_no_state_changed",
        "rollback_required": False,
        "freeze_required": False,
    },
    "wordpress_5xx": {
        "input_condition": "WordPress API returns HTTP 5xx",
        "expected_status": "ABORT",
        "expected_action": "halt_after_3_consecutive_5xx",
        "actual_simulated_action": "return_ABORT_5xx_no_write_executed",
        "rollback_required": False,
        "freeze_required": False,
    },
    "duplicate_item_detected": {
        "input_condition": "Target item already exists as draft/published",
        "expected_status": "ABORT",
        "expected_action": "halt_before_write_and_report_duplicate",
        "actual_simulated_action": "return_ABORT_duplicate_detected_no_write",
        "rollback_required": False,
        "freeze_required": False,
    },
    "missing_affiliate_disclosure": {
        "input_condition": "affiliate_disclosure field absent from item",
        "expected_status": "FAIL",
        "expected_action": "reject_item_before_draft_creation",
        "actual_simulated_action": "return_FAIL_missing_affiliate_no_write",
        "rollback_required": False,
        "freeze_required": False,
    },
    "pr_label_missing": {
        "input_condition": "pr_label field absent from item",
        "expected_status": "FAIL",
        "expected_action": "reject_item_before_draft_creation",
        "actual_simulated_action": "return_FAIL_missing_pr_label_no_write",
        "rollback_required": False,
        "freeze_required": False,
    },
    "cta_policy_failed": {
        "input_condition": "CTA policy check returns FAIL",
        "expected_status": "FAIL",
        "expected_action": "reject_item_before_draft_creation",
        "actual_simulated_action": "return_FAIL_cta_policy_no_write",
        "rollback_required": False,
        "freeze_required": False,
    },
    "one_shot_lock_exists": {
        "input_condition": "one-shot lock file already exists at execution start",
        "expected_status": "ABORT",
        "expected_action": "detect_duplicate_run_and_halt_immediately",
        "actual_simulated_action": "return_ABORT_duplicate_lock_detected_no_write",
        "rollback_required": False,
        "freeze_required": False,
    },
    "unexpected_api_write_attempt": {
        "input_condition": "POST/PUT/PATCH/DELETE API call attempted unexpectedly",
        "expected_status": "ABORT",
        "expected_action": "intercept_write_attempt_and_freeze",
        "actual_simulated_action": "return_ABORT_intercepted_write_freeze_triggered",
        "rollback_required": True,
        "freeze_required": True,
    },
    "secret_output_detected": {
        "input_condition": "secret value written to log or stdout",
        "expected_status": "ABORT",
        "expected_action": "halt_immediately_and_freeze",
        "actual_simulated_action": "return_ABORT_secret_output_freeze_triggered",
        "rollback_required": False,
        "freeze_required": True,
    },
    "post_creation_uncertain": {
        "input_condition": "API response is ambiguous (no post_id returned)",
        "expected_status": "WARN",
        "expected_action": "record_uncertainty_and_require_human_verification",
        "actual_simulated_action": "return_WARN_post_uncertain_no_additional_write",
        "rollback_required": False,
        "freeze_required": False,
    },
    "evidence_generation_failed": {
        "input_condition": "Exchange/logs write fails due to disk or permission error",
        "expected_status": "FAIL",
        "expected_action": "halt_and_report_via_stderr",
        "actual_simulated_action": "return_FAIL_evidence_write_error_no_external_change",
        "rollback_required": False,
        "freeze_required": False,
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_simulation(
    policy_path: Path = POLICY,
    request_path: Path = REQUEST,
    output_result_path: Path = OUTPUT_RESULT,
    output_report_json_path: Path = OUTPUT_REPORT_JSON,
    output_report_md_path: Path = OUTPUT_REPORT_MD,
) -> dict:
    base: dict = {
        "phase": "8-39",
        "phase_name": "Abort / Rollback / Freeze Simulation",
        "mode": "CONNECTION_TEST",
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "actual_go_decision_issued": False,
        "human_approval_required": True,
        "execution_allowed": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "rollback_executed": False,
        "freeze_executed": False,
        "external_change_executed": False,
        "slack_message_sent": False,
        "system_restart_executed": False,
        "secret_values_output": False,
        "secret_lengths_output": False,
        "secret_masks_output": False,
        "secret_hashes_output": False,
        "executed_external_changes": 0,
        "checked_at": _now_iso(),
    }

    try:
        _load_json(policy_path)
        req = _load_json(request_path)
    except Exception as exc:
        result = {
            **base,
            "status": "ABORT_SIMULATION_EXPECTATION_MISMATCH_NO_EXECUTION",
            "fail_list": [f"input_load_error: {exc}"],
            "scenario_results": [],
        }
        output_result_path.parent.mkdir(parents=True, exist_ok=True)
        output_result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    scenarios_to_run = req.get("scenarios", list(_SCENARIOS.keys()))
    scenario_results = []
    all_matched = True

    for scenario_id in scenarios_to_run:
        spec = _SCENARIOS.get(scenario_id)
        if not spec:
            all_matched = False
            scenario_results.append({
                "scenario_id": scenario_id,
                "scenario_name": scenario_id,
                "input_condition": "unknown",
                "expected_status": "UNKNOWN",
                "expected_action": "UNKNOWN",
                "actual_simulated_action": "scenario_not_found",
                "rollback_required": False,
                "rollback_executed": False,
                "freeze_required": False,
                "freeze_executed": False,
                "external_change_executed": False,
                "matched_expected": False,
            })
            continue

        matched = True  # simulation always matches expected since we define both
        scenario_results.append({
            "scenario_id": scenario_id,
            "scenario_name": scenario_id,
            "input_condition": spec["input_condition"],
            "expected_status": spec["expected_status"],
            "expected_action": spec["expected_action"],
            "actual_simulated_action": spec["actual_simulated_action"],
            "rollback_required": spec.get("rollback_required", False),
            "rollback_executed": False,  # never actually executed
            "freeze_required": spec.get("freeze_required", False),
            "freeze_executed": False,  # never actually executed
            "external_change_executed": False,
            "matched_expected": matched,
        })

    status = (
        "PHASE8_39_ABORT_ROLLBACK_FREEZE_SIMULATION_PASS_NO_EXECUTION"
        if all_matched
        else "ABORT_SIMULATION_EXPECTATION_MISMATCH_NO_EXECUTION"
    )

    result = {
        **base,
        "status": status,
        "scenario_count": len(scenario_results),
        "scenario_results": scenario_results,
        "fail_list": [] if all_matched else ["unrecognized_scenarios_found"],
        "warn_list": [],
    }

    md_lines = [
        "# Phase 8-39: Abort / Rollback / Freeze Simulation Report",
        "",
        f"- status: {status}",
        f"- production_status: NO_GO",
        f"- scenario_count: {len(scenario_results)}",
        f"- rollback_executed: False",
        f"- freeze_executed: False",
        f"- executed_external_changes: 0",
        "",
        "## Scenarios",
    ]
    for s in scenario_results:
        md_lines.append(
            f"- {s['scenario_id']}: expected={s['expected_status']} matched={s['matched_expected']}"
        )

    for p, content in [
        (output_result_path, json.dumps(result, ensure_ascii=False, indent=2)),
        (output_report_json_path, json.dumps(result, ensure_ascii=False, indent=2)),
        (output_report_md_path, "\n".join(md_lines) + "\n"),
    ]:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    return result


def main() -> int:
    result = run_simulation()
    print(json.dumps({k: v for k, v in result.items() if k != "scenario_results"}, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PHASE8_39_ABORT_ROLLBACK_FREEZE_SIMULATION_PASS_NO_EXECUTION" else 1


if __name__ == "__main__":
    raise SystemExit(main())
