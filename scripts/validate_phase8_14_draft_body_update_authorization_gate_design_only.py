#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_14_draft_body_update_authorization_gate_design_only_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_14_draft_body_update_authorization_gate_design_only_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_14_draft_body_update_authorization_gate_design_only_result.md"


FALSE_FLAGS = {
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
    previous_status: str | None,
    evidence_summary: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> dict[str, Any]:
    ready = status == "PHASE8_14_DRAFT_BODY_UPDATE_AUTHORIZATION_GATE_READY_DESIGN_ONLY_NO_EXECUTION"
    return {
        "phase": policy.get("phase", "Phase 8-14"),
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "execution": policy.get("execution", "DRY_RUN"),
        "target_post_id": policy.get("target_post_id"),
        "previous_phase_status": previous_status,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": (
            policy.get("allowed_next_step_if_ready")
            if ready
            else policy.get("allowed_next_step_if_blocked", "Keep NO_GO")
        ),
        "checked_at": _now_iso(),
        **FALSE_FLAGS,
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-14 Draft Body Update Authorization Gate (Design Only)",
        "",
        "## Purpose",
        "Prepare a gate definition before any WordPress body update operation.",
        "This phase does not permit execution.",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- previous_phase_status: {result.get('previous_phase_status')}",
        f"- production_status: {result.get('production_status')}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- update_allowed: {result.get('update_allowed')}",
        f"- delete_allowed: {result.get('delete_allowed')}",
        f"- export_allowed: {result.get('export_allowed')}",
        f"- auto_post: {result.get('auto_post')}",
        f"- gate_is_execution_permission: {result.get('gate_is_execution_permission')}",
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


def validate_phase8_14_draft_body_update_authorization_gate_design_only(
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
        policy = {"phase": "Phase 8-14", "production_status": "NO_GO", "execution": "DRY_RUN"}
        errors.append(f"missing_policy: {policy_path}")
        result = _build_result(
            policy=policy,
            status="ABORT_MISSING_POLICY",
            previous_status=None,
            evidence_summary=evidence_summary,
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
    previous_status: str | None = None

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            errors.append(f"missing_evidence: {rel}")
            continue
        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if "phase8_13" in rel:
            previous_status = status

    if safety_violations:
        result = _build_result(
            policy=policy,
            status="ABORT_POLICY_VIOLATION",
            previous_status=previous_status,
            evidence_summary=evidence_summary,
            errors=errors,
            warnings=warnings,
            safety_violations=safety_violations,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    if errors:
        result = _build_result(
            policy=policy,
            status="ABORT_MISSING_EVIDENCE",
            previous_status=previous_status,
            evidence_summary=evidence_summary,
            errors=errors,
            warnings=warnings,
            safety_violations=safety_violations,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    required_previous = policy.get("required_previous_status")
    blocked_previous = set(policy.get("blocked_previous_statuses", []))

    if previous_status == required_previous:
        status = "PHASE8_14_DRAFT_BODY_UPDATE_AUTHORIZATION_GATE_READY_DESIGN_ONLY_NO_EXECUTION"
    elif previous_status in blocked_previous:
        status = "PHASE8_14_DRAFT_BODY_UPDATE_AUTHORIZATION_GATE_BLOCKED_PHASE8_13_REQUEST_FIX"
        warnings.append("Phase 8-13 is not approved yet; keep NO_GO and do not update WordPress body")
    else:
        status = "ABORT_UNEXPECTED_PREVIOUS_STATUS"
        safety_violations.append(
            f"phase8_13 status must be {required_previous!r} or blocked set {sorted(blocked_previous)!r}, got {previous_status!r}"
        )

    result = _build_result(
        policy=policy,
        status=status,
        previous_status=previous_status,
        evidence_summary=evidence_summary,
        errors=errors,
        warnings=warnings,
        safety_violations=safety_violations,
    )
    _write_outputs(result, output_json_path, output_md_path)
    return result


def main() -> int:
    result = validate_phase8_14_draft_body_update_authorization_gate_design_only()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_14_DRAFT_BODY_UPDATE_AUTHORIZATION_GATE_READY_DESIGN_ONLY_NO_EXECUTION",
        "PHASE8_14_DRAFT_BODY_UPDATE_AUTHORIZATION_GATE_BLOCKED_PHASE8_13_REQUEST_FIX",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
