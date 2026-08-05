#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange/human_review/phase8_11_manual_draft_review_post_114.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_11_manual_draft_review_post_114_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_11_manual_draft_review_post_114_result.md"

ALLOWED_DECISIONS = {
    "APPROVE_DRAFT_REVIEW_ONLY",
    "REQUEST_FIX",
    "REJECT",
    "ABORT",
    "PENDING",
}

REQUIRED_CHECKLIST_KEYS = [
    "draft_exists_and_is_draft",
    "title_is_expected",
    "content_has_no_break_or_blank_or_dangerous_html",
    "affiliate_or_pr_disclosure_present",
    "links_are_intended",
    "still_not_published",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _all_false(flags: dict[str, Any], keys: list[str]) -> bool:
    return all(flags.get(k) is False for k in keys)


def _all_true(flags: dict[str, Any], keys: list[str]) -> bool:
    return all(flags.get(k) is True for k in keys)


def read_phase8_11_manual_draft_review(
    input_path: Path = DEFAULT_INPUT,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    input_path = Path(input_path)
    output_json_path = Path(output_json_path)
    output_md_path = Path(output_md_path)

    errors: list[str] = []
    warnings: list[str] = []
    policy_violations: list[str] = []

    if not input_path.exists():
        result = {
            "phase": "Phase 8-11",
            "status": "ABORT",
            "decision": "ABORT",
            "reason": f"input file not found: {input_path}",
            "publish_allowed": False,
            "update_allowed": False,
            "delete_allowed": False,
            "export_allowed": False,
            "auto_post": False,
            "production_status": "NO_GO",
            "wordpress_write_executed": False,
            "next_step": "fix_manual_review_input",
            "errors": [f"missing_input:{input_path}"],
            "warnings": [],
            "policy_violations": ["missing_manual_review_input"],
            "checked_at": _now_iso(),
        }
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        output_md_path.write_text(build_markdown(result), encoding="utf-8")
        return result

    payload = _load_json(input_path)

    if payload.get("phase") != "Phase 8-11":
        policy_violations.append("phase must be Phase 8-11")
    if payload.get("mode") != "MANUAL_REVIEW_ONLY":
        policy_violations.append("mode must be MANUAL_REVIEW_ONLY")
    if payload.get("execution") != "NO_WRITE":
        policy_violations.append("execution must be NO_WRITE")

    decision = str(payload.get("decision", "")).strip()
    if decision not in ALLOWED_DECISIONS:
        policy_violations.append("decision is outside allowed values")

    safety_flags = payload.get("safety_flags", {})
    prohibited_ops = payload.get("prohibited_operations_confirmed", {})

    if not _all_false(
        safety_flags,
        [
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
        policy_violations.append("all safety_flags must remain false")

    if not _all_true(
        prohibited_ops,
        [
            "publish",
            "update",
            "delete",
            "export",
            "additional_retry",
            "auto_post",
            "systemctl_restart",
            "systemctl_daemon_reload",
        ],
    ):
        policy_violations.append("all prohibited_operations_confirmed flags must be true")

    checklist = payload.get("checklist", {})
    missing_checklist_keys = [k for k in REQUIRED_CHECKLIST_KEYS if k not in checklist]
    if missing_checklist_keys:
        policy_violations.append(f"missing checklist keys: {', '.join(missing_checklist_keys)}")

    all_checks_passed = all(checklist.get(k) is True for k in REQUIRED_CHECKLIST_KEYS)

    reviewer = str(payload.get("reviewer", "")).strip()
    reviewed_at_utc = str(payload.get("reviewed_at_utc", "")).strip()
    if reviewer in {"", "REPLACE_WITH_REVIEWER"}:
        warnings.append("reviewer not finalized")
    if reviewed_at_utc in {"", "REPLACE_WITH_UTC_TIMESTAMP"}:
        warnings.append("reviewed_at_utc not finalized")

    status = "ABORT"
    next_step = "manual_freeze_investigation"
    reason = "policy violation"

    if policy_violations:
        status = "ABORT"
        next_step = "fix_manual_review_input"
        reason = "policy violation"
    elif decision == "PENDING":
        status = "PENDING_REVIEW_INCOMPLETE"
        next_step = "continue_manual_visual_review_without_publish"
        reason = "manual review is still in progress"
    elif decision == "APPROVE_DRAFT_REVIEW_ONLY":
        if not all_checks_passed:
            status = "REQUEST_FIX_REVIEW_GAP"
            next_step = "fill_remaining_review_items"
            reason = "approve selected but not all checklist items are true"
            warnings.append("approve selected before all checklist items passed")
        else:
            status = "PHASE8_11_DRAFT_REVIEW_APPROVED_NO_PUBLISH"
            next_step = "maintain_no_go_and_prepare_next_manual_gate"
            reason = "manual draft review completed and approved without publish"
    elif decision == "REQUEST_FIX":
        status = "PHASE8_11_REQUEST_FIX"
        next_step = "request_fix_and_re_review_without_publish"
        reason = "manual review requested fixes"
    elif decision == "REJECT":
        status = "PHASE8_11_REJECTED"
        next_step = "keep_no_go_and_stop_without_publish"
        reason = "manual review rejected draft"
    elif decision == "ABORT":
        status = "ABORT"
        next_step = "stop_without_publish"
        reason = "manual review aborted"

    result = {
        "phase": "Phase 8-11",
        "status": status,
        "decision": decision,
        "reason": reason,
        "target_post_id": payload.get("target", {}).get("wordpress_post_id"),
        "target_expected_status": payload.get("target", {}).get("expected_status"),
        "checklist": checklist,
        "all_checklist_items_passed": all_checks_passed,
        "reviewer": reviewer,
        "reviewed_at_utc": reviewed_at_utc,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "export_allowed": False,
        "auto_post": False,
        "production_status": "NO_GO",
        "wordpress_write_executed": False,
        "additional_retry_allowed": False,
        "next_step": next_step,
        "errors": errors,
        "warnings": warnings,
        "policy_violations": policy_violations,
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    checklist = result.get("checklist", {})
    lines = [
        "# Phase 8-11 Manual Draft Review Result",
        "",
        "## Decision",
        f"- status: {result.get('status')}",
        f"- decision: {result.get('decision')}",
        f"- reason: {result.get('reason')}",
        "",
        "## Target",
        f"- target_post_id: {result.get('target_post_id')}",
        f"- expected_status: {result.get('target_expected_status')}",
        "",
        "## Checklist",
    ]

    for key in REQUIRED_CHECKLIST_KEYS:
        lines.append(f"- {key}: {checklist.get(key)}")

    lines.extend(
        [
            "",
            "## Safety",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- update_allowed: {result.get('update_allowed')}",
            f"- delete_allowed: {result.get('delete_allowed')}",
            f"- export_allowed: {result.get('export_allowed')}",
            f"- auto_post: {result.get('auto_post')}",
            f"- additional_retry_allowed: {result.get('additional_retry_allowed')}",
            "",
            "## Review Metadata",
            f"- reviewer: {result.get('reviewer')}",
            f"- reviewed_at_utc: {result.get('reviewed_at_utc')}",
            "",
            "## Next Step",
            f"- {result.get('next_step')}",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    result = read_phase8_11_manual_draft_review()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_11_DRAFT_REVIEW_APPROVED_NO_PUBLISH",
        "PHASE8_11_REQUEST_FIX",
        "PHASE8_11_REJECTED",
        "PENDING_REVIEW_INCOMPLETE",
        "REQUEST_FIX_REVIEW_GAP",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())
