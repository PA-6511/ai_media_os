#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config/phase8_50_prep_one_shot_draft_creation_final_approval_checklist_policy.json"
DEFAULT_REVIEW = ROOT / "exchange/human_review/phase8_50_prep_one_shot_draft_creation_final_approval_checklist.example.json"
DEFAULT_OUTPUT_JSON = ROOT / "exchange/logs/phase8_50_prep_one_shot_draft_creation_final_approval_checklist_result.json"
DEFAULT_OUTPUT_MD = ROOT / "exchange/logs/phase8_50_prep_one_shot_draft_creation_final_approval_checklist_result.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_root(path: Path) -> Path:
    if path.parent.name == "config":
        return path.parent.parent
    return path.parent


def _write_outputs(result: dict[str, Any], output_json_path: Path, output_md_path: Path) -> None:
    output_json_path.parent.mkdir(parents=True, exist_ok=True)
    output_md_path.parent.mkdir(parents=True, exist_ok=True)
    output_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# Phase 8-50-PREP One-Shot Draft Creation Final Approval Checklist Result",
        "",
        f"- status: {result.get('status')}",
        f"- decision: {result.get('decision')}",
        f"- approval_label: {result.get('approval_label')}",
        f"- approval_label_consumed: {result.get('approval_label_consumed')}",
        f"- one_shot_lock_exists: {result.get('one_shot_lock_exists')}",
        f"- rollback_plan_defined: {result.get('rollback_plan_defined')}",
        f"- freeze_plan_defined: {result.get('freeze_plan_defined')}",
        f"- execution_allowed: {result.get('execution_allowed')}",
        f"- actual_go_decision_issued: {result.get('actual_go_decision_issued')}",
        f"- wordpress_api_call_allowed: {result.get('wordpress_api_call_allowed')}",
        f"- wordpress_write_executed: {result.get('wordpress_write_executed')}",
        f"- wordpress_draft_created: {result.get('wordpress_draft_created')}",
        f"- secret_values_output: {result.get('secret_values_output')}",
        "",
        "## Next Step",
        f"- {result.get('allowed_next_step')}",
    ]
    output_md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_phase8_50_prep(
    policy_path: Path = DEFAULT_POLICY,
    review_path: Path = DEFAULT_REVIEW,
    output_json_path: Path = DEFAULT_OUTPUT_JSON,
    output_md_path: Path = DEFAULT_OUTPUT_MD,
) -> dict[str, Any]:
    policy = _load_json(policy_path)
    root = _resolve_root(policy_path)

    errors: list[str] = []
    warnings: list[str] = []
    safety_violations: list[str] = []
    evidence_summary: list[dict[str, Any]] = []

    for flag in [
        "checklist_is_execution_permission",
        "execution_allowed",
        "actual_go_decision_issued",
        "wordpress_api_call_allowed",
        "wordpress_write_executed",
        "wordpress_draft_created",
        "secret_values_output",
        "approval_label_consumed",
    ]:
        if policy.get(flag) is not False:
            safety_violations.append(f"policy.{flag} must be false")

    missing_evidence = False
    bad_status = False
    required_statuses = policy.get("required_statuses", {})
    for rel in policy.get("required_evidence", []):
        p = root / rel
        if not p.exists():
            missing_evidence = True
            errors.append(f"missing_evidence: {rel}")
            evidence_summary.append({"path": rel, "exists": False, "status": None})
            continue
        payload = _load_json(p)
        status = payload.get("status") or payload.get("overall_status")
        evidence_summary.append({"path": rel, "exists": True, "status": status})
        if status not in set(required_statuses.get(rel, [])):
            bad_status = True
            errors.append(f"unexpected_status: {rel}={status}")

    review = _load_json(review_path)
    decision = str(review.get("decision", ""))
    approval_label = review.get("approval_label")
    approval_label_consumed = bool(review.get("approval_label_consumed", False))
    one_shot_lock_exists = bool(review.get("one_shot_lock_exists", False))
    rollback_plan_defined = bool(review.get("rollback_plan_defined", False))
    freeze_plan_defined = bool(review.get("freeze_plan_defined", False))

    if review.get("secret_values_included") is True:
        safety_violations.append("review.secret_values_included must be false")
    if review.get("target_item_count") != 1:
        safety_violations.append("review.target_item_count must be 1")
    if approval_label != policy.get("required_approval_label"):
        safety_violations.append(
            f"review.approval_label must be {policy.get('required_approval_label')}"
        )
    if approval_label_consumed:
        safety_violations.append("approval_label_consumed must be false")
    if one_shot_lock_exists:
        safety_violations.append("one_shot_lock_exists must be false")
    if not rollback_plan_defined:
        safety_violations.append("rollback_plan_defined must be true")
    if not freeze_plan_defined:
        safety_violations.append("freeze_plan_defined must be true")
    if review.get("no_secret_output_compliance") is not True:
        safety_violations.append("no_secret_output_compliance must be true")
    if review.get("post_execution_freeze_restore_plan_defined") is not True:
        safety_violations.append("post_execution_freeze_restore_plan_defined must be true")
    if review.get("failure_rollback_abort_ready") is not True:
        safety_violations.append("failure_rollback_abort_ready must be true")

    for ack in policy.get("required_review_acknowledgements", []):
        if review.get(ack) is not True:
            safety_violations.append(f"review.{ack} must be true")

    if decision not in set(policy.get("allowed_decisions", [])):
        safety_violations.append(f"unknown_decision: {decision}")

    if safety_violations:
        status = "ABORT"
    elif missing_evidence or bad_status:
        status = "FAIL"
    elif decision == "FINAL_APPROVAL_CHECKLIST_READY_NO_EXECUTION":
        status = "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_PASS_NO_EXECUTION"
    elif decision == "REQUEST_FIX":
        status = "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_REQUEST_FIX_NO_EXECUTION"
    elif decision == "REJECT":
        status = "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_REJECTED_NO_EXECUTION"
    elif decision == "ABORT":
        status = "ABORT"
    else:
        status = "FAIL"

    if status == "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_PASS_NO_EXECUTION":
        allowed_next_step = policy.get("allowed_next_step_if_ready", "")
    else:
        allowed_next_step = policy.get("allowed_next_step_if_fix_required", "")

    result = {
        "phase": "Phase 8-50-PREP",
        "status": status,
        "production_status": "NO_GO",
        "execution": "DRY_RUN",
        "execution_allowed": False,
        "actual_go_decision_issued": False,
        "wordpress_api_call_allowed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_created": False,
        "secret_values_output": False,
        "decision": decision,
        "approval_label": approval_label,
        "approval_label_consumed": approval_label_consumed,
        "one_shot_lock_exists": one_shot_lock_exists,
        "rollback_plan_defined": rollback_plan_defined,
        "freeze_plan_defined": freeze_plan_defined,
        "errors": errors,
        "warnings": warnings,
        "safety_violations": safety_violations,
        "evidence_summary": evidence_summary,
        "allowed_next_step": allowed_next_step,
        "checked_at": _now_iso(),
    }
    _write_outputs(result, output_json_path, output_md_path)
    return result


def main() -> int:
    result = validate_phase8_50_prep()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    acceptable = {
        "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_PASS_NO_EXECUTION",
        "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_REQUEST_FIX_NO_EXECUTION",
        "PHASE8_50_PREP_FINAL_APPROVAL_CHECKLIST_REJECTED_NO_EXECUTION",
        "FAIL",
    }
    return 0 if result.get("status") in acceptable else 2


if __name__ == "__main__":
    raise SystemExit(main())