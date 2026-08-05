#!/usr/bin/env python3
"""Validate SVC-5 daemon-reload preflight gate design (design-only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_svc_5_daemon_reload_preflight_gate_policy.json"
DEFAULT_RUNBOOK = ROOT / "docs/runbooks/phase8_svc_5_daemon_reload_preflight_gate_design.md"
DEFAULT_OUTPUT = ROOT / "exchange/logs/phase8_svc_5_daemon_reload_preflight_gate_design_result.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_daemon_reload_preflight_design(
    policy_path: Path = DEFAULT_POLICY,
    runbook_path: Path = DEFAULT_RUNBOOK,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    missing_sections: list[str] = []
    forbidden_hits: list[str] = []
    policy_violations: list[str] = []

    policy_path = Path(policy_path)
    runbook_path = Path(runbook_path)
    output_path = Path(output_path)

    if not policy_path.exists():
        errors.append(f"missing_policy: {policy_path}")
        result = _build_result("FAIL", missing_sections, forbidden_hits, policy_violations, errors, warnings, {})
        _write_result(output_path, result)
        return result

    if not runbook_path.exists():
        errors.append(f"missing_runbook: {runbook_path}")
        result = _build_result("FAIL", missing_sections, forbidden_hits, policy_violations, errors, warnings, {})
        _write_result(output_path, result)
        return result

    policy = _load_json(policy_path)
    runbook_text = runbook_path.read_text(encoding="utf-8")

    if policy.get("design_only") is not True:
        policy_violations.append("design_only must be true")

    for key, value in policy.get("activation_actions", {}).items():
        if value is not False:
            policy_violations.append(f"activation_actions.{key} must be false")

    for key, value in policy.get("execution_actions", {}).items():
        if value is not False:
            policy_violations.append(f"execution_actions.{key} must be false")

    for section in policy.get("required_runbook_sections", []):
        if section not in runbook_text:
            missing_sections.append(section)

    # For design docs, patterns may appear as prohibited bullets.
    # Abort only when explicit executable lines are present.
    for pattern in policy.get("forbidden_patterns", []):
        for line in runbook_text.splitlines():
            normalized = line.strip().lower()
            if not normalized:
                continue
            if pattern.lower() in normalized and not normalized.startswith("-"):
                if normalized.startswith("systemctl ") or normalized.startswith("curl ") or normalized.startswith("requests."):
                    forbidden_hits.append(f"runbook_executable:{line.strip()}")

    if forbidden_hits:
        status = "ABORT"
    elif errors or missing_sections or policy_violations:
        status = "FAIL"
    else:
        status = "PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK"

    result = _build_result(status, missing_sections, forbidden_hits, policy_violations, errors, warnings, policy)
    _write_result(output_path, result)
    return result


def _build_result(
    status: str,
    missing_sections: list[str],
    forbidden_hits: list[str],
    policy_violations: list[str],
    errors: list[str],
    warnings: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "8-SVC-5",
        "phase_name": "Daemon-Reload Preflight Gate Design",
        "status": status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "design_only": True,
        "daemon_reload_executed": False,
        "systemctl_enable_executed": False,
        "systemctl_start_executed": False,
        "systemctl_restart_executed": False,
        "credential_env_created": False,
        "secret_input_executed": False,
        "phase8_29_to_8_40_rerun_executed": False,
        "wordpress_api_call_attempted": False,
        "wordpress_draft_created": False,
        "wordpress_publish_executed": False,
        "missing_sections": missing_sections,
        "forbidden_hits": forbidden_hits,
        "policy_violations": policy_violations,
        "errors": errors,
        "warnings": warnings,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "SVC-6 daemon-reload execution checkpoint (no enable/start)",
        ),
        "checked_at": _now_iso(),
    }


def _write_result(output_path: Path, payload: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    result = validate_daemon_reload_preflight_design()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PASS_DESIGN_ONLY_DAEMON_RELOAD_PRECHECK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
