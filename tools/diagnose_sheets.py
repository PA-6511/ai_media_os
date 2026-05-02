from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

from src.sheets import fetch_all_rows, get_spreadsheet

QUEUE_SHEET_NAME = "投稿キュー"
ERROR_LOG_SHEET_NAME = "エラーログ"
EXPECTED_HEADERS = [
    "row_id",
    "status",
    "article_type",
    "priority",
    "title",
    "work_title",
    "author",
    "publisher",
    "genre",
    "series_name",
    "volume",
    "store",
    "asin",
    "rakuten_url",
    "dmm_url",
    "official_url",
    "campaign_name",
    "sale_start_date",
    "sale_end_date",
    "entry_required",
    "discount_text",
    "point_text",
    "target_keyword",
    "category",
    "tags",
    "internal_link_candidates",
    "cta_store_priority",
    "notes",
    "wp_post_id",
    "wp_draft_url",
    "published_url",
    "error_message",
    "created_at",
    "updated_at",
]
REQUIRED_COLUMNS = [
    "row_id",
    "status",
    "article_type",
    "work_title",
    "category",
    "tags",
    "wp_post_id",
    "wp_draft_url",
    "error_message",
    "updated_at",
]


def _validate_env() -> None:
    spreadsheet_id = os.getenv("SPREADSHEET_ID", "").strip()
    if not spreadsheet_id:
        raise ValueError("SPREADSHEET_ID が未設定です")

    service_account_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not service_account_raw:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON が未設定です")

    if service_account_raw.startswith("/"):
        path = Path(service_account_raw)
        if not path.exists():
            raise FileNotFoundError(
                f"GOOGLE_SERVICE_ACCOUNT_JSON が指すファイルが存在しません: {path}"
            )


def main() -> int:
    load_dotenv(BASE_DIR / ".env")

    try:
        print("OK: .env 読み込み")
        _validate_env()
        print("OK: 必須環境変数確認")

        spreadsheet = get_spreadsheet()
        print(f"OK: Google Sheets 接続成功 ({spreadsheet.title})")

        queue_sheet = spreadsheet.worksheet(QUEUE_SHEET_NAME)
        print("OK: 投稿キューシート取得")

        headers = queue_sheet.row_values(1)
        if headers != EXPECTED_HEADERS:
            print("SHEETS_HEADER_MISMATCH")
            print(f"現在ヘッダー列数: {len(headers)} / 期待列数: {len(EXPECTED_HEADERS)}")
            return 1
        print("OK: ヘッダー34列確認")

        missing_required = [name for name in REQUIRED_COLUMNS if name not in headers]
        if missing_required:
            print("SHEETS_MISSING_REQUIRED_COLUMN")
            print(", ".join(missing_required))
            return 1
        print("OK: 必須列確認")

        error_log_sheet = spreadsheet.worksheet(ERROR_LOG_SHEET_NAME)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        error_log_sheet.append_row(
            [timestamp, "INFO", "diagnose_sheets", "", "diagnose test append"]
        )
        print("OK: エラーログシート追記確認")

        rows = fetch_all_rows(queue_sheet)
        new_count = sum(1 for row in rows if str(row.get("status", "")).strip().upper() == "NEW")
        print(f"OK: NEW 行数 = {new_count}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"エラー: Google Sheets 診断に失敗しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())