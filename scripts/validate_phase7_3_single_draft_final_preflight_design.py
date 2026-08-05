#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_3_single_draft_final_preflight_design_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase7_3_single_draft_final_preflight_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_3_single_draft_final_preflight_design_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_3_single_draft_final_preflight_design_result.md"

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


def _resolve_root(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def validate_phase7_3_preflight_design(
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

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        policy: dict[str, Any] = {}
    else:
        policy = _load_json(policy_path)

    if not request_path.exists():
        safety_violations.append(f"missing_preflight_request: {request_path}")
        request: dict[str, Any] = {}
    else:
        request = _load_json(request_path)

    checks = [
        (policy.get("phase") == "Phase 7-3", "phase must be Phase 7-3"),
        (policy.get("policy_status") == "DESIGN_ONLY", "policy_status must be DESIGN_ONLY"),
        (policy.get("production_status") == "NO_GO", "production_status must be NO_GO"),
        (policy.get("mode") == "CONNECTION_TEST", "mode must be CONNECTION_TEST"),
        (policy.get("execution") == "DRY_RUN", "execution must be DRY_RUN"),
        (policy.get("human_approval_required") is True, "human_approval_required must be true"),
        (
            policy.get("approve_draft_create_only_currently_allowed") is False,
            "approve_draft_create_only_currently_allowed must be false",
        ),
        (policy.get("unlock_in_this_phase") is False, "unlock_in_this_phase must be false"),
        (
            policy.get("eligible_is_execution_permission") is False,
            "eligible_is_execution_permission must be false",
        ),
        (policy.get("wordpress_draft_creation") == "NO_GO", "wordpress_draft_creation must be NO_GO"),
        (
            policy.get("wordpress_write_executed") is False,
            "wordpress_write_executed must be false",
        ),
        (policy.get("publish_allowed") is False, "publish_allowed must be false"),
        (policy.get("auto_post") is False, "auto_post must be false"),
        (policy.get("auto_update") is False, "auto_update must be false"),
        (policy.get("auto_delete") is False, "auto_delete must be false"),
        (policy.get("auto_export") is False, "auto_export must be false"),
    ]
    for ok, message in checks:
        if not ok:
            safety_violations.append(message)

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
        if status in {"PASS_DRY_RUN_ONLY_WITH_WARN", "PASS_DESIGN_ONLY_WITH_WARN", "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN"}:
            warnings.append(f"upstream_warning_status: {rel}")

    if request.get("phase") != "Phase 7-3":
        errors.append("request.phase must be Phase 7-3")
    if request.get("decision_token") != "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("approval_token_mismatch")
    if request.get("preflight_mode") != "FINAL_PREFLIGHT_DESIGN_ONLY":
        errors.append("request.preflight_mode must be FINAL_PREFLIGHT_DESIGN_ONLY")
    if request.get("mode") != "CONNECTION_TEST":
        errors.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        safety_violations.append("request.execution must be DRY_RUN")

    if request.get("target_item_count") != 1:
        safety_violations.append("target_item_count_not_1")
    if request.get("single_item_lock") is not True:
        safety_violations.append("single_item_lock must be true")

    human_approval = request.get("human_approval")
    if not isinstance(human_approval, dict):
        safety_violations.append("missing_human_approval_file")
    else:
        if human_approval.get("file_exists") is not True:
            safety_violations.append("missing_human_approval_file")
        if human_approval.get("review_status") not in {"PENDING_REVIEW", "UNDER_REVIEW"}:
            errors.append("human_approval.review_status must be PENDING_REVIEW or UNDER_REVIEW")
        if human_approval.get("approved_for_live_execution") is not False:
            safety_violations.append("approved_for_live_execution must be false in Phase 7-3 design")
        if human_approval.get("token") != "APPROVE_DRAFT_CREATE_ONLY":
            safety_violations.append("approval_token_mismatch")
        if human_approval.get("expired") is not False:
            safety_violations.append("approval_expired")

    freeze = request.get("freeze_plan")
    if not isinstance(freeze, dict):
        safety_violations.append("missing_freeze_plan")
    else:
        if freeze.get("exists") is not True:
            safety_violations.append("missing_freeze_plan")
        if freeze.get("freeze_on_wordpress_write_attempt") is not True:
            safety_violations.append("freeze_on_write_attempt must be true")
        if freeze.get("freeze_on_publish_attempt") is not True:
            safety_violations.append("freeze_on_publish_attempt must be true")
        if freeze.get("freeze_on_bulk_execution") is not True:
            safety_violations.append("freeze_on_bulk_attempt must be true")
        if freeze.get("freeze_on_external_write") is not True:
            safety_violations.append("freeze_on_external_write must be true")

    flags = request.get("safety_flags", {})
    for key, expected in [
        ("production_status", "NO_GO"),
        ("wordpress_draft_creation", "NO_GO"),
    ]:
        if flags.get(key) != expected:
            safety_violations.append(f"safety_flags.{key} must be {expected}")

    bool_false_keys = [
        "wordpress_write_executed",
        "approve_draft_create_only_currently_allowed",
        "unlock_in_this_phase",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "publish_allowed",
        "bulk_execution",
        "external_write",
        "vps_self_builder_execution",
    ]
    for key in bool_false_keys:
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
        "phase": "Phase 7-3",
        "name": "single_draft_final_preflight_design_policy",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "human_approval_required": True,
        "target_item_count": request.get("target_item_count"),
        "upstream_evidence_checked": upstream_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "freeze_required": status == "ABORT",
        "blocked_operations": policy.get("blocked_operations", []),
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-4 execution gate validation with NO_GO freeze maintained",
        ),
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 7-3 Single Draft Final Preflight Design Report",
        "",
        "## Purpose",
        "- Fix final preflight conditions for one-item controlled flow while keeping NO_GO and no real WordPress write.",
        "",
        "## Overall Status",
        f"- status: {result.get('status')}",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
        "",
        "## Upstream Evidence",
    ]
    upstream = result.get("upstream_evidence_checked", [])
    if upstream:
        for item in upstream:
            lines.append(f"- {item.get('path')}: status={item.get('status')} exists={item.get('exists')}")
    else:
        lines.append("- none")

    lines.extend(["", "## Safety Violations"])
    if result.get("safety_violations"):
        for item in result["safety_violations"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines.extend(["", "## Blocked Operations"])
    for op in result.get("blocked_operations", []):
        lines.append(f"- {op}")

    lines.extend(
        [
            "",
            "## Allowed Next Step",
            f"- {result.get('allowed_next_step')}",
            "",
            "## Final Judgment",
            f"- status: {result.get('status')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = validate_phase7_3_preflight_design()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_DESIGN_ONLY", "PASS_DESIGN_ONLY_WITH_WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
