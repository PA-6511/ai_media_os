#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_5_first_controlled_draft_completion_report_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_5_first_controlled_draft_completion_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_5_first_controlled_draft_completion_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_completion_report(
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

    policy = _load_json(policy_path) if policy_path.exists() else {}
    if not policy_path.exists():
        safety_violations.append(f"missing_policy: {policy_path}")

    for key in ["publish_allowed", "update_allowed", "delete_allowed", "auto_post", "auto_update", "auto_delete", "auto_export"]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    evidence_payloads: dict[str, dict[str, Any]] = {}
    missing_evidence = False

    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        evidence_payloads[rel] = payload

    if safety_violations:
        status = "ABORT"
        freeze_required = True
    elif missing_evidence:
        status = policy.get("decision_rules", {}).get("freeze_required", "FIRST_DRAFT_FREEZE_REQUIRED")
        freeze_required = True
        errors.append("required evidence missing")
    else:
        for _, payload in evidence_payloads.items():
            if payload.get("publish_allowed") is True:
                safety_violations.append("publish_allowed must stay false in all evidence")
            if payload.get("update_allowed") is True:
                safety_violations.append("update_allowed must stay false in all evidence")
            if payload.get("delete_allowed") is True:
                safety_violations.append("delete_allowed must stay false in all evidence")
            if payload.get("auto_post") is True:
                safety_violations.append("auto_post must stay false in all evidence")
            if payload.get("auto_update") is True:
                safety_violations.append("auto_update must stay false in all evidence")
            if payload.get("auto_delete") is True:
                safety_violations.append("auto_delete must stay false in all evidence")
            if payload.get("auto_export") is True:
                safety_violations.append("auto_export must stay false in all evidence")

        if safety_violations:
            status = "ABORT"
            freeze_required = True
        else:
            phase84_rel = "exchange/logs/phase8_4_post_execution_verification_result.json"
            phase84_status = evidence_payloads.get(phase84_rel, {}).get("status")
            rules = policy.get("decision_rules", {})
            if phase84_status == "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW":
                status = rules.get("verified_pending_human_review", "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW")
                freeze_required = False
            elif phase84_status == "NOT_EXECUTED_CONFIRMED":
                status = rules.get("not_executed", "FIRST_DRAFT_NOT_EXECUTED")
                freeze_required = False
            elif phase84_status == "FREEZE_REQUIRED":
                status = rules.get("freeze_required", "FIRST_DRAFT_FREEZE_REQUIRED")
                freeze_required = True
            elif phase84_status == "ABORT":
                status = rules.get("abort", "ABORT")
                freeze_required = True
            else:
                status = rules.get("freeze_required", "FIRST_DRAFT_FREEZE_REQUIRED")
                freeze_required = True
                warnings.append(f"unexpected phase8_4 status: {phase84_status}")

    post_payload = evidence_payloads.get("exchange/logs/phase8_3_first_one_item_wordpress_draft_create_result.json", {})
    post_id = post_payload.get("post_id")
    post_status = post_payload.get("post_status")

    if status == "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW":
        allowed_next_step = policy.get("allowed_next_step_on_success", "Phase 8-6 manual inspection of created WordPress draft")
    elif status == "FIRST_DRAFT_NOT_EXECUTED":
        allowed_next_step = policy.get(
            "allowed_next_step_on_not_executed",
            "Provide credentials or keep NO_GO, then rerun Phase 8-3 only after approval",
        )
        post_id = None
        post_status = None
    else:
        allowed_next_step = policy.get("allowed_next_step_on_freeze", "Manual review and freeze investigation")
        if status != "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW":
            post_id = None
            post_status = None

    result = {
        "phase": "Phase 8-5",
        "status": status,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "human_review_required": True,
        "post_id": post_id,
        "post_status": post_status,
        "freeze_required": freeze_required,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": allowed_next_step,
        "checked_at": _now_iso(),
    }

    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    output_md_path.write_text(build_markdown(result), encoding="utf-8")
    return result


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Phase 8-5 First Controlled Draft Completion Report",
        "",
        "## Purpose",
        "- Consolidate Phase 8-1 to 8-4 and finalize first controlled draft flow state.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Completion Decision",
            f"- status: {result.get('status')}",
            "",
            "## Draft Result",
            f"- post_id: {result.get('post_id')}",
            f"- post_status: {result.get('post_status')}",
            "",
            "## Safety Flags",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- update_allowed: {result.get('update_allowed')}",
            f"- delete_allowed: {result.get('delete_allowed')}",
            f"- auto_post: {result.get('auto_post')}",
            f"- auto_update: {result.get('auto_update')}",
            f"- auto_delete: {result.get('auto_delete')}",
            f"- auto_export: {result.get('auto_export')}",
            "",
            "## Human Review Requirement",
            f"- human_review_required: {result.get('human_review_required')}",
            "",
            "## Freeze Requirement",
            f"- freeze_required: {result.get('freeze_required')}",
            "",
            "## Final Judgment",
            f"- {result.get('status')}",
            "",
            "## Next Step",
            f"- {result.get('allowed_next_step')}",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    result = generate_completion_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "FIRST_DRAFT_CREATED_PENDING_HUMAN_REVIEW",
        "FIRST_DRAFT_NOT_EXECUTED",
        "FIRST_DRAFT_FREEZE_REQUIRED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
