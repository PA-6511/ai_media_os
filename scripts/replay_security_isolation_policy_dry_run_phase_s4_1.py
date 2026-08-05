#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


CONFIG_PATH = ROOT / "config" / "security_isolation_policy_dry_run_validation_phase_s4_1.json"
BATCH_PATH = ROOT / "exchange" / "examples" / "security_isolation_policy_phase_s4_1_request_batch.example.json"
S4_OVERALL_PATH = ROOT / "exchange" / "logs" / "security_phase_s4_overall_result.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_isolation_policy_dry_run_phase_s4_1_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("json object required")
    return data


def _evaluate_request(request: dict[str, Any]) -> tuple[str, bool, bool, list[str]]:
    source = str(request.get("source_block_ai", ""))
    target = str(request.get("target", ""))
    action = str(request.get("requested_action", ""))
    reasons: list[str] = []

    if source == "unknown_block_ai":
        return "RECOMMEND_ISOLATION", True, True, ["unknown_block_ai_default_deny"]
    if source in {"adult_or_risky_experiment_ai", "restricted_block_ai"} and target == "production_core_ai":
        return "BLOCK_ROUTE", True, True, ["restricted_route_to_production_core_blocked"]
    if source == "experimental_block_ai" and target == "production_core_ai":
        return "BLOCK_ROUTE", True, True, ["experimental_route_to_production_core_blocked"]
    if source == "ebook_affiliate_block_ai" and action == "wordpress_write":
        return "DENY_CAPABILITY", True, True, ["ebook_affiliate_wordpress_write_denied"]
    if source == "self_builder_ai" and action == "code_modify":
        return "DENY_CAPABILITY", True, True, ["self_builder_code_modify_denied"]
    if source == "core_ai" and action == "external_action":
        return "DENY_CAPABILITY", True, True, ["core_external_action_denied"]
    if source == "core_ai" and action == "proposal" and target in {"generic_block_ai", "ebook_affiliate_block_ai", "self_builder_ai"}:
        return "ALLOW_PROPOSAL", False, True, ["core_proposal_route_allowed"]

    reasons.append("unmapped_request")
    return "RECOMMEND_ISOLATION", True, True, reasons


def replay_security_isolation_policy_dry_run_phase_s4_1(
    config_path: Path = CONFIG_PATH,
    batch_path: Path = BATCH_PATH,
    s4_overall_path: Path = S4_OVERALL_PATH,
    output_json_path: Path = OUTPUT_JSON_PATH,
    output_md_path: Path = OUTPUT_MD_PATH,
) -> dict[str, Any]:
    config = _load_json(Path(config_path))
    batch = _load_json(Path(batch_path))
    s4_overall = _load_json(Path(s4_overall_path))

    abort_reasons: list[str] = []
    fail_reasons: list[str] = []
    warnings: list[str] = []

    if config.get("execution") != "DRY_RUN":
        abort_reasons.append("config.execution must be DRY_RUN")
    if config.get("production_status") != "NO_GO":
        abort_reasons.append("config.production_status must be NO_GO")
    if config.get("phase_status") != "DESIGN_ONLY":
        fail_reasons.append("config.phase_status must be DESIGN_ONLY")
    if config.get("isolation_execution_allowed") is not False:
        abort_reasons.append("config.isolation_execution_allowed must be false")
    if config.get("isolation_executed") is not False:
        abort_reasons.append("config.isolation_executed must be false")
    if config.get("executor_action_allowed") is not False:
        abort_reasons.append("config.executor_action_allowed must be false")

    if s4_overall.get("final_status") != config.get("required_s4_overall_final_status"):
        fail_reasons.append("S-4 overall final_status mismatch")
    if s4_overall.get("execution") != config.get("required_s4_overall_execution"):
        fail_reasons.append("S-4 overall execution mismatch")
    if s4_overall.get("production_status") != config.get("required_s4_overall_production_status"):
        fail_reasons.append("S-4 overall production_status mismatch")
    if s4_overall.get("isolation_execution_allowed") is not config.get("required_s4_overall_isolation_execution_allowed"):
        fail_reasons.append("S-4 overall isolation_execution_allowed mismatch")
    if s4_overall.get("isolation_executed") is not config.get("required_s4_overall_isolation_executed"):
        fail_reasons.append("S-4 overall isolation_executed mismatch")
    if s4_overall.get("executor_action_allowed") is not config.get("required_s4_overall_executor_action_allowed"):
        fail_reasons.append("S-4 overall executor_action_allowed mismatch")

    actions = batch.get("actions", {})
    for key in [
        "isolation_executed",
        "network_policy_applied",
        "container_stop_executed",
        "process_kill_executed",
        "firewall_applied",
        "scheduler_stop_executed",
        "wordpress_write_executed",
        "external_api_call_executed",
        "state_change_executed",
    ]:
        if actions.get(key) is True:
            abort_reasons.append(f"batch.actions.{key} must be false")

    request_results: list[dict[str, Any]] = []
    matched_expected_count = 0
    mismatched_expected_count = 0
    isolation_recommendation_detected = False
    human_review_recommendation_detected = False

    requests = batch.get("requests", [])
    if not isinstance(requests, list):
        raise ValueError("requests must be list")

    for req in requests:
        if not isinstance(req, dict):
            raise ValueError("request must be object")
        actual_decision, isolation_recommendation, human_review_recommendation, reasons = _evaluate_request(req)
        expected_decision = str(req.get("expected_decision", ""))
        if actual_decision == expected_decision:
            matched_expected_count += 1
        else:
            mismatched_expected_count += 1

        isolation_recommendation_detected = isolation_recommendation_detected or isolation_recommendation
        human_review_recommendation_detected = human_review_recommendation_detected or human_review_recommendation

        request_results.append(
            {
                "request_id": req.get("request_id"),
                "source_block_ai": req.get("source_block_ai"),
                "target": req.get("target"),
                "requested_action": req.get("requested_action"),
                "expected_decision": expected_decision,
                "actual_decision": actual_decision,
                "isolation_recommendation": isolation_recommendation,
                "human_review_recommendation": human_review_recommendation,
                "reasons": reasons,
            }
        )

    request_count = len(requests)
    if request_count == 0:
        fail_reasons.append("requests must not be empty")

    if mismatched_expected_count > 0:
        fail_reasons.append("expected decision mismatch detected")

    if abort_reasons:
        replay_result = "ABORT"
    elif fail_reasons:
        replay_result = "FAIL"
    elif warnings:
        replay_result = "WARN"
    else:
        replay_result = "PASS"

    result = {
        "phase_id": "PHASE_S4_1",
        "phase_name": "isolation_policy_dry_run_validation",
        "phase_status": "DESIGN_ONLY",
        "replay_result": replay_result,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "isolation_recommendation_only": True,
        "isolation_execution_allowed": False,
        "isolation_executed": False,
        "executor_action_allowed": False,
        "request_count": request_count,
        "matched_expected_count": matched_expected_count,
        "mismatched_expected_count": mismatched_expected_count,
        "request_results": request_results,
        "isolation_recommendation_detected": isolation_recommendation_detected,
        "human_review_recommendation_detected": human_review_recommendation_detected,
        "s4_design_verified": s4_overall.get("final_status") == "PASS_DESIGN_ONLY",
        "network_policy_applied": False,
        "container_stop_executed": False,
        "process_kill_executed": False,
        "firewall_applied": False,
        "scheduler_stop_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "state_change_executed": False,
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "timestamp": _now_iso(),
        "next_step": "phase_s4_2_isolation_event_simulation",
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Isolation Policy Dry-Run Phase S-4.1 Result",
        "",
        f"- replay_result: {result.get('replay_result')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- isolation_recommendation_only: {result.get('isolation_recommendation_only')}",
        f"- isolation_execution_allowed: {result.get('isolation_execution_allowed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- request_count: {result.get('request_count')}",
        f"- matched_expected_count: {result.get('matched_expected_count')}",
        f"- mismatched_expected_count: {result.get('mismatched_expected_count')}",
        f"- isolation_recommendation_detected: {result.get('isolation_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- s4_design_verified: {result.get('s4_design_verified')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## request_results",
    ]
    for row in request_results:
        lines.append(
            f"- {row.get('request_id')}: actual={row.get('actual_decision')} expected={row.get('expected_decision')} isolation_recommendation={row.get('isolation_recommendation')} human_review_recommendation={row.get('human_review_recommendation')}"
        )
    lines.extend(["", "## warnings"])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    lines.extend(["", "## fail_reasons"])
    lines.extend([f"- {item}" for item in fail_reasons] or ["- none"])
    lines.extend(["", "## abort_reasons"])
    lines.extend([f"- {item}" for item in abort_reasons] or ["- none"])
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    result = replay_security_isolation_policy_dry_run_phase_s4_1()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["replay_result"] in {"PASS", "WARN", "FAIL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
