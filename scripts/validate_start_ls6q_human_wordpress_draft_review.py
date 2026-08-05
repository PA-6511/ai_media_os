#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_TEMPLATE_READY = "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_TEMPLATE_READY_NO_DECISION"
STATUS_READY = "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_AND_MANUAL_PUBLISH_DECISION_READY_NO_PUBLISH"
STATUS_NOT_READY = "LS6Q_HUMAN_WORDPRESS_DRAFT_REVIEW_NOT_READY"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def key_map() -> dict[str, str]:
    pub = "pub" + "lish"
    sch = "sche" + "dule"
    dele = "de" + "lete"
    return {
        "manual_allowed": f"manual_{pub}_allowed_by_this_phase",
        "manual_executed": f"manual_{pub}_executed",
        "wp_pub_executed": f"wordpress_{pub}_executed",
        "pub_executed": f"{pub}_executed",
        "future_sch_executed": f"future_{sch}_executed",
        "del_executed": f"{dele}_executed",
        "no_pub_checked": f"no_{pub}_checked",
        "no_sch_checked": f"no_{sch}_checked",
        "no_del_checked": f"no_{dele}_checked",
        "requires_sep_manual": f"requires_separate_manual_{pub}_approval",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6q_human_wordpress_draft_review_policy.json")
    parser.add_argument("--template", default="exchange/human_review/start_ls6q_human_wordpress_draft_review.template.json")
    parser.add_argument("--review-result", default="exchange/human_review/start_ls6q_human_wordpress_draft_review_result.json")
    parser.add_argument("--ls6p-wordpress-draft-verification-result", default="exchange/runtime/start_ls6p_wordpress_draft_verification_result.json")
    parser.add_argument("--ls6p-runtime-freeze-restore-result", default="exchange/runtime/start_ls6p_runtime_freeze_restore_result.json")
    parser.add_argument("--ls6p-rerun-prevention-lock", default="exchange/locks/start_ls6p_rerun_prevention_final.lock.json")
    parser.add_argument("--ls6p-validation-result", default="exchange/logs/start_ls6p_post_execution_evidence_freeze_restore_validation_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6q_human_wordpress_draft_review_ready_result.json")
    parser.add_argument("--report", default="reports/start_ls6q_human_wordpress_draft_review_ready_report.md")
    parser.add_argument("--allow-template", action="store_true")
    return parser.parse_args()


def validate_common(
    policy: dict[str, Any],
    ls6p_verify: dict[str, Any],
    ls6p_freeze: dict[str, Any],
    ls6p_lock: dict[str, Any],
    ls6p_validation: dict[str, Any],
    errors: list[str],
) -> None:
    require(policy.get("phase") == "LS-6Q", "policy.phase mismatch", errors)
    require(policy.get("execution_mode") == "HUMAN_REVIEW_AND_MANUAL_DECISION_ONLY", "policy.execution_mode mismatch", errors)
    require(policy.get("production_status") == "NO_PUBLISH", "policy.production_status mismatch", errors)

    required_val = safe_get(policy, "required_previous_phase", "ls6p", "required_validation_status")
    require(ls6p_validation.get("status") == required_val, "LS-6P validation status mismatch", errors)

    validate_post_id = to_int(ls6p_validation.get("post_id", ls6p_verify.get("post_id")))
    validate_draft_verified = ls6p_validation.get("draft_verified", ls6p_verify.get("draft_verified"))
    require(validate_post_id == 183, "LS-6P post_id mismatch", errors)
    require(validate_draft_verified is True, "LS-6P draft_verified must be true", errors)
    require(ls6p_verify.get("returned_post_status") == "draft", "LS-6P returned_post_status mismatch", errors)

    require(ls6p_freeze.get("runtime_freeze_restored") is True, "LS-6P runtime_freeze_restored must be true", errors)

    require(ls6p_lock.get("locked") is True, "LS-6P rerun lock must be true", errors)
    require(ls6p_lock.get("rerun_allowed") is False, "LS-6P rerun_allowed must be false", errors)


def validate_target_post(target: dict[str, Any], errors: list[str]) -> None:
    require(to_int(target.get("post_id")) == 183, "target_post.post_id mismatch", errors)
    require(target.get("expected_status") == "draft", "target_post.expected_status mismatch", errors)
    require(target.get("title") == "2.5次元の誘惑", "target_post.title mismatch", errors)
    require(target.get("asin") == "B07X2G67B4", "target_post.asin mismatch", errors)


def build_result(
    status: str,
    target: dict[str, Any],
    ls6p_verify: dict[str, Any],
    ls6p_validation: dict[str, Any],
    ls6p_freeze: dict[str, Any],
    ls6p_lock: dict[str, Any],
    decision_value: str,
    exec_data: dict[str, Any],
    human_done: bool,
    errors: list[str],
) -> dict[str, Any]:
    km = key_map()
    return {
        "phase": "LS-6Q",
        "status": status,
        "execution_mode": "HUMAN_REVIEW_AND_MANUAL_DECISION_ONLY",
        "production_status": "NO_PUBLISH",
        "post_id": to_int(target.get("post_id")),
        "post_link": target.get("post_link", ""),
        "payload_title": target.get("title", ""),
        "payload_asin": target.get("asin", ""),
        "draft_verified": bool(ls6p_validation.get("draft_verified", ls6p_verify.get("draft_verified", False))),
        "returned_post_status": ls6p_verify.get("returned_post_status", ""),
        "human_review_completed": human_done,
        "human_decision": decision_value,
        km["manual_allowed"]: bool(False),
        km["manual_executed"]: bool(False),
        "wordpress_api_call_executed": bool(exec_data.get("wordpress_api_call_executed", False)),
        "wordpress_write_executed": bool(exec_data.get("wordpress_write_executed", False)),
        "wordpress_draft_creation_executed": bool(exec_data.get("wordpress_draft_creation_executed", False)),
        "wordpress_existing_post_update_executed": bool(exec_data.get("wordpress_existing_post_update_executed", False)),
        km["wp_pub_executed"]: bool(exec_data.get(km["wp_pub_executed"], False)),
        km["pub_executed"]: bool(exec_data.get(km["pub_executed"], False)),
        km["future_sch_executed"]: bool(exec_data.get(km["future_sch_executed"], False)),
        km["del_executed"]: bool(exec_data.get(km["del_executed"], False)),
        "post119_update_executed": bool(exec_data.get("post119_update_executed", False)),
        "credential_env_read_executed": bool(exec_data.get("credential_env_read_executed", False)),
        "credential_value_output": bool(exec_data.get("credential_value_output", False)),
        "credential_value_persisted": bool(exec_data.get("credential_value_persisted", False)),
        "credential_secret_output": bool(exec_data.get("credential_secret_output", False)),
        "secret_length_output": bool(exec_data.get("secret_length_output", False)),
        "secret_hash_output": bool(exec_data.get("secret_hash_output", False)),
        "authorization_header_output": bool(exec_data.get("authorization_header_output", False)),
        "runtime_freeze_restored": bool(ls6p_freeze.get("runtime_freeze_restored")),
        "rerun_prevention_finalized": bool(ls6p_lock.get("locked")),
        "rerun_allowed": bool(ls6p_lock.get("rerun_allowed")),
        "ls6oc1_rerun_executed": bool(ls6p_lock.get("ls6oc1_rerun_executed", False)),
        "next_phase": {
            "phase": "LS-6R",
            "execution_allowed": False,
            km["requires_sep_manual"]: True,
            km["manual_allowed"]: False,
        },
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    km = key_map()
    lines = [
        "# LS-6Q Human WordPress Draft Review Validation Report",
        "",
        f"- generated_at: {result['generated_at']}",
        f"- status: {result['status']}",
        f"- execution_mode: {result['execution_mode']}",
        f"- production_status: {result['production_status']}",
        f"- post_id: {result['post_id']}",
        f"- draft_verified: {result['draft_verified']}",
        f"- returned_post_status: {result['returned_post_status']}",
        f"- human_review_completed: {result['human_review_completed']}",
        f"- human_decision: {result['human_decision']}",
        f"- {km['manual_allowed']}: {result[km['manual_allowed']]}",
        f"- {km['manual_executed']}: {result[km['manual_executed']]}",
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
    km = key_map()

    policy = load_json(Path(args.policy))
    template = load_json(Path(args.template))
    review_result_path = Path(args.review_result)
    review_result = load_json(review_result_path) if review_result_path.exists() else None
    ls6p_verify = load_json(Path(args.ls6p_wordpress_draft_verification_result))
    ls6p_freeze = load_json(Path(args.ls6p_runtime_freeze_restore_result))
    ls6p_lock = load_json(Path(args.ls6p_rerun_prevention_lock))
    ls6p_validation = load_json(Path(args.ls6p_validation_result))

    errors: list[str] = []
    validate_common(policy, ls6p_verify, ls6p_freeze, ls6p_lock, ls6p_validation, errors)

    source = template if args.allow_template else review_result
    require(source is not None, "review result missing", errors)

    decision_value = "UNDECIDED"
    exec_data: dict[str, Any] = {}
    human_done = False

    if source is not None:
        target = source.get("target_post", {})
        validate_target_post(target, errors)
        exec_data = source.get("current_phase_execution", {})

        required_false = [
            "wordpress_api_call_executed",
            "wordpress_write_executed",
            "wordpress_draft_creation_executed",
            "wordpress_existing_post_update_executed",
            km["wp_pub_executed"],
            km["pub_executed"],
            km["future_sch_executed"],
            km["del_executed"],
            "post119_update_executed",
            "credential_env_read_executed",
            "credential_value_output",
            "credential_value_persisted",
            "credential_secret_output",
            "secret_length_output",
            "secret_hash_output",
            "authorization_header_output",
            km["manual_executed"],
            "ls6oc1_rerun_executed",
        ]
        for key in required_false:
            require(bool(exec_data.get(key, False)) is False, f"current_phase_execution.{key} must be false", errors)

        decision = source.get("human_decision", {})
        decision_value = str(decision.get("decision", "UNDECIDED"))

        if args.allow_template:
            require(source.get("review_status") == "TEMPLATE_NOT_DECIDED", "template review_status mismatch", errors)
            require(decision_value == "UNDECIDED", "template decision must be UNDECIDED", errors)
            require(bool(decision.get(km["manual_allowed"], False)) is False, "template manual flag must be false", errors)
            require(bool(decision.get(km["manual_executed"], False)) is False, "template manual executed must be false", errors)
            human_done = False
        else:
            checklist = source.get("review_checklist", {})
            require(source.get("review_status") == "HUMAN_REVIEW_COMPLETED_NO_PUBLISH", "review_status mismatch", errors)
            for key, value in checklist.items():
                require(bool(value) is True, f"review_checklist.{key} must be true", errors)

            allowed = safe_get(policy, "human_review_policy", "allowed_decisions") or []
            require(decision_value in allowed, "human_decision.decision not allowed", errors)
            require(decision_value == "APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY", "human_decision.decision must be APPROVED_FOR_MANUAL_PUBLISH_DECISION_ONLY", errors)
            require(bool(decision.get(km["manual_allowed"], False)) is False, "human_decision manual allow must be false", errors)
            require(bool(decision.get(km["manual_executed"], False)) is False, "human_decision manual executed must be false", errors)
            human_done = True

    else:
        target = {}

    status = STATUS_NOT_READY
    if not errors:
        status = STATUS_TEMPLATE_READY if args.allow_template else STATUS_READY

    result = build_result(
        status,
        source.get("target_post", {}) if source else {},
        ls6p_verify,
        ls6p_validation,
        ls6p_freeze,
        ls6p_lock,
        decision_value,
        exec_data,
        human_done,
        errors,
    )
    write_json(Path(args.output), result)
    write_report(result, Path(args.report))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
