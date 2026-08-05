#!/usr/bin/env python3
"""Build dry-run WordPress draft preview payload from manual items."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "manual_affiliate_builder" / "manual_items.example.json"
DEFAULT_PAYLOAD_OUT = ROOT / "exchange" / "logs" / "phase8_50_manual_wp_draft_payload_preview.json"
DEFAULT_MD_OUT = ROOT / "reports" / "phase8_50_manual_wp_draft_payload_preview.md"
JST = timezone(timedelta(hours=9))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_input(input_path: Path) -> None:
    validator = ROOT / "scripts" / "validate_manual_affiliate_items.py"
    completed = subprocess.run(
        [sys.executable, str(validator), "--input", str(input_path)],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "manual affiliate item validation failed\n"
            + completed.stdout
            + completed.stderr
        )


def build_post_content(item: Dict[str, Any]) -> str:
    title = item["title"]
    author = item["author"]
    volume = item["volume"]
    release_date = item["release_date"]
    url = item["manual_affiliate_url"]

    return "\n".join(
        [
            "**PR** This page contains affiliate links.",
            "",
            f"{title}",
            "",
            f"{title} is an ebook by {author}.",
            "",
            f"Volume: {volume}",
            "",
            f"Release date: {release_date}",
            "",
            "Purchase link",
            f"[Check on Amazon]({url})",
            "",
            "Prices and availability may change. Please check the latest details on Amazon before purchasing.",
            "",
        ]
    )


def build_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    generated_at = datetime.now(JST).isoformat()

    posts: List[Dict[str, Any]] = []
    for item in data["items"]:
        asin = item["asin"].strip().upper()

        posts.append(
            {
                "local_preview_id": f"manual-preview-{asin}",
                "post_type": "post",
                "post_status": "draft_preview_only",
                "wordpress_write_allowed": False,
                "amazon_api_call_allowed": False,
                "source_used": "manual",
                "source_mode": item["source_mode"],
                "migration_status": item["migration_status"],
                "asin": asin,
                "canonical_item_id": item["canonical_item_id"],
                "title": f"{item['title']} | Ebook Introduction",
                "content": build_post_content(item),
                "categories": ["ebook", "manga-lightnovel", "manual-import"],
                "tags": [asin, item["author"], item["title"]],
                "meta": {
                    "phase": "Phase 8-50-MANUAL",
                    "execution_mode": "DRY_RUN_ONLY",
                    "production_status": "NO_GO",
                    "generated_at": generated_at,
                    "api_verified": item.get("api_verified", False),
                    "human_review_status": item.get("human_review_status", "pending"),
                    "wordpress_status": item.get("wordpress_status", "not_created"),
                },
            }
        )

    return {
        "phase": "Phase 8-50-MANUAL",
        "status": "PREVIEW_GENERATED_DRY_RUN_ONLY",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "amazon_api_call_allowed": False,
        "wordpress_write_allowed": False,
        "generated_at": generated_at,
        "post_count": len(posts),
        "posts": posts,
    }


def write_markdown(payload: Dict[str, Any], output_path: Path) -> None:
    lines: List[str] = []

    lines.append("# Phase 8-50-MANUAL Manual Affiliate Draft Preview")
    lines.append("")
    lines.append(f"- Status: `{payload['status']}`")
    lines.append(f"- Execution: `{payload['execution_mode']}`")
    lines.append(f"- Production: `{payload['production_status']}`")
    lines.append(f"- Amazon API call allowed: `{str(payload['amazon_api_call_allowed']).lower()}`")
    lines.append(f"- WordPress write allowed: `{str(payload['wordpress_write_allowed']).lower()}`")
    lines.append(f"- Generated at: `{payload['generated_at']}`")
    lines.append(f"- Post count: `{payload['post_count']}`")
    lines.append("")
    lines.append("## Draft previews")
    lines.append("")

    for post in payload["posts"]:
        lines.append(f"### {post['title']}")
        lines.append("")
        lines.append(f"- ASIN: `{post['asin']}`")
        lines.append(f"- Canonical item ID: `{post['canonical_item_id']}`")
        lines.append(f"- Source used: `{post['source_used']}`")
        lines.append(f"- Migration status: `{post['migration_status']}`")
        lines.append(f"- WordPress write allowed: `{str(post['wordpress_write_allowed']).lower()}`")
        lines.append(f"- Amazon API call allowed: `{str(post['amazon_api_call_allowed']).lower()}`")
        lines.append("")
        lines.append("#### Content preview")
        lines.append("")
        lines.append("```markdown")
        lines.append(post["content"])
        lines.append("```")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build WordPress draft payload preview from manual affiliate items."
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
        help="Path to manual affiliate items JSON.",
    )
    parser.add_argument(
        "--payload-out",
        default=str(DEFAULT_PAYLOAD_OUT),
        help="Output path for preview JSON payload.",
    )
    parser.add_argument(
        "--md-out",
        default=str(DEFAULT_MD_OUT),
        help="Output path for markdown preview.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    payload_out = Path(args.payload_out)
    md_out = Path(args.md_out)

    try:
        validate_input(input_path)
        data = load_json(input_path)
        payload = build_payload(data)

        payload_out.parent.mkdir(parents=True, exist_ok=True)
        md_out.parent.mkdir(parents=True, exist_ok=True)

        payload_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        write_markdown(payload, md_out)

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "phase": "Phase 8-50-MANUAL",
                    "execution_mode": "DRY_RUN_ONLY",
                    "production_status": "NO_GO",
                    "amazon_api_call_allowed": False,
                    "wordpress_write_allowed": False,
                    "payload_out": str(payload_out),
                    "markdown_out": str(md_out),
                    "post_count": payload["post_count"],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "phase": "Phase 8-50-MANUAL",
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
