#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATUS_VALIDATED = "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_VALIDATED_DESIGN_ONLY_NO_EXECUTION"
STATUS_NOT_VALIDATED = "LSNEW1_NEW_RELEASE_COMIC_PURCHASE_NAVIGATION_PROTOCOL_NOT_VALIDATED"

PROHIBITED_COPY_KEYS = [
    "official_synopsis_copy_allowed",
    "store_description_copy_allowed",
    "publisher_description_copy_allowed",
    "review_copy_allowed",
    "user_comment_copy_allowed",
    "catchcopy_copy_allowed",
]

EXAMPLE_SAFETY_FALSE_KEYS = [
    "scraping_allowed",
    "external_api_call_allowed",
    "wordpress_write_allowed",
    "x_post_allowed",
    "publish_allowed",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls_new1_new_release_comic_purchase_navigation_policy.json")
    parser.add_argument("--example", default="exchange/examples/start_ls_new1_new_release_comic_candidate.example.json")
    parser.add_argument("--wp-template", default="exchange/templates/start_ls_new1_wp_purchase_navigation_template.md")
    parser.add_argument("--x-templates", default="exchange/templates/start_ls_new1_x_post_templates.md")
    parser.add_argument("--output", default="exchange/logs/start_ls_new1_new_release_comic_purchase_navigation_result.json")
    parser.add_argument("--report", default="reports/start_ls_new1_new_release_comic_purchase_navigation_report.md")
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


def try_load_text(path: Path, errors: list[str], label: str) -> str:
    if not path.exists():
        errors.append(f"missing file: {path}")
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


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# LS-NEW-1 New Release Comic Purchase Navigation Validation Report",
        "",
        f"- generated_at: {payload.get('generated_at', '')}",
        f"- validation_status: {payload.get('validation_status', '')}",
        f"- phase: {payload.get('phase', '')}",
        f"- status: {payload.get('status', '')}",
        f"- production_status: {payload.get('production_status', '')}",
        f"- sale_route_status: {payload.get('sale_route_status', '')}",
        f"- new_release_comic_route_status: {payload.get('new_release_comic_route_status', '')}",
        f"- media_type: {payload.get('media_type', '')}",
        f"- not_media_type: {payload.get('not_media_type', '')}",
        f"- work_introduction_required: {payload.get('work_introduction_required', '')}",
        f"- long_work_explanation_required: {payload.get('long_work_explanation_required', '')}",
        f"- recommended_next_action: {payload.get('recommended_next_action', '')}",
        "",
        "## Errors",
    ]
    if payload.get("errors"):
        lines.extend(f"- {e}" for e in payload["errors"])
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Warnings")
    if payload.get("warnings"):
        lines.extend(f"- {w}" for w in payload["warnings"])
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Canonical Sources")
    canonical_sources = payload.get("canonical_sources", [])
    if canonical_sources:
        lines.extend(f"- {s}" for s in canonical_sources)
    else:
        lines.append("- none")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _has_source_url(example: dict[str, Any]) -> bool:
    sales_channels = example.get("sales_channels", [])
    if isinstance(sales_channels, list):
        for ch in sales_channels:
            if isinstance(ch, dict) and str(ch.get("source_url") or "").strip():
                return True
    return False


def _first_template_block_length(text: str, marker: str) -> int:
    idx = text.find(marker)
    if idx < 0:
        return 0
    rest = text[idx:].splitlines()
    block_lines: list[str] = []
    started = False
    blank_streak = 0
    for line in rest:
        if not started:
            if line.strip() == marker:
                started = True
                block_lines.append(line)
            continue
        if line.strip() == "":
            blank_streak += 1
            block_lines.append(line)
            if blank_streak >= 2:
                break
            continue
        blank_streak = 0
        block_lines.append(line)
    return len("\n".join(block_lines).strip())


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    warnings: list[str] = []

    policy = try_load_json(Path(args.policy), errors)
    example = try_load_json(Path(args.example), errors)
    wp_template = try_load_text(Path(args.wp_template), errors, "wp template")
    x_templates = try_load_text(Path(args.x_templates), errors, "x templates")

    route_policy = policy.get("route_policy", {}) if isinstance(policy, dict) else {}
    content_strategy = policy.get("content_strategy", {}) if isinstance(policy, dict) else {}
    copy_policy = policy.get("copy_policy", {}) if isinstance(policy, dict) else {}
    source_policy = policy.get("source_policy", {}) if isinstance(policy, dict) else {}
    resource_allocation = policy.get("resource_allocation_policy", {}) if isinstance(policy, dict) else {}
    safety = policy.get("safety", {}) if isinstance(policy, dict) else {}
    must_remain_false = policy.get("must_remain_false_flags", {}) if isinstance(policy, dict) else {}

    req(policy.get("phase") == "LS-NEW-1", "policy.phase mismatch", errors)
    req(policy.get("status") == "DESIGN_ONLY_NO_EXECUTION", "policy.status mismatch", errors)
    req(policy.get("production_status") == "NO_GO", "policy.production_status mismatch", errors)

    req(bool(safety.get("design_only", False)) is True, "policy.safety.design_only must be true", errors)
    req(bool(safety.get("no_execution", False)) is True, "policy.safety.no_execution must be true", errors)
    req(bool(safety.get("wordpress_write_allowed", True)) is False, "policy.safety.wordpress_write_allowed must be false", errors)
    req(bool(safety.get("x_post_allowed", True)) is False, "policy.safety.x_post_allowed must be false", errors)
    req(bool(safety.get("external_api_call_allowed", True)) is False, "policy.safety.external_api_call_allowed must be false", errors)
    req(bool(safety.get("scraping_allowed", True)) is False, "policy.safety.scraping_allowed must be false", errors)
    req(bool(safety.get("publish_allowed", True)) is False, "policy.safety.publish_allowed must be false", errors)
    req(bool(safety.get("human_review_required", False)) is True, "policy.safety.human_review_required must be true", errors)

    req(route_policy.get("sale_route_status") == "ON_HOLD", "route_policy.sale_route_status mismatch", errors)
    req(
        route_policy.get("new_release_comic_route_status") == "PRIMARY_NEXT_ROUTE",
        "route_policy.new_release_comic_route_status mismatch",
        errors,
    )

    req(content_strategy.get("media_type") == "purchase_navigation_media", "content_strategy.media_type mismatch", errors)
    req(
        content_strategy.get("not_media_type") == "work_explanation_media",
        "content_strategy.not_media_type mismatch",
        errors,
    )
    req(
        bool(content_strategy.get("work_introduction_required", True)) is False,
        "content_strategy.work_introduction_required must be false",
        errors,
    )
    req(
        bool(content_strategy.get("long_work_explanation_required", True)) is False,
        "content_strategy.long_work_explanation_required must be false",
        errors,
    )

    for key in PROHIBITED_COPY_KEYS:
        req(bool(copy_policy.get(key, True)) is False, f"copy_policy.{key} must be false", errors)

    hon_no_hikidashi = source_policy.get("hon_no_hikidashi", {}) if isinstance(source_policy, dict) else {}
    req(
        hon_no_hikidashi.get("usage") == "human_checked_auxiliary_source_only",
        "source_policy.hon_no_hikidashi.usage mismatch",
        errors,
    )
    forbidden = hon_no_hikidashi.get("forbidden", [])
    req(isinstance(forbidden, list) and "auto_scraping" in forbidden, "source_policy.hon_no_hikidashi.forbidden must include auto_scraping", errors)

    canonical_sources = source_policy.get("canonical_sources", [])
    req(isinstance(canonical_sources, list) and "publisher_official" in canonical_sources, "source_policy.canonical_sources missing publisher_official", errors)
    req(isinstance(canonical_sources, list) and "amazon_kindle" in canonical_sources, "source_policy.canonical_sources missing amazon_kindle", errors)

    preferred_methods = source_policy.get("preferred_acquisition_methods", [])
    req(isinstance(preferred_methods, list) and "api" in preferred_methods, "source_policy.preferred_acquisition_methods missing api", errors)

    high_priority = resource_allocation.get("priority_high", [])
    req(isinstance(high_priority, list) and "x_post_generation" in high_priority, "resource_allocation_policy.priority_high missing x_post_generation", errors)
    req(isinstance(high_priority, list) and "price_comparison" in high_priority, "resource_allocation_policy.priority_high missing price_comparison", errors)

    for key, value in must_remain_false.items():
        req(bool(value) is False, f"must_remain_false_flags.{key} must be false", errors)

    req(example.get("protocol") == "LS-NEW-1", "example.protocol mismatch", errors)
    req(example.get("content_type") == "new_release_comic", "example.content_type mismatch", errors)

    item = example.get("item", {}) if isinstance(example, dict) else {}
    title = str(item.get("title", "")).strip()
    release_date = str(item.get("release_date", "")).strip()
    req(title != "", "example.item.title missing", errors)
    req(release_date != "", "example.item.release_date missing", errors)

    sales_channels = example.get("sales_channels", []) if isinstance(example, dict) else []
    req(isinstance(sales_channels, list) and len(sales_channels) > 0, "example.sales_channels missing", errors)
    if isinstance(sales_channels, list):
        for i, channel in enumerate(sales_channels):
            checked_at = ""
            if isinstance(channel, dict):
                checked_at = str(channel.get("checked_at", "")).strip()
            req(checked_at != "", f"example.sales_channels[{i}].checked_at missing", errors)

    has_source_url = _has_source_url(example)
    source_pending = bool(example.get("source_pending", False))
    req(has_source_url or source_pending, "example requires source_url or source_pending=true", errors)

    publisher = str(item.get("publisher", "")).strip()
    req(publisher != "" or has_source_url, "example requires item.publisher or sales_channels[].source_url", errors)

    content_policy = example.get("content_policy", {}) if isinstance(example, dict) else {}
    for key in PROHIBITED_COPY_KEYS:
        req(bool(content_policy.get(key, True)) is False, f"example.content_policy.{key} must be false", errors)
    req(
        bool(content_policy.get("long_work_explanation_required", True)) is False,
        "example.content_policy.long_work_explanation_required must be false",
        errors,
    )

    example_safety = example.get("safety", {}) if isinstance(example, dict) else {}
    for key in EXAMPLE_SAFETY_FALSE_KEYS:
        req(bool(example_safety.get(key, True)) is False, f"example.safety.{key} must be false", errors)
    req(bool(example_safety.get("human_review_required", False)) is True, "example.safety.human_review_required must be true", errors)

    wp_has_store_comparison = "販売ストア確認" in wp_template and "Kindle" in wp_template
    req(wp_has_store_comparison, "wp template missing store comparison section", errors)
    req("作品説明なしでも購入判断ページとして成立すること" in wp_template, "wp template must allow purchase navigation without work explanation", errors)

    wp_forbidden_required_markers = [
        "公式あらすじ必須",
        "あらすじ必須",
        "作品解説必須",
        "長文作品解説必須",
        "長文作品解説を必須とする",
    ]
    for marker in wp_forbidden_required_markers:
        req(marker not in wp_template, f"wp template contains forbidden requirement: {marker}", errors)

    req("【新刊予定】" in x_templates, "x templates missing new release template", errors)
    req("【電子書籍セール】" in x_templates, "x templates missing sale template", errors)

    new_release_len = _first_template_block_length(x_templates, "【新刊予定】")
    sale_len = _first_template_block_length(x_templates, "【電子書籍セール】")
    if new_release_len > 280:
        warnings.append(f"x template new_release exceeds 280 chars: {new_release_len}")
    if sale_len > 280:
        warnings.append(f"x template sale exceeds 280 chars: {sale_len}")

    validation_status = STATUS_VALIDATED if not errors else STATUS_NOT_VALIDATED

    payload = {
        "phase": str(policy.get("phase", "")),
        "name": str(policy.get("name", "")),
        "japanese_name": str(policy.get("japanese_name", "")),
        "status": str(policy.get("status", "")),
        "production_status": str(policy.get("production_status", "")),
        "execution_mode": str(policy.get("execution_mode", "")),
        "validation_status": validation_status,
        "protocol": str(example.get("protocol", "")),
        "content_type": str(example.get("content_type", "")),
        "sale_route_status": str(route_policy.get("sale_route_status", "")),
        "new_release_comic_route_status": str(route_policy.get("new_release_comic_route_status", "")),
        "media_type": str(content_strategy.get("media_type", "")),
        "not_media_type": str(content_strategy.get("not_media_type", "")),
        "work_introduction_required": bool(content_strategy.get("work_introduction_required", False)),
        "long_work_explanation_required": bool(content_strategy.get("long_work_explanation_required", False)),
        "route_policy": route_policy,
        "content_strategy": content_strategy,
        "copy_policy": copy_policy,
        "source_policy": source_policy,
        "resource_allocation_policy": resource_allocation,
        "safety": safety,
        "must_remain_false_flags": must_remain_false,
        "recommended_next_action": str(policy.get("next_phase", {}).get("recommended_next_action", "")),
        "recommended_next_phase_options": list(policy.get("next_phase", {}).get("recommended_next_phase_options", [])),
        "canonical_sources": list(canonical_sources) if isinstance(canonical_sources, list) else [],
        "preferred_acquisition_methods": list(preferred_methods) if isinstance(preferred_methods, list) else [],
        "warnings": warnings,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    write_json(Path(args.output), payload)
    write_report(Path(args.report), payload)
    print(validation_status)
    return 0 if validation_status == STATUS_VALIDATED else 1


if __name__ == "__main__":
    raise SystemExit(main())
