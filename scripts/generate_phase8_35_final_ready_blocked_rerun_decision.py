#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_35_final_ready_blocked_rerun_decision_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_35_final_ready_blocked_rerun_decision.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_35_final_ready_blocked_rerun_decision.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_final_ready_blocked_rerun_decision(
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
        result = _build_result(
            "ABORT", planned_manual_commands, evidence_summary, errors, warnings, safety_violations, {}
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    for flag in [
        "decision_is_execution_permission",
        "commands_executed_in_this_phase",
        "phase8_6_to_8_10_executed",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
        "auto_post",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"{flag} must be false")

    root = _resolve_root(policy_path)
    statuses: dict[str, str | None] = {
        "phase8_31": None,
        "phase8_32": None,
        "phase8_33": None,
        "phase8_34": None,
    }
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
            safety_violations.append(f"evidence_terminal_status: {rel}={status}")

        for key in statuses:
            if key in rel:
                statuses[key] = status
                break

    ready_statuses = policy.get("ready_statuses", {})
    blocked_statuses = set(policy.get("blocked_statuses", []))
    all_ready = True
    for key, expected in ready_statuses.items():
        if statuses.get(key) != expected:
            all_ready = False
            break

    if missing_evidence:
        status = "RERUN_DECISION_NOT_READY"
    elif safety_violations:
        status = "ABORT"
    elif all_ready:
        planned_manual_commands = list(policy.get("planned_manual_commands_if_ready", []))
        status = "READY_FOR_EXISTING_PHASE8_6_TO_8_10_MANUAL_RERUN_BUT_NOT_EXECUTED"
    elif any((v in blocked_statuses) for v in statuses.values()):
        status = "BLOCKED_CREDENTIALS_MISSING"
    else:
        status = "RERUN_DECISION_NOT_READY"

    for cmd in planned_manual_commands:
        for pattern in policy.get("forbidden_command_patterns", []):
            if pattern in cmd:
                safety_violations.append(f"forbidden_command_pattern_detected: {pattern}")

    if safety_violations:
        status = "ABORT"

    result = _build_result(
        status, planned_manual_commands, evidence_summary, errors, warnings, safety_violations, policy
    )
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
    if status == "READY_FOR_EXISTING_PHASE8_6_TO_8_10_MANUAL_RERUN_BUT_NOT_EXECUTED":
        allowed_next_step = policy.get("allowed_next_step_if_ready", "")
    elif status == "BLOCKED_CREDENTIALS_MISSING":
        allowed_next_step = policy.get("allowed_next_step_if_blocked", "")
    else:
        allowed_next_step = policy.get("allowed_next_step_if_blocked", "")

    return {
        "phase": "Phase 8-35",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "decision_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "phase8_6_to_8_10_executed": False,
        "target_item_count": policy.get("target_item_count", 1),
        "planned_manual_commands": planned_manual_commands,
        "secret_values_written": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": allowed_next_step,
        "checked_at": _now_iso(),
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-35 Final READY/BLOCKED Rerun Decision",
        "",
        "## Purpose",
        "Issue final READY/BLOCKED decision before any manual rerun, without execution.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend([
        "",
        "## Credential Readiness",
        "- Derived from Phase 8-32 and Phase 8-33 statuses.",
        "",
        "## One-Time Lock Status",
        "- Derived from Phase 8-34 lock package status.",
        "",
        "## Planned Manual Commands",
    ])
    for cmd in result.get("planned_manual_commands", []):
        lines.append(f"- {cmd}")
    if not result.get("planned_manual_commands"):
        lines.append("- none")

    lines.extend([
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- decision_is_execution_permission: {result.get('decision_is_execution_permission')}",
        f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
        f"- phase8_6_to_8_10_executed: {result.get('phase8_6_to_8_10_executed')}",
        f"- secret_values_written: {result.get('secret_values_written')}",
        "",
        "## Final Decision",
        f"- status: {result.get('status')}",
        "",
        "## Final Judgment",
        f"- {result.get('status')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ])
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def main() -> int:
    result = generate_final_ready_blocked_rerun_decision()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "READY_FOR_EXISTING_PHASE8_6_TO_8_10_MANUAL_RERUN_BUT_NOT_EXECUTED",
        "BLOCKED_CREDENTIALS_MISSING",
        "RERUN_DECISION_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())