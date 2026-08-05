#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_TEMPLATE_READY_NO_PUBLISH"
STATUS_READY = "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6R_SEPARATE_MANUAL_PUBLISH_APPROVAL_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6r_separate_manual_publish_approval_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.template.json")
    parser.add_argument("--approval", default="exchange/human_review/start_ls6r_separate_manual_publish_approval.json")
    parser.add_argument("--ls6q-ready-result", default="exchange/logs/start_ls6q_human_wordpress_draft_review_ready_result.json")
    parser.add_argument("--ls6q-review-result", default="exchange/human_review/start_ls6q_human_wordpress_draft_review_result.json")
    parser.add_argument("--ls6p-draft-verification-result", default="exchange/runtime/start_ls6p_wordpress_draft_verification_result.json")
    parser.add_argument("--ls6p-runtime-freeze-restore-result", default="exchange/runtime/start_ls6p_runtime_freeze_restore_result.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6p-validation-result", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_validation_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6r_separate_manual_publish_approval_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6r_separate_manual_publish_approval_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def validate_common(
    policy: dict[str, Any],
    ls6q_ready: dict[str, Any],
    ls6q_review: dict[str, Any],
    ls6p_verify: dict[str, Any],
    ls6p_freeze: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6p_validation: dict[str, Any],
    errors: list[str],
) -> None:
    require(policy.get("phase") == "LS-6R", "policy.phase mismatch", errors)
    require(policy.get("execution_mode") == "SEPARATE_APPROVAL_GATE_ONLY", "policy.execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    require(
        ls6q_ready.get("status")
        == safe_get(policy, "required_previous_phase", "ls6q", "required_ready_status"),
        "LS-6Q ready status mismatch",
        errors,
    )
    require(ls6q_ready.get("human_decision") == "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY", "LS-6Q human_decision mismatch", errors)
    require(ls6q_ready.get("manual_publish_allowed_by_this_phase") is False, "LS-6Q manual_publish_allowed_by_this_phase must be false", errors)
    require(ls6q_ready.get("manual_publish_executed") is False, "LS-6Q manual_publish_executed must be false", errors)
    require(safe_get(ls6q_ready, "next_phase", "phase") == "LS-6R", "LS-6Q next_phase.phase mismatch", errors)
    require(ls6q_ready.get("human_review_completed") is True, "LS-6Q human_review_completed must be true", errors)

    require(
        safe_get(ls6q_review, "human_decision", "decision")
        == safe_get(policy, "required_previous_phase", "ls6q", "required_human_decision"),
        "LS-6Q review_result human_decision mismatch",
        errors,
    )

    require(
        ls6p_validation.get("status")
        == safe_get(policy, "required_previous_phase", "ls6p", "required_validation_status"),
        "LS-6P validation status mismatch",
        errors,
    )

    post_id = to_int(ls6p_validation.get("post_id", ls6p_verify.get("post_id")))
    draft_verified = ls6p_validation.get("draft_verified", ls6p_verify.get("draft_verified"))
    require(post_id == 183, "LS-6P post_id mismatch", errors)
    require(draft_verified is True, "LS-6P draft_verified must be true", errors)
    require(ls6p_verify.get("returned_post_status") == "draft", "LS-6P returned_post_status mismatch", errors)

    require(ls6p_validation.get("runtime_freeze_restored") is True, "LS-6P runtime_freeze_restored must be true", errors)
    require(ls6p_freeze.get("runtime_freeze_restored") is True, "LS-6P runtime_freeze_restore result mismatch", errors)
    require(ls6p_lock.get("locked") is True, "LS-6P rerun prevention lock must be true", errors)
    require(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)


def validate_target_post(target: dict[str, Any], errors: list[str]) -> None:
    require(to_int(target.get("post_id")) == 183, "target_post.post_id mismatch", errors)
    require(target.get("expected_current_status") == "draft", "target_post.expected_current_status mismatch", errors)
    require(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    require(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def validate_current_phase_flags(data: dict[str, Any], errors: list[str]) -> None:
    keys = [
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "wordpress_draft_creation_executed",
        "wordpress_existing_post_update_executed",
        "wordpress_publish_executed",
        "publish_executed",
        "future_schedule_executed",
        "delete_executed",
        "post119_update_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_value_persisted",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "authorization_header_output",
        "ls6oc1_rerun_executed",
        "rerun_allowed",
    ]
    for key in keys:
        require(bool(data.get(key, False)) is False, f"current_phase_execution.{key} must be false", errors)


def validate_approval(approval_doc: dict[str, Any], errors: list[str]) -> None:
    require(approval_doc.get("approval_status") == "APPROVED_NO_PUBLISH_EXECUTION", "approval_status mismatch", errors)

    approval = approval_doc.get("approval", {})
    require(
        approval.get("approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
        "approval.approval_label mismatch",
        errors,
    )
    require(
        approval.get("required_approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
        "approval.required_approval_label mismatch",
        errors,
    )
    require(approval.get("approval_label_consumed") is False, "approval.approval_label_consumed must be false", errors)
    require(approval.get("manual_publish_allowed_by_this_phase") is False, "approval.manual_publish_allowed_by_this_phase must be false", errors)
    require(
        approval.get("manual_publish_execution_allowed_by_this_phase") is False,
        "approval.manual_publish_execution_allowed_by_this_phase must be false",
        errors,
    )
    require(approval.get("manual_publish_executed") is False, "approval.manual_publish_executed must be false", errors)
    require(approval.get("requires_next_phase") == "LS-6S", "approval.requires_next_phase mismatch", errors)


def validate_template(template_doc: dict[str, Any], errors: list[str]) -> None:
    require(template_doc.get("approval_status") == "TEMPLATE_NOT_APPROVED", "template approval_status mismatch", errors)
    approval = template_doc.get("approval", {})
    require(approval.get("approval_label") in ("", None), "template approval.approval_label must be empty", errors)
    require(
        approval.get("required_approval_label") == "APPROVED_FOR_SEPARATE_MANUAL_PUBLISH_APPROVAL_GATE_ONLY",
        "template required_approval_label mismatch",
        errors,
    )
    require(approval.get("approval_label_consumed") is False, "template approval_label_consumed must be false", errors)
    require(approval.get("manual_publish_allowed_by_this_phase") is False, "template manual_publish_allowed_by_this_phase must be false", errors)
    require(
        approval.get("manual_publish_execution_allowed_by_this_phase") is False,
        "template manual_publish_execution_allowed_by_this_phase must be false",
        errors,
    )
    require(approval.get("manual_publish_executed") is False, "template manual_publish_executed must be false", errors)


def build_result(
    status: str,
    target: dict[str, Any],
    approval: dict[str, Any],
    current_phase_execution: dict[str, Any],
    ls6q_ready: dict[str, Any],
    ls6p_verify: dict[str, Any],
    ls6p_validation: dict[str, Any],
    ls6p_freeze: dict[str, Any],
    ls6p_lock: dict[str, Any],
    separate_manual_publish_approval_recorded: bool,
    errors: list[str],
) -> dict[str, Any]:
    return {
        "phase": "LS-6R",
        "status": status,
        "execution_mode": "SEPARATE_APPROVAL_GATE_ONLY",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(target.get("post_id")),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "draft_verified": bool(ls6p_validation.get("draft_verified", ls6p_verify.get("draft_verified", False))),
        "returned_post_status": ls6p_verify.get("returned_post_status", ""),
        "ls6q_human_review_completed": bool(ls6q_ready.get("human_review_completed", False)),
        "ls6q_human_decision": ls6q_ready.get("human_decision", ""),
        "separate_manual_publish_approval_recorded": separate_manual_publish_approval_recorded,
        "approval_status": "APPROVED_NO_PUBLISH_EXECUTION" if separate_manual_publish_approval_recorded else "TEMPLATE_NOT_APPROVED",
        "approval_label": approval.get("approval_label", ""),
        "approval_label_consumed": bool(approval.get("approval_label_consumed", False)),
        "manual_publish_allowed_by_this_phase": bool(approval.get("manual_publish_allowed_by_this_phase", False)),
        "manual_publish_execution_allowed_by_this_phase": bool(
            approval.get("manual_publish_execution_allowed_by_this_phase", False)
        ),
        "manual_publish_executed": bool(approval.get("manual_publish_executed", False)),
        "wordpress_api_call_executed": bool(current_phase_execution.get("wordpress_api_call_executed", False)),
        "wordpress_write_executed": bool(current_phase_execution.get("wordpress_write_executed", False)),
        "wordpress_draft_creation_executed": bool(current_phase_execution.get("wordpress_draft_creation_executed", False)),
        "wordpress_existing_post_update_executed": bool(current_phase_execution.get("wordpress_existing_post_update_executed", False)),
        "wordpress_publish_executed": bool(current_phase_execution.get("wordpress_publish_executed", False)),
        "publish_executed": bool(current_phase_execution.get("publish_executed", False)),
        "future_schedule_executed": bool(current_phase_execution.get("future_schedule_executed", False)),
        "delete_executed": bool(current_phase_execution.get("delete_executed", False)),
        "post119_update_executed": bool(current_phase_execution.get("post119_update_executed", False)),
        "credential_env_read_executed": bool(current_phase_execution.get("credential_env_read_executed", False)),
        "credential_value_output": bool(current_phase_execution.get("credential_value_output", False)),
        "credential_value_persisted": bool(current_phase_execution.get("credential_value_persisted", False)),
        "credential_secret_output": bool(current_phase_execution.get("credential_secret_output", False)),
        "secret_length_output": bool(current_phase_execution.get("secret_length_output", False)),
        "secret_hash_output": bool(current_phase_execution.get("secret_hash_output", False)),
        "authorization_header_output": bool(current_phase_execution.get("authorization_header_output", False)),
        "runtime_freeze_restored": bool(ls6p_freeze.get("runtime_freeze_restored")),
        "rerun_prevention_finalized": bool(ls6p_lock.get("locked")),
        "rerun_allowed": bool(ls6p_lock.get("rerun_allowed")),
        "ls6oc1_rerun_executed": bool(current_phase_execution.get("ls6oc1_rerun_executed", False)),
        "next_phase": {
            "phase": "LS-6S",
            "execution_allowed": False,
            "manual_publish_execution_allowed_by_this_phase": False,
            "requires_final_publish_preflight": True,
            "requires_separate_execute_now_confirmation": True,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    lines = [
        "# LS-6R Separate Manual Publish Approval Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- ls6q_human_review_completed: {result['ls6q_human_review_completed']}",
        f"- ls6q_human_decision: {result['ls6q_human_decision']}",
        f"- separate_manual_publish_approval_recorded: {result['separate_manual_publish_approval_recorded']}",
        f"- approval_status: {result['approval_status']}",
        f"- approval_label: {result['approval_label']}",
        f"- approval_label_consumed: {result['approval_label_consumed']}",
        f"- manual_publish_allowed_by_this_phase: {result['manual_publish_allowed_by_this_phase']}",
        f"- manual_publish_execution_allowed_by_this_phase: {result['manual_publish_execution_allowed_by_this_phase']}",
        f"- manual_publish_executed: {result['manual_publish_executed']}",
        "",
        "## Errors",
    ]
    if result["errors"]:
        lines.extend(f"- {item}" for item in result["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    args = parse_args()

    policy = load_json(Path(args.policy))
    template_doc = load_json(Path(args.template))
    approval_path = Path(args.approval)
    approval_doc = load_json(approval_path) if approval_path.exists() else None

    ls6q_ready = load_json(Path(args.ls6q_ready_result))
    ls6q_review = load_json(Path(args.ls6q_review_result))
    ls6p_verify = load_json(Path(args.ls6p_draft_verification_result))
    ls6p_freeze = load_json(Path(args.ls6p_runtime_freeze_restore_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6p_validation = load_json(Path(args.ls6p_validation_result))

    errors: list[str] = []
    validate_common(policy, ls6q_ready, ls6q_review, ls6p_verify, ls6p_freeze, ls6p_lock, ls6p_validation, errors)

    target_source = template_doc if args.allow_template else (approval_doc or {})
    validate_target_post(target_source.get("target_post", {}), errors)

    if args.allow_template:
        validate_template(template_doc, errors)
        validate_current_phase_flags(template_doc.get("current_phase_execution", {}), errors)
        approval_data = template_doc.get("approval", {})
        current_phase_execution = template_doc.get("current_phase_execution", {})
        recorded = False
    else:
        require(approval_doc is not None, "approval file missing", errors)
        if approval_doc is None:
            approval_data = {}
            current_phase_execution = {}
            recorded = False
        else:
            validate_approval(approval_doc, errors)
            validate_current_phase_flags(approval_doc.get("current_phase_execution", {}), errors)
            approval_data = approval_doc.get("approval", {})
            current_phase_execution = approval_doc.get("current_phase_execution", {})
            recorded = True

    status = STATUS_NOT_READY
    if not errors:
        status = STATUS_TEMPLATE_READY if args.allow_template else STATUS_READY

    result = build_result(
        status=status,
        target=target_source.get("target_post", {}),
        approval=approval_data,
        current_phase_execution=current_phase_execution,
        ls6q_ready=ls6q_ready,
        ls6p_verify=ls6p_verify,
        ls6p_validation=ls6p_validation,
        ls6p_freeze=ls6p_freeze,
        ls6p_lock=ls6p_lock,
        separate_manual_publish_approval_recorded=recorded,
        errors=errors,
    )

    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
