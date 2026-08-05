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

from scripts.security_abort_conditions_shared_s2 import evaluate_shared_abort_conditions

CONFIG_PATH = ROOT / "config" / "security_emergency_revoke_phase_s2.json"
OUTPUT_JSON_PATH = ROOT / "exchange" / "logs" / "security_emergency_revoke_phase_s2_validation_result.json"
OUTPUT_MD_PATH = ROOT / "exchange" / "logs" / "security_emergency_revoke_phase_s2_validation_result.md"
OVERALL_JSON_PATH = ROOT / "exchange" / "logs" / "security_phase_s2_overall_result.json"
OVERALL_MD_PATH = ROOT / "exchange" / "logs" / "security_phase_s2_overall_result.md"

DEPENDENT_RESULTS = [
    ROOT / "exchange" / "logs" / "security_environment_isolation_phase_s2_validation_result.json",
    ROOT / "exchange" / "logs" / "security_read_only_policy_phase_s2_validation_result.json",
    ROOT / "exchange" / "logs" / "security_api_permission_map_phase_s2_validation_result.json",
    ROOT / "exchange" / "logs" / "security_emergency_revoke_phase_s2_validation_result.json",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def validate_security_emergency_revoke_phase_s2(data: dict[str, Any]) -> dict[str, Any]:
    warnings: list[str] = []
    fail_reasons: list[str] = []
    abort_reasons: list[str] = evaluate_shared_abort_conditions(data)

    if data.get("phase_id") != "PHASE_S2":
        fail_reasons.append("phase_id must be PHASE_S2")
    if data.get("status") != "DESIGN_ONLY":
        fail_reasons.append("status must be DESIGN_ONLY")
    if data.get("revoke_plan_status") != "DESIGN_ONLY":
        fail_reasons.append("revoke_plan_status must be DESIGN_ONLY")
    if data.get("execution") != "DRY_RUN":
        fail_reasons.append("execution must be DRY_RUN")
    if data.get("production_status") != "NO_GO":
        fail_reasons.append("production_status must be NO_GO")
    if data.get("human_approval_required") is not True:
        fail_reasons.append("human_approval_required must be true")

    revoke_targets = data.get("revoke_targets")
    if not isinstance(revoke_targets, dict):
        fail_reasons.append("revoke_targets must be object")
    else:
        for key in ["openai_api_key", "wordpress_app_password", "slack_webhook", "github_actions_secret"]:
            if revoke_targets.get(key) != "plan_only":
                fail_reasons.append(f"revoke_targets.{key} must be plan_only")

    revoke_actions = data.get("revoke_actions")
    if not isinstance(revoke_actions, dict):
        fail_reasons.append("revoke_actions must be object")
    else:
        for key in ["auto_revoke_execute", "auto_secret_rotation_execute", "external_api_call_execute"]:
            if revoke_actions.get(key) is True:
                abort_reasons.append(f"revoke_actions.{key}=true is prohibited")
            elif revoke_actions.get(key) is not False:
                fail_reasons.append(f"revoke_actions.{key} must be false")

    incident_trigger = data.get("incident_trigger")
    if not isinstance(incident_trigger, list):
        fail_reasons.append("incident_trigger must be list")
    else:
        required = {
            "token_leak_detected",
            "unauthorized_write_attempt",
            "suspicious_scheduler_loop",
            "unknown_unlock_token_detected",
        }
        missing = sorted([value for value in required if value not in incident_trigger])
        if missing:
            fail_reasons.append(f"incident_trigger missing values: {missing}")

    required_manual_steps = data.get("required_manual_steps")
    if not isinstance(required_manual_steps, list):
        fail_reasons.append("required_manual_steps must be list")
    else:
        required_steps = {"manual_approval_record", "revoke_checklist", "post_revoke_evidence"}
        missing_steps = sorted([value for value in required_steps if value not in required_manual_steps])
        if missing_steps:
            fail_reasons.append(f"required_manual_steps missing values: {missing_steps}")

    if abort_reasons:
        validator_result = "ABORT"
    elif fail_reasons:
        validator_result = "FAIL"
    elif warnings:
        validator_result = "WARN"
    else:
        validator_result = "PASS"

    result = {
        "phase_id": "PHASE_S2",
        "validator": "validate_security_emergency_revoke_phase_s2",
        "validator_result": validator_result,
        "phase_status": "PASS_DESIGN_ONLY" if validator_result in {"PASS", "WARN"} else "BLOCKED",
        "DRY_RUN": data.get("execution") == "DRY_RUN",
        "NO_GO": data.get("production_status") == "NO_GO",
        "production_status": data.get("production_status"),
        "wordpress_write_executed": bool(data.get("wordpress_write_executed", False)),
        "abort_reasons": abort_reasons,
        "fail_reasons": fail_reasons,
        "warnings": warnings,
        "timestamp": _now_iso(),
        "next_step": "generate_security_phase_s2_overall_result" if validator_result in {"PASS", "WARN"} else "manual_security_review",
    }
    return result


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Security Emergency Revoke Phase S-2 Validation",
        "",
        f"- validator_result: {result.get('validator_result')}",
        f"- phase_status: {result.get('phase_status')}",
        f"- DRY_RUN: {result.get('DRY_RUN')}",
        f"- NO_GO: {result.get('NO_GO')}",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- timestamp: {result.get('timestamp')}",
        f"- next_step: {result.get('next_step')}",
    ]
    for section in ["warnings", "fail_reasons", "abort_reasons"]:
        lines.extend(["", f"## {section}"])
        values = result.get(section, [])
        if values:
            for value in values:
                lines.append(f"- {value}")
        else:
            lines.append("- none")
    return "\n".join(lines) + "\n"


def _write_result(result: dict[str, Any]) -> None:
    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_MD_PATH.write_text(_build_markdown(result), encoding="utf-8")


def _write_overall_result() -> None:
    validator_results: list[dict[str, Any]] = []
    missing_logs: list[str] = []

    for path in DEPENDENT_RESULTS:
        if not path.exists():
            missing_logs.append(str(path.relative_to(ROOT)))
            continue
        validator_results.append(_load_json(path))

    statuses = [item.get("validator_result") for item in validator_results]
    any_abort = any(status == "ABORT" for status in statuses)
    all_pass_or_warn = bool(statuses) and all(status in {"PASS", "WARN"} for status in statuses)

    if any_abort:
        final_status = "BLOCKED"
    elif all_pass_or_warn:
        final_status = "PASS_DRY_RUN_ONLY"
    else:
        final_status = "BLOCKED"

    overall = {
        "phase_id": "PHASE_S2",
        "name": "security_phase_s2_overall_result",
        "validator_result": "PASS" if all_pass_or_warn and not any_abort else "FAIL",
        "phase_status": final_status,
        "all_validators_passed_or_warn_only": all_pass_or_warn,
        "any_abort_detected": any_abort,
        "final_status": final_status,
        "keep_freeze": True,
        "human_approval_required": True,
        "DRY_RUN": True,
        "NO_GO": True,
        "production_status": "NO_GO",
        "wordpress_write_executed": False,
        "missing_logs": missing_logs,
        "validators": [
            {
                "validator": item.get("validator"),
                "validator_result": item.get("validator_result"),
                "phase_status": item.get("phase_status"),
            }
            for item in validator_results
        ],
        "timestamp": _now_iso(),
        "next_step": "hold_no_go_and_prepare_s3_observability" if final_status == "PASS_DRY_RUN_ONLY" else "manual_security_review",
    }

    OVERALL_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERALL_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERALL_JSON_PATH.write_text(json.dumps(overall, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Security Phase S-2 Overall Result",
        "",
        f"- final_status: {overall.get('final_status')}",
        f"- all_validators_passed_or_warn_only: {overall.get('all_validators_passed_or_warn_only')}",
        f"- any_abort_detected: {overall.get('any_abort_detected')}",
        f"- keep_freeze: {overall.get('keep_freeze')}",
        f"- human_approval_required: {overall.get('human_approval_required')}",
        f"- DRY_RUN: {overall.get('DRY_RUN')}",
        f"- NO_GO: {overall.get('NO_GO')}",
        f"- production_status: {overall.get('production_status')}",
        f"- wordpress_write_executed: {overall.get('wordpress_write_executed')}",
        f"- timestamp: {overall.get('timestamp')}",
        f"- next_step: {overall.get('next_step')}",
        "",
        "## validators",
    ]
    for item in overall.get("validators", []):
        md_lines.append(
            f"- {item.get('validator')}: validator_result={item.get('validator_result')} phase_status={item.get('phase_status')}"
        )

    md_lines.extend(["", "## missing_logs"])
    if overall.get("missing_logs"):
        for path in overall["missing_logs"]:
            md_lines.append(f"- {path}")
    else:
        md_lines.append("- none")

    OVERALL_MD_PATH.write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def main() -> int:
    try:
        data = _load_json(CONFIG_PATH)
        result = validate_security_emergency_revoke_phase_s2(data)
    except Exception as exc:
        result = {
            "phase_id": "PHASE_S2",
            "validator": "validate_security_emergency_revoke_phase_s2",
            "validator_result": "ABORT",
            "phase_status": "BLOCKED",
            "DRY_RUN": True,
            "NO_GO": True,
            "production_status": "NO_GO",
            "wordpress_write_executed": False,
            "abort_reasons": [f"validator_exception: {exc}"],
            "fail_reasons": [],
            "warnings": [],
            "timestamp": _now_iso(),
            "next_step": "manual_security_review",
        }

    _write_result(result)
    _write_overall_result()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["validator_result"] in {"PASS", "WARN"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
