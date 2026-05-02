"""scripts/sale_end_check.py

セール終了チェック。

【主入力】Google Sheets 投稿キュー (src.sheets)
【補助入力】data/items/*_sale_article_*.json
  - Sheets への接続が失敗した場合（.env 未設定時など）は
    data/items/*.json を fallback として使用する。
  - ただし fallback 時は status 更新・error_log 追記は行わない。

status 更新ルール:
  - article_type が SALE_TYPES 以外 → スキップ
  - status が FAILED / SKIPPED → 触らない
  - STATUS_CONFLICT → FAILED にしない（スキップ）
  - sale_end_date が空 → スキップ
  - sale_end_date <= today:
      PUBLISHED        → NEEDS_UPDATE
      DRAFTED / NEEDS_REVIEW / NEW / GENERATED / DRAFTING → SALE_ENDED
  - 1行失敗しても次へ継続

Usage:
    cd ~/ai_media_os
    python scripts/sale_end_check.py [--dry-run] [--items-dir PATH]
"""
from __future__ import annotations

import argparse
import importlib
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

BASE_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = BASE_DIR / "data" / "logs" / "sale_end_check.log"
ITEMS_DIR = BASE_DIR / "data" / "items"

# 対象 article_type
SALE_TYPES: frozenset[str] = frozenset({"sale_article", "sale"})

# status ごとの更新先（sale_end_date が期限切れの場合）
EXPIRED_STATUS_MAP: dict[str, str] = {
    "PUBLISHED": "NEEDS_UPDATE",
    "DRAFTED": "SALE_ENDED",
    "NEEDS_REVIEW": "SALE_ENDED",
    "NEW": "SALE_ENDED",
    "GENERATED": "SALE_ENDED",
    "DRAFTING": "SALE_ENDED",
}

# 更新対象外 status（触らない）
SKIP_STATUSES: frozenset[str] = frozenset({"FAILED", "SKIPPED", "STATUS_CONFLICT"})


# --- ロガー ---

def _setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("scripts.sale_end_check")
    logger.setLevel(logging.INFO)
    # テストで main() を繰り返し呼んでもハンドラをリークさせない。
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    logger.propagate = False
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


# --- ユーティリティ ---

def _parse_date(value: str) -> date | None:
    """YYYY-MM-DD または ISO8601 文字列を date に変換する。"""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


# --- 補助: data/items/*.json 読み込み (fallback 用) ---

def load_local_sale_items(items_dir: Path) -> list[dict[str, Any]]:
    """items_dir 配下の *_sale_article_*.json を読み込み、
    Sheets 行と同じ dict 形式に正規化して返す。
    """
    results: list[dict[str, Any]] = []
    if not items_dir.exists():
        return results
    for p in sorted(items_dir.glob("*_sale_article_*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("article_type", "sale_article")
                data.setdefault("status", "")
                data["_source"] = "local"
                data["_source_file"] = p.name
                results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return results


# --- コアロジック（純粋関数）---

def determine_new_status(row: dict[str, Any], today: date) -> str | None:
    """1行のデータを評価してステータス変更先を返す。変更不要なら None。

    Args:
        row:   fetch_all_rows / load_local_sale_items で得た行 dict
        today: 判定基準日

    Returns:
        新しいステータス文字列、または None（変更不要）
    """
    article_type = str(row.get("article_type", "")).strip()
    if article_type not in SALE_TYPES:
        return None

    status = str(row.get("status", "")).strip().upper()
    if status in SKIP_STATUSES:
        return None

    end_val = str(row.get("sale_end_date", "")).strip()
    if not end_val:
        return None

    end_date = _parse_date(end_val)
    if end_date is None:
        return None

    if end_date > today:
        return None  # まだアクティブ

    return EXPIRED_STATUS_MAP.get(status)  # マップにない status は None → スキップ


# --- I/O を受け取って処理するメイン関数 ---

def process_rows(
    rows: list[dict[str, Any]],
    today: date,
    *,
    update_fn: Callable[[int, str], None] | None = None,
    error_fn: Callable[[int, str], None] | None = None,
) -> dict[str, Any]:
    """行リストを処理してステータスを更新する。

    Args:
        rows:      fetch_all_rows / load_local_sale_items で得た行リスト
        today:     判定基準日
        update_fn: callable(row_index, new_status) - 実際の更新関数。
                   None の場合は集計のみ（dry-run / fallback 兼用）。
        error_fn:  callable(row_index, error_msg)  - エラーログ追記関数。
                   None の場合はスキップ。

    Returns:
        {
            "updated": list[dict],  # 更新したアイテム
            "skipped": list[str],   # work_id のリスト（変更不要）
            "errors":  list[dict],  # {"work_id": str, "error": str}
        }
    """
    updated: list[dict[str, Any]] = []
    skipped: list[str] = []
    errors: list[dict[str, Any]] = []

    for row in rows:
        work_id = str(row.get("work_id", "unknown"))
        row_index: int | None = row.get("_row_index")

        try:
            new_status = determine_new_status(row, today)
            if new_status is None:
                skipped.append(work_id)
                continue

            if update_fn is not None and row_index is not None:
                update_fn(row_index, new_status)

            updated.append({
                "work_id": work_id,
                "old_status": str(row.get("status", "")).strip(),
                "new_status": new_status,
                "sale_end_date": str(row.get("sale_end_date", "")).strip(),
                "row_index": row_index,
                "source": row.get("_source", "sheets"),
            })

        except Exception as exc:  # noqa: BLE001
            errors.append({"work_id": work_id, "error": str(exc)})
            if error_fn is not None and row_index is not None:
                try:
                    error_fn(row_index, str(exc))
                except Exception:  # noqa: BLE001
                    pass

    return {"updated": updated, "skipped": skipped, "errors": errors}


# --- CLI ---

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="セール終了チェック (Google Sheets 主入力)")
    parser.add_argument("--dry-run", action="store_true", help="チェックのみ。Sheets 更新・Slack 通知を行わない")
    parser.add_argument(
        "--items-dir",
        default=str(ITEMS_DIR),
        help=f"fallback 用 items ディレクトリ (デフォルト: {ITEMS_DIR})",
    )
    args = parser.parse_args(argv)

    logger = _setup_logger(LOG_PATH)
    today = datetime.now(timezone.utc).date()

    logger.info("sale_end_check start | today=%s | dry_run=%s", today, args.dry_run)

    # --- 1. Google Sheets から行を取得（主入力）---
    sheet = None
    rows: list[dict[str, Any]] = []
    sheets_mod = None
    using_fallback = False

    try:
        sheets_mod = importlib.import_module("src.sheets")
        sheet = sheets_mod.get_sheet()
        rows = sheets_mod.fetch_all_rows(sheet)
        logger.info("sheets loaded | rows=%d", len(rows))
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "sheets unavailable (%s) – falling back to data/items/*.json",
            exc,
        )
        using_fallback = True
        rows = load_local_sale_items(Path(args.items_dir))
        logger.info("local fallback loaded | rows=%d", len(rows))

    # --- 2. コールバックを設定（dry_run または fallback 時は None）---
    update_fn: Callable[[int, str], None] | None = None
    error_fn: Callable[[int, str], None] | None = None

    if not args.dry_run and not using_fallback and sheet is not None and sheets_mod is not None:
        _sheet = sheet
        _smod = sheets_mod
        update_fn = lambda ri, st: _smod.update_status(_sheet, ri, st)  # noqa: E731
        error_fn = lambda ri, msg: _smod.append_error_log(_sheet, ri, msg)  # noqa: E731

    # --- 3. 処理実行 ---
    result = process_rows(rows, today, update_fn=update_fn, error_fn=error_fn)

    updated_count = len(result["updated"])
    error_count = len(result["errors"])

    logger.info(
        "result | updated=%d skipped=%d errors=%d fallback=%s",
        updated_count, len(result["skipped"]), error_count, using_fallback,
    )

    for item in result["updated"]:
        logger.warning(
            "sale_ended | work_id=%s old_status=%s new_status=%s end_date=%s",
            item["work_id"], item["old_status"], item["new_status"], item["sale_end_date"],
        )

    for err in result["errors"]:
        logger.error("row_error | work_id=%s error=%s", err["work_id"], err["error"])

    # --- 4. Slack 通知 ---
    if not args.dry_run:
        try:
            notifier = importlib.import_module("src.slack_notifier")
            notifier.notify_sale_ended(result["updated"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("slack notify skipped: %s", exc)
    else:
        logger.info("dry-run: slack notify skipped")

    exit_code = 1 if updated_count > 0 or error_count > 0 else 0
    logger.info("sale_end_check done | exit_code=%d", exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
