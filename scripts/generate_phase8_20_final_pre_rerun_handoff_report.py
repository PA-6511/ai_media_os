#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_20_final_pre_rerun_handoff_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_20_final_pre_rerun_handoff_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_20_final_pre_rerun_handoff_report.md"

_EVIDENCE_FRAGMENT_MAP = {
    "phase8_16": "phase8_16",
    "phase8_17": "phase8_17",
    "phase8_18": "phase8_18",
    "phase8_19": "phase8_19",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_final_pre_rerun_handoff_report(
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

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    if policy.get("handoff_is_execution_permission") is not False:
        safety_violations.append("handoff_is_execution_permission must be false")
    if policy.get("commands_executed_in_this_phase") is not False:
        safety_violations.append("commands_executed_in_this_phase must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    dangerous_ops = policy.get("dangerous_operations", {})
    for op_name, op_value in dangerous_ops.items():
        if op_value is not False:
            safety_violations.append(f"dangerous_operations.{op_name} must be false")

    if safety_violations:
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

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

        for fragment, key in _EVIDENCE_FRAGMENT_MAP.items():
            if fragment in rel:
                phase_statuses[key] = status
                break

    if safety_violations:
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    if missing_evidence:
        result = _build_result("NOT_READY_FOR_RERUN", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    ready_statuses = policy.get("ready_statuses", {})
    credential_missing_statuses = set(policy.get("credential_missing_statuses", []))

    all_ready = True
    for key, expected in ready_statuses.items():
        if phase_statuses.get(key) != expected:
            all_ready = False
            break

    if all_ready:
        status = "READY_FOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"
    elif any((phase_statuses.get(k) in credential_missing_statuses) for k in _EVIDENCE_FRAGMENT_MAP.values()):
        status = "NOT_READY_FOR_RERUN_CREDENTIALS_MISSING"
    else:
        status = "NOT_READY_FOR_RERUN"

    result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
    policy: dict[str, Any],
) -> dict[str, Any]:
    is_ready = status == "READY_FOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"
    return {
        "phase": "Phase 8-20",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "handoff_is_execution_permission": False,
        "commands_executed_in_this_phase": False,
        "target_item_count": policy.get("target_item_count", 1),
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
        "# Phase 8-20 Final Pre-Rerun Handoff Report",
        "",
        "## Purpose",
        "Issue the final lock/handoff decision before manual rerun.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Credential Readiness",
            "- Readiness is derived from Phase 8-16 and 8-17 results.",
            "",
            "## Command Plan Status",
            "- Command plan state is derived from Phase 8-19.",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- handoff_is_execution_permission: {result.get('handoff_is_execution_permission')}",
            f"- commands_executed_in_this_phase: {result.get('commands_executed_in_this_phase')}",
            f"- target_item_count: {result.get('target_item_count')}",
            "",
            "## Final Handoff Decision",
            f"- status: {result.get('status')}",
            "",
            "## Manual Next Step",
            f"- {result.get('allowed_next_step')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = generate_final_pre_rerun_handoff_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "READY_FOR_MANUAL_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED",
        "NOT_READY_FOR_RERUN_CREDENTIALS_MISSING",
        "NOT_READY_FOR_RERUN",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
