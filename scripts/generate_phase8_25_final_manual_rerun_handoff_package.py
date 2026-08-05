#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_25_final_manual_rerun_handoff_package_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_25_final_manual_rerun_handoff_package.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_25_final_manual_rerun_handoff_package.md"

EVIDENCE_MAP = {
    "phase8_21": "phase8_21",
    "phase8_22": "phase8_22",
    "phase8_23": "phase8_23",
    "phase8_24": "phase8_24",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_final_manual_rerun_handoff_package(
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
    evidence_summary: list[dict[str, Any]] = []
    planned_manual_commands: list[str] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", planned_manual_commands, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("handoff_package_is_execution_permission") is not False:
        safety_violations.append("handoff_package_is_execution_permission must be false")
    if policy.get("commands_executed_in_this_phase") is not False:
        safety_violations.append("commands_executed_in_this_phase must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    root = _resolve_root(policy_path)
    phase_statuses: dict[str, str | None] = {}
    missing_evidence = False

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            errors.append(f"missing_evidence: {rel}")
            continue

        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})

        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")
        if status in {"FAIL", "ABORT"}:
            safety_violations.append(f"{rel} has terminal status: {status}")

        for frag, key in EVIDENCE_MAP.items():
            if frag in rel:
                phase_statuses[key] = status
                break

    ready_statuses = policy.get("ready_statuses", {})
    blocked_statuses = set(policy.get("blocked_statuses", []))

    all_ready = True
    for key, expected in ready_statuses.items():
        if phase_statuses.get(key) != expected:
            all_ready = False
            break

    if missing_evidence:
        status = "HANDOFF_NOT_READY"
    elif safety_violations:
        status = "ABORT"
    elif all_ready:
        planned_manual_commands = list(policy.get("planned_manual_commands_if_ready", []))
        status = "READY_FOR_OPERATOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"
    elif any((phase_statuses.get(key) in blocked_statuses) for key in EVIDENCE_MAP.values()):
        status = "HANDOFF_BLOCKED_CREDENTIALS_MISSING"
    else:
        status = "HANDOFF_NOT_READY"

    forbidden_patterns = list(policy.get("forbidden_command_patterns", []))
    for cmd in planned_manual_commands:
        for pattern in forbidden_patterns:
            if pattern in cmd:
                safety_violations.append(f"forbidden_command_pattern_detected: {pattern}")

    if safety_violations:
        status = "ABORT"

    result = _build_result(status, planned_manual_commands, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    planned_manual_commands: list[str],
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    is_ready = status == "READY_FOR_OPERATOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"
    return {
        "phase": "Phase 8-25",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "handoff_package_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "target_item_count": policy.get("target_item_count", 1),
        "planned_manual_commands": planned_manual_commands,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": (
            policy.get("allowed_next_step_if_ready") if is_ready else policy.get("allowed_next_step_if_blocked", "Keep NO_GO")
        ),
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-25 Final Manual Rerun Handoff Package",
        "",
        "## Purpose",
        "Generate final handoff package for manual rerun without executing commands.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Operator Decision",
            "- Operator decision is derived from Phase 8-24 evidence.",
            "",
            "## Credential Readiness",
            f"- status: {result.get('status')}",
            "",
            "## Planned Manual Commands",
        ]
    )
    for cmd in result.get("planned_manual_commands", []):
        lines.append(f"- {cmd}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- handoff_package_is_execution_permission: {result.get('handoff_package_is_execution_permission')}",
            f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
            f"- secret_values_written: {result.get('secret_values_written')}",
            "",
            "## Handoff Decision",
            f"- status: {result.get('status')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = generate_final_manual_rerun_handoff_package()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "READY_FOR_OPERATOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED",
        "HANDOFF_BLOCKED_CREDENTIALS_MISSING",
        "HANDOFF_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
