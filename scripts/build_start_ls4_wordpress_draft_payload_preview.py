#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "exchange" / "logs" / "phase8_50b_manual_items.from_csv.json"
DEFAULT_OUTPUT = ROOT / "exchange" / "logs" / "start_ls4_wordpress_draft_payload_preview.json"
JST = timezone(timedelta(hours=9))


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_content(item: Dict[str, Any]) -> str:
    title = item.get("title", "")
    author = item.get("author", "")
    volume = item.get("volume", "")
    release_date = item.get("release_date", "")
    url = item.get("manual_affiliate_url", "")

    return "\n".join(
        [
            "**PR** This page contains affiliate links.",
            "",
            title,
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


def build_preview(data: Dict[str, Any], max_items: int = 1) -> Dict[str, Any]:
    generated_at = datetime.now(JST).isoformat()
    source_items = list(data.get("items", []))[: max(0, max_items)]

    payloads = []
    for item in source_items:
        title = item.get("title", "")
        payloads.append(
            {
                "post_status": "draft",
                "title": title,
                "content": build_content(item),
                "affiliate_disclosure_present": True,
                "affiliate_link_present": True,
                "category_or_tag_present": True,
                "categories": ["ebook", "manga-lightnovel", "manual-import"],
                "tags": [item.get("asin", ""), item.get("author", ""), title],
                "core_boundary_ref": None,
                "audit_observation_ref": None,
                "risk_score": None,
                "rollback_pointer": {
                    "required": True,
                    "status": "DRY_RUN_PLACEHOLDER",
                },
            }
        )

    return {
        "phase": "LS-4",
        "execution_mode": "DRY_RUN_ONLY",
        "production_status": "NO_GO",
        "wordpress_api_call_executed": False,
        "wordpress_write_executed": False,
        "wordpress_draft_creation_executed": False,
        "publish_executed": False,
        "max_items": max_items,
        "generated_at": generated_at,
        "payloads": payloads,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build LS-4 WordPress draft payload preview.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--max-items", type=int, default=1)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    data = load_json(input_path)
    preview = build_preview(data, max_items=args.max_items)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output_path), "payloads": len(preview["payloads"])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())