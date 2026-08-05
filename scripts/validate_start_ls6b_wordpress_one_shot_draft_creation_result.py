#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_success(result: dict[str, Any], errors: list[str]) -> None:
    require(result.get("phase") == "LS-6B", "phase must be LS-6B", errors)
    require(result.get("status") == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN", "status mismatch for success", errors)
    require(result.get("execution_mode") == "ONE_SHOT_WRITE_ALLOWED", "execution_mode mismatch", errors)
    require(result.get("production_status") == "LIMITED_GO_DRAFT_ONLY", "production_status mismatch", errors)
    require(result.get("approval_label") == "APPROVED_FOR_ONE_SHOT_DRAFT_CREATION_ONLY", "approval_label mismatch", errors)
    require(result.get("approval_is_actual") is True, "approval_is_actual must be true", errors)
    require(isinstance(result.get("post_id"), int), "post_id must exist", errors)
    require(result.get("post_status") == "draft", "post_status must be draft", errors)
    require(result.get("max_items") == 1, "max_items must be 1", errors)
    require(result.get("payload_count") == 1, "payload_count must be 1", errors)
    require(result.get("wordpress_api_call_executed") is True, "wordpress_api_call_executed must be true", errors)
    require(result.get("wordpress_write_executed") is True, "wordpress_write_executed must be true", errors)
    require(result.get("wordpress_draft_creation_executed") is True, "wordpress_draft_creation_executed must be true", errors)
    require(result.get("publish_executed") is False, "publish_executed must be false", errors)
    require(result.get("future_schedule_executed") is False, "future_schedule_executed must be false", errors)
    require(result.get("existing_post_update_executed") is False, "existing_post_update_executed must be false", errors)
    require(result.get("delete_executed") is False, "delete_executed must be false", errors)
    require(result.get("amazon_api_call_executed") is False, "amazon_api_call_executed must be false", errors)
    require(result.get("x_api_call_executed") is False, "x_api_call_executed must be false", errors)
    require(result.get("x_post_executed") is False, "x_post_executed must be false", errors)
    require(result.get("credential_secret_output") is False, "credential_secret_output must be false", errors)
    require(result.get("secret_length_output") is False, "secret_length_output must be false", errors)
    require(result.get("secret_hash_output") is False, "secret_hash_output must be false", errors)
    require(result.get("approval_token_consumed") is True, "approval_token_consumed must be true", errors)
    require(result.get("freeze_after_run_executed") is True, "freeze_after_run_executed must be true", errors)
    require(result.get("safe_stop") is False, "safe_stop must be false", errors)
    next_phase = result.get("next_phase", {})
    require(next_phase.get("phase") == "LS-7", "next_phase.phase must be LS-7", errors)
    require(next_phase.get("execution_allowed") is False, "next_phase.execution_allowed must be false", errors)
    require(next_phase.get("requires_human_review") is True, "next_phase.requires_human_review must be true", errors)
    require(next_phase.get("manual_publish_only") is True, "next_phase.manual_publish_only must be true", errors)


def validate_preflight(result: dict[str, Any], errors: list[str]) -> None:
    require(result.get("phase") == "LS-6B", "phase must be LS-6B", errors)
    require(result.get("status") == "LS6B_ONE_SHOT_DRAFT_CREATION_PREFLIGHT_PASS_NO_EXECUTION", "status mismatch for preflight", errors)
    require(result.get("wordpress_api_call_executed") is False, "preflight wordpress_api_call_executed must be false", errors)
    require(result.get("wordpress_write_executed") is False, "preflight wordpress_write_executed must be false", errors)
    require(result.get("wordpress_draft_creation_executed") is False, "preflight wordpress_draft_creation_executed must be false", errors)
    require(result.get("approval_token_consumed") is False, "preflight approval_token_consumed must be false", errors)


def validate_safe_stop(result: dict[str, Any], errors: list[str]) -> None:
    require(result.get("status") in {"LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP", "LS6B_ONE_SHOT_ALREADY_EXECUTED_LOCKED"}, "safe stop status mismatch", errors)
    require(result.get("safe_stop") is True, "safe_stop must be true", errors)
    require(result.get("publish_executed") is False, "publish_executed must be false", errors)


def classify_and_validate(result: dict[str, Any]) -> tuple[str, list[str]]:
    errors: list[str] = []
    status = result.get("status")
    if status == "LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATED_AND_FROZEN":
        validate_success(result, errors)
        return ("LS6B_ONE_SHOT_DRAFT_CREATION_RESULT_VALIDATED" if not errors else "LS6B_RESULT_VALIDATION_FAILED", errors)
    if status == "LS6B_ONE_SHOT_DRAFT_CREATION_PREFLIGHT_PASS_NO_EXECUTION":
        validate_preflight(result, errors)
        return ("LS6B_PREFLIGHT_RESULT_VALIDATED_NO_EXECUTION" if not errors else "LS6B_RESULT_VALIDATION_FAILED", errors)
    if status in {"LS6B_WORDPRESS_ONE_SHOT_DRAFT_CREATION_FAILED_SAFE_STOP", "LS6B_ONE_SHOT_ALREADY_EXECUTED_LOCKED"}:
        validate_safe_stop(result, errors)
        return ("LS6B_SAFE_STOP_RESULT_RECORDED" if not errors else "LS6B_RESULT_VALIDATION_FAILED", errors)
    return "LS6B_RESULT_VALIDATION_FAILED", ["unknown result status"]


def validate_result(result: dict[str, Any]) -> tuple[str, list[str]]:
    return classify_and_validate(result)


def write_report(payload: dict[str, Any], report_path: Path) -> None:
    lines = [
        "# LS-6B One-shot Draft Creation Validation Report",
        "",
        f"- generated_at: {payload['generated_at']}",
        f"- validation_status: {payload['validation_status']}",
        f"- source_status: {payload.get('source_status')}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")
    lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--result", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls6b_wordpress_one_shot_draft_creation_validation_result.json")
    p.add_argument("--report", default="reports/start_ls6b_wordpress_one_shot_draft_creation_validation_report.md")
    return p.parse_args()


def main() -> int:
    a = parse_args()
    result = load_json(Path(a.result))
    validation_status, errors = classify_and_validate(result)
    out = {
        "phase": "LS-6B",
        "validation_status": validation_status,
        "source_status": result.get("status"),
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    output_path = Path(a.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out, Path(a.report))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
