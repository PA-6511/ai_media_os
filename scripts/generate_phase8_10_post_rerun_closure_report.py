#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_10_post_rerun_closure_policy.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_10_post_rerun_closure_report.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_10_post_rerun_closure_report.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def generate_post_rerun_closure_report(
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

    for key in [
        "publish_allowed", "update_allowed", "delete_allowed",
        "auto_cleanup_allowed", "auto_publish_allowed",
        "auto_post", "auto_update", "auto_delete", "auto_export",
    ]:
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
        st = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": st})
        evidence_payloads[rel] = payload

    post_id = None
    post_status_val = None
    post_link = None
    freeze_required = True

    if safety_violations:
        status = "ABORT"
        freeze_required = True
    elif missing_evidence:
        status = policy.get("decision_rules", {}).get("rerun_failed", "RERUN_FREEZE_REQUIRED")
        freeze_required = True
        errors.append("required evidence missing")
    else:
        for _, payload in evidence_payloads.items():
            for bad_key in ["publish_allowed", "update_allowed", "delete_allowed",
                            "auto_post", "auto_update", "auto_delete", "auto_export"]:
                if payload.get(bad_key) is True:
                    safety_violations.append(f"{bad_key} must stay false in all evidence")

        if safety_violations:
            status = "ABORT"
            freeze_required = True
        else:
            phase89 = {}
            for ev_key, ev_val in evidence_payloads.items():
                if "phase8_9" in str(ev_key):
                    phase89 = ev_val
                    break
            phase89_status = phase89.get("status")
            rules = policy.get("decision_rules", {})

            resp_post_status = str(phase89.get("post_status") or "").lower()
            if resp_post_status in {"publish", "published"}:
                status = "ABORT"
                freeze_required = True
                errors.append("post_status publish/published is forbidden")
            elif phase89.get("publish_allowed") is True:
                status = "ABORT"
                freeze_required = True
                errors.append("phase8_9 publish_allowed must be false")
            elif phase89_status == "RERUN_DRAFT_CREATED_PENDING_HUMAN_REVIEW":
                pid = phase89.get("post_id")
                pst = phase89.get("post_status")
                if not pid:
                    status = rules.get("rerun_failed", "RERUN_FREEZE_REQUIRED")
                    freeze_required = True
                    errors.append("post_id is required on rerun success")
                elif str(pst) != "draft":
                    status = rules.get("rerun_failed", "RERUN_FREEZE_REQUIRED")
                    freeze_required = True
                    errors.append(f"post_status must be draft but got {pst}")
                else:
                    status = rules.get("rerun_draft_created", "RERUN_DRAFT_VERIFIED_PENDING_HUMAN_REVIEW")
                    freeze_required = False
                    post_id = pid
                    post_status_val = pst
                    post_link = phase89.get("post_link")
            elif phase89_status in {"RERUN_NOT_EXECUTED_MISSING_CREDENTIALS", "NOT_EXECUTED_CREDENTIAL_PREFLIGHT_NOT_READY"}:
                status = rules.get("rerun_not_executed", "RERUN_NOT_EXECUTED_CONFIRMED")
                freeze_required = False
            elif phase89_status == "RERUN_DRAFT_CREATE_FAILED_FREEZE_REQUIRED":
                status = rules.get("rerun_failed", "RERUN_FREEZE_REQUIRED")
                freeze_required = True
            elif phase89_status == "ABORT":
                status = rules.get("abort", "ABORT")
                freeze_required = True
            elif phase89.get("wordpress_write_executed") is True and not phase89.get("post_id"):
                status = rules.get("rerun_failed", "RERUN_FREEZE_REQUIRED")
                freeze_required = True
                errors.append("wordpress_write_executed=true but post_id missing")
            else:
                status = rules.get("rerun_failed", "RERUN_FREEZE_REQUIRED")
                freeze_required = True
                warnings.append(f"unexpected phase8_9 status: {phase89_status}")

    if status == "RERUN_DRAFT_VERIFIED_PENDING_HUMAN_REVIEW":
        allowed_next_step = policy.get("allowed_next_step_on_success", "Phase 8-11 manual inspection of created WordPress draft")
    elif status == "RERUN_NOT_EXECUTED_CONFIRMED":
        allowed_next_step = policy.get(
            "allowed_next_step_on_not_executed",
            "Keep NO_GO, set credentials, then rerun Phase 8-6 to Phase 8-9 after explicit review",
        )
        post_id = None
        post_status_val = None
        post_link = None
    else:
        allowed_next_step = policy.get("allowed_next_step_on_freeze", "Manual freeze investigation, no auto cleanup")
        if status not in {"RERUN_DRAFT_VERIFIED_PENDING_HUMAN_REVIEW"}:
            post_id = None
            post_status_val = None
            post_link = None

    result = {
        "phase": "Phase 8-10",
        "status": status,
        "publish_allowed": False,
        "update_allowed": False,
        "delete_allowed": False,
        "auto_cleanup_allowed": False,
        "auto_post": False,
        "auto_update": False,
        "auto_delete": False,
        "auto_export": False,
        "human_review_required": True,
        "post_id": post_id,
        "post_status": post_status_val,
        "post_link": post_link,
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
        "# Phase 8-10 Post-Rerun Closure Report",
        "",
        "## Purpose",
        "- Verify Phase 8-9 rerun outcome and finalize controlled draft flow state.",
        "",
        "## Evidence Summary",
    ]
    for item in result.get("evidence_summary", []):
        lines.append(f"- {item.get('path')}: exists={item.get('exists')} status={item.get('status')}")

    lines.extend(
        [
            "",
            "## Rerun Decision",
            f"- status: {result.get('status')}",
            "",
            "## Draft Result",
            f"- post_id: {result.get('post_id')}",
            f"- post_status: {result.get('post_status')}",
            f"- post_link: {result.get('post_link')}",
            "",
            "## Safety Flags",
            f"- publish_allowed: {result.get('publish_allowed')}",
            f"- update_allowed: {result.get('update_allowed')}",
            f"- delete_allowed: {result.get('delete_allowed')}",
            f"- auto_cleanup_allowed: {result.get('auto_cleanup_allowed')}",
            f"- auto_post: {result.get('auto_post')}",
            f"- auto_update: {result.get('auto_update')}",
            f"- auto_delete: {result.get('auto_delete')}",
            f"- auto_export: {result.get('auto_export')}",
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
    result = generate_post_rerun_closure_report()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") in {
        "RERUN_DRAFT_VERIFIED_PENDING_HUMAN_REVIEW",
        "RERUN_NOT_EXECUTED_CONFIRMED",
        "RERUN_FREEZE_REQUIRED",
    } else 2


if __name__ == "__main__":
    raise SystemExit(main())
