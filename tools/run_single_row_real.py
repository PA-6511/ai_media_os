from __future__ import annotations

import contextlib
import io
import os
import sys
import logging
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
from pipelines.publish_article_pipeline import build_wp_article, create_publisher_from_env, enforce_wp_prepublish_quality
from src.sheets import append_error_log, fetch_all_rows, get_sheet, update_row_fields

QUEUE_SHEET_NAME = "投稿キュー"


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
            f"[run_single_row_real] draft投稿 成功 {row_id}",
            [f"status: {status}", f"draft_url: {draft_url}"],
        )
    except Exception as e:
        logging.getLogger(__name__).warning("Slack notification failed (run_single_row_real): %s", e)


def _print_result(row_id: str, status: str, wp_post_id: str, wp_draft_url: str, error_message: str) -> None:
    print(f"row_id={row_id}")
    print(f"status={status}")
    print(f"wp_post_id={wp_post_id}")
    print(f"wp_draft_url={wp_draft_url}")
    print(f"error_message={error_message}")


def _confirm_execution(row_id: str) -> bool:
    print("確認: この処理はWordPressに実際の下書きを1件作成します")
    print("確認: 公開はしません")
    print(f"確認: 対象 row_id: {row_id}")
    answer = input("続行する場合は YES と入力してください: ").strip()
    return answer == "YES"


def _should_skip_confirmation(args: list[str]) -> bool:
    return any(arg == "--yes" for arg in args)


def _build_taxonomy_from_row(row: dict[str, Any]) -> tuple[list[str], list[str]]:
    category = str(row.get("category", "")).strip() or "review"
    raw_tags = str(row.get("tags", "")).strip()

    categories = [category]
    tags: list[str] = []
    if raw_tags:
        tags = [part.strip() for part in raw_tags.split(",") if part.strip()]
    if not tags:
        work_title = str(row.get("work_title", "")).strip()
        if work_title:
            tags = [work_title, "test"]
        else:
            tags = ["test"]
    return categories, tags


def main(argv: list[str] | None = None) -> int:
    load_dotenv(BASE_DIR / ".env", override=True)

    args = argv if argv is not None else sys.argv[1:]
    skip_confirmation = _should_skip_confirmation(args)
    normalized_args = [arg for arg in args if arg != "--yes"]
    if len(normalized_args) != 1:
        print("エラー: row_id を1つ指定してください。例: python3 tools/run_single_row_real.py TEST-WP-001")
        return 1

    row_id = normalized_args[0].strip()
    if not row_id:
        print("エラー: row_id が空です")
        return 1

    if not skip_confirmation and not _confirm_execution(row_id):
        print("中止: YES が入力されなかったため処理を停止しました")
        return 1

    sheet = None
    row: dict[str, Any] | None = None
    try:
        # 実投稿ゲートでは必ず real-run を強制する。
        os.environ["WP_DRY_RUN"] = "0"
        os.environ["DRY_RUN"] = "false"

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

        wp_article = build_wp_article(article_output)
        wp_article["row_id"] = row_id
        category_names, tag_names = _build_taxonomy_from_row(row)
        if not wp_article.get("category_names"):
            wp_article["category_names"] = category_names
        if not wp_article.get("tag_names"):
            wp_article["tag_names"] = tag_names

        wp_article = enforce_wp_prepublish_quality(wp_article, row=row)
        publisher, _ = create_publisher_from_env()
        publish_result = publisher.publish(wp_article, dry_run=False)

        wp_post_id = str(publish_result.get("post_id", ""))
        wp_draft_url = str(publish_result.get("link", ""))
        now = datetime.now(timezone.utc).isoformat()

        update_row_fields(
            sheet,
            int(row["_row_index"]),
            {
                "status": "DRAFTED",
                "wp_post_id": wp_post_id,
                "wp_draft_url": wp_draft_url,
                "error_message": "",
                "updated_at": now,
            },
        )

        _notify_success(row_id, "DRAFTED", wp_draft_url)
        _print_result(
            row_id=row_id,
            status="DRAFTED",
            wp_post_id=wp_post_id,
            wp_draft_url=wp_draft_url,
            error_message="",
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        error_message = str(exc)
        if sheet is not None and row is not None:
            try:
                update_row_fields(
                    sheet,
                    int(row["_row_index"]),
                    {
                        "error_message": error_message,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                append_error_log(sheet, int(row["_row_index"]), error_message)
            except Exception as sheet_err:
                logging.getLogger(__name__).warning("Sheets error-log write failed (FAILED branch): %s", sheet_err)

        _print_result(
            row_id=row_id,
            status="FAILED",
            wp_post_id="",
            wp_draft_url="",
            error_message=error_message,
        )
        return 1
    except KeyboardInterrupt:
        error_message = "KeyboardInterrupt"
        if sheet is not None and row is not None:
            try:
                update_row_fields(
                    sheet,
                    int(row["_row_index"]),
                    {
                        "error_message": error_message,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                )
                append_error_log(sheet, int(row["_row_index"]), error_message)
            except Exception as sheet_err:
                logging.getLogger(__name__).warning("Sheets error-log write failed (KeyboardInterrupt): %s", sheet_err)

        _print_result(
            row_id=row_id,
            status="FAILED",
            wp_post_id="",
            wp_draft_url="",
            error_message=error_message,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())