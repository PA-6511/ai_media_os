#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase7_1_eligible_single_controlled_run_policy.json"
DEFAULT_CANDIDATE = ROOT / "exchange/examples/phase7_1_eligible_candidate.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase7_1_eligible_single_controlled_run_policy_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase7_1_eligible_single_controlled_run_policy_result.md"

SAFE_STATUS = {"PASS", "PASS_DRY_RUN_ONLY", "PASS_DRY_RUN_ONLY_WITH_WARN"}
REJECTED_PHASE6_STATUS = {"FAIL", "ABORT"}
REJECTED_LINK_SCHEMES = {"http", "javascript", "data", "file"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root_from_policy(policy_path: Path) -> Path:
    if policy_path.parent.name == "config":
        return policy_path.parent.parent
    return policy_path.parent


def _is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() == "https" and bool(parsed.netloc)


def _has_rejected_scheme(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme.lower() in REJECTED_LINK_SCHEMES


def _read_phase6_evidence(
    root_dir: Path,
    required_paths: list[str],
    acceptable_statuses: set[str],
    errors: list[str],
    warnings: list[str],
    safety_violations: list[str],
) -> list[dict[str, Any]]:
    checked: list[dict[str, Any]] = []

    for rel in required_paths:
        evidence_path = root_dir / rel
        if not evidence_path.exists():
            safety_violations.append(f"missing_phase6_evidence: {rel}")
            checked.append({"path": rel, "exists": False, "status": None})
            continue

        try:
            payload = _load_json(evidence_path)
        except json.JSONDecodeError as exc:
            safety_violations.append(f"invalid_phase6_evidence_json: {rel}: {exc}")
            checked.append({"path": rel, "exists": True, "status": "INVALID_JSON"})
            continue

        status = payload.get("status") or payload.get("overall_status")
        checked.append({"path": rel, "exists": True, "status": status})

        if status in REJECTED_PHASE6_STATUS:
            safety_violations.append(f"phase6_evidence_fail_or_abort: {rel}={status}")
            continue

        if status not in acceptable_statuses:
            safety_violations.append(f"phase6_evidence_unacceptable_status: {rel}={status}")
            continue

        if status == "PASS_DRY_RUN_ONLY_WITH_WARN":
            warnings.append(f"phase6_evidence_warn_status: {rel}")

    return checked


def validate_policy(
    policy_path: Path = DEFAULT_POLICY,
    candidate_path: Path = DEFAULT_CANDIDATE,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    candidate_path = Path(candidate_path)
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

    if not candidate_path.exists():
        safety_violations.append(f"missing_candidate: {candidate_path}")
        candidate: dict[str, Any] = {}
    else:
        candidate = _load_json(candidate_path)

    root_dir = _resolve_root_from_policy(policy_path)

    checks = [
        (policy.get("phase") == "Phase 7-1", "phase must be Phase 7-1"),
        (policy.get("policy_status") == "DESIGN_ONLY", "policy_status must be DESIGN_ONLY"),
        (policy.get("production_status") == "NO_GO", "production_status must be NO_GO"),
        (policy.get("mode") == "CONNECTION_TEST", "mode must be CONNECTION_TEST"),
        (policy.get("execution") == "DRY_RUN", "execution must be DRY_RUN"),
        (policy.get("human_approval_required") is True, "human_approval_required must be true"),
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
    ]

    for ok, msg in checks:
        if not ok:
            safety_violations.append(msg)

    token = policy.get("future_reserved_decision_token", {})
    if token.get("token") != "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("future_reserved_decision_token.token must be APPROVE_DRAFT_CREATE_ONLY")
    if token.get("currently_allowed") is not False:
        safety_violations.append("future_reserved_decision_token.currently_allowed must be false")
    if token.get("phase7_1_allows_this_token") is not False:
        safety_violations.append("future_reserved_decision_token.phase7_1_allows_this_token must be false")

    limit = policy.get("single_item_limit", {})
    if limit.get("enabled") is not True:
        safety_violations.append("single_item_limit.enabled must be true")
    if limit.get("required") is not True:
        safety_violations.append("single_item_limit.required must be true")
    if limit.get("max_items") != 1:
        safety_violations.append("single_item_limit.max_items must be 1")
    if limit.get("bulk_run_allowed") is not False:
        safety_violations.append("single_item_limit.bulk_run_allowed must be false")

    dangerous = policy.get("dangerous_operations", {})
    for key, value in dangerous.items():
        if value is not False:
            safety_violations.append(f"dangerous_operations.{key} must be false")

    acceptable_statuses = set(policy.get("acceptable_phase6_statuses", [])) or SAFE_STATUS
    required_evidence = policy.get("required_phase6_evidence", [])
    evidence_checked = _read_phase6_evidence(
        root_dir,
        required_evidence,
        acceptable_statuses,
        errors,
        warnings,
        safety_violations,
    )

    required_fields = policy.get("candidate_required_fields", [])
    for field in required_fields:
        if field not in candidate:
            if field == "human_review":
                safety_violations.append("human_review_missing")
            elif field == "freeze_plan":
                safety_violations.append("freeze_plan_missing")
            else:
                errors.append(f"candidate_missing_required_field: {field}")

    if candidate.get("mode") != "CONNECTION_TEST":
        errors.append("candidate.mode must be CONNECTION_TEST")
    if candidate.get("execution") != "DRY_RUN":
        errors.append("candidate.execution must be DRY_RUN")

    target_item_count = candidate.get("target_item_count")
    if target_item_count != 1:
        errors.append("candidate.target_item_count must be 1")
    if isinstance(target_item_count, int) and target_item_count > 1:
        safety_violations.append("candidate.target_item_count must not be greater than 1")

    decision_token = candidate.get("decision_token")
    if decision_token != "ELIGIBLE":
        errors.append("candidate.decision_token must be ELIGIBLE")
    if decision_token == "APPROVE_DRAFT_CREATE_ONLY":
        safety_violations.append("approve_draft_create_only_used_in_phase7_1")

    dup = candidate.get("duplicate_check", {})
    if dup.get("status") != "PASS":
        errors.append("candidate.duplicate_check.status must be PASS")

    quality = candidate.get("quality_gate", {})
    quality_status = quality.get("status")
    if quality_status not in acceptable_statuses:
        if quality_status in REJECTED_PHASE6_STATUS:
            safety_violations.append("candidate.quality_gate.status indicates fail_or_abort")
        else:
            errors.append("candidate.quality_gate.status not acceptable")
    if quality_status == "PASS_DRY_RUN_ONLY_WITH_WARN":
        warnings.append("candidate.quality_gate.status has warning tier")

    pr_notice = candidate.get("pr_notice", {})
    if pr_notice.get("exists") is not True:
        errors.append("candidate.pr_notice.exists must be true")

    cta = candidate.get("cta", {})
    if cta.get("exists") is not True:
        errors.append("candidate.cta.exists must be true")
    cta_items = cta.get("items")
    if not isinstance(cta_items, list) or len(cta_items) == 0:
        errors.append("candidate.cta.items must contain at least one item")
    else:
        for i, item in enumerate(cta_items):
            url = str(item.get("url", ""))
            if _has_rejected_scheme(url) or not _is_https_url(url):
                safety_violations.append(f"candidate.cta.items[{i}].url must be https")

    affiliate_links = candidate.get("affiliate_links")
    if not isinstance(affiliate_links, list) or len(affiliate_links) == 0:
        errors.append("candidate.affiliate_links must contain at least one item")
    else:
        for i, link in enumerate(affiliate_links):
            url = str(link.get("url", ""))
            if _has_rejected_scheme(url) or not _is_https_url(url):
                safety_violations.append(f"candidate.affiliate_links[{i}].url must be https")

    human_review = candidate.get("human_review")
    if not isinstance(human_review, dict):
        safety_violations.append("human_review_missing")
    else:
        if human_review.get("required") is not True:
            safety_violations.append("candidate.human_review.required must be true")
        if human_review.get("status") != "REQUIRED_NOT_APPROVED_IN_PHASE7_1":
            errors.append("candidate.human_review.status must be REQUIRED_NOT_APPROVED_IN_PHASE7_1")
        if human_review.get("approval_token_used") is not False:
            errors.append("candidate.human_review.approval_token_used must be false")
        if human_review.get("approve_draft_create_only_used") is not False:
            safety_violations.append("candidate.human_review.approve_draft_create_only_used must be false")

    freeze_plan = candidate.get("freeze_plan")
    if not isinstance(freeze_plan, dict):
        safety_violations.append("freeze_plan_missing")
    else:
        if freeze_plan.get("exists") is not True:
            safety_violations.append("candidate.freeze_plan.exists must be true")
        if freeze_plan.get("freeze_on_mismatch") is not True:
            safety_violations.append("candidate.freeze_plan.freeze_on_mismatch must be true")
        if freeze_plan.get("freeze_on_wordpress_write_attempt") is not True:
            safety_violations.append("candidate.freeze_plan.freeze_on_wordpress_write_attempt must be true")
        if freeze_plan.get("freeze_on_bulk_execution") is not True:
            safety_violations.append("candidate.freeze_plan.freeze_on_bulk_execution must be true")

    safety_flags = candidate.get("safety_flags", {})
    if safety_flags.get("production_status") != "NO_GO":
        safety_violations.append("candidate.safety_flags.production_status must be NO_GO")
    if safety_flags.get("wordpress_draft_creation") != "NO_GO":
        safety_violations.append("candidate.safety_flags.wordpress_draft_creation must be NO_GO")

    if safety_flags.get("wordpress_write_executed") is not False:
        safety_violations.append("candidate.safety_flags.wordpress_write_executed must be false")

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
        if safety_flags.get(key) is not False:
            safety_violations.append(f"candidate.safety_flags.{key} must be false")

    if safety_violations:
        status = "ABORT"
    elif errors:
        status = "NOT_ELIGIBLE"
    elif warnings:
        status = "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN"
    else:
        status = "ELIGIBLE_DRY_RUN_ONLY"

    freeze_required = status == "ABORT"

    result = {
        "phase": "Phase 7-1",
        "name": "eligible_single_controlled_run_policy",
        "status": status,
        "production_status": policy.get("production_status", "NO_GO"),
        "wordpress_draft_creation": policy.get("wordpress_draft_creation", "NO_GO"),
        "wordpress_write_executed": bool(policy.get("wordpress_write_executed", False)),
        "auto_post": bool(policy.get("dangerous_operations", {}).get("auto_post", False)),
        "auto_update": bool(policy.get("dangerous_operations", {}).get("auto_update", False)),
        "auto_delete": bool(policy.get("dangerous_operations", {}).get("auto_delete", False)),
        "auto_export": bool(policy.get("dangerous_operations", {}).get("auto_export", False)),
        "publish_allowed": bool(policy.get("publish_allowed", False)),
        "eligible_is_execution_permission": bool(policy.get("eligible_is_execution_permission", False)),
        "target_item_count": target_item_count,
        "human_approval_required": bool(policy.get("human_approval_required", False)),
        "approve_draft_create_only_currently_allowed": bool(token.get("currently_allowed", False)),
        "phase6_evidence_checked": evidence_checked,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "freeze_required": freeze_required,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 7-2 APPROVE_DRAFT_CREATE_ONLY pre-unlock review design only",
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
    evidence_lines = [
        f"- {item.get('path')}: status={item.get('status')} exists={item.get('exists')}"
        for item in result.get("phase6_evidence_checked", [])
    ] or ["- (none)"]

    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    safety_violations = result.get("safety_violations", [])

    lines = [
        "# Phase 7-1 Eligible Single Controlled Run Policy Report",
        "",
        "## Purpose",
        "- Fix ELIGIBLE candidate screening and one-item controlled-run constraints as design-only gates.",
        "",
        "## Overall Status",
        f"- status: {result.get('status')}",
        f"- production_status: {result.get('production_status')}",
        f"- wordpress_draft_creation: {result.get('wordpress_draft_creation')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- freeze_required: {result.get('freeze_required')}",
        "",
        "## Phase 6 Evidence Summary",
        *evidence_lines,
        "",
        "## Eligible Conditions",
        f"- target_item_count: {result.get('target_item_count')}",
        f"- human_approval_required: {result.get('human_approval_required')}",
        f"- eligible_is_execution_permission: {result.get('eligible_is_execution_permission')}",
        f"- approve_draft_create_only_currently_allowed: {result.get('approve_draft_create_only_currently_allowed')}",
        "",
        "## Safety Flags",
        f"- auto_post: {result.get('auto_post')}",
        f"- auto_update: {result.get('auto_update')}",
        f"- auto_delete: {result.get('auto_delete')}",
        f"- auto_export: {result.get('auto_export')}",
        f"- publish_allowed: {result.get('publish_allowed')}",
        "",
        "## Freeze Conditions",
        "- Triggered when safety violations exist.",
    ]

    if safety_violations:
        lines.extend([f"- {item}" for item in safety_violations])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Blocked Operations",
        ]
    )

    blocked = result.get("blocked_next_steps", [])
    if blocked:
        lines.extend([f"- {item}" for item in blocked])
    else:
        lines.append("- none")

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

    if errors:
        lines.append("- errors:")
        lines.extend([f"  - {item}" for item in errors])

    if warnings:
        lines.append("- warnings:")
        lines.extend([f"  - {item}" for item in warnings])

    return "\n".join(lines) + "\n"


def main() -> int:
    result = validate_policy()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {"ELIGIBLE_DRY_RUN_ONLY", "ELIGIBLE_DRY_RUN_ONLY_WITH_WARN"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
