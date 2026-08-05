#!/usr/bin/env python3
"""enqueue_sale_candidates.py

47-C: 手動承認付きで sale candidate を最大1件だけ投稿キューへ投入する。

仕様概要:
- preview_sale_candidates.py と同一のバリデーション・期限切れ・重複判定を使う
- review_status=approved の候補のみ対象
- 期限が最も近い候補を1件だけ選び、YES 入力時のみ Sheets に追記する
- --dry-run 時は Sheets へ書き込まない
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

from tools.preview_sale_candidates import (  # reuse 47-B判定ロジック
    DEFAULT_INPUT,
    compute_candidate_id,
    is_expired,
    validate,
)


def _load_candidates(input_path: Path) -> list[dict[str, Any]]:
    if not input_path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")
    try:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON パースエラー: {exc}") from exc

    if not isinstance(payload, list):
        raise ValueError("JSON のトップレベルがリストではありません")

    return payload


def _collect_valid_candidates(candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    today = datetime.now(tz=timezone.utc).date()
    seen_ids: set[str] = set()
    results: dict[str, list[dict[str, Any]]] = {
        "valid": [],
        "skip_expired": [],
        "skip_duplicate": [],
        "skip_validation_error": [],
    }

    for idx, c in enumerate(candidates):
        cid = c.get("candidate_id") or compute_candidate_id(c)
        label = f"[{idx + 1}] {c.get('work_title', '(無題)')!r} ({c.get('source_store', '?')})"

        errors = validate(c)
        if errors:
            results["skip_validation_error"].append(
                {"candidate_id": cid, "label": label, "errors": errors}
            )
            continue

        if is_expired(c, today):
            results["skip_expired"].append(
                {
                    "candidate_id": cid,
                    "label": label,
                    "sale_end_date": c.get("sale_end_date", ""),
                }
            )
            continue

        if cid in seen_ids:
            results["skip_duplicate"].append({"candidate_id": cid, "label": label})
            continue

        seen_ids.add(cid)
        results["valid"].append(
            {
                "candidate_id": cid,
                "index": idx,
                "candidate": c,
                "sale_end_date": c.get("sale_end_date", "9999-12-31"),
                "review_status": str(c.get("review_status", "pending")).strip().lower(),
            }
        )

    stats = {
        "total": len(candidates),
        "valid": len(results["valid"]),
        "skip_expired": len(results["skip_expired"]),
        "skip_duplicate": len(results["skip_duplicate"]),
        "skip_validation_error": len(results["skip_validation_error"]),
    }
    return stats, results


def _select_target(results: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    approved = [r for r in results["valid"] if r.get("review_status") == "approved"]
    if not approved:
        return None

    approved_sorted = sorted(
        approved,
        key=lambda r: (str(r.get("sale_end_date", "9999-12-31")), int(r.get("index", 0))),
    )
    return approved_sorted[0]


def _print_summary(input_path: Path, stats: dict[str, Any], approved_count: int) -> None:
    print("=" * 60)
    print("  SALE CANDIDATE ENQUEUE  [47-C: 最大1件 / 手動承認必須]")
    print("=" * 60)
    print(f"  実行日時      : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  入力ファイル  : {input_path}")
    print()
    print(f"  total_candidates       : {stats['total']}")
    print(f"  valid_candidates       : {stats['valid']}")
    print(f"  approved_candidates    : {approved_count}")
    print(f"  skipped_expired        : {stats['skip_expired']}")
    print(f"  skipped_duplicate      : {stats['skip_duplicate']}")
    print(f"  skipped_validation_err : {stats['skip_validation_error']}")
    print()


def _next_row_id(rows: list[dict[str, Any]]) -> int:
    max_row_id = 0
    for row in rows:
        raw = str(row.get("row_id", "")).strip()
        if raw.isdigit():
            max_row_id = max(max_row_id, int(raw))
    return max_row_id + 1


def _set_if_exists(target: dict[str, Any], headers: list[str], key: str, value: Any) -> None:
    if key in headers:
        target[key] = value


def _build_append_row(candidate: dict[str, Any], row_id: int, headers: list[str]) -> list[Any]:
    now_utc = datetime.now(tz=timezone.utc).replace(microsecond=0).isoformat()
    cid = candidate.get("candidate_id") or compute_candidate_id(candidate)

    values: dict[str, Any] = {}
    _set_if_exists(values, headers, "row_id", row_id)
    _set_if_exists(values, headers, "status", "NEW")
    _set_if_exists(values, headers, "article_type", "sale_article")
    _set_if_exists(values, headers, "store", candidate.get("source_store", ""))
    _set_if_exists(values, headers, "work_title", candidate.get("work_title", ""))
    _set_if_exists(values, headers, "campaign_name", candidate.get("campaign_name", ""))
    _set_if_exists(values, headers, "sale_start_date", candidate.get("sale_start_date", ""))
    _set_if_exists(values, headers, "sale_end_date", candidate.get("sale_end_date", ""))
    _set_if_exists(values, headers, "entry_required", candidate.get("entry_required", ""))
    _set_if_exists(values, headers, "discount_text", candidate.get("discount_text", ""))
    _set_if_exists(values, headers, "point_text", candidate.get("point_text", ""))
    _set_if_exists(values, headers, "rakuten_url", candidate.get("rakuten_url", ""))
    _set_if_exists(values, headers, "dmm_url", candidate.get("dmm_url", ""))
    _set_if_exists(values, headers, "official_url", candidate.get("official_url", ""))
    _set_if_exists(values, headers, "cta_store_priority", candidate.get("cta_store_priority", ""))
    _set_if_exists(values, headers, "created_at", now_utc)
    _set_if_exists(values, headers, "updated_at", now_utc)

    note_parts = [
        f"candidate_id={cid}",
        f"enqueued_at={now_utc}",
    ]
    amazon_url = str(candidate.get("amazon_url", "")).strip()
    if amazon_url:
        note_parts.append(f"amazon_url={amazon_url}")
    _set_if_exists(values, headers, "notes", " | ".join(note_parts))

    return [values.get(header, "") for header in headers]


def _print_target(target: dict[str, Any]) -> None:
    candidate = target["candidate"]
    cid = target["candidate_id"]
    print("=" * 60)
    print("  [投入予定 1件]")
    print(f"  candidate_id : {cid}")
    print(f"  work_title   : {candidate.get('work_title', '')}")
    print(f"  campaign     : {candidate.get('campaign_name', '')}")
    print(f"  store        : {candidate.get('source_store', '')}")
    print(f"  sale_end     : {candidate.get('sale_end_date', '')}")
    print(f"  status       : {candidate.get('review_status', '')}")
    print("=" * 60)


def enqueue(input_path: Path, dry_run: bool) -> int:
    try:
        candidates = _load_candidates(input_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    stats, results = _collect_valid_candidates(candidates)
    approved_count = sum(1 for r in results["valid"] if r.get("review_status") == "approved")
    _print_summary(input_path, stats, approved_count)

    target = _select_target(results)
    if not target:
        print("[INFO] 投入対象の approved 候補がありません。")
        return 0

    _print_target(target)
    if dry_run:
        print("[DRY_RUN] Sheets への書き込みは行いません。")
        return 0

    print("!! Sheets の投稿キューに 1件 NEW として書き込みます。")
    print("!! この操作は取り消せません。")
    answer = input("!! 続行するには YES と入力してください（それ以外でキャンセル）: ").strip()
    if answer != "YES":
        print("[CANCELLED] 書き込みを中止しました。Sheets は変更されていません。")
        return 0

    load_dotenv(BASE_DIR / ".env")
    try:
        from src.sheets import fetch_all_rows, get_sheet

        sheet = get_sheet()
        rows = fetch_all_rows(sheet)
        headers = sheet.row_values(1)

        row_id = _next_row_id(rows)
        append_values = _build_append_row(target["candidate"], row_id, headers)
        sheet.append_row(append_values)

        inserted_row_index = len(rows) + 2
        print(f"[OK] 1件を投稿キューへ追加しました。 row_id={row_id} row_index={inserted_row_index}")
        print(f"[OK] candidate_id={target['candidate_id']}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Sheets 書き込みに失敗しました: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="approved 候補を最大1件だけ NEW で投入")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"候補JSONファイルのパス（デフォルト: {DEFAULT_INPUT}）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="判定のみ実行し、Sheets への書き込みを行わない",
    )
    args = parser.parse_args()
    sys.exit(enqueue(args.input, args.dry_run))


if __name__ == "__main__":
    main()