#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BLOCKED_TOKENS = ["MANUAL_REQUIRED", "Sample", "sample", "exampletag", "B0DUMMY001"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def contains_blocked_token(value: str) -> bool:
    return any(token in value for token in BLOCKED_TOKENS)


def build_html_content(item: dict[str, Any]) -> str:
    return "\n".join(
        [
            "<p><strong>PR</strong> このページには広告リンクが含まれます。</p>",
            "<h2>作品情報</h2>",
            "<ul>",
            f"  <li>作品名: {item['title']}</li>",
            f"  <li>著者: {item['author']}</li>",
            f"  <li>巻数: {item['volume']}</li>",
            f"  <li>発売日: {item['release_date']}</li>",
            "</ul>",
            f"<p>{item['summary']}</p>",
            f"<p><a href=\"{item['purchase_url']}\" rel=\"nofollow sponsored noopener\" target=\"_blank\">Amazonで確認する</a></p>",
            "<p>価格や在庫状況は変動する場合があります。購入前にAmazonの商品ページで最新情報をご確認ください。</p>",
        ]
    )


def validate_item(item: dict[str, Any], errors: list[str]) -> None:
    required_keys = [
        "title",
        "author",
        "volume",
        "release_date",
        "asin",
        "affiliate_tag",
        "summary",
        "purchase_url",
        "category",
        "tags",
    ]
    for key in required_keys:
        require(key in item, f"item.{key} is required", errors)

    for key in ["title", "author", "volume", "release_date", "asin", "affiliate_tag", "summary", "purchase_url", "category"]:
        value = str(item.get(key, ""))
        require(bool(value.strip()), f"item.{key} must not be empty", errors)
        require(not contains_blocked_token(value), f"item.{key} contains blocked token", errors)

    asin = str(item.get("asin", ""))
    require(asin.startswith("B0") and len(asin) == 10, "item.asin must look like Amazon ASIN", errors)

    tag = str(item.get("affiliate_tag", ""))
    require(tag.endswith("-22"), "item.affiliate_tag must end with -22", errors)

    purchase_url = str(item.get("purchase_url", ""))
    require("https://www.amazon.co.jp/dp/" in purchase_url, "item.purchase_url must contain amazon.co.jp/dp", errors)
    require("tag=" in purchase_url, "item.purchase_url must contain tag=", errors)
    require(tag in purchase_url, "item.purchase_url must include affiliate_tag", errors)

    category = str(item.get("category", ""))
    require(category != "未分類", "item.category must not be 未分類", errors)

    tags = item.get("tags")
    require(isinstance(tags, list) and len(tags) > 0, "item.tags must be a non-empty list", errors)
    if isinstance(tags, list):
        for i, t in enumerate(tags):
            require(bool(str(t).strip()), f"item.tags[{i}] must not be empty", errors)
            require(not contains_blocked_token(str(t)), f"item.tags[{i}] contains blocked token", errors)


def build_result_not_ready(errors: list[str]) -> dict[str, Any]:
    return {
        "phase": "LS-6C",
        "status": "LS6C_REAL_INPUT_NOT_READY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "payload_ready": False,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
        "errors": errors,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_result_ready(item: dict[str, Any]) -> dict[str, Any]:
    html = build_html_content(item)
    payload = {
        "post_status": "draft",
        "title": item["title"],
        "content_format": "html",
        "content": html,
        "affiliate_disclosure_present": "このページには広告リンクが含まれます" in html,
        "affiliate_link_present": "amazon.co.jp/dp/" in html,
        "html_link_present": "<a href=" in html,
        "markdown_link_present": "[" in html and "](" in html,
        "category": item["category"],
        "tags": item["tags"],
        "category_or_tag_present": bool(item["category"]) and len(item["tags"]) > 0,
        "sample_content_detected": contains_blocked_token(html),
        "core_boundary_ref": None,
        "audit_observation_ref": None,
        "risk_score": None,
        "rollback_pointer": {
            "required": True,
            "status": "DRY_RUN_PLACEHOLDER",
        },
    }

    return {
        "phase": "LS-6C",
        "status": "LS6C_REAL_DRAFT_PAYLOAD_REBUILT_DRY_RUN_READY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "payload_ready": True,
        "input_status": "ACTUAL_MANUAL_INPUT",
        "max_items": 1,
        "payload_count": 1,
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "wordpress_existing_post_update_executed": False,
        "post119_update_executed": False,
        "publish_executed": False,
        "approval_token_consumed": False,
        "payloads": [payload],
        "errors": [],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def run_builder(policy_path: Path, input_path: Path, output_path: Path) -> dict[str, Any]:
    _policy = load_json(policy_path)

    if not input_path.exists():
        result = build_result_not_ready(["actual manual input file not found"])
    else:
        input_json = load_json(input_path)
        errors: list[str] = []
        require(input_json.get("phase") == "LS-6C", "input phase must be LS-6C", errors)
        require(input_json.get("input_status") == "ACTUAL_MANUAL_INPUT", "input_status must be ACTUAL_MANUAL_INPUT", errors)
        item = input_json.get("item", {})
        require(isinstance(item, dict), "item must be object", errors)
        if isinstance(item, dict):
            validate_item(item, errors)

        result = build_result_not_ready(errors) if errors else build_result_ready(item)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="config/start_ls6c_real_draft_payload_rebuild_dry_run_policy.json")
    parser.add_argument("--input", default="manual_affiliate_builder/real_manual_item.input.json")
    parser.add_argument("--output", default="exchange/logs/start_ls6c_real_draft_payload_preview.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_builder(Path(args.policy), Path(args.input), Path(args.output))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
