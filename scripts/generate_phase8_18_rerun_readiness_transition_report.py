#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_18_rerun_readiness_transition_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_18_rerun_readiness_transition_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_18_rerun_readiness_transition_report.md"

_EVIDENCE_FRAGMENT_MAP = {
    "phase8_16": "phase8_16",
    "phase8_17": "phase8_17",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_rerun_readiness_transition_report(
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

    if policy.get("transition_is_execution_permission") is not False:
        safety_violations.append("transition_is_execution_permission must be false")
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

        for fragment, key in _EVIDENCE_FRAGMENT_MAP.items():
            if fragment in rel:
                phase_statuses[key] = status
                break

        if status in {"FAIL", "ABORT"}:
            safety_violations.append(f"{rel} has terminal status: {status}")

    if safety_violations:
        result = _build_result("ABORT", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    if missing_evidence:
        result = _build_result("RERUN_SEQUENCE_NOT_READY", evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    ready_statuses = policy.get("ready_statuses", {})
    not_ready_statuses = set(policy.get("not_ready_statuses", []))

    phase8_16_status = phase_statuses.get("phase8_16")
    phase8_17_status = phase_statuses.get("phase8_17")

    if (
        phase8_16_status == ready_statuses.get("phase8_16")
        and phase8_17_status == ready_statuses.get("phase8_17")
    ):
        status = "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED"
    elif phase8_16_status in not_ready_statuses or phase8_17_status in not_ready_statuses:
        status = "RERUN_SEQUENCE_NOT_READY_CREDENTIALS_MISSING"
    else:
        status = "RERUN_SEQUENCE_NOT_READY"

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
    is_ready = status == "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED"
    return {
        "phase": "Phase 8-18",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "transition_is_execution_permission": False,
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
        "# Phase 8-18 Rerun Readiness Transition Report",
        "",
        "## Purpose",
        "Integrate Phase 8-16 and 8-17 to determine rerun transition readiness.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Credential Readiness",
            "- Transition is based on operator confirmation and env presence checks.",
            "",
            "## Transition Decision",
            f"- status: {result.get('status')}",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- transition_is_execution_permission: {result.get('transition_is_execution_permission')}",
            f"- target_item_count: {result.get('target_item_count')}",
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
    result = generate_rerun_readiness_transition_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "READY_FOR_RERUN_SEQUENCE_BUT_NOT_EXECUTED",
        "RERUN_SEQUENCE_NOT_READY_CREDENTIALS_MISSING",
        "RERUN_SEQUENCE_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
