#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_17_draft_body_update_human_approval_package_design_only_policy.json"
DEFAULT_PACKAGE = ROOT / "exchange/human_review/phase8_17_draft_body_update_human_approval_package_post_114.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_17_draft_body_update_human_approval_package_design_only_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_17_draft_body_update_human_approval_package_design_only_result.md"

FALSE_FLAGS = {
    "wordpress_api_call_allowed": False,
    "wordpress_api_call_attempted": False,
    "wordpress_write_allowed": False,
    "wordpress_write_executed": False,
    "publish_allowed": False,
    "update_allowed": False,
    "delete_allowed": False,
    "export_allowed": False,
    "publish": False,
    "update": False,
    "delete": False,
    "export": False,
    "auto_post": False,
    "gate_is_execution_permission": False,
    "systemctl_restart_allowed": False,
    "systemctl_daemon_reload_allowed": False,
    "credential_env_edit_allowed": False,
}


ACK_FLAGS = {
    "acknowledged_no_go": True,
    "acknowledged_no_wordpress_api_call": True,
    "acknowledged_no_wordpress_write": True,
    "acknowledged_no_publish": True,
    "acknowledged_no_update": True,
    "acknowledged_no_delete": True,
    "acknowledged_no_export": True,
    "acknowledged_no_auto_post": True,
    "acknowledged_no_systemctl": True,
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
    phase8_16_status: str | None,
    package_decision: str | None,
    evidence_summary: list[dict[str, Any]],
    checks: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> dict[str, Any]:
    ready = status == "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_READY_DESIGN_ONLY_NO_EXECUTION"
    return {
        "phase": policy.get("phase", "Phase 8-17"),
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "execution": policy.get("execution", "DRY_RUN"),
        "human_approval_required": policy.get("human_approval_required", True),
        "target_post_id": policy.get("target_post_id"),
        "phase8_16_status": phase8_16_status,
        "package_decision": package_decision,
        "evidence_summary": evidence_summary,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": (
            policy.get("allowed_next_step_if_ready")
            if ready
            else policy.get("allowed_next_step_if_blocked", "Keep NO_GO freeze")
        ),
        "checked_at": _now_iso(),
        **FALSE_FLAGS,
    }


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-17 Draft Body Update Human Approval Package (Design Only)",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- phase8_16_status: {result.get('phase8_16_status')}",
        f"- package_decision: {result.get('package_decision')}",
        f"- production_status: {result.get('production_status')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        "",
        "## Safety Flags",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        f"- update_allowed: {result.get('update_allowed')}",
        f"- delete_allowed: {result.get('delete_allowed')}",
        f"- export_allowed: {result.get('export_allowed')}",
        f"- publish: {result.get('publish')}",
        f"- update: {result.get('update')}",
        f"- delete: {result.get('delete')}",
        f"- export: {result.get('export')}",
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


def validate_phase8_17_draft_body_update_human_approval_package_design_only(
    policy_path: Path = DEFAULT_POLICY,
    package_path: Path = DEFAULT_PACKAGE,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    package_path = Path(package_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    evidence_summary: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}

    if not policy_path.exists():
        policy = {"phase": "Phase 8-17", "production_status": "NO_GO", "execution": "DRY_RUN"}
        errors.append(f"missing_policy: {policy_path}")
        result = _build_result(
            policy=policy,
            status="ABORT_MISSING_POLICY",
            phase8_16_status=None,
            package_decision=None,
            evidence_summary=evidence_summary,
            checks=checks,
            errors=errors,
            warnings=warnings,
            safety_violations=safety_violations,
        )
        _write_outputs(result, output_json_path, output_md_path)
        return result

    policy = _load_json(policy_path)

    for key, expected in FALSE_FLAGS.items():
        if policy.get(key) is not expected:
            safety_violations.append(f"policy.{key} must be false")

    if policy.get("production_status") != "NO_GO":
        safety_violations.append("policy.production_status must be NO_GO")
    if policy.get("execution") != "DRY_RUN":
        safety_violations.append("policy.execution must be DRY_RUN")
    if policy.get("human_approval_required") is not True:
        safety_violations.append("policy.human_approval_required must be true")

    root = _resolve_root(policy_path)
    phase8_16_payload: dict[str, Any] = {}
    phase8_16_status: str | None = None

    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            errors.append(f"missing_evidence: {rel}")
            continue

        payload = _load_json(ev_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if "phase8_16" in rel:
            phase8_16_payload = payload
            phase8_16_status = status

    if not package_path.exists():
        errors.append(f"missing_human_approval_package: {package_path}")
        package: dict[str, Any] = {}
    else:
        package = _load_json(package_path)

    for field in policy.get("required_human_approval_fields", []):
        checks[f"package_has_{field}"] = field in package

    decision = package.get("decision")
    checks["package_decision_allowed"] = decision in set(policy.get("allowed_decisions", []))
    checks["package_decision_not_forbidden"] = decision not in set(policy.get("forbidden_decisions", []))

    checks["phase8_16_status_ok"] = phase8_16_status == policy.get("required_phase8_16_status")
    checks["phase8_16_production_status_ok"] = (
        phase8_16_payload.get("production_status") == policy.get("required_phase8_16_production_status")
    )

    checks["target_post_id_ok"] = package.get("target_post_id") == policy.get("target_post_id")
    checks["target_item_count_is_one"] = package.get("target_item_count") == 1

    for key, expected in ACK_FLAGS.items():
        checks[f"package_{key}"] = package.get(key) is expected

    scope = package.get("approval_scope", {})
    required_scope = policy.get("approval_scope_required", {})
    for key, expected in required_scope.items():
        checks[f"approval_scope_{key}"] = scope.get(key) is expected

    change_request = package.get("change_request", {})
    checks["change_request_execute_now_false"] = change_request.get("execute_now") is False
    checks["change_request_requires_additional_human_approval_for_execution_true"] = (
        change_request.get("requires_additional_human_approval_for_execution") is True
    )

    if safety_violations:
        status = "ABORT_POLICY_VIOLATION"
    elif errors:
        status = "ABORT_MISSING_EVIDENCE"
    elif decision == "ACKNOWLEDGE_PACKAGE_READY_ONLY" and all(checks.values()):
        status = "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_READY_DESIGN_ONLY_NO_EXECUTION"
    else:
        status = "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_BLOCKED_DESIGN_ONLY_NO_EXECUTION"
        warnings.append("Human approval package is not execution permission; keep NO_GO and no execution")

    result = _build_result(
        policy=policy,
        status=status,
        phase8_16_status=phase8_16_status,
        package_decision=decision,
        evidence_summary=evidence_summary,
        checks=checks,
        errors=errors,
        warnings=warnings,
        safety_violations=safety_violations,
    )
    _write_outputs(result, output_json_path, output_md_path)
    return result


def main() -> int:
    result = validate_phase8_17_draft_body_update_human_approval_package_design_only()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_READY_DESIGN_ONLY_NO_EXECUTION",
        "PHASE8_17_DRAFT_BODY_UPDATE_HUMAN_APPROVAL_PACKAGE_BLOCKED_DESIGN_ONLY_NO_EXECUTION",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
