#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_4_post_execution_verification_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_4_post_execution_verification_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_4_post_execution_verification_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def verify_post_execution_evidence(
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

    for key in ["publish_allowed", "update_allowed", "delete_allowed", "auto_cleanup_allowed"]:
        if policy.get(key) is not False:
            safety_violations.append(f"{key} must be false")

    if policy.get("auto_publish_allowed") is True:
        safety_violations.append("auto_publish_allowed must be false")

    root = _resolve_root(policy_path)
    evidence_summary: list[dict[str, Any]] = []
    phase83_payload: dict[str, Any] = {}
    missing_evidence = False

    for rel in policy.get("required_evidence", []):
        evidence_path = root / rel
        if not evidence_path.exists():
            missing_evidence = True
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(evidence_path)
        phase83_payload = payload
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})

    post_id = phase83_payload.get("post_id")
    post_status = phase83_payload.get("post_status")
    phase83_status = phase83_payload.get("status")

    if safety_violations:
        status = "ABORT"
        freeze_required = True
    elif missing_evidence:
        status = "FREEZE_REQUIRED"
        freeze_required = True
        errors.append("required evidence missing")
    elif phase83_payload.get("publish_allowed") is True:
        status = "ABORT"
        freeze_required = True
        errors.append("phase8_3 publish_allowed must be false")
    elif phase83_payload.get("update_allowed") is True:
        status = "ABORT"
        freeze_required = True
        errors.append("phase8_3 update_allowed must be false")
    elif phase83_payload.get("delete_allowed") is True:
        status = "ABORT"
        freeze_required = True
        errors.append("phase8_3 delete_allowed must be false")
    elif str(post_status).lower() in {"publish", "published"}:
        status = "ABORT"
        freeze_required = True
        errors.append("post_status publish/published is forbidden")
    elif phase83_status == policy.get("success_status"):
        if not post_id:
            status = "FREEZE_REQUIRED"
            freeze_required = True
            errors.append("post_id is required on success")
        elif post_status != policy.get("required_post_status"):
            status = "FREEZE_REQUIRED"
            freeze_required = True
            errors.append(f"post_status must be {policy.get('required_post_status')}")
        else:
            status = "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW"
            freeze_required = False
    elif phase83_status == policy.get("not_executed_status"):
        status = "NOT_EXECUTED_CONFIRMED"
        freeze_required = False
        post_id = None
        post_status = None
    elif phase83_status in set(policy.get("failure_statuses", [])):
        status = "FREEZE_REQUIRED"
        freeze_required = True
    elif phase83_payload.get("wordpress_write_executed") is True and not post_id:
        status = "FREEZE_REQUIRED"
        freeze_required = True
        errors.append("wordpress_write_executed=true but post_id missing")
    else:
        status = "FREEZE_REQUIRED"
        freeze_required = True
        warnings.append(f"unknown phase8_3 status: {phase83_status}")

    result = {
        "phase": "Phase 8-4",
        "status": status,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "auto_cleanup_allowed": False,
        "human_review_required": True,
        "post_id": post_id if status == "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW" else None,
        "post_status": post_status if status == "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW" else None,
        "freeze_required": freeze_required,
        "evidence_summary": evidence_summary,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "allowed_next_step": policy.get(
            "allowed_next_step",
            "Phase 8-5 first controlled draft creation completion report",
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
        "# Phase 8-4 Post-Execution Verification Report",
        "",
        "## Purpose",
        "- Verify Phase 8-3 outcome and freeze on mismatch.",
        "",
        "## Phase 8-3 Evidence",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Verification Decision",
            f"- status: {result.get('status')}",
            f"- post_id: {result.get('post_id')}",
            f"- post_status: {result.get('post_status')}",
            "",
            "## Safety Flags",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- update_allowed: {result.get('update_allowed')}",
            f"- delete_allowed: {result.get('delete_allowed')}",
            f"- auto_cleanup_allowed: {result.get('auto_cleanup_allowed')}",
            "",
            "## Freeze Requirement",
            f"- freeze_required: {result.get('freeze_required')}",
            "",
            "## Human Review Requirement",
            f"- human_review_required: {result.get('human_review_required')}",
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
    result = verify_post_execution_evidence()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "POST_EXECUTION_VERIFIED_PENDING_HUMAN_REVIEW",
        "NOT_EXECUTED_CONFIRMED",
        "FREEZE_REQUIRED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
