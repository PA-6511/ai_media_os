"""
check_affiliate_links.py

Phase4.16 リンクBLOCKゲート検証:
- HTML内の href="#" 残存チェック
- JSON内の affiliate_url / campaign_url 未設定チェック

終了コード:
- 0: PASS
- 1: BLOCK
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


INVALID_URL_VALUES = {"", "#"}


def is_invalid_url(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return True
    return value.strip() in INVALID_URL_VALUES


def check_html_placeholders(html_path: Path) -> tuple[int, list[str]]:
    text = html_path.read_text(encoding="utf-8")
    count = len(re.findall(r'href="#"', text))

    # data-item-id を持つカードで href="#" のID一覧を抽出（なければ空）
    ids = re.findall(
        r'<a[^>]*class="book-card"[^>]*href="#"[^>]*data-item-id="([^"]+)"',
        text,
    )
    return count, ids


def check_json_links(json_path: Path) -> tuple[int, list[str]]:
    items = json.loads(json_path.read_text(encoding="utf-8"))

    invalid_ids: list[str] = []
    for item in items:
        item_id = str(item.get("id", "<unknown>"))
        url = item.get("affiliate_url", item.get("campaign_url"))
        if is_invalid_url(url):
            invalid_ids.append(item_id)

    return len(invalid_ids), invalid_ids


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase4.16 affiliate link BLOCK gate check"
    )
    parser.add_argument(
        "--html",
        default="kobo-campaign-list-final-v3.html",
        help="HTML file path (default: kobo-campaign-list-final-v3.html)",
    )
    parser.add_argument(
        "--json",
        default="data/campaign_items.json",
        help="campaign items JSON path (default: data/campaign_items.json)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    html_path = Path(args.html)
    json_path = Path(args.json)

    if not html_path.exists():
        print(f"NG: html file not found: {html_path}")
        return 1
    if not json_path.exists():
        print(f"NG: json file not found: {json_path}")
        return 1

    html_count, html_ids = check_html_placeholders(html_path)
    json_count, json_ids = check_json_links(json_path)

    print("=== Affiliate Link Block Gate ===")
    print(f"html href=# count : {html_count}")
    print(f"json invalid count: {json_count}")

    if html_ids:
        print("html href=# item_ids:", ", ".join(html_ids))
    if json_ids:
        print("json invalid item_ids:", ", ".join(json_ids))

    if html_count > 0 or json_count > 0:
        print("RESULT: BLOCK (do not reflect to production)")
        return 1

    print("RESULT: PASS (safe to proceed to next gate)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
