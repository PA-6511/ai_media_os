from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

from src.sheets import get_spreadsheet

QUEUE_SHEET_NAME = "投稿キュー"
REQUIRED_HEADERS = [
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

WORKSHEET_SPECS: dict[str, list[str]] = {
    "投稿キュー": REQUIRED_HEADERS,
    "ASP管理": ["asp_name", "program_name", "base_url", "notes", "updated_at"],
    "記事別収益管理": ["row_id", "work_title", "article_type", "revenue", "updated_at"],
    "リンク管理": ["link_id", "row_id", "store", "url", "rel", "updated_at"],
    "セール管理": ["row_id", "work_title", "sale_start_date", "sale_end_date", "updated_at"],
    "内部リンク管理": ["row_id", "source", "target", "anchor_text", "updated_at"],
    "月次レポート": ["month", "published_count", "draft_count", "updated_at"],
    "エラーログ": ["timestamp", "level", "source", "row_id", "message"],
}


def _ensure_worksheet(spreadsheet, title: str, headers: list[str]) -> tuple[str, object]:
    try:
        worksheet = spreadsheet.worksheet(title)
        action = "既存"
    except Exception:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(len(headers), 10))
        action = "新規作成"

    current_headers = worksheet.row_values(1)
    if current_headers != headers:
        worksheet.update("1:1", [headers])
        action = f"{action}・ヘッダー整備"

    try:
        worksheet.freeze(rows=1)
    except Exception:
        pass
    return action, worksheet


def main() -> int:
    load_dotenv(BASE_DIR / ".env")

    try:
        spreadsheet = get_spreadsheet()
        print(f"OK: スプレッドシート接続成功 ({spreadsheet.title})")
        for title, headers in WORKSHEET_SPECS.items():
            action, _ = _ensure_worksheet(spreadsheet, title, headers)
            print(f"OK: {title} -> {action}")
        print("OK: シート初期化が完了しました")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"エラー: Google Sheets 初期化に失敗しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())