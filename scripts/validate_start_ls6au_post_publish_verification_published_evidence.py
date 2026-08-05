#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STATUS_VALIDATED = "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATED"
STATUS_NOT_VALIDATED = "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_NOT_VALIDATED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--policy",
        default="config/start_ls6au_post_publish_verification_published_evidence_policy.json",
    )
    parser.add_argument(
        "--post-publish-verification-result",
        default="exchange/runtime/start_ls6au_post_publish_verification_published_evidence_result.json",
    )
    parser.add_argument(
        "--post-publish-verification-lock",
        default="exchange/locks/start_ls6au_post_publish_verification_published_evidence.lock.json",
    )
    parser.add_argument(
        "--run-result",
        default="exchange/logs/start_ls6au_post_publish_verification_published_evidence_result.json",
    )
    parser.add_argument(
        "--ls6at-publish-execution-result",
        default="exchange/runtime/start_ls6at_actual_publish_execution_runner_separated_publish_execution_result.json",
    )
    parser.add_argument(
        "--ls6at-publish-execution-lock",
        default="exchange/locks/start_ls6at_actual_publish_execution_runner_separated_publish_execution.lock.json",
    )
    parser.add_argument(
        "--ls6at-validation-result",
        default="exchange/logs/start_ls6at_actual_publish_execution_runner_separated_publish_execution_validation_result.json",
    )
    parser.add_argument(
        "--output",
        default="exchange/logs/start_ls6au_post_publish_verification_published_evidence_validation_result.json",
    )
    parser.add_argument(
        "--report",
        default="reports/start_ls6au_post_publish_verification_published_evidence_validation_report.md",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing file: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json: {path}")
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-6AU Post Publish Verification Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- phase: {payload['phase']}",
        f"- status: {payload['status']}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- post_id: {payload.get('post_id', 0)}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    result = try_load_json(Path(args.post_publish_verification_result), errors)
    lock = try_load_json(Path(args.post_publish_verification_lock), errors)
    run_result = try_load_json(Path(args.run_result), errors)
    ls6at_result = try_load_json(Path(args.ls6at_publish_execution_result), errors)
    ls6at_lock = try_load_json(Path(args.ls6at_publish_execution_lock), errors)
    ls6at_validation = try_load_json(Path(args.ls6at_validation_result), errors)

    target = policy.get("target_post", {})
    post_id = int(target.get("post_id", 0))

    req(policy.get("phase") == "LS-6AU", "policy.phase mismatch", errors)
    req(result.get("status") == "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_PASSED", "status mismatch", errors)
    req(result == run_result, "result and run_result mismatch", errors)
    req(result.get("production_status") == "PUBLISHED_VERIFIED", "production_status mismatch", errors)
    req(int(result.get("post_id", 0)) == post_id, "post_id mismatch", errors)
    req(str(result.get("rest_returned_post_status", "")) == "publish", "rest status mismatch", errors)
    req(bool(result.get("public_url_reachable", False)) is True, "public_url_reachable mismatch", errors)
    req(bool(result.get("post_publish_verified", False)) is True, "post_publish_verified mismatch", errors)
    req(bool(result.get("published_evidence_recorded", False)) is True, "published_evidence_recorded mismatch", errors)
    req(bool(result.get("rollback_readiness_recorded", False)) is True, "rollback_readiness_recorded mismatch", errors)
    req(bool(result.get("rollback_executed", False)) is False, "rollback_executed mismatch", errors)
    req(bool(result.get("unpublish_executed", False)) is False, "unpublish_executed mismatch", errors)
    req(bool(result.get("draft_revert_executed", False)) is False, "draft_revert_executed mismatch", errors)
    req(bool(result.get("wordpress_post_executed", False)) is False, "wordpress_post_executed mismatch", errors)
    req(bool(result.get("wordpress_write_executed_by_this_phase", False)) is False, "wordpress_write_executed_by_this_phase mismatch", errors)
    req(bool(result.get("publish_executed_by_this_phase", False)) is False, "publish_executed_by_this_phase mismatch", errors)
    req(bool(result.get("post119_update_executed", False)) is False, "post119_update_executed mismatch", errors)
    req(bool(result.get("credential_value_output", False)) is False, "credential_value_output mismatch", errors)
    req(bool(result.get("secret_length_output", False)) is False, "secret_length_output mismatch", errors)
    req(bool(result.get("secret_hash_output", False)) is False, "secret_hash_output mismatch", errors)
    req(bool(result.get("rerun_allowed", False)) is False, "rerun_allowed mismatch", errors)
    req(str(result.get("completion_status", "")) == "START_LS_ONE_SHOT_PUBLISH_CHAIN_PUBLISHED_AND_VERIFIED", "completion_status mismatch", errors)
    req(bool(result.get("start_ls_one_shot_publish_chain_closed", False)) is True, "chain closed mismatch", errors)

    req(lock.get("status") == "LS6AU_POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_LOCKED", "lock status mismatch", errors)
    req(bool(lock.get("locked", False)) is True, "lock mismatch", errors)

    req(ls6at_result.get("status") == "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_PASSED_PUBLISHED", "LS-6AT run status mismatch", errors)
    req(ls6at_validation.get("status") == "LS6AT_ACTUAL_PUBLISH_EXECUTION_RUNNER_SEPARATED_PUBLISH_EXECUTION_VALIDATED_PUBLISHED", "LS-6AT validation status mismatch", errors)
    req(bool(ls6at_lock.get("locked", False)) is True, "LS-6AT lock mismatch", errors)

    status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": "LS-6AU",
        "document_type": "POST_PUBLISH_VERIFICATION_PUBLISHED_EVIDENCE_VALIDATION_RESULT",
        "status": status,
        "run_status": str(result.get("status", "")),
        "execution_mode": str(result.get("execution_mode", "")),
        "production_status": str(result.get("production_status", "")),
        "post_id": int(result.get("post_id", 0)),
        "post_link": str(result.get("post_link", "")),
        "payload_title": str(result.get("payload_title", "")),
        "payload_asin": str(result.get("payload_asin", "")),
        "rest_returned_post_status": str(result.get("rest_returned_post_status", "")),
        "public_url_reachable": bool(result.get("public_url_reachable", False)),
        "post_publish_verified": bool(result.get("post_publish_verified", False)),
        "published_evidence_recorded": bool(result.get("published_evidence_recorded", False)),
        "rollback_readiness_recorded": bool(result.get("rollback_readiness_recorded", False)),
        "rollback_executed": bool(result.get("rollback_executed", False)),
        "unpublish_executed": bool(result.get("unpublish_executed", False)),
        "draft_revert_executed": bool(result.get("draft_revert_executed", False)),
        "wordpress_post_executed": bool(result.get("wordpress_post_executed", False)),
        "wordpress_write_executed_by_this_phase": bool(result.get("wordpress_write_executed_by_this_phase", False)),
        "publish_executed_by_this_phase": bool(result.get("publish_executed_by_this_phase", False)),
        "post119_update_executed": bool(result.get("post119_update_executed", False)),
        "credential_value_output": bool(result.get("credential_value_output", False)),
        "secret_length_output": bool(result.get("secret_length_output", False)),
        "secret_hash_output": bool(result.get("secret_hash_output", False)),
        "rerun_allowed": bool(result.get("rerun_allowed", False)),
        "completion_status": str(result.get("completion_status", "")),
        "start_ls_one_shot_publish_chain_closed": bool(result.get("start_ls_one_shot_publish_chain_closed", False)),
        "next_phase": result.get("next_phase", {}),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
