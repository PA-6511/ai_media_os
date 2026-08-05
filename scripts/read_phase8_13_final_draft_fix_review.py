#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_13_final_draft_fix_review_dry_run_policy.json"
DEFAULT_INPUT = ROOT / "exchange/human_review/phase8_13_final_draft_fix_review_post_114.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_13_final_draft_fix_review_post_114_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_13_final_draft_fix_review_post_114_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _all_false(payload: dict[str, Any], keys: list[str]) -> bool:
    return all(payload.get(k) is False for k in keys)


def _all_true(payload: dict[str, Any], keys: list[str]) -> bool:
    return all(payload.get(k) is True for k in keys)


def read_phase8_13_final_draft_fix_review(
    policy_path: Path = DEFAULT_POLICY,
    input_path: Path = DEFAULT_INPUT,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy_path = Path(policy_path)
    input_path = Path(input_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    policy_violations: list[str] = []

    if not policy_path.exists() or not input_path.exists():
        missing = []
        if not policy_path.exists():
            missing.append(f"missing_policy:{policy_path}")
        if not input_path.exists():
            missing.append(f"missing_input:{input_path}")
        result = {
            "phase": "Phase 8-13",
            "status": "ABORT",
            "decision": "ABORT",
            "reason": "required file missing",
            "production_status": "NO_GO",
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
            "auto_post": False,
            "wordpress_api_call_allowed": False,
            "wordpress_write_executed": False,
            "errors": missing,
            "warnings": [],
            "policy_violations": ["required_file_missing"],
            "allowed_next_step": "fix_required_files",
            "checked_at": _now_iso(),
        }
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_path.write_text(_build_markdown(result), encoding="utf-8")
        return result

    policy = _load_json(policy_path)
    review = _load_json(input_path)
    root = _resolve_root(policy_path)

    for key in [
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "publish_allowed",
        "update_allowed",
        "delete_allowed",
        "export_allowed",
        "auto_post",
        "auto_update",
        "auto_delete",
        "auto_export",
    ]:
        if policy.get(key) is not False:
            policy_violations.append(f"policy.{key} must be false")

    if review.get("phase") != "Phase 8-13":
        policy_violations.append("review.phase must be Phase 8-13")
    if review.get("mode") != "FINAL_DRAFT_FIX_REVIEW":
        policy_violations.append("review.mode must be FINAL_DRAFT_FIX_REVIEW")
    if review.get("execution") != "DRY_RUN":
        policy_violations.append("review.execution must be DRY_RUN")

    decision = str(review.get("decision", "")).strip()
    if decision not in set(policy.get("allowed_decisions", [])):
        policy_violations.append("review.decision must be one of allowed_decisions")

    if review.get("target_post_id") != policy.get("target_post_id"):
        policy_violations.append("target_post_id mismatch")

    safety_flags = review.get("safety_flags", {})
    if not _all_false(
        safety_flags,
        [
            "wordpress_api_call_allowed",
            "wordpress_write_executed",
            "publish_allowed",
            "update_allowed",
            "delete_allowed",
            "export_allowed",
            "auto_post",
            "auto_update",
            "auto_delete",
            "auto_export",
        ],
    ):
        policy_violations.append("all review.safety_flags must be false")

    prohibited_ops = review.get("prohibited_operations_confirmed", {})
    if not _all_true(
        prohibited_ops,
        [
            "publish",
            "update",
            "delete",
            "export",
            "auto_post",
            "additional_retry",
            "systemctl_restart",
            "systemctl_daemon_reload",
        ],
    ):
        policy_violations.append("all prohibited_operations_confirmed must be true")

    evidence_summary: list[dict[str, Any]] = []
    phase812_payload: dict[str, Any] = {}
    missing_evidence = False
    for rel in policy.get("required_evidence", []):
        ev_path = root / rel
        if not ev_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(ev_path)
        st = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": st})
        phase812_payload = payload

    if missing_evidence:
        policy_violations.append("required evidence missing")
    elif phase812_payload.get("status") != policy.get("required_phase8_12_status"):
        policy_violations.append("phase8_12 status mismatch")

    required_checks = policy.get("required_manual_checks", {})
    manual_checks = review.get("manual_checks", {})
    for key in required_checks.keys():
        if key not in manual_checks:
            policy_violations.append(f"manual_checks missing key: {key}")

    reviewer = str(review.get("reviewer", "")).strip()
    reviewed_at_utc = str(review.get("reviewed_at_utc", "")).strip()
    if reviewer in {"", "REPLACE_WITH_REVIEWER"}:
        warnings.append("reviewer not finalized")
    if reviewed_at_utc in {"", "REPLACE_WITH_UTC_TIMESTAMP"}:
        warnings.append("reviewed_at_utc not finalized")

    replace_plan = review.get("replace_plan", {})
    official_url = str(replace_plan.get("official_product_url", "")).strip()
    affiliate_url = str(replace_plan.get("affiliate_url", "")).strip()

    if decision == "APPROVE_FIX_DRY_RUN_ONLY":
        for key, expected in required_checks.items():
            if manual_checks.get(key) is not expected:
                policy_violations.append(f"manual_checks.{key} must be {expected} for approve")
        if official_url in {"", "REPLACE_WITH_REAL_OFFICIAL_URL"}:
            policy_violations.append("official_product_url must be finalized for approve")
        if affiliate_url in {"", "REPLACE_WITH_REAL_AFFILIATE_URL"}:
            policy_violations.append("affiliate_url must be finalized for approve")

    status = "ABORT"
    reason = "policy violation"
    next_step = "fix_inputs_and_retry"

    if policy_violations:
        status = "ABORT"
        reason = "policy violation"
        next_step = "fix_inputs_and_retry"
    elif decision == "PENDING":
        status = "PENDING_REVIEW_INCOMPLETE"
        reason = "manual review in progress"
        next_step = "continue_final_dry_run_review"
    elif decision == "APPROVE_FIX_DRY_RUN_ONLY":
        status = "PHASE8_13_APPROVE_FIX_DRY_RUN_ONLY"
        reason = "final dry-run fix draft approved without WordPress update"
        next_step = policy.get("allowed_next_step_on_approve")
    elif decision == "REQUEST_FIX":
        status = "PHASE8_13_REQUEST_FIX"
        reason = "additional fixes requested in final dry-run review"
        next_step = policy.get("allowed_next_step_on_request_fix")
    elif decision == "REJECT":
        status = "PHASE8_13_REJECTED"
        reason = "final dry-run fix draft rejected"
        next_step = policy.get("allowed_next_step_on_reject")
    elif decision == "ABORT":
        status = "ABORT"
        reason = "manual review aborted"
        next_step = policy.get("allowed_next_step_on_abort")

    result = {
        "phase": "Phase 8-13",
        "status": status,
        "decision": decision,
        "reason": reason,
        "production_status": "NO_GO",
        "target_post_id": review.get("target_post_id"),
        "manual_checks": manual_checks,
        "replace_plan": replace_plan,
        "reviewer": reviewer,
        "reviewed_at_utc": reviewed_at_utc,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "policy_violations": policy_violations,
        "allowed_next_step": next_step,
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(_build_markdown(result), encoding="utf-8")
    return result


def _build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-13 Final Draft Fix Review DRY_RUN Result",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- decision: {result.get('decision')}",
        f"- reason: {result.get('reason')}",
        "",
        "## Target",
        f"- target_post_id: {result.get('target_post_id')}",
        "",
        "## Manual Checks",
    ]

    for key, val in (result.get("manual_checks") or {}).items():
        lines.append(f"- {key}: {val}")

    lines.extend(
        [
            "",
            "## Replace Plan",
            f"- official_product_url: {(result.get('replace_plan') or {}).get('official_product_url')}",
            f"- affiliate_url: {(result.get('replace_plan') or {}).get('affiliate_url')}",
            f"- link_validation_memo: {(result.get('replace_plan') or {}).get('link_validation_memo')}",
            "",
            "## Safety Flags",
            f"- production_status: {result.get('production_status')}",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- update_allowed: {result.get('update_allowed')}",
            f"- delete_allowed: {result.get('delete_allowed')}",
            f"- export_allowed: {result.get('export_allowed')}",
            f"- auto_post: {result.get('auto_post')}",
            f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
            f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = read_phase8_13_final_draft_fix_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_13_APPROVE_FIX_DRY_RUN_ONLY",
        "PHASE8_13_REQUEST_FIX",
        "PHASE8_13_REJECTED",
        "PENDING_REVIEW_INCOMPLETE",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
