#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_15_rerun_handoff_report_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_15_rerun_handoff_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_15_rerun_handoff_report.md"

# Fragment → phase key in ready_statuses
_EVIDENCE_FRAGMENT_MAP = {
    "phase8_11": "phase8_11",
    "phase8_12": "phase8_12",
    "phase8_13": "phase8_13",
    "phase8_14": "phase8_14",
}

_ABORT_TERMINAL_STATUSES = {"FAIL", "ABORT"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_rerun_handoff_report(
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
        status = "ABORT"
        result = _build_result(status, evidence_summary, errors, warnings, safety_violations, {})
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    # Safety flags check
    if policy.get("handoff_is_execution_permission") is not False:
        safety_violations.append("handoff_is_execution_permission must be false")
    if policy.get("wordpress_api_call_allowed") is not False:
        safety_violations.append("wordpress_api_call_allowed must be false")
    if policy.get("wordpress_write_executed") is not False:
        safety_violations.append("wordpress_write_executed must be false")
    if policy.get("publish_allowed") is not False:
        safety_violations.append("publish_allowed must be false")

    # Dangerous operations check
    dangerous_ops = policy.get("dangerous_operations", {})
    for op_name, op_val in dangerous_ops.items():
        if op_val is not False:
            safety_violations.append(f"dangerous_operations.{op_name} must be false")

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    root = _resolve_root(policy_path)
    ready_statuses = policy.get("ready_statuses", {})
    not_ready_statuses = policy.get("not_ready_statuses", [])

    # Collect evidence statuses
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
        st = payload.get("status") or payload.get("overall_status")

        # Check for secret_values_written = true in evidence
        if payload.get("secret_values_written") is True:
            safety_violations.append(f"secret_values_written=true in {rel}")

        evidence_summary.append({"path": rel, "exists": True, "status": st})

        for fragment, key in _EVIDENCE_FRAGMENT_MAP.items():
            if fragment in rel:
                phase_statuses[key] = st
                break

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    if missing_evidence:
        status = "RERUN_HANDOFF_NOT_READY"
        result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    # Determine status
    # Check for ABORT/FAIL in any evidence
    for key, st in phase_statuses.items():
        if st in _ABORT_TERMINAL_STATUSES:
            safety_violations.append(f"{key} has terminal status: {st}")

    if safety_violations:
        status = "ABORT"
        result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
        _write_outputs(result, output_json_path, output_md_path)
        return result

    # Check for not-ready statuses (credentials/authorization missing)
    for key, st in phase_statuses.items():
        if st in not_ready_statuses:
            status = "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING"
            result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
            _write_outputs(result, output_json_path, output_md_path)
            return result

    # Check all ready statuses match
    all_ready = True
    for key, expected in ready_statuses.items():
        actual = phase_statuses.get(key)
        if actual != expected:
            errors.append(f"{key} must be {expected!r} but got {actual!r}")
            all_ready = False

    if all_ready:
        status = "READY_TO_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"
    else:
        status = "RERUN_HANDOFF_NOT_READY"

    result = _build_result(status, evidence_summary, errors, warnings, safety_violations, policy)
    _write_outputs(result, output_json_path, output_md_path)
    return result


def _build_result(
    status: str,
    evidence_summary: list,
    errors: list,
    warnings: list,
    safety_violations: list,
    policy: dict,
) -> dict[str, Any]:
    is_ready = status == "READY_TO_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED"
    return {
        "phase": "Phase 8-15",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "publish_allowed": False,
        "handoff_is_execution_permission": False,
        "secret_values_written": False,
        "target_item_count": policy.get("target_item_count", 1),
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": (
            policy.get("allowed_next_step_if_ready")
            if is_ready
            else policy.get(
                "allowed_next_step_if_not_ready",
                "Set credentials manually without exposing secrets, then rerun Phase 8-13",
            )
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
        "# Phase 8-15 Rerun Handoff Report",
        "",
        "## Purpose",
        "Summarise the readiness of Phase 8-11 to 8-14 for Phase 8-6 to 8-10 re-execution.",
        "This report is NOT execution permission.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- handoff_is_execution_permission: {result.get('handoff_is_execution_permission')}",
            f"- secret_values_written: {result.get('secret_values_written')}",
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
    result = generate_rerun_handoff_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "READY_TO_RERUN_PHASE8_6_TO_8_10_BUT_NOT_EXECUTED",
        "RERUN_HANDOFF_NOT_READY_CREDENTIALS_MISSING",
        "RERUN_HANDOFF_NOT_READY",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
