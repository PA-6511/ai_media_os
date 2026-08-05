#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_VALIDATED = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
STATUS_NOT_VALIDATED = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_NOT_VALIDATED"

EXPECTED_RUN_STATUS = "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION"
EXPECTED_PRODUCTION_STATUS = "NO_EXECUTION_NEW_RELEASE_CANDIDATE_INTAKE_ONLY"
EXPECTED_NEXT_ACTION = "FILL_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_OR_CONTINUE_MONITORING"
EXPECTED_LSNEW1_VALIDATION = "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_VALIDATED_DESIGN_ONLY_NO_EXECUTION"

FORBIDDEN_TRUE_RESULT_KEYS = [
    "ready_for_ls_new_3",
    "execution_allowed",
    "wordpress_api_call_executed",
    "credential_env_read_executed",
    "external_api_call_executed",
    "http_get_executed",
    "web_scraping_executed",
    "amazon_api_call_executed",
    "pa_api_call_executed",
    "creators_api_call_executed",
    "x_api_call_executed",
    "x_post_executed",
    "candidate_selected",
    "ls_next1_fill_updated",
    "post119_update_executed",
    "post183_update_executed_by_this_phase",
    "secret_length_output",
    "secret_hash_output",
    "authorization_header_output",
    "rerun_allowed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_new2_new_release_comic_candidate_intake_policy.json")
    parser.add_argument("--schema", default="config/start_ls_new2_new_release_comic_candidate_intake_schema.json")
    parser.add_argument("--candidate-template", default="exchange/new_release/start_ls_new2_new_release_comic_candidate_intake.template.json")
    parser.add_argument("--candidate-record", default="exchange/new_release/start_ls_new2_new_release_comic_candidate_intake.json")
    parser.add_argument("--simple-x-template", default="exchange/templates/start_ls_new2_simple_x_post_template.md")
    parser.add_argument("--result", default="exchange/runtime/start_ls_new2_new_release_comic_candidate_intake_result.json")
    parser.add_argument("--lock", default="exchange/locks/start_ls_new2_new_release_comic_candidate_intake.lock.json")
    parser.add_argument("--run-result", default="exchange/logs/start_ls_new2_new_release_comic_candidate_intake_result.json")
    parser.add_argument("--ls-new1-result", default="exchange/logs/start_ls_new1_new_release_comic_purchase_navigation_result.json")
    parser.add_argument("--output", default="exchange/logs/start_ls_new2_new_release_comic_candidate_intake_validation_result.json")
    parser.add_argument("--report", default="reports/start_ls_new2_new_release_comic_candidate_intake_validation_report.md")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def try_load_json(path: Path, errors: list[str], label: str) -> dict[str, Any]:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return {}
    try:
        return load_json(path)
    except json.JSONDecodeError:
        errors.append(f"invalid json {label}: {path}")
        return {}


def try_load_text(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"missing {label}: {path}")
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        errors.append(f"failed to read {label}: {path}")
        return ""


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_simple_template_text(markdown: str) -> str:
    marker = "```text"
    i = markdown.find(marker)
    if i < 0:
        return ""
    j = markdown.find("```", i + len(marker))
    if j < 0:
        return ""
    block = markdown[i + len(marker):j]
    return block.strip("\n")


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-2 New Release Comic Candidate Intake Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- ls_new1_validation_status: {payload.get('ls_new1_validation_status', '')}",
        f"- simple_x_template_under_280: {payload.get('simple_x_template_under_280', False)}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    candidate_template = try_load_json(Path(args.candidate_template), errors, "candidate-template")
    candidate_record = try_load_json(Path(args.candidate_record), errors, "candidate-record")
    simple_x_template_md = try_load_text(Path(args.simple_x_template), errors, "simple-x-template")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls_new1_result = try_load_json(Path(args.ls_new1_result), errors, "ls-new1-result")

    req(result == run_result, "result and run_result mismatch", errors)

    req(policy.get("phase") == "LS-NEW-2", "policy.phase mismatch", errors)
    req(result.get("status") == EXPECTED_RUN_STATUS, "status mismatch", errors)
    req(result.get("production_status") == EXPECTED_PRODUCTION_STATUS, "production_status mismatch", errors)

    req(ls_new1_result.get("validation_status") == EXPECTED_LSNEW1_VALIDATION, "ls-new1 validation mismatch", errors)

    req(schema.get("phase") == "LS-NEW-2", "schema.phase mismatch", errors)
    req(schema.get("content_type") == "new_release_comic", "schema.content_type mismatch", errors)
    req(schema.get("media_type") == "purchase_navigation_media", "schema.media_type mismatch", errors)

    req(candidate_template.get("document_type") == "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_TEMPLATE", "candidate template document_type mismatch", errors)
    req(candidate_record.get("document_type") == "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RECORD", "candidate record document_type mismatch", errors)

    simple_rule = schema.get("simple_x_post_rule", {}) if isinstance(schema, dict) else {}
    req(bool(simple_rule.get("does_not_require_synopsis", False)) is True, "simple x rule synopsis must not be required", errors)
    req(bool(simple_rule.get("does_not_require_price_or_point_rate", False)) is True, "simple x rule price/point must not be required", errors)
    req(bool(simple_rule.get("does_not_require_store_comparison", False)) is True, "simple x rule store comparison must not be required", errors)

    template_text = extract_simple_template_text(simple_x_template_md)
    req(template_text != "", "simple x template text block missing", errors)
    req("#PR" in template_text, "simple x template missing #PR", errors)
    req("URL" in template_text, "simple x template missing URL", errors)
    req("『タイトル』第○巻" in template_text, "simple x template missing title placeholder", errors)
    req(len(template_text) <= 280, "simple x template over 280", errors)

    req(bool(result.get("simple_x_template_under_280", False)) is True, "result.simple_x_template_under_280 must be true", errors)
    req(int(result.get("simple_x_post_max_characters", 0)) == 280, "result.simple_x_post_max_characters mismatch", errors)
    req(bool(result.get("human_input_required", False)) is True, "human_input_required must be true", errors)

    req(bool(result.get("work_explanation_required", True)) is False, "work_explanation_required must be false", errors)
    req(bool(result.get("long_work_explanation_required", True)) is False, "long_work_explanation_required must be false", errors)
    req(bool(result.get("synopsis_required", True)) is False, "synopsis_required must be false", errors)
    req(bool(result.get("price_comparison_required_in_x_post", True)) is False, "price_comparison_required_in_x_post must be false", errors)
    req(bool(result.get("point_reward_rate_required_in_x_post", True)) is False, "point_reward_rate_required_in_x_post must be false", errors)
    req(bool(result.get("store_comparison_required_in_x_post", True)) is False, "store_comparison_required_in_x_post must be false", errors)

    for key in FORBIDDEN_TRUE_RESULT_KEYS:
        req(bool(result.get(key, False)) is False, f"{key} must be false", errors)

    req(bool(lock.get("locked", False)) is True, "lock.locked must be true", errors)
    req(bool(lock.get("execution_allowed", True)) is False, "lock.execution_allowed must be false", errors)
    req(bool(lock.get("candidate_selected", False)) is False, "lock.candidate_selected must be false", errors)

    expected_action = str(policy.get("next_phase", {}).get("recommended_next_action", EXPECTED_NEXT_ACTION))
    req(str(result.get("recommended_next_action", "")) == expected_action, "recommended_next_action mismatch", errors)

    validation_status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED
    payload = {
        "phase": "LS-NEW-2",
        "document_type": "START_LS_NEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATION_RESULT",
        "validation_status": validation_status,
        "run_status": str(result.get("status", "")),
        "production_status": str(result.get("production_status", "")),
        "ls_new1_validation_status": str(ls_new1_result.get("validation_status", "")),
        "simple_x_template_under_280": bool(result.get("simple_x_template_under_280", False)),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(validation_status)
    return 0 if validation_status == STATUS_VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
