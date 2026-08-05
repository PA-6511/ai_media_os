#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_16_draft_body_update_unlock_request_design_only_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_16_draft_body_update_unlock_request_design_only_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_16_draft_body_update_unlock_request_design_only_result.md"

FALSE_FLAGS = {
    "unlock_request_is_execution_permission": False,
    "wordpress_api_call_allowed": False,
    "wordpress_api_call_attempted": False,
    "wordpress_write_allowed": False,
    "wordpress_write_executed": False,
    "publish_allowed": False,
    "update_allowed": False,
    "delete_allowed": False,
    "export_allowed": False,
    "auto_post": False,
    "auto_update": False,
    "auto_delete": False,
    "auto_export": False,
    "gate_is_execution_permission": False,
    "systemctl_restart_allowed": False,
    "systemctl_daemon_reload_allowed": False,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _build_result(
    policy: dict[str, Any],
    status: str,
    phase8_15_status: str | None,
    evidence_summary: list[dict[str, Any]],
    checks: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> dict[str, Any]:
    ready = status == "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_READY_DESIGN_ONLY_NO_EXECUTION"
    return {
        "phase": policy.get("phase", "Phase 8-16"),
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "execution": policy.get("execution", "DRY_RUN"),
        "target_post_id": policy.get("target_post_id"),
        "phase8_15_status": phase8_15_status,
        "evidence_summary": evidence_summary,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": (
            policy.get("allowed_next_step_if_ready")
            if ready
            else policy.get("allowed_next_step_if_blocked", "Keep NO_GO and locked state")
        ),
        "checked_at": _now_iso(),
        **FALSE_FLAGS,
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-16 Draft Body Update Unlock Request (Design Only)",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- phase8_15_status: {result.get('phase8_15_status')}",
        f"- production_status: {result.get('production_status')}",
        "",
        "## Safety Flags",
        f"- unlock_request_is_execution_permission: {result.get('unlock_request_is_execution_permission')}",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- update_allowed: {result.get('update_allowed')}",
        f"- delete_allowed: {result.get('delete_allowed')}",
        f"- export_allowed: {result.get('export_allowed')}",
        f"- auto_post: {result.get('auto_post')}",
        f"- gate_is_execution_permission: {result.get('gate_is_execution_permission')}",
        f"- systemctl_restart_allowed: {result.get('systemctl_restart_allowed')}",
        f"- systemctl_daemon_reload_allowed: {result.get('systemctl_daemon_reload_allowed')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ]
    return "\n".join(lines) + "\n"


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")


def validate_phase8_16_draft_body_update_unlock_request_design_only(
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
    checks: dict[str, Any] = {}

    if not policy_path.exists():
        policy = {"phase": "Phase 8-16", "production_status": "NO_GO", "execution": "DRY_RUN"}
        errors.append(f"missing_policy: {policy_path}")
        result = _build_result(
            policy=policy,
            status="ABORT_MISSING_POLICY",
            phase8_15_status=None,
            evidence_summary=evidence_summary,
            checks=checks,
            errors=errors,
            warnings=warnings,
            safety_violations=safety_violations,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    for flag, expected in FALSE_FLAGS.items():
        if policy.get(flag) is not expected:
            safety_violations.append(f"policy.{flag} must be false")

    if policy.get("production_status") != "NO_GO":
        safety_violations.append("policy.production_status must be NO_GO")
    if policy.get("execution") != "DRY_RUN":
        safety_violations.append("policy.execution must be DRY_RUN")

    root = _resolve_root(policy_path)
    phase8_15_payload: dict[str, Any] = {}
    phase8_15_status: str | None = None

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            errors.append(f"missing_evidence: {rel}")
            continue

        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if "phase8_15" in rel:
            phase8_15_payload = payload
            phase8_15_status = status

    checks["phase8_15_status_ok"] = phase8_15_status == policy.get("required_phase8_15_status")
    checks["phase8_15_production_status_ok"] = (
        phase8_15_payload.get("production_status") == policy.get("required_phase8_15_production_status")
    )
    checks["phase8_15_gate_not_execution_permission"] = (
        phase8_15_payload.get("gate_is_execution_permission")
        is policy.get("required_phase8_15_gate_is_execution_permission")
    )

    if safety_violations:
        status = "ABORT_POLICY_VIOLATION"
    elif errors:
        status = "ABORT_MISSING_EVIDENCE"
    elif all(checks.values()):
        status = "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_READY_DESIGN_ONLY_NO_EXECUTION"
    else:
        status = "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_BLOCKED_DESIGN_ONLY_NO_EXECUTION"
        warnings.append("Unlock request prerequisites are not met; keep lock and NO_GO")

    result = _build_result(
        policy=policy,
        status=status,
        phase8_15_status=phase8_15_status,
        evidence_summary=evidence_summary,
        checks=checks,
        errors=errors,
        warnings=warnings,
        safety_violations=safety_violations,
    )
    _write_outputs(result, output_json_path, output_md_path)
    return result


def main() -> int:
    result = validate_phase8_16_draft_body_update_unlock_request_design_only()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_READY_DESIGN_ONLY_NO_EXECUTION",
        "PHASE8_16_DRAFT_BODY_UPDATE_UNLOCK_REQUEST_BLOCKED_DESIGN_ONLY_NO_EXECUTION",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())