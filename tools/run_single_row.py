from __future__ import annotations

import contextlib
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

from article_generator.generator import generate_article_content
from article_planner.planner import generate_plan
from monitoring.slack_notifier import send_slack_block
from pipelines.post_status_store import build_status_record, upsert_status
from pipelines.wp_post_enricher import build_slug
from src.sheets import fetch_all_rows, get_sheet, update_row_fields, append_error_log

QUEUE_SHEET_NAME = "投稿キュー"


def _to_bool(value: str, default: bool = False) -> bool:
    text = (value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _find_row(rows: list[dict[str, Any]], row_id: str) -> dict[str, Any] | None:
    for row in rows:
        if str(row.get("row_id", "")).strip() == row_id:
            return row
    return None


def _build_plan_input(row: dict[str, Any]) -> dict[str, Any]:
    work_title = str(row.get("work_title", "")).strip() or str(row.get("title", "")).strip() or "テスト作品"
    keyword = str(row.get("target_keyword", "")).strip() or f"{work_title} レビュー"
    return {
        "work_id": str(row.get("row_id", "")).strip().lower() or "test-001",
        "title": work_title,
        "keyword": keyword,
        "article_type": str(row.get("article_type", "review")).strip() or "review",
        "author": str(row.get("author", "")).strip(),
        "publisher": str(row.get("publisher", "")).strip(),
        "category": str(row.get("category", "review")).strip() or "review",
        "campaign_name": str(row.get("campaign_name", "")).strip(),
        "sale_start_date": str(row.get("sale_start_date", "")).strip(),
        "sale_end_date": str(row.get("sale_end_date", "")).strip(),
        "entry_required": str(row.get("entry_required", "")).strip(),
        "discount_text": str(row.get("discount_text", "")).strip(),
        "point_text": str(row.get("point_text", "")).strip(),
        "store": str(row.get("store", "")).strip(),
        "rakuten_url": str(row.get("rakuten_url", "")).strip(),
        "official_url": str(row.get("official_url", "")).strip(),
        "dmm_url": str(row.get("dmm_url", "")).strip(),
        "cta_store_priority": str(row.get("cta_store_priority", "")).strip(),
    }


def _notify_success(row_id: str, status: str, draft_url: str) -> None:
    if not os.getenv("SLACK_WEBHOOK_URL", "").strip():
        return
    try:
        send_slack_block(
            f"[run_single_row] DRY_RUN 成功 {row_id}",
            [f"status: {status}", f"draft_url: {draft_url}"]
        )
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    load_dotenv(BASE_DIR / ".env")

    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print("エラー: row_id を1つ指定してください。例: python3 tools/run_single_row.py TEST-001")
        return 1

    row_id = args[0].strip()
    if not row_id:
        print("エラー: row_id が空です")
        return 1

    try:
        dry_run = _to_bool(os.getenv("DRY_RUN", os.getenv("WP_DRY_RUN", "true")), default=True)
        if not dry_run:
            print("エラー: DRY_RUN=true で実行してください")
            return 1

        os.environ["WP_DRY_RUN"] = "1"
        sheet = get_sheet(QUEUE_SHEET_NAME)
        rows = fetch_all_rows(sheet)
        row = _find_row(rows, row_id)
        if row is None:
            print(f"エラー: row_id={row_id} が投稿キューに見つかりません")
            return 1

        current_status = str(row.get("status", "")).strip().upper()
        if current_status != "NEW":
            print(f"エラー: row_id={row_id} の status が NEW ではありません: {current_status}")
            return 1

        plan_input = _build_plan_input(row)
        plan = generate_plan(plan_input)
        with contextlib.redirect_stdout(io.StringIO()):
            article_output = generate_article_content(plan)

        slug = build_slug(article_output)
        now = datetime.now(timezone.utc).isoformat()
        draft_token = f"DRY_RUN-{row_id}"
        base_url = os.getenv("WP_BASE_URL", "https://example.invalid").rstrip("/")
        draft_url = f"{base_url}/dry-run/{row_id}"

        update_row_fields(
            sheet,
            int(row["_row_index"]),
            {
                "status": "DRAFTED",
                "wp_post_id": draft_token,
                "wp_draft_url": draft_url,
                "error_message": "",
                "updated_at": now,
            },
        )

        status_record = build_status_record(
            slug=slug,
            work_id=str(article_output.get("work_id", row_id)),
            keyword=str(article_output.get("keyword", "")),
            article_type=str(article_output.get("article_type", "work_article")),
            title=str(article_output.get("title", "")),
            status="draft",
            post_id=None,
            link=draft_url,
            error_message=None,
        )
        upsert_status(status_record)

        _notify_success(row_id, "DRAFTED", draft_url)
        print(f"OK: row_id={row_id} を DRY_RUN で処理しました")
        print("OK: status=DRAFTED")
        print(f"OK: wp_post_id={draft_token}")
        print(f"OK: wp_draft_url={draft_url}")
        return 0
    except Exception as exc:  # noqa: BLE001
        try:
            sheet = get_sheet(QUEUE_SHEET_NAME)
            rows = fetch_all_rows(sheet)
            row = _find_row(rows, row_id)
            if row is not None:
                update_row_fields(
                    sheet,
                    int(row["_row_index"]),
                    {
                        "error_message": str(exc),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                append_error_log(sheet, int(row["_row_index"]), str(exc))
        except Exception:
            pass
        print(f"エラー: 単発DRY_RUN検証に失敗しました: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())