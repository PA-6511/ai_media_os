#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.security_phase_s3_common import now_iso


LOG_DIR = ROOT / "exchange" / "logs"
RESULT_FILES = [
    LOG_DIR / "security_observability_policy_phase_s3_validation_result.json",
    LOG_DIR / "security_scheduler_anomaly_detector_phase_s3_validation_result.json",
    LOG_DIR / "security_wordpress_write_observer_phase_s3_validation_result.json",
    LOG_DIR / "security_external_api_intent_observer_phase_s3_validation_result.json",
    LOG_DIR / "security_env_access_observer_phase_s3_validation_result.json",
    LOG_DIR / "security_process_anomaly_observer_phase_s3_validation_result.json",
]
OUTPUT_JSON = LOG_DIR / "security_phase_s3_overall_result.json"
OUTPUT_MD = LOG_DIR / "security_phase_s3_overall_result.md"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def generate_security_phase_s3_overall_result() -> dict:
    rows = []
    missing = []
    for path in RESULT_FILES:
        if not path.exists():
            missing.append(str(path.relative_to(ROOT)))
            continue
        rows.append(_load(path))

    statuses = [row.get("validator_result") for row in rows]
    any_abort = any(s == "ABORT" for s in statuses)
    any_fail = any(s == "FAIL" for s in statuses)
    any_warn = any(s == "WARN" for s in statuses)
    all_pass_or_warn = bool(rows) and all(s in {"PASS", "WARN"} for s in statuses)

    if any_abort:
        final_status = "ABORT"
    elif any_fail:
        final_status = "OBSERVABILITY_REVIEW_REQUIRED"
    elif all_pass_or_warn:
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "OBSERVABILITY_REVIEW_REQUIRED"

    freeze_recommendation_detected = any(bool(row.get("freeze_recommendation")) for row in rows)
    human_review_recommendation_detected = any(bool(row.get("human_review_recommendation")) for row in rows)

    result = {
        "phase_id": "PHASE_S3",
        "phase_name": "runtime_observability_detector_only",
        "final_status": final_status,
        "execution": "DRY_RUN",
        "production_status": "NO_GO",
        "human_approval_required": True,
        "detector_only": True,
        "recommendation_only": True,
        "executor_action_allowed": False,
        "any_abort_detected": any_abort,
        "any_fail_detected": any_fail,
        "any_warning_detected": any_warn,
        "all_validators_passed_or_warn_only": all_pass_or_warn,
        "freeze_recommendation_detected": freeze_recommendation_detected,
        "human_review_recommendation_detected": human_review_recommendation_detected,
        "state_change_executed": False,
        "freeze_executed": False,
        "revoke_executed": False,
        "isolation_executed": False,
        "wordpress_write_executed": False,
        "external_api_call_executed": False,
        "validator_results": [
            {
                "validator_name": row.get("validator_name"),
                "validator_result": row.get("validator_result"),
                "freeze_recommendation": bool(row.get("freeze_recommendation", False)),
                "human_review_recommendation": bool(row.get("human_review_recommendation", False)),
            }
            for row in rows
        ],
        "missing_results": missing,
        "timestamp": now_iso(),
        "next_step": "human_review_or_continue_observability_only",
    }
    return result


def _write(result: dict) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Security Phase S-3 Overall Result",
        "",
        f"- final_status: {result.get('final_status')}",
        f"- execution: {result.get('execution')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- detector_only: {result.get('detector_only')}",
        f"- recommendation_only: {result.get('recommendation_only')}",
        f"- executor_action_allowed: {result.get('executor_action_allowed')}",
        f"- any_abort_detected: {result.get('any_abort_detected')}",
        f"- any_fail_detected: {result.get('any_fail_detected')}",
        f"- any_warning_detected: {result.get('any_warning_detected')}",
        f"- all_validators_passed_or_warn_only: {result.get('all_validators_passed_or_warn_only')}",
        f"- freeze_recommendation_detected: {result.get('freeze_recommendation_detected')}",
        f"- human_review_recommendation_detected: {result.get('human_review_recommendation_detected')}",
        f"- state_change_executed: {result.get('state_change_executed')}",
        f"- freeze_executed: {result.get('freeze_executed')}",
        f"- revoke_executed: {result.get('revoke_executed')}",
        f"- isolation_executed: {result.get('isolation_executed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- external_api_call_executed: {result.get('external_api_call_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
        "",
        "## validator_results",
    ]
    for row in result.get("validator_results", []):
        lines.append(
            f"- {row.get('validator_name')}: {row.get('validator_result')} (freeze_recommendation={row.get('freeze_recommendation')}, human_review_recommendation={row.get('human_review_recommendation')})"
        )
    lines.extend(["", "## missing_results"])
    if result.get("missing_results"):
        for item in result["missing_results"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    result = generate_security_phase_s3_overall_result()
    _write(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["final_status"] in {"PASS_DRY_RUN_ONLY", "OBSERVABILITY_REVIEW_REQUIRED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
