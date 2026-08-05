#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_19_controlled_rerun_command_plan_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_19_controlled_rerun_command_plan.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_19_controlled_rerun_command_plan.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_controlled_rerun_command_plan(
    policy_path: Path = DEFAULT_POLICY,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    planned_commands: list[str] = []
    evidence_summary: list[dict[str, Any]] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", planned_commands, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("command_plan_is_execution_permission") is not False:
        safety_violations.append("command_plan_is_execution_permission must be false")
    if policy.get("commands_executed_in_this_phase") is not False:
        safety_violations.append("commands_executed_in_this_phase must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    if safety_violations:
        result = _build_result("ABORT", planned_commands, evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    root = _resolve_root(policy_path)
    transition_status = None
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            errors.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        transition_status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": transition_status})
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")

    if missing_evidence:
        status = "RERUN_COMMAND_PLAN_NOT_READY"
    elif transition_status in {"FAIL", "ABORT"}:
        safety_violations.append(f"phase8_18 has terminal status: {transition_status}")
        status = "ABORT"
    elif transition_status == policy.get("ready_status"):
        status = "RERUN_COMMAND_PLAN_READY_BUT_NOT_EXECUTED"
        planned_commands = list(policy.get("planned_commands_if_ready", []))
    elif transition_status in set(policy.get("not_ready_statuses", [])):
        status = "RERUN_COMMAND_PLAN_NOT_READY_CREDENTIALS_MISSING"
        planned_commands = list(policy.get("planned_commands_if_not_ready", []))
    else:
        status = "RERUN_COMMAND_PLAN_NOT_READY"
        warnings.append(f"unexpected_phase8_18_status: {transition_status}")

    forbidden_patterns = list(policy.get("forbidden_command_patterns", []))
    for cmd in planned_commands:
        for pattern in forbidden_patterns:
            if pattern in cmd:
                safety_violations.append(f"forbidden_command_pattern_detected: {pattern}")
        if "WORDPRESS_APP_PASSWORD=" in cmd:
            safety_violations.append("planned command contains WORDPRESS_APP_PASSWORD=")

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, planned_commands, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    planned_commands: list[str],
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    is_ready = status == "RERUN_COMMAND_PLAN_READY_BUT_NOT_EXECUTED"
    return {
        "phase": "Phase 8-19",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "command_plan_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "target_item_count": policy.get("target_item_count", 1),
        "planned_commands": planned_commands,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": (
            policy.get("allowed_next_step_if_ready")
            if is_ready
            else policy.get("allowed_next_step_if_not_ready", "Keep NO_GO")
        ),
        "checked_at": _now_iso(),
    }


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-19 Controlled Rerun Command Plan",
        "",
        "## Purpose",
        "Prepare rerun commands for Phase 8-6 to 8-10 without executing them.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Rerun Readiness",
            f"- status: {result.get('status')}",
            "",
            "## Planned Commands",
        ]
    )
    for cmd in result.get("planned_commands", []):
        lines.append(f"- {cmd}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- command_plan_is_execution_permission: {result.get('command_plan_is_execution_permission')}",
            f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
            f"- target_item_count: {result.get('target_item_count')}",
            "",
            "## Forbidden Command Check",
            "- forbidden command patterns are validated against planned_commands.",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = generate_controlled_rerun_command_plan()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "RERUN_COMMAND_PLAN_READY_BUT_NOT_EXECUTED",
        "RERUN_COMMAND_PLAN_NOT_READY_CREDENTIALS_MISSING",
        "RERUN_COMMAND_PLAN_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
