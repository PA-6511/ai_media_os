#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VALIDATED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATED_NO_EXECUTION"
NOT_VALIDATED = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_NOT_VALIDATED"
RUN_STATUS = "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_PASSED_NO_EXECUTION"
PRODUCTION_STATUS = "NO_EXECUTION_CANDIDATE_EVIDENCE_DRY_RUN_ONLY"
REQUIRED_LS_NEW2_VALIDATION = "LSNEW2_FILL_HUMAN_NEW_RELEASE_COMIC_CANDIDATE_VALIDATED_NO_EXECUTION"

REQUIRED_STORES = [
    "publisher_official",
    "kindle",
    "rakuten_kobo",
    "dmm_books",
    "ebookjapan",
    "booklive",
    "manual_source",
]

SOURCE_URL_FIELDS = [
    "publisher_source_url",
    "kindle_url",
    "rakuten_kobo_url",
    "dmm_books_url",
    "ebookjapan_url",
    "booklive_url",
    "manual_source_url",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--policy", default="config/start_ls_new3_candidate_evidence_dry_run_policy.json")
    p.add_argument("--schema", default="config/start_ls_new3_candidate_evidence_schema.json")
    p.add_argument("--evidence-record", default="exchange/new_release/start_ls_new3_candidate_evidence_dry_run.json")
    p.add_argument("--source-inventory", default="exchange/new_release/start_ls_new3_source_url_inventory.json")
    p.add_argument("--store-slots", default="exchange/new_release/start_ls_new3_store_evidence_slots.json")
    p.add_argument("--x-preview", default="exchange/new_release/start_ls_new3_simple_x_post_preview.json")
    p.add_argument("--wp-preview", default="exchange/new_release/start_ls_new3_wp_purchase_navigation_preview.md")
    p.add_argument("--result", default="exchange/runtime/start_ls_new3_candidate_evidence_dry_run_result.json")
    p.add_argument("--lock", default="exchange/locks/start_ls_new3_candidate_evidence_dry_run.lock.json")
    p.add_argument("--run-result", default="exchange/logs/start_ls_new3_candidate_evidence_dry_run_result.json")
    p.add_argument("--ls-new2-fill-validation-result", default="exchange/logs/start_ls_new2_fill_human_new_release_comic_candidate_validation_result.json")
    p.add_argument("--output", default="exchange/logs/start_ls_new3_candidate_evidence_dry_run_validation_result.json")
    p.add_argument("--report", default="reports/start_ls_new3_candidate_evidence_dry_run_validation_report.md")
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


def _validate_result(result: dict[str, Any], errors: list[str]) -> None:
    req(result.get("phase") == "LS-NEW-3", "result phase mismatch", errors)
    req(result.get("status") == RUN_STATUS, "result status mismatch", errors)
    req(result.get("production_status") == PRODUCTION_STATUS, "result production_status mismatch", errors)
    req(bool(result.get("ls_new2_fill_validated", False)) is True, "ls_new2_fill_validated mismatch", errors)
    req(bool(result.get("source_url_inventory_created", False)) is True, "source_url_inventory_created mismatch", errors)
    req(bool(result.get("store_evidence_slots_created", False)) is True, "store_evidence_slots_created mismatch", errors)
    req(bool(result.get("simple_x_post_preview_created", False)) is True, "simple_x_post_preview_created mismatch", errors)
    req(bool(result.get("wp_purchase_navigation_preview_created", False)) is True, "wp_purchase_navigation_preview_created mismatch", errors)
    req(bool(result.get("simple_x_post_under_280", False)) is True, "simple_x_post_under_280 mismatch", errors)
    req(bool(result.get("ready_for_ls_new_4", False)) is True, "ready_for_ls_new_4 mismatch", errors)
    req(bool(result.get("execution_allowed", True)) is False, "execution_allowed=true", errors)

    must_false = [
        "external_fetch_executed",
        "http_get_executed",
        "web_scraping_executed",
        "rss_fetch_executed",
        "amazon_api_call_executed",
        "pa_api_call_executed",
        "creators_api_call_executed",
        "x_api_call_executed",
        "x_post_executed",
        "wordpress_api_call_executed",
        "wordpress_write_executed",
        "credential_env_read_executed",
        "credential_value_output",
        "credential_secret_output",
        "secret_length_output",
        "secret_hash_output",
        "candidate_selected",
        "ls_next1_fill_updated",
        "post119_update_executed",
        "post183_update_executed",
        "rerun_allowed",
        "publish_rerun_allowed",
    ]
    for key in must_false:
        req(bool(result.get(key, False)) is False, f"{key}=true", errors)


def _validate_lock(lock: dict[str, Any], errors: list[str]) -> None:
    req(lock.get("phase") == "LS-NEW-3", "lock phase mismatch", errors)
    req(lock.get("status") == "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_LOCKED_NO_EXECUTION", "lock status mismatch", errors)
    req(bool(lock.get("locked", False)) is True, "lock locked mismatch", errors)
    req(bool(lock.get("ready_for_ls_new_4", False)) is True, "lock ready_for_ls_new_4 mismatch", errors)
    req(bool(lock.get("execution_allowed", True)) is False, "lock execution_allowed=true", errors)


def _validate_source_inventory(source_inventory: dict[str, Any], errors: list[str]) -> None:
    for field in SOURCE_URL_FIELDS:
        entry = source_inventory.get(field)
        req(isinstance(entry, dict), f"source inventory missing field: {field}", errors)
        if not isinstance(entry, dict):
            continue
        req(bool(entry.get("fetch_executed", True)) is False, f"source inventory fetch_executed=true: {field}", errors)
        present = bool(entry.get("present", False))
        status = str(entry.get("verification_status", ""))
        if present:
            req(status == "DRY_RUN_NOT_FETCHED", f"source inventory status mismatch: {field}", errors)
        else:
            req(status == "NOT_PROVIDED", f"source inventory not provided mismatch: {field}", errors)


def _validate_store_slots(store_slots: dict[str, Any], errors: list[str]) -> None:
    slots = store_slots.get("slots")
    req(isinstance(slots, list), "store slots missing list", errors)
    if not isinstance(slots, list):
        return

    by_name = {str(slot.get("store", "")): slot for slot in slots if isinstance(slot, dict)}
    for name in REQUIRED_STORES:
        req(name in by_name, f"missing store slot: {name}", errors)

    for name, slot in by_name.items():
        req(bool(slot.get("fetch_executed", True)) is False, f"store slot fetch_executed=true: {name}", errors)
        req(bool(slot.get("api_call_executed", True)) is False, f"store slot api_call_executed=true: {name}", errors)
        present = bool(slot.get("url_present", False))
        status = str(slot.get("verification_status", ""))
        if present:
            req(status == "DRY_RUN_NOT_FETCHED", f"store slot status mismatch: {name}", errors)
        else:
            req(status == "NOT_PROVIDED", f"store slot not provided mismatch: {name}", errors)


def _validate_x_preview(x_preview: dict[str, Any], errors: list[str]) -> None:
    post_text = str(x_preview.get("post_text", ""))
    req(x_preview.get("phase") == "LS-NEW-3", "x preview phase mismatch", errors)
    req(x_preview.get("document_type") == "START_LS_NEW3_SIMPLE_X_POST_PREVIEW", "x preview document_type mismatch", errors)
    req(bool(x_preview.get("generated", False)) is True, "x preview generated mismatch", errors)
    req(bool(x_preview.get("x_post_executed", False)) is False, "x post executed mismatch", errors)
    req(bool(x_preview.get("under_280", False)) is True, "x preview over 280", errors)
    req(len(post_text) <= 280, "x preview text length over 280", errors)
    req("#PR" in post_text, "x preview missing #PR", errors)
    req("#Amazonmanga" in post_text, "x preview missing #Amazonmanga", errors)
    req("#Kindle" in post_text, "x preview missing #Kindle", errors)
    req("URL" in post_text, "x preview missing URL placeholder", errors)
    req(bool(x_preview.get("contains_pr", False)) is True, "x preview contains_pr mismatch", errors)
    req(bool(x_preview.get("contains_title", False)) is True, "x preview contains_title mismatch", errors)
    req(bool(x_preview.get("contains_author_hashtag", False)) is True, "x preview contains_author_hashtag mismatch", errors)
    req(bool(x_preview.get("contains_url_placeholder", False)) is True, "x preview contains_url_placeholder mismatch", errors)


def _validate_wp_preview_text(wp_preview_text: str, result: dict[str, Any], errors: list[str]) -> None:
    req("NO_EXECUTION / PREVIEW_ONLY" in wp_preview_text, "wp preview missing execution marker", errors)
    req("WordPress write executed: false" in wp_preview_text, "wp preview missing wordpress write false marker", errors)
    req(str(result.get("title", "")) in wp_preview_text, "wp preview missing title", errors)
    req(str(result.get("volume", "")) in wp_preview_text, "wp preview missing volume", errors)
    req(str(result.get("release_date", "")) in wp_preview_text, "wp preview missing release_date", errors)
    req("外部サイト取得、価格確認、還元率確認、配信状態確認は実行していません。" in wp_preview_text, "wp preview missing no external fetch statement", errors)


def _validate_evidence(evidence: dict[str, Any], result: dict[str, Any], errors: list[str]) -> None:
    req(evidence.get("phase") == "LS-NEW-3", "evidence phase mismatch", errors)
    req(evidence.get("status") == "LSNEW3_CANDIDATE_EVIDENCE_DRY_RUN_READY_NO_EXECUTION", "evidence status mismatch", errors)
    candidate = evidence.get("candidate_identity", {})
    req(isinstance(candidate, dict), "candidate_identity missing", errors)
    if isinstance(candidate, dict):
        req(candidate.get("content_item_id") == result.get("content_item_id"), "candidate content_item_id mismatch", errors)
        req(candidate.get("title") == result.get("title"), "candidate title mismatch", errors)
        req(candidate.get("volume") == result.get("volume"), "candidate volume mismatch", errors)

    safety = evidence.get("safety", {})
    req(isinstance(safety, dict), "evidence safety missing", errors)
    if isinstance(safety, dict):
        must_false = [
            "external_fetch_executed",
            "http_get_executed",
            "web_scraping_executed",
            "rss_fetch_executed",
            "amazon_api_call_executed",
            "pa_api_call_executed",
            "creators_api_call_executed",
            "x_api_call_executed",
            "x_post_executed",
            "wordpress_api_call_executed",
            "wordpress_write_executed",
            "credential_env_read_executed",
            "credential_value_output",
            "credential_secret_output",
            "secret_length_output",
            "secret_hash_output",
            "candidate_selected",
            "ls_next1_fill_updated",
            "post119_update_executed",
            "post183_update_executed",
            "execution_allowed",
        ]
        for key in must_false:
            req(bool(safety.get(key, False)) is False, f"evidence safety flag mismatch: {key}", errors)


def _write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-3 Candidate Evidence Dry Run Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- run_status: {payload.get('run_status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        "",
        "## Errors",
    ]
    errors = payload.get("errors", [])
    if errors:
        lines.extend(f"- {e}" for e in errors)
    else:
        lines.append("- none")
    write_text(path, "\n".join(lines) + "\n")


def main() -> int:
    args = parse_args()
    errors: list[str] = []

    policy = try_load_json(Path(args.policy), errors, "policy")
    schema = try_load_json(Path(args.schema), errors, "schema")
    evidence = try_load_json(Path(args.evidence_record), errors, "evidence-record")
    source_inventory = try_load_json(Path(args.source_inventory), errors, "source-inventory")
    store_slots = try_load_json(Path(args.store_slots), errors, "store-slots")
    x_preview = try_load_json(Path(args.x_preview), errors, "x-preview")
    wp_preview_text = read_text(Path(args.wp_preview), errors, "wp-preview")
    result = try_load_json(Path(args.result), errors, "result")
    lock = try_load_json(Path(args.lock), errors, "lock")
    run_result = try_load_json(Path(args.run_result), errors, "run-result")
    ls_new2_validation = try_load_json(Path(args.ls_new2_fill_validation_result), errors, "ls-new2-fill-validation-result")

    req(policy.get("phase") == "LS-NEW-3", "policy phase mismatch", errors)
    req(schema.get("phase") == "LS-NEW-3", "schema phase mismatch", errors)
    req(ls_new2_validation.get("validation_status") == REQUIRED_LS_NEW2_VALIDATION, "ls-new2-fill validation mismatch", errors)
    req(result == run_result, "result and run_result mismatch", errors)

    _validate_result(result, errors)
    _validate_lock(lock, errors)
    _validate_source_inventory(source_inventory, errors)
    _validate_store_slots(store_slots, errors)
    _validate_x_preview(x_preview, errors)
    _validate_wp_preview_text(wp_preview_text, result, errors)
    _validate_evidence(evidence, result, errors)

    validation_status = VALIDATED if len(errors) == 0 else NOT_VALIDATED
    payload = {
        "phase": "LS-NEW-3",
        "document_type": "START_LS_NEW3_CANDIDATE_EVIDENCE_DRY_RUN_VALIDATION_RESULT",
        "validation_status": validation_status,
        "run_status": str(result.get("status", "")),
        "production_status": str(result.get("production_status", "")),
        "recommended_next_action": str(result.get("recommended_next_action", "")),
        "recommended_next_phase_options": list(result.get("recommended_next_phase_options", [])),
        "errors": list(errors),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json(Path(args.output), payload)
    _write_report(Path(args.report), payload)
    print(validation_status)
    return 0 if validation_status == VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
