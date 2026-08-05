#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_VALID_WAITING = "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT_VALIDATED_NO_EXECUTION"
STATUS_VALID_FILLED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATED_NO_EXECUTION"
STATUS_INVALID = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_NOT_VALIDATED"

RUN_WAITING = "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT_NO_EXECUTION"
RUN_FILLED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new2_fill_human_new_release_comic_candidate_policy.json")
    p.add_argument("--result", default="exchange/runtime/start_ls_new2_fill_human_new_release_comic_candidate_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new2_fill_human_new_release_comic_candidate.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new2_fill_human_new_release_comic_candidate_result.json")
    p.add_argument("--human-input-template", default="exchange/new_release/start_ls_new2_fill_human_candidate_input.template.json")
    p.add_argument("--human-input-record", default="exchange/new_release/start_ls_new2_fill_human_candidate_input.json")
    p.add_argument("--filled-candidate-record", default="exchange/new_release/start_ls_new2_filled_new_release_comic_candidate_intake.json")
    p.add_argument("--ls-new2-result", default="exchange/runtime/start_ls_new2_new_release_comic_candidate_intake_result.json")
    p.add_argument("--ls-new2-validation-result", default="exchange/logs/start_ls_new2_new_release_comic_candidate_intake_validation_result.json")
    p.add_argument("--simple-x-template", default="exchange/templates/start_ls_new2_simple_x_post_template.md")
    p.add_argument("--output", default="exchange/logs/start_ls_new2_fill_human_new_release_comic_candidate_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new2_fill_human_new_release_comic_candidate_validation_report.md")
    return p.parse_args()


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


def read_text(path: Path, errors: list[str], label: str) -> str:
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


def _extract_simple_text(md: str) -> str:
    marker = "```text"
    i = md.find(marker)
    if i < 0:
        return ""
    j = md.find("```", i + len(marker))
    if j < 0:
        return ""
    return md[i + len(marker):j].strip("\n")


def _required_field_missing(result: dict[str, Any]) -> bool:
    missing = result.get("missing_required_human_fields", [])
    return isinstance(missing, list) and len(missing) > 0


def _report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-2-FILL Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
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
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    human_template = try_load_json(Path(args.human_input_template), errors, "human-input-template")
    human_record = try_load_json(Path(args.human_input_record), errors, "human-input-record")
    filled_record = try_load_json(Path(args.filled_candidate_record), errors, "filled-candidate-record")
    ls_new2_result = try_load_json(Path(args.ls_new2_result), errors, "ls-new2-result")
    ls_new2_validation = try_load_json(Path(args.ls_new2_validation_result), errors, "ls-new2-validation-result")
    simple_x_md = read_text(Path(args.simple_x_template), errors, "simple-x-template")

    req(result == run_result, "result and run_result mismatch", errors)
    req(policy.get("phase") == "LS-NEW-2-FILL", "policy phase mismatch", errors)

    req(ls_new2_result.get("status") == "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION", "ls-new2 status mismatch", errors)
    req(ls_new2_validation.get("validation_status") == "LSNEW2_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_VALIDATED_WAITING_FOR_HUMAN_INPUT_NO_EXECUTION", "ls-new2 validation mismatch", errors)

    req(human_template.get("document_type") == "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_TEMPLATE", "human template document_type mismatch", errors)
    req(human_record.get("document_type") == "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_RECORD", "human record document_type mismatch", errors)

    simple_text = _extract_simple_text(simple_x_md)
    req(simple_text != "", "simple x template missing text block", errors)
    req(len(simple_text) <= 280, "simple x template over 280", errors)
    req("#PR" in simple_text, "simple x template missing #PR", errors)
    req("URL" in simple_text, "simple x template missing URL", errors)

    run_status = str(result.get("status", ""))
    if run_status == RUN_WAITING:
        req(result.get("production_status") == "WAITING_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT_NO_EXECUTION", "production_status mismatch", errors)
        req(bool(result.get("human_filled", True)) is False, "human_filled mismatch", errors)
        req(bool(result.get("human_confirmed", True)) is False, "human_confirmed mismatch", errors)
        req(bool(result.get("candidate_intake_completed", True)) is False, "candidate_intake_completed mismatch", errors)
        req(bool(result.get("ready_for_ls_new_3", True)) is False, "ready_for_ls_new_3 mismatch", errors)
        req(bool(result.get("human_input_required", False)) is True, "human_input_required mismatch", errors)
        if bool(result.get("ready_for_ls_new_3", False)) and _required_field_missing(result):
            errors.append("ready_for_ls_new_3=true while missing fields")
    elif run_status == RUN_FILLED:
        req(result.get("production_status") == "NO_EXECUTION_HUMAN_NEW_RELEASE_CANDIDATE_FILLED", "production_status mismatch", errors)
        req(bool(result.get("human_filled", False)) is True, "human_filled mismatch", errors)
        req(bool(result.get("human_confirmed", False)) is True, "human_confirmed mismatch", errors)
        req(bool(result.get("candidate_intake_completed", False)) is True, "candidate_intake_completed mismatch", errors)
        req(bool(result.get("ready_for_ls_new_3", False)) is True, "ready_for_ls_new_3 mismatch", errors)
        req(bool(result.get("human_input_required", True)) is False, "human_input_required mismatch", errors)
        req(_required_field_missing(result) is False, "filled result has missing_required_human_fields", errors)
    else:
        errors.append("status mismatch")

    req(bool(result.get("execution_allowed", False)) is False, "execution_allowed=true", errors)

    must_false = [
        "wordpress_api_call_executed",
        "credential_env_read_executed",
        "external_api_call_executed",
        "http_get_executed",
        "web_scraping_executed",
        "amazon_api_call_executed",
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
    for k in must_false:
        req(bool(result.get(k, False)) is False, f"{k}=true", errors)

    req(bool(lock.get("locked", False)) is True, "lock mismatch", errors)
    req(filled_record.get("phase") == "LS-NEW-2-FILL", "filled record phase mismatch", errors)

    if errors:
        validation_status = STATUS_INVALID
    elif run_status == RUN_WAITING:
        validation_status = STATUS_VALID_WAITING
    else:
        validation_status = STATUS_VALID_FILLED

    payload = {
        "phase": "LS-NEW-2-FILL",
        "document_type": "START_LS_NEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATION_RESULT",
        "validation_status": validation_status,
        "run_status": run_status,
        "production_status": str(result.get("production_status", "")),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), payload)
    _report(Path(args.report), payload)
    print(validation_status)
    return 0 if validation_status in (STATUS_VALID_WAITING, STATUS_VALID_FILLED) else 1


if __name__ == "__main__":
    raise SystemExit(main())
