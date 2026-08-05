#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_4_execution_gate_no_go_freeze_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase7_4_execution_gate_validation_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_4_execution_gate_no_go_freeze_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_4_execution_gate_no_go_freeze_result.md"

DEFAULT_ACCEPTABLE = {
    "PASS",
    "PASS_DRY_RUN_ONLY",
    "PASS_DRY_RUN_ONLY_WITH_WARN",
    "ELIGIBLE_DRY_RUN_ONLY",
    "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN",
    "PASS_DESIGN_ONLY",
    "PASS_DESIGN_ONLY_WITH_WARN",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_phase7_4_gate(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []

    policy = _load_json(policy_path) if policy_path.exists() else {}
    request = _load_json(request_path) if request_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
    if not request_path.exists():
        safety_violations.append(f"missing_request: {request_path}")

    policy_checks = [
        (policy.get("phase") == "Phase 7-4", "phase must be Phase 7-4"),
        (policy.get("policy_status") == "DESIGN_ONLY", "policy_status must be DESIGN_ONLY"),
        (policy.get("production_status") == "NO_GO", "production_status must be NO_GO"),
        (policy.get("mode") == "CONNECTION_TEST", "mode must be CONNECTION_TEST"),
        (policy.get("execution") == "DRY_RUN", "execution must be DRY_RUN"),
        (policy.get("human_approval_required") is True, "human_approval_required must be true"),
        (
            policy.get("approve_draft_create_only_currently_allowed") is False,
            "approve_draft_create_only_enabled",
        ),
        (policy.get("unlock_in_this_phase") is False, "unlock_in_this_phase_enabled"),
        (policy.get("eligible_is_execution_permission") is False, "eligible_is_execution_permission must be false"),
        (policy.get("wordpress_draft_creation") == "NO_GO", "wordpress_draft_creation must be NO_GO"),
        (policy.get("wordpress_write_executed") is False, "wordpress_write_attempt_detected"),
        (policy.get("publish_allowed") is False, "publish_requested"),
    ]
    for ok, message in policy_checks:
        if not ok:
            safety_violations.append(message)

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    root_dir = _resolve_root(policy_path)
    acceptable = set(policy.get("acceptable_upstream_statuses", [])) or DEFAULT_ACCEPTABLE
    upstream_summary: list[dict[str, Any]] = []
    for rel in policy.get("required_upstream_evidence", []):
        p = root_dir / rel
        if not p.exists():
            safety_violations.append(f"missing_upstream_evidence: {rel}")
            upstream_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(p)
        status = payload.get("status") or payload.get("overall_status")
        upstream_summary.append({"path": rel, "exists": True, "status": status})
        if status not in acceptable:
            safety_violations.append(f"unacceptable_upstream_status: {rel}={status}")

    if request.get("phase") != "Phase 7-4":
        errors.append("request.phase must be Phase 7-4")
    if request.get("decision_token") != "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("approval_token_mismatch")
    if request.get("mode") != "CONNECTION_TEST":
        errors.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        safety_violations.append("request.execution must be DRY_RUN")

    if request.get("target_item_count") != 1:
        safety_violations.append("target_item_count_not_1")

    approval = request.get("human_approval")
    if not isinstance(approval, dict):
        safety_violations.append("missing_human_approval_file")
    else:
        if approval.get("required") is not True:
            safety_violations.append("human_approval_required_false")
        if approval.get("file_exists") is not True:
            safety_violations.append("missing_human_approval_file")
        rel_path = approval.get("file_path")
        if not rel_path:
            safety_violations.append("missing_human_approval_file")
        else:
            if not (root_dir / str(rel_path)).exists():
                safety_violations.append("missing_human_approval_file")
        if approval.get("review_status") not in {"PENDING_REVIEW", "UNDER_REVIEW"}:
            errors.append("human_approval.review_status must be PENDING_REVIEW or UNDER_REVIEW")
        if approval.get("token") != "APPROVE_DRAFT_CREATE_ONLY":
            safety_violations.append("approval_token_mismatch")

    freeze = request.get("freeze_plan")
    if not isinstance(freeze, dict):
        safety_violations.append("freeze_conditions_missing")
    else:
        for key in [
            "exists",
            "freeze_on_missing_human_approval_file",
            "freeze_on_wordpress_write_attempt",
            "freeze_on_wordpress_rest_write_request",
            "freeze_on_bulk_execution",
            "freeze_on_external_write",
        ]:
            if freeze.get(key) is not True:
                safety_violations.append(f"freeze_plan.{key} must be true")

    flags = request.get("safety_flags", {})
    if flags.get("production_status") != "NO_GO":
        safety_violations.append("production_no_go_not_maintained")
    if flags.get("wordpress_draft_creation") != "NO_GO":
        safety_violations.append("wordpress_draft_creation_not_no_go")

    false_keys = [
        "wordpress_write_executed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "publish_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "wordpress_rest_api_post",
        "wordpress_rest_api_put",
        "wordpress_rest_api_patch",
        "wordpress_rest_api_delete",
        "bulk_execution",
        "external_write",
        "vps_self_builder_execution",
    ]
    for key in false_keys:
        if flags.get(key) is not False:
            safety_violations.append(f"safety_flags.{key} must be false")

    if safety_violations:
        status = "ABORT"
    elif errors:
        status = "ABORT"
    elif warnings:
        status = "PASS_DESIGN_ONLY_WITH_WARN"
    else:
        status = "PASS_DESIGN_ONLY"

    result = {
        "phase": "Phase 7-4",
        "name": "execution_gate_no_go_freeze_policy",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "target_item_count": request.get("target_item_count"),
        "human_approval_required": bool(policy.get("human_approval_required", False)),
        "upstream_evidence_checked": upstream_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "freeze_required": status == "ABORT",
        "allowed_next_step": policy.get(
            "allowed_next_step", "Phase 7-5 freeze-or-live decision report generation"
        ),
        "blocked_next_steps": policy.get("blocked_next_steps", []),
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-4 Execution Gate NO_GO Freeze Report",
        "",
        "## Purpose",
        "- Validate execution gate in design-only mode while keeping NO_GO and freeze controls.",
        "",
        "## Overall Status",
        f"- status: {result.get('status')}",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
        f"- unlock_in_this_phase: {result.get('unlock_in_this_phase')}",
        f"- target_item_count: {result.get('target_item_count')}",
        "",
        "## Upstream Evidence",
    ]
    for item in result.get("upstream_evidence_checked", []):
        lines.append(f"- {item.get('path')}: status={item.get('status')} exists={item.get('exists')}")

    lines.extend(["", "## Safety Violations"])
    if result.get("safety_violations"):
        for item in result.get("safety_violations", []):
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## Allowed Next Step", f"- {result.get('allowed_next_step')}"])
    lines.extend(["", "## Final Judgment", f"- status: {result.get('status')}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    result = validate_phase7_4_gate()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_DESIGN_ONLY", "PASS_DESIGN_ONLY_WITH_WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
