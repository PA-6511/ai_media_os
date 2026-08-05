#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_2_approve_draft_create_only_pre_unlock_review_policy.json"
DEFAULT_REQUEST = ROOT / "exchange/examples/phase7_2_approve_draft_create_only_pre_unlock_review_request.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_2_approve_draft_create_only_pre_unlock_review_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_2_approve_draft_create_only_pre_unlock_review_result.md"

SAFE_STATUSES = {
    "PASS",
    "PASS_DRY_RUN_ONLY",
    "PASS_DRY_RUN_ONLY_WITH_WARN",
    "ELIGIBLE_DRY_RUN_ONLY",
    "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def validate_phase7_2_policy(
    policy_path: Path = DEFAULT_POLICY,
    request_path: Path = DEFAULT_REQUEST,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    request_path = Path(request_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    safety_violations: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []

    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")
        policy: dict[str, Any] = {}
    else:
        policy = _load_json(policy_path)

    if not request_path.exists():
        safety_violations.append(f"missing_review_request: {request_path}")
        request: dict[str, Any] = {}
    else:
        request = _load_json(request_path)

    checks = [
        (policy.get("phase") == "Phase 7-2", "phase must be Phase 7-2"),
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
    acceptable = set(policy.get("acceptable_upstream_statuses", [])) or SAFE_STATUSES
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
        if status == "PASS_DRY_RUN_ONLY_WITH_WARN":
            warnings.append(f"upstream_warning_status: {rel}")

    if request.get("phase") != "Phase 7-2":
        errors.append("request.phase must be Phase 7-2")
    if request.get("decision_token") != "APPROVE_DRAFT_CREATE_ONLY":
        errors.append("request.decision_token must be APPROVE_DRAFT_CREATE_ONLY")
    if request.get("review_mode") != "PRE_UNLOCK_DESIGN_REVIEW_ONLY":
        errors.append("request.review_mode must be PRE_UNLOCK_DESIGN_REVIEW_ONLY")
    if request.get("mode") != "CONNECTION_TEST":
        errors.append("request.mode must be CONNECTION_TEST")
    if request.get("execution") != "DRY_RUN":
        errors.append("request.execution must be DRY_RUN")

    if request.get("target_item_count") != 1:
        safety_violations.append("request.target_item_count must be 1")
    if request.get("single_item_lock") is not True:
        safety_violations.append("request.single_item_lock must be true")

    approval = request.get("human_approval_file")
    if not isinstance(approval, dict):
        safety_violations.append("missing_human_approval_file")
    else:
        if approval.get("exists") is not True:
            safety_violations.append("human_approval_file.exists must be true")
        if approval.get("approved") is not False:
            safety_violations.append("human_approval_file.approved must be false in Phase 7-2")
        if approval.get("review_status") not in {"PENDING_REVIEW", "UNDER_REVIEW"}:
            errors.append("human_approval_file.review_status must be PENDING_REVIEW or UNDER_REVIEW")

    reviewer = request.get("reviewer_verification")
    if not isinstance(reviewer, dict):
        safety_violations.append("missing_reviewer_verification")
    else:
        if reviewer.get("exists") is not True:
            safety_violations.append("reviewer_verification.exists must be true")
        if reviewer.get("identity_verified") is not True:
            safety_violations.append("reviewer_verification.identity_verified must be true")

    expiry = request.get("decision_expiry")
    if not isinstance(expiry, dict):
        safety_violations.append("missing_decision_expiry")
    else:
        if expiry.get("exists") is not True:
            safety_violations.append("decision_expiry.exists must be true")
        if expiry.get("expired") is not False:
            safety_violations.append("approval_expired")

    freeze = request.get("freeze_conditions")
    if not isinstance(freeze, dict):
        safety_violations.append("missing_freeze_conditions")
    else:
        if freeze.get("exists") is not True:
            safety_violations.append("freeze_conditions.exists must be true")
        if freeze.get("freeze_on_wordpress_write_attempt") is not True:
            safety_violations.append("freeze_on_wordpress_write_attempt must be true")
        if freeze.get("freeze_on_bulk_execution") is not True:
            safety_violations.append("freeze_on_bulk_execution must be true")
        if freeze.get("freeze_on_external_write") is not True:
            safety_violations.append("freeze_on_external_write must be true")
        if freeze.get("freeze_on_missing_preflight") is not True:
            safety_violations.append("freeze_on_missing_preflight must be true")

    safety_flags = request.get("safety_flags", {})
    safe_pairs = [
        (safety_flags.get("production_status") == "NO_GO", "safety_flags.production_status must be NO_GO"),
        (
            safety_flags.get("wordpress_draft_creation") == "NO_GO",
            "safety_flags.wordpress_draft_creation must be NO_GO",
        ),
        (
            safety_flags.get("wordpress_write_executed") is False,
            "safety_flags.wordpress_write_executed must be false",
        ),
        (
            safety_flags.get("approve_draft_create_only_currently_allowed") is False,
            "safety_flags.approve_draft_create_only_currently_allowed must be false",
        ),
        (
            safety_flags.get("unlock_in_this_phase") is False,
            "safety_flags.unlock_in_this_phase must be false",
        ),
    ]
    for key in [
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
        "publish_allowed",
        "bulk_execution",
        "external_write",
        "vps_self_builder_execution",
    ]:
        safe_pairs.append((safety_flags.get(key) is False, f"safety_flags.{key} must be false"))

    for ok, message in safe_pairs:
        if not ok:
            safety_violations.append(message)

    if safety_violations:
        status = "ABORT"
    elif errors:
        status = "ABORT"
    elif warnings:
        status = "PASS_DESIGN_ONLY_WITH_WARN"
    else:
        status = "PASS_DESIGN_ONLY"

    result = {
        "phase": "Phase 7-2",
        "name": "approve_draft_create_only_pre_unlock_review_policy",
        "status": status,
        "production_status": "NO_GO",
        "wordpress_draft_creation": "NO_GO",
        "wordpress_write_executed": False,
        "approve_draft_create_only_currently_allowed": False,
        "unlock_in_this_phase": False,
        "human_approval_required": True,
        "upstream_evidence_checked": upstream_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "freeze_required": status == "ABORT",
        "blocked_operations": policy.get("blocked_operations", []),
        "allowed_next_step": policy.get("allowed_next_step", "Phase 7-3 WordPress single draft final preflight design"),
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    upstream = result.get("upstream_evidence_checked", [])
    lines = [
        "# Phase 7-2 APPROVE_DRAFT_CREATE_ONLY Pre-Unlock Review Report",
        "",
        "## Purpose",
        "- Fix pre-unlock review requirements without enabling WordPress write operations.",
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
    if upstream:
        for item in upstream:
            lines.append(f"- {item.get('path')}: status={item.get('status')} exists={item.get('exists')}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Safety Violations",
        ]
    )
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
    result = validate_phase7_2_policy()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"PASS_DESIGN_ONLY", "PASS_DESIGN_ONLY_WITH_WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
