#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_14b_draft_body_update_final_preflight_design_only_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_14b_draft_body_update_final_preflight_design_only_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_14b_draft_body_update_final_preflight_design_only_result.md"


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


def _has_placeholder(value: str, markers: list[str]) -> bool:
    if not value.strip():
        return True
    upper = value.upper()
    return any(marker.upper() in upper for marker in markers)


def _build_result(
    policy: dict[str, Any],
    status: str,
    phase8_13_status: str | None,
    phase8_14_status: str | None,
    phase8_13_decision: str | None,
    evidence_summary: list[dict[str, Any]],
    checks: dict[str, Any],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> dict[str, Any]:
    ready = status == "PHASE8_14B_DRAFT_BODY_UPDATE_FINAL_PREFLIGHT_READY_DESIGN_ONLY_NO_EXECUTION"
    return {
        "phase": policy.get("phase", "Phase 8-14B"),
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "execution": policy.get("execution", "DRY_RUN"),
        "target_post_id": policy.get("target_post_id"),
        "phase8_13_status": phase8_13_status,
        "phase8_13_decision": phase8_13_decision,
        "phase8_14_status": phase8_14_status,
        "evidence_summary": evidence_summary,
        "checks": checks,
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
        "# Phase 8-14B Draft Body Update Final Preflight (Design Only)",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- phase8_13_status: {result.get('phase8_13_status')}",
        f"- phase8_13_decision: {result.get('phase8_13_decision')}",
        f"- phase8_14_status: {result.get('phase8_14_status')}",
        f"- production_status: {result.get('production_status')}",
        "",
        "## Check Summary",
    ]
    for key, val in (result.get("checks") or {}).items():
        lines.append(f"- {key}: {val}")

    lines.extend(
        [
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
            f"- systemctl_restart_allowed: {result.get('systemctl_restart_allowed')}",
            f"- systemctl_daemon_reload_allowed: {result.get('systemctl_daemon_reload_allowed')}",
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


def validate_phase8_14b_draft_body_update_final_preflight_design_only(
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
        policy = {"phase": "Phase 8-14B", "production_status": "NO_GO", "execution": "DRY_RUN"}
        errors.append(f"missing_policy: {policy_path}")
        result = _build_result(
            policy=policy,
            status="ABORT_MISSING_POLICY",
            phase8_13_status=None,
            phase8_14_status=None,
            phase8_13_decision=None,
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
    phase8_13_payload: dict[str, Any] = {}
    phase8_14_payload: dict[str, Any] = {}

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
            phase8_13_payload = payload
        if "phase8_14" in rel:
            phase8_14_payload = payload

    phase8_13_status = str(phase8_13_payload.get("status", "")).strip() or None
    phase8_13_decision = str(phase8_13_payload.get("decision", "")).strip() or None
    phase8_14_status = str(phase8_14_payload.get("status", "")).strip() or None

    manual_checks = phase8_13_payload.get("manual_checks", {})
    replace_plan = phase8_13_payload.get("replace_plan", {})
    official_product_url = str(replace_plan.get("official_product_url", "")).strip()
    affiliate_url = str(replace_plan.get("affiliate_url", "")).strip()

    checks["phase8_13_status_ok"] = phase8_13_status == policy.get("required_phase8_13_status")
    checks["phase8_13_decision_ok"] = phase8_13_decision == policy.get("required_phase8_13_decision")
    checks["phase8_14_status_ok"] = phase8_14_status == policy.get("required_phase8_14_status")
    checks["phase8_14_gate_not_execution_permission"] = (
        phase8_14_payload.get("gate_is_execution_permission")
        is policy.get("required_phase8_14_gate_is_execution_permission")
    )
    checks["pr_disclosure_kept"] = manual_checks.get("pr_disclosure_kept") is policy.get("required_pr_disclosure_kept")
    checks["dangerous_html_not_included"] = (
        manual_checks.get("dangerous_html_not_included") is policy.get("required_dangerous_html_not_included")
    )
    checks["no_wordpress_update_executed"] = (
        manual_checks.get("no_wordpress_update_executed") is policy.get("required_no_wordpress_update_executed")
    )
    checks["no_publish_executed"] = manual_checks.get("no_publish_executed") is policy.get("required_no_publish_executed")

    placeholder_markers = list(policy.get("forbidden_placeholders", []))
    official_is_non_placeholder = not _has_placeholder(official_product_url, placeholder_markers)
    affiliate_is_non_placeholder = not _has_placeholder(affiliate_url, placeholder_markers)
    checks["official_product_url_non_placeholder"] = official_is_non_placeholder
    checks["affiliate_url_non_placeholder"] = affiliate_is_non_placeholder

    required_aff_tag = str(policy.get("required_affiliate_tag", "")).strip()
    checks["affiliate_url_has_required_tag"] = bool(required_aff_tag) and required_aff_tag in affiliate_url

    if safety_violations:
        status = "ABORT_POLICY_VIOLATION"
    elif errors:
        status = "ABORT_MISSING_EVIDENCE"
    elif all(checks.values()):
        status = "PHASE8_14B_DRAFT_BODY_UPDATE_FINAL_PREFLIGHT_READY_DESIGN_ONLY_NO_EXECUTION"
    else:
        status = "PHASE8_14B_DRAFT_BODY_UPDATE_FINAL_PREFLIGHT_BLOCKED_NO_EXECUTION"
        warnings.append("Final preflight conditions are not fully satisfied; keep NO_GO and do not execute WordPress update")

    result = _build_result(
        policy=policy,
        status=status,
        phase8_13_status=phase8_13_status,
        phase8_14_status=phase8_14_status,
        phase8_13_decision=phase8_13_decision,
        evidence_summary=evidence_summary,
        checks=checks,
        errors=errors,
        warnings=warnings,
        safety_violations=safety_violations,
    )
    _write_outputs(result, output_json_path, output_md_path)
    return result


def main() -> int:
    result = validate_phase8_14b_draft_body_update_final_preflight_design_only()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_14B_DRAFT_BODY_UPDATE_FINAL_PREFLIGHT_READY_DESIGN_ONLY_NO_EXECUTION",
        "PHASE8_14B_DRAFT_BODY_UPDATE_FINAL_PREFLIGHT_BLOCKED_NO_EXECUTION",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())