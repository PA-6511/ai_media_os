#!/usr/bin/env python3
"""Generate Phase 7-5 VPS connection test completion report."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SOURCES = {
    "policy_validation_result": ROOT / "exchange/logs/phase7_1_vps_connection_policy_validation_result.json",
    "connectivity_check": ROOT / "exchange/logs/vps_connectivity_check.example.json",
    "stability_evaluation": ROOT / "exchange/logs/vps_connection_stability_evaluation_result.json",
    "failure_classification": ROOT / "exchange/logs/vps_connection_failure_classification_result.json",
}

DEFAULT_JSON_OUTPUT = ROOT / "exchange/logs/phase7_vps_connection_test_completion_report.json"
DEFAULT_MD_OUTPUT = ROOT / "exchange/logs/phase7_vps_connection_test_completion_report.md"


def _abort(reason: str) -> dict:
    return {
        "package_type": "phase7_vps_connection_test_completion_report_result",
        "phase": "Phase 7-5",
        "status": "ABORT",
        "reason": reason,
        "report_generated": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _derive_overall_status(stability_status: str) -> str:
    mapping = {
        "PASS_DRY_RUN_ONLY": "PASS_DRY_RUN_ONLY",
        "WARN_DRY_RUN_ONLY": "WARN_DRY_RUN_ONLY",
        "FAIL_DRY_RUN_ONLY": "FAIL_DRY_RUN_ONLY",
        "ABORT": "ABORT",
    }
    return mapping.get(stability_status, "ABORT")


def _derive_next_step(overall_status: str) -> str:
    if overall_status == "PASS_DRY_RUN_ONLY":
        return "Phase 7-6 REST API DRY_RUN design"
    if overall_status == "WARN_DRY_RUN_ONLY":
        return "Additional manual measurements"
    if overall_status == "FAIL_DRY_RUN_ONLY":
        return "Investigate VPS/SSH/network root cause"
    return "Immediate stop and human review"


def _validate_safety(connectivity: dict, stability: dict) -> str | None:
    if connectivity.get("secrets_exposed") is True:
        return "connectivity_check: secrets_exposed=true"
    if connectivity.get("remote_write_executed") is True:
        return "connectivity_check: remote_write_executed=true"
    if connectivity.get("remote_command_executed") is True:
        return "connectivity_check: remote_command_executed=true"
    if stability.get("overall_status") == "ABORT":
        return f"stability_evaluation: {stability.get('reason', 'ABORT detected')}"
    return None


def _build_markdown(report: dict) -> str:
    return f"""# Phase 7 VPS Connection Test Completion Report

## Summary

- overall_status: `{report['overall_status']}`
- production_status: `{report['production_status']}`
- allowed_next_step: `{report['allowed_next_step']}`
- human_review_required: `{report['human_review_required']}`

## Evidence

- policy_validation_result: `{report['policy_validation_result']}`
- connectivity_check: `{report['connectivity_check']}`
- stability_evaluation: `{report['stability_evaluation']}`
- failure_classification: `{report['failure_classification']}`

## Blocked Actions

{chr(10).join(f"- {item}" for item in report['blocked_actions'])}

## Decision

`{report['overall_status']}`

Created at: `{report['created_at']}`
"""


def generate_report(
    source_paths: dict | None = None,
    json_output: Path | None = None,
    md_output: Path | None = None,
) -> dict:
    source_paths = source_paths or DEFAULT_SOURCES
    json_output = Path(json_output or DEFAULT_JSON_OUTPUT)
    md_output = Path(md_output or DEFAULT_MD_OUTPUT)

    loaded = {}
    for key, path in source_paths.items():
        p = Path(path)
        if not p.exists():
            return _abort(f"required source not found: {p}")
        loaded[key] = _load_json(p)

    policy = loaded["policy_validation_result"]
    connectivity = loaded["connectivity_check"]
    stability = loaded["stability_evaluation"]
    failure = loaded["failure_classification"]

    if policy.get("status") != "PASS":
        return _abort("policy_validation_result must be PASS")

    safety_reason = _validate_safety(connectivity, stability)
    if safety_reason:
        overall_status = "ABORT"
    else:
        overall_status = _derive_overall_status(stability.get("overall_status"))

    report = {
        "package_type": "phase7_vps_connection_test_completion_report",
        "phase": "Phase 7-5",
        "policy_validation_result": policy.get("status"),
        "connectivity_check": connectivity.get("check_id"),
        "stability_evaluation": stability.get("overall_status"),
        "failure_classification": failure.get("classification", []),
        "production_status": "NO_GO",
        "allowed_next_step": _derive_next_step(overall_status),
        "blocked_actions": [
            "production execution",
            "wordpress posting",
            "external service write",
            "remote write",
            "remote command execution",
            "auto execute",
        ],
        "human_review_required": True,
        "overall_status": overall_status,
        "reason": safety_reason or "phase7 dry-run only verification completed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_output.write_text(_build_markdown(report), encoding="utf-8")

    return {
        "package_type": "phase7_vps_connection_test_completion_report_result",
        "phase": "Phase 7-5",
        "status": "PASS" if overall_status != "ABORT" else "ABORT",
        "overall_status": overall_status,
        "report_generated": True,
        "json_output": str(json_output),
        "md_output": str(md_output),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    result = generate_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())