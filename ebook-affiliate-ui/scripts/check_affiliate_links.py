"""
check_affiliate_links.py

Phase4.81 リンク検証拡張:
- HTML内の href="#" 残存チェック
- JSON内の affiliate_url / campaign_url の両方を検証
- LINK_CHECK_MODE=DRY_RUN/PRODUCTION のモード分離
- store別許可ドメイン検証

終了コード:
- 0: PRODUCTIONで全条件PASS
- 1: BLOCK
- 2: 実行エラー/設定エラー
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse


INVALID_URL_VALUES = {"", "#"}
ALLOWED_MODES = {"DRY_RUN", "PRODUCTION"}

# 設計書準拠の基本定義。実データのstore値もここで吸収する。
ALLOWED_DOMAINS_BY_STORE = {
    "kobo": {"books.rakuten.co.jp", "hb.afl.rakuten.co.jp"},
    "rakuten": {"books.rakuten.co.jp", "hb.afl.rakuten.co.jp"},
    "amazon": {"www.amazon.co.jp", "amzn.to"},
    "rakuten_kobo": {"books.rakuten.co.jp", "hb.afl.rakuten.co.jp"},
    "kindle": {"www.amazon.co.jp", "amzn.to"},
    "cmoa": {"www.cmoa.jp"},
    "dmm_books": {"book.dmm.com", "al.dmm.com"},
}


def normalize_mode(raw_mode: str | None) -> str:
    mode = (raw_mode or "DRY_RUN").strip().upper()
    if mode not in ALLOWED_MODES:
        raise ValueError(
            f"invalid LINK_CHECK_MODE: {raw_mode!r} (use DRY_RUN or PRODUCTION)"
        )
    return mode


def is_invalid_url(value: object) -> bool:
    if value is None:
        return True
    if not isinstance(value, str):
        return True
    return value.strip() in INVALID_URL_VALUES


def detect_invalid_reason(url_value: object) -> str | None:
    if is_invalid_url(url_value):
        return "empty_or_unset"
    if not isinstance(url_value, str):
        return "empty_or_unset"
    trimmed = url_value.strip()
    if trimmed.lower().startswith("javascript:"):
        return "invalid_url"
    return None


def parse_https_hostname(url: str) -> tuple[str | None, str | None]:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return None, "non_https"
    if not parsed.hostname:
        return None, "invalid_url"
    return parsed.hostname.lower(), None


def is_example_invalid_host(hostname: str) -> bool:
    return hostname == "example.invalid"


def validate_url_for_store(mode: str, store: object, url_value: object) -> tuple[bool, bool, str]:
    base_invalid = detect_invalid_reason(url_value)
    if base_invalid is not None:
        return False, False, base_invalid

    assert isinstance(url_value, str)
    hostname, parse_error = parse_https_hostname(url_value.strip())
    if parse_error:
        return False, False, parse_error

    assert hostname is not None
    if is_example_invalid_host(hostname):
        if mode == "DRY_RUN":
            return True, True, "dry_run_placeholder"
        return False, True, "placeholder_not_allowed_in_production"

    store_key = str(store or "").strip().lower()
    if not store_key:
        return False, False, "store_missing"

    allowed_domains = ALLOWED_DOMAINS_BY_STORE.get(store_key)
    if not allowed_domains:
        return False, False, "store_not_allowed"

    if hostname not in allowed_domains:
        return False, False, "domain_not_allowed"

    return True, False, "ok"


def check_html_placeholders(html_path: Path) -> tuple[int, list[str]]:
    text = html_path.read_text(encoding="utf-8")
    count = len(re.findall(r'href="#"', text))

    # data-item-id を持つカードで href="#" のID一覧を抽出（なければ空）
    ids = re.findall(
        r'<a[^>]*class="book-card"[^>]*href="#"[^>]*data-item-id="([^"]+)"',
        text,
    )
    return count, ids


def check_json_links(mode: str, json_path: Path) -> dict[str, object]:
    items = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise ValueError("campaign_items.json root must be a list")

    affiliate_checked = 0
    campaign_checked = 0
    invalid_count = 0
    example_invalid_count = 0
    invalid_records: list[str] = []

    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each campaign item must be an object")

        item_id = str(item.get("id", "<unknown>"))
        store = item.get("store")

        for field in ("affiliate_url", "campaign_url"):
            if field == "affiliate_url":
                affiliate_checked += 1
            else:
                campaign_checked += 1

            ok, is_placeholder, reason = validate_url_for_store(mode, store, item.get(field))

            if is_placeholder:
                example_invalid_count += 1

            if not ok:
                invalid_count += 1
                invalid_records.append(f"{item_id}:{field}:{reason}")

    return {
        "total_items": len(items),
        "affiliate_checked": affiliate_checked,
        "campaign_checked": campaign_checked,
        "invalid_count": invalid_count,
        "example_invalid_count": example_invalid_count,
        "invalid_records": invalid_records,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase4.81 affiliate link domain/policy check"
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
    try:
        args = parse_args()
        mode = normalize_mode(os.getenv("LINK_CHECK_MODE"))

        html_path = Path(args.html)
        json_path = Path(args.json)

        if not html_path.exists():
            print(f"NG: html file not found: {html_path}")
            return 2
        if not json_path.exists():
            print(f"NG: json file not found: {json_path}")
            return 2

        html_count, html_ids = check_html_placeholders(html_path)
        json_report = check_json_links(mode, json_path)

        print("=== Affiliate Link Block Gate (Phase4.81) ===")
        print(f"mode                 : {mode}")
        print(f"total items          : {json_report['total_items']}")
        print(f"affiliate checked    : {json_report['affiliate_checked']}")
        print(f"campaign checked     : {json_report['campaign_checked']}")
        print(f"html href=# count    : {html_count}")
        print(f"json invalid count   : {json_report['invalid_count']}")
        print(f"example.invalid count: {json_report['example_invalid_count']}")

        if html_ids:
            print("html href=# item_ids:", ", ".join(html_ids))

        invalid_records = json_report["invalid_records"]
        if invalid_records:
            print("json invalid records:", ", ".join(invalid_records))

        dry_run_placeholder_detected = mode == "DRY_RUN" and json_report[
            "example_invalid_count"
        ] > 0
        if dry_run_placeholder_detected:
            print("WARN: DRY_RUN placeholder detected (example.invalid)")

        should_block = (
            html_count > 0
            or json_report["invalid_count"] > 0
            or dry_run_placeholder_detected
        )

        result = "BLOCKED" if should_block else "PASS"
        print(f"production reflection: {result}")

        if mode == "PRODUCTION" and not should_block:
            print("RESULT: PASS")
            return 0

        print("RESULT: BLOCK")
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
