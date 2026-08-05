#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_WAITING = "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT_NO_EXECUTION"
STATUS_PASSED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION"
STATUS_FAILED = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_FAILED_NO_EXECUTION"

PRODUCTION_WAITING = "WAITING_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT_NO_EXECUTION"
PRODUCTION_PASSED = "NO_EXECUTION_HUMAN_NEW_RELEASE_CANDIDATE_FILLED"
PRODUCTION_FAILED = "NO_EXECUTION_HUMAN_NEW_RELEASE_CANDIDATE_FILL_ONLY"

LOCK_WAITING = "LSNEW2_FILL_LOCKED_WAITING_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT_NO_EXECUTION"
LOCK_PASSED = "LSNEW2_FILL_LOCKED_HUMAN_NEW_RELEASE_CANDIDATE_PASSED_NO_EXECUTION"
LOCK_FAILED = "LSNEW2_FILL_LOCK_FAILED_NO_EXECUTION"

RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new2_fill_human_new_release_comic_candidate_policy.json")
    p.add_argument("--ls-new2-result", default="exchange/runtime/start_ls_new2_new_release_comic_candidate_intake_result.json")
    p.add_argument("--ls-new2-lock", default="exchange/locks/start_ls_new2_new_release_comic_candidate_intake.lock.json")
    p.add_argument("--ls-new2-run-result", default="exchange/logs/start_ls_new2_new_release_comic_candidate_intake_result.json")
    p.add_argument("--ls-new2-validation-result", default="exchange/logs/start_ls_new2_new_release_comic_candidate_intake_validation_result.json")
    p.add_argument("--ls-new2-candidate-schema", default="config/start_ls_new2_new_release_comic_candidate_intake_schema.json")
    p.add_argument("--ls-new2-candidate-template", default="exchange/new_release/start_ls_new2_new_release_comic_candidate_intake.template.json")
    p.add_argument("--ls-new2-candidate-record", default="exchange/new_release/start_ls_new2_new_release_comic_candidate_intake.json")
    p.add_argument("--ls-new2-simple-x-template", default="exchange/templates/start_ls_new2_simple_x_post_template.md")
    p.add_argument("--human-input-template-output", default="exchange/new_release/start_ls_new2_fill_human_candidate_input.template.json")
    p.add_argument("--human-input-record", default="exchange/new_release/start_ls_new2_fill_human_candidate_input.json")
    p.add_argument("--filled-candidate-output", default="exchange/new_release/start_ls_new2_filled_new_release_comic_candidate_intake.json")
    p.add_argument("--output", default="exchange/runtime/start_ls_new2_fill_human_new_release_comic_candidate_result.json")
    p.add_argument("--lock-output", default="exchange/locks/start_ls_new2_fill_human_new_release_comic_candidate.lock.json")
    p.add_argument("--report", default="reports/start_ls_new2_fill_human_new_release_comic_candidate_report.md")

    p.add_argument("--create-human-input-template", action="store_true")
    p.add_argument("--require-no-wordpress-api", action="store_true")
    p.add_argument("--require-no-credential-read", action="store_true")
    p.add_argument("--require-no-external-fetch", action="store_true")
    p.add_argument("--require-no-amazon-api", action="store_true")
    p.add_argument("--require-no-x-api", action="store_true")
    p.add_argument("--require-no-candidate-selection", action="store_true")
    p.add_argument("--require-no-ls-next1-fill-update", action="store_true")
    p.add_argument("--forbid-post119-update", action="store_true")
    p.add_argument("--forbid-post183-update", action="store_true")
    p.add_argument("--require-human-filled", action="store_true")
    p.add_argument("--require-human-confirmed", action="store_true")
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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def req(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)


def _default_template() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_TEMPLATE",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-2-FILL",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "content_item_id": "",
        "title": "",
        "volume": "",
        "author": "",
        "publisher": "",
        "label": "",
        "release_date": "",
        "ebook_release_date": "",
        "paper_release_date": "",
        "candidate_source_type": "",
        "publisher_source_url": "",
        "kindle_url": "",
        "rakuten_kobo_url": "",
        "dmm_books_url": "",
        "ebookjapan_url": "",
        "booklive_url": "",
        "manual_source_url": "",
        "source_pending": True,
        "asin": "",
        "isbn": "",
        "store_product_ids": {},
        "price_notes": "",
        "point_reward_notes": "",
        "reservation_status_notes": "",
        "delivery_status_notes": "",
        "campaign_notes": "",
        "short_original_comment": "",
        "affiliate_url_pending": True,
        "simple_x_post_template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
        "simple_x_post_max_characters": 280,
        "human_filled": False,
        "human_confirmed": False,
        "execution_allowed": False,
        "notes": "Fill this file manually. Do not let AI infer title, release date, ASIN, source URL, or candidate data.",
    }


def _default_waiting_record() -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEW2_FILL_HUMAN_CANDIDATE_INPUT_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-2-FILL",
        "status": "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "content_item_id": "",
        "title": "",
        "volume": "",
        "author": "",
        "publisher": "",
        "label": "",
        "release_date": "",
        "ebook_release_date": "",
        "paper_release_date": "",
        "candidate_source_type": "",
        "publisher_source_url": "",
        "kindle_url": "",
        "rakuten_kobo_url": "",
        "dmm_books_url": "",
        "ebookjapan_url": "",
        "booklive_url": "",
        "manual_source_url": "",
        "source_pending": True,
        "asin": "",
        "isbn": "",
        "store_product_ids": {},
        "price_notes": "",
        "point_reward_notes": "",
        "reservation_status_notes": "",
        "delivery_status_notes": "",
        "campaign_notes": "",
        "short_original_comment": "",
        "affiliate_url_pending": True,
        "simple_x_post_template": "配信開始です\n#PR #Amazonmanga #Kindle #作者名\n『タイトル』第○巻\n\nURL",
        "simple_x_post_max_characters": 280,
        "human_filled": False,
        "human_confirmed": False,
        "human_input_required": True,
        "candidate_intake_completed": False,
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
        "missing_required_human_fields": [
            "content_item_id",
            "title",
            "volume",
            "author",
            "publisher",
            "release_date",
            "candidate_source_type",
            "human_confirmed",
        ],
        "missing_source_requirement": False,
        "errors": [],
    }


def _default_filled_record(src: dict[str, Any], missing_fields: list[str], missing_source_requirement: bool) -> dict[str, Any]:
    return {
        "document_type": "START_LS_NEW2_FILLED_NEW_RELEASE_COMIC_CANDIDATE_INTAKE_RECORD",
        "schema_version": "1.0.0",
        "phase": "LS-NEW-2-FILL",
        "status": "LSNEW2_FILL_WAITING_FOR_HUMAN_CANDIDATE_INPUT",
        "content_type": "new_release_comic",
        "media_type": "purchase_navigation_media",
        "content_item_id": str(src.get("content_item_id", "")),
        "title": str(src.get("title", "")),
        "volume": str(src.get("volume", "")),
        "author": str(src.get("author", "")),
        "publisher": str(src.get("publisher", "")),
        "label": str(src.get("label", "")),
        "release_date": str(src.get("release_date", "")),
        "ebook_release_date": str(src.get("ebook_release_date", "")),
        "paper_release_date": str(src.get("paper_release_date", "")),
        "candidate_source_type": str(src.get("candidate_source_type", "")),
        "publisher_source_url": str(src.get("publisher_source_url", "")),
        "kindle_url": str(src.get("kindle_url", "")),
        "rakuten_kobo_url": str(src.get("rakuten_kobo_url", "")),
        "dmm_books_url": str(src.get("dmm_books_url", "")),
        "ebookjapan_url": str(src.get("ebookjapan_url", "")),
        "booklive_url": str(src.get("booklive_url", "")),
        "manual_source_url": str(src.get("manual_source_url", "")),
        "source_pending": bool(src.get("source_pending", False)),
        "asin": str(src.get("asin", "")),
        "isbn": str(src.get("isbn", "")),
        "store_product_ids": src.get("store_product_ids", {}) if isinstance(src.get("store_product_ids", {}), dict) else {},
        "price_notes": str(src.get("price_notes", "")),
        "point_reward_notes": str(src.get("point_reward_notes", "")),
        "reservation_status_notes": str(src.get("reservation_status_notes", "")),
        "delivery_status_notes": str(src.get("delivery_status_notes", "")),
        "campaign_notes": str(src.get("campaign_notes", "")),
        "short_original_comment": str(src.get("short_original_comment", "")),
        "affiliate_url_pending": bool(src.get("affiliate_url_pending", True)),
        "simple_x_post_template": str(src.get("simple_x_post_template", "")),
        "simple_x_post_max_characters": int(src.get("simple_x_post_max_characters", 280)),
        "human_filled": bool(src.get("human_filled", False)),
        "human_confirmed": bool(src.get("human_confirmed", False)),
        "human_input_required": not (bool(src.get("human_filled", False)) and bool(src.get("human_confirmed", False))),
        "candidate_intake_completed": len(missing_fields) == 0 and (not missing_source_requirement),
        "ready_for_ls_new_3": False,
        "execution_allowed": False,
        "missing_required_human_fields": list(missing_fields),
        "missing_source_requirement": bool(missing_source_requirement),
        "errors": [],
    }


def _required_fields() -> list[str]:
    return [
        "content_item_id",
        "title",
        "volume",
        "author",
        "publisher",
        "release_date",
        "candidate_source_type",
        "human_confirmed",
    ]


def _is_non_empty(v: Any) -> bool:
    return isinstance(v, str) and v.strip() != ""


def _source_url_fields() -> list[str]:
    return [
        "publisher_source_url",
        "kindle_url",
        "rakuten_kobo_url",
        "dmm_books_url",
        "ebookjapan_url",
        "booklive_url",
        "manual_source_url",
    ]


def _missing_fields(record: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for k in _required_fields():
        if k == "human_confirmed":
            if bool(record.get("human_confirmed", False)) is not True:
                missing.append(k)
            continue
        if not _is_non_empty(record.get(k, "")):
            missing.append(k)
    return missing


def _missing_source_requirement(record: dict[str, Any]) -> bool:
    has_source = any(_is_non_empty(record.get(k, "")) for k in _source_url_fields())
    source_pending = bool(record.get("source_pending", False))
    return not (has_source or source_pending)


def _simple_template_under_280(text: str) -> bool:
    marker = "```text"
    i = text.find(marker)
    if i < 0:
        return False
    j = text.find("```", i + len(marker))
    if j < 0:
        return False
    body = text[i + len(marker):j].strip("\n")
    return len(body) <= 280 and "#PR" in body and "URL" in body


def _validate_required_flags(args: argparse.Namespace, errors: list[str]) -> None:
    required = {
        "--create-human-input-template": args.create_human_input_template,
        "--require-no-wordpress-api": args.require_no_wordpress_api,
        "--require-no-credential-read": args.require_no_credential_read,
        "--require-no-external-fetch": args.require_no_external_fetch,
        "--require-no-amazon-api": args.require_no_amazon_api,
        "--require-no-x-api": args.require_no_x_api,
        "--require-no-candidate-selection": args.require_no_candidate_selection,
        "--require-no-ls-next1-fill-update": args.require_no_ls_next1_fill_update,
        "--forbid-post119-update": args.forbid_post119_update,
        "--forbid-post183-update": args.forbid_post183_update,
    }
    for key, ok in required.items():
        req(ok, f"missing required flag: {key}", errors)


def _build_result(policy: dict[str, Any], status: str, production_status: str, human_record: dict[str, Any], missing_fields: list[str], missing_source_requirement: bool, ls_new2_validated: bool, template_created: bool, simple_under_280: bool, errors: list[str]) -> dict[str, Any]:
    next_phase = policy.get("next_phase", {}) if isinstance(policy, dict) else {}
    if status == STATUS_PASSED:
        next_action = str(next_phase.get("recommended_next_action_valid", "BEGIN_LS_NEW_3_CANDIDATE_EVIDENCE_DRY_RUN"))
        next_options = list(next_phase.get("recommended_next_phase_options_valid", ["LS-NEW-3_AFTER_HUMAN_INPUT", "LS-MON-2"]))
        human_input_required = False
        candidate_done = True
        ready_for_ls_new_3 = True
    else:
        next_action = str(next_phase.get("recommended_next_action_waiting", "WAIT_FOR_HUMAN_NEW_RELEASE_CANDIDATE_INPUT"))
        next_options = list(next_phase.get("recommended_next_phase_options_waiting", ["LS-NEW-2-FILL_AFTER_HUMAN_INPUT", "LS-MON-2"]))
        human_input_required = True
        candidate_done = False
        ready_for_ls_new_3 = False

    return {
        "phase": "LS-NEW-2-FILL",
        "document_type": "START_LS_NEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_RESULT",
        "status": status,
        "execution_mode": "HUMAN_CANDIDATE_INPUT_REGISTRATION_ONLY_NO_EXECUTION",
        "production_status": production_status,
        "ls_new2_validated": bool(ls_new2_validated),
        "simple_x_template_under_280": bool(simple_under_280),
        "human_input_template_created": bool(template_created),
        "human_input_record_exists": True,
        "human_filled": bool(human_record.get("human_filled", False)),
        "human_confirmed": bool(human_record.get("human_confirmed", False)),
        "human_input_required": bool(human_input_required),
        "candidate_intake_completed": bool(candidate_done),
        "ready_for_ls_new_3": bool(ready_for_ls_new_3),
        "execution_allowed": False,
        "content_item_id": str(human_record.get("content_item_id", "")),
        "title": str(human_record.get("title", "")),
        "volume": str(human_record.get("volume", "")),
        "author": str(human_record.get("author", "")),
        "publisher": str(human_record.get("publisher", "")),
        "release_date": str(human_record.get("release_date", "")),
        "candidate_source_type": str(human_record.get("candidate_source_type", "")),
        "source_pending": bool(human_record.get("source_pending", False)),
        "missing_required_human_fields": list([] if status == STATUS_PASSED else missing_fields),
        "missing_source_requirement": bool(missing_source_requirement),
        "work_explanation_required": False,
        "long_work_explanation_required": False,
        "synopsis_required": False,
        "price_comparison_required_in_x_post": False,
        "point_reward_rate_required_in_x_post": False,
        "store_comparison_required_in_x_post": False,
        "simple_x_post_template": str(human_record.get("simple_x_post_template", "")),
        "simple_x_post_max_characters": int(human_record.get("simple_x_post_max_characters", 280)),
        "wordpress_api_call_executed": False,
        "wordpress_get_executed": False,
        "wordpress_post_executed": False,
        "wordpress_write_executed_by_this_phase": False,
        "wordpress_draft_created": False,
        "publish_executed_by_this_phase": False,
        "x_post_executed": False,
        "external_api_call_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "rss_fetch_executed": False,
        "amazon_api_call_executed": False,
        "pa_api_call_executed": False,
        "creators_api_call_executed": False,
        "x_api_call_executed": False,
        "credential_env_read_executed": False,
        "credential_value_output": False,
        "credential_secret_output": False,
        "secret_length_output": False,
        "secret_hash_output": False,
        "authorization_header_generated": False,
        "authorization_header_output": False,
        "basic_auth_string_generated": False,
        "basic_auth_string_output": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "ls_next1_fill_updated": False,
        "ls_next2_started": False,
        "ls_sale_route_started": False,
        "asin_auto_inferred": False,
        "title_auto_inferred": False,
        "release_date_auto_inferred": False,
        "price_auto_inferred": False,
        "point_reward_rate_auto_inferred": False,
        "candidate_ranking_executed": False,
        "candidate_selected": False,
        "locked": True,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": next_action,
        "recommended_next_phase_options": next_options,
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_lock(result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status", "")
    if status == STATUS_PASSED:
        lock_status = LOCK_PASSED
    elif status == STATUS_WAITING:
        lock_status = LOCK_WAITING
    else:
        lock_status = LOCK_FAILED

    return {
        "phase": "LS-NEW-2-FILL",
        "document_type": "START_LS_NEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_LOCK",
        "status": lock_status,
        "locked": True,
        "human_input_template_created": bool(result.get("human_input_template_created", False)),
        "human_input_record_exists": bool(result.get("human_input_record_exists", False)),
        "human_filled": bool(result.get("human_filled", False)),
        "human_confirmed": bool(result.get("human_confirmed", False)),
        "candidate_intake_completed": bool(result.get("candidate_intake_completed", False)),
        "ready_for_ls_new_3": bool(result.get("ready_for_ls_new_3", False)),
        "execution_allowed": False,
        "wordpress_api_call_executed": False,
        "credential_env_read_executed": False,
        "external_api_call_executed": False,
        "http_get_executed": False,
        "web_scraping_executed": False,
        "amazon_api_call_executed": False,
        "x_api_call_executed": False,
        "x_post_executed": False,
        "candidate_selected": False,
        "ls_next1_fill_updated": False,
        "post119_update_executed": False,
        "post183_update_executed_by_this_phase": False,
        "rerun_allowed": False,
        "publish_rerun_allowed": False,
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
    }


def _write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-2-FILL Human New Release Comic Candidate Report",
        "",
        f"- generated_at: {result.get('generated_at', '')}",
        f"- status: {result.get('status', '')}",
        f"- production_status: {result.get('production_status', '')}",
        f"- ls_new2_validated: {result.get('ls_new2_validated', False)}",
        f"- human_filled: {result.get('human_filled', False)}",
        f"- human_confirmed: {result.get('human_confirmed', False)}",
        f"- candidate_intake_completed: {result.get('candidate_intake_completed', False)}",
        f"- ready_for_ls_new_3: {result.get('ready_for_ls_new_3', False)}",
        f"- recommended_next_action: {result.get('recommended_next_action', '')}",
        "",
        "## Errors",
    ]
    if result.get("errors"):
        lines.extend(f"- {e}" for e in result["errors"])
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors, "policy")
    ls_new2_result = try_load_json(Path(args.ls_new2_result), errors, "ls-new2-result")
    ls_new2_lock = try_load_json(Path(args.ls_new2_lock), errors, "ls-new2-lock")
    ls_new2_run_result = try_load_json(Path(args.ls_new2_run_result), errors, "ls-new2-run-result")
    ls_new2_validation_result = try_load_json(Path(args.ls_new2_validation_result), errors, "ls-new2-validation-result")
    _ = try_load_json(Path(args.ls_new2_candidate_schema), errors, "ls-new2-candidate-schema")
    _ = try_load_json(Path(args.ls_new2_candidate_template), errors, "ls-new2-candidate-template")
    _ = try_load_json(Path(args.ls_new2_candidate_record), errors, "ls-new2-candidate-record")
    simple_x_template_md = read_text(Path(args.ls_new2_simple_x_template), errors, "ls-new2-simple-x-template")

    _validate_required_flags(args, errors)

    req(ls_new2_result == ls_new2_run_result, "ls-new2 result/run_result mismatch", errors)
    req(bool(ls_new2_lock.get("locked", False)) is True, "ls-new2 lock mismatch", errors)

    prev = policy.get("required_previous_phase", {}) if isinstance(policy, dict) else {}
    req(ls_new2_result.get("status") == prev.get("required_ls_new2_status"), "ls-new2 status mismatch", errors)
    req(
        ls_new2_validation_result.get("validation_status") == prev.get("required_ls_new2_validation_status"),
        "ls-new2 validation mismatch",
        errors,
    )
    req(
        ls_new2_result.get("production_status") == prev.get("required_ls_new2_production_status"),
        "ls-new2 production_status mismatch",
        errors,
    )
    req(
        bool(ls_new2_result.get("simple_x_template_under_280", False)) is bool(prev.get("required_simple_x_template_under_280", True)),
        "ls-new2 simple_x_template_under_280 mismatch",
        errors,
    )
    req(
        bool(ls_new2_result.get("ready_for_ls_new_3", True)) is bool(prev.get("required_ready_for_ls_new_3", False)),
        "ls-new2 ready_for_ls_new_3 mismatch",
        errors,
    )
    req(
        bool(ls_new2_result.get("execution_allowed", True)) is bool(prev.get("required_execution_allowed", False)),
        "ls-new2 execution_allowed mismatch",
        errors,
    )

    simple_under_280 = _simple_template_under_280(simple_x_template_md)
    req(simple_under_280, "simple x template not compliant", errors)

    template_created = False
    template_path = Path(args.human_input_template_output)
    if args.create_human_input_template and not template_path.exists():
        write_json(template_path, _default_template())
        template_created = True

    if not template_path.exists():
        errors.append(f"missing human input template: {template_path}")

    human_input_record_path = Path(args.human_input_record)
    if not human_input_record_path.exists():
        write_json(human_input_record_path, _default_waiting_record())

    human_record = try_load_json(human_input_record_path, errors, "human-input-record")
    missing_fields = _missing_fields(human_record)
    missing_source_requirement = _missing_source_requirement(human_record)

    release_date = str(human_record.get("release_date", "")).strip()
    if release_date and not RE_DATE.match(release_date):
        errors.append("invalid release_date format")

    if missing_source_requirement:
        errors.append("missing source_url and source_pending=false")

    human_filled = bool(human_record.get("human_filled", False))
    human_confirmed = bool(human_record.get("human_confirmed", False))

    if args.require_human_filled and not human_filled:
        missing_fields = sorted(set(missing_fields + ["human_filled"]))
    if args.require_human_confirmed and not human_confirmed:
        missing_fields = sorted(set(missing_fields + ["human_confirmed"]))

    # Any protocol/safety/source-rule error is a hard failure.
    blocking_errors = list(errors)

    if blocking_errors:
        status = STATUS_FAILED
        prod = PRODUCTION_FAILED
    else:
        if missing_fields or missing_source_requirement or (args.require_human_filled and not human_filled) or (args.require_human_confirmed and not human_confirmed):
            status = STATUS_WAITING
            prod = PRODUCTION_WAITING
        else:
            status = STATUS_PASSED
            prod = PRODUCTION_PASSED

    filled_record = _default_filled_record(human_record, missing_fields, missing_source_requirement)
    if status == STATUS_PASSED:
        filled_record["status"] = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_PASSED_NO_EXECUTION"
        filled_record["candidate_intake_completed"] = True
        filled_record["ready_for_ls_new_3"] = True
        filled_record["human_input_required"] = False
        filled_record["missing_required_human_fields"] = []
    write_json(Path(args.filled_candidate_output), filled_record)

    result = _build_result(
        policy,
        status,
        prod,
        human_record,
        missing_fields,
        missing_source_requirement,
        ls_new2_validated=not blocking_errors,
        template_created=(template_created or template_path.exists()),
        simple_under_280=simple_under_280,
        errors=[] if status != STATUS_FAILED else blocking_errors,
    )

    lock_payload = _build_lock(result)
    write_json(Path(args.output), result)
    write_json(Path(args.lock_output), lock_payload)
    _write_report(Path(args.report), result)

    print(status)
    return 0 if status in (STATUS_WAITING, STATUS_PASSED) else 1


if __name__ == "__main__":
    raise SystemExit(main())
