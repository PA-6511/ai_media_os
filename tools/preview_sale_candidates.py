"""preview_sale_candidates.py

DRY_RUN 専用。候補 JSON を読み込み、バリデーション・期限切れ・重複の
判定結果を標準出力に表示するだけで、Sheets への書き込みや draft 生成は
一切行わない。

使い方:
    python3 tools/preview_sale_candidates.py
    python3 tools/preview_sale_candidates.py --input samples/auto_collection/sale_candidates.sample.json
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

ALLOWED_STORES = {"rakuten_kobo", "dmm_books", "kindle_amazon"}
ALLOWED_ENTRY_REQUIRED = {"required", "optional", "none"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

DEFAULT_INPUT = Path(__file__).parent.parent / "samples" / "auto_collection" / "sale_candidates.sample.json"


# ---------------------------------------------------------------------------
# candidate_id 生成（設計書仕様: sha1 先頭12桁）
# ---------------------------------------------------------------------------

def compute_candidate_id(c: dict) -> str:
    key = "".join([
        c.get("source_store", ""),
        c.get("work_title", ""),
        c.get("campaign_name", ""),
        c.get("sale_end_date", ""),
    ])
    return hashlib.sha1(key.encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# バリデーション
# ---------------------------------------------------------------------------

def _has_cta_url(c: dict) -> bool:
    return any(c.get(f) for f in ("rakuten_url", "dmm_url", "amazon_url", "official_url"))


def validate(c: dict) -> list[str]:
    """バリデーションエラーの文字列リストを返す。空なら OK。"""
    errors: list[str] = []
    if c.get("source_store") not in ALLOWED_STORES:
        errors.append(f"source_store 不正: {c.get('source_store')!r}")
    if not c.get("work_title", "").strip():
        errors.append("work_title が空")
    if not c.get("campaign_name", "").strip():
        errors.append("campaign_name が空")
    if not DATE_RE.match(c.get("sale_end_date", "")):
        errors.append(f"sale_end_date の形式不正: {c.get('sale_end_date')!r}")
    if c.get("entry_required") not in ALLOWED_ENTRY_REQUIRED:
        errors.append(f"entry_required 不正: {c.get('entry_required')!r}")
    if not _has_cta_url(c):
        errors.append("CTA候補URLが1件もない")
    return errors


# ---------------------------------------------------------------------------
# 期限切れ判定
# ---------------------------------------------------------------------------

def is_expired(c: dict, today: date) -> bool:
    try:
        end = datetime.strptime(c["sale_end_date"], "%Y-%m-%d").date()
        return end < today
    except (KeyError, ValueError):
        # バリデーション側でエラー扱いになるため expired 扱いはしない
        return False


# ---------------------------------------------------------------------------
# メイン処理
# ---------------------------------------------------------------------------

def preview(input_path: Path) -> int:
    """
    Returns:
        0: 正常終了（would_enqueue >= 0）
        1: 入力ファイルが見つからない、または JSON 構文エラー
    """
    if not input_path.exists():
        print(f"[ERROR] 入力ファイルが見つかりません: {input_path}", file=sys.stderr)
        return 1

    try:
        candidates: list[dict] = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[ERROR] JSON パースエラー: {exc}", file=sys.stderr)
        return 1

    if not isinstance(candidates, list):
        print("[ERROR] JSON のトップレベルがリストではありません", file=sys.stderr)
        return 1

    today = datetime.now(tz=timezone.utc).date()

    # 統計
    total = len(candidates)
    seen_ids: set[str] = set()
    results = {
        "valid": [],
        "skip_expired": [],
        "skip_duplicate": [],
        "skip_validation_error": [],
    }

    for idx, c in enumerate(candidates):
        cid = c.get("candidate_id") or compute_candidate_id(c)
        label = f"[{idx+1}] {c.get('work_title', '(無題)')!r} ({c.get('source_store', '?')})"

        # ---- バリデーション
        errors = validate(c)
        if errors:
            results["skip_validation_error"].append({
                "candidate_id": cid,
                "label": label,
                "errors": errors,
            })
            continue

        # ---- 期限切れ
        if is_expired(c, today):
            results["skip_expired"].append({
                "candidate_id": cid,
                "label": label,
                "sale_end_date": c["sale_end_date"],
            })
            continue

        # ---- 重複
        if cid in seen_ids:
            results["skip_duplicate"].append({
                "candidate_id": cid,
                "label": label,
            })
            continue

        seen_ids.add(cid)
        results["valid"].append({
            "candidate_id": cid,
            "label": label,
            "source_store": c.get("source_store"),
            "campaign_name": c.get("campaign_name"),
            "sale_end_date": c.get("sale_end_date"),
            "review_status": c.get("review_status", "pending"),
        })

    # ---------------------------------------------------------------------------
    # 出力
    # ---------------------------------------------------------------------------
    print("=" * 60)
    print("  SALE CANDIDATE PREVIEW  [DRY_RUN — Sheets 書き込みなし]")
    print("=" * 60)
    print(f"  実行日時      : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"  入力ファイル  : {input_path}")
    print(f"  基準日        : {today}")
    print()
    print(f"  total_candidates       : {total}")
    print(f"  valid_candidates       : {len(results['valid'])}")
    print(f"  skipped_expired        : {len(results['skip_expired'])}")
    print(f"  skipped_duplicate      : {len(results['skip_duplicate'])}")
    print(f"  skipped_validation_err : {len(results['skip_validation_error'])}")
    print(f"  would_enqueue          : {len(results['valid'])}  ← Sheets 未書き込み")
    print()

    if results["valid"]:
        print("─" * 60)
        print("  [投入予定] (review_status に関わらず表示)")
        print("─" * 60)
        for r in results["valid"]:
            print(f"  + {r['candidate_id']}  {r['label']}")
            print(f"      campaign : {r['campaign_name']}")
            print(f"      end_date : {r['sale_end_date']}")
            print(f"      status   : {r['review_status']}")
        print()

    if results["skip_expired"]:
        print("─" * 60)
        print("  [SKIP: 期限切れ]")
        print("─" * 60)
        for r in results["skip_expired"]:
            print(f"  - {r['candidate_id']}  {r['label']}")
            print(f"      sale_end_date: {r['sale_end_date']}  < today {today}")
        print()

    if results["skip_duplicate"]:
        print("─" * 60)
        print("  [SKIP: 重複]")
        print("─" * 60)
        for r in results["skip_duplicate"]:
            print(f"  - {r['candidate_id']}  {r['label']}")
        print()

    if results["skip_validation_error"]:
        print("─" * 60)
        print("  [SKIP: バリデーションエラー]")
        print("─" * 60)
        for r in results["skip_validation_error"]:
            print(f"  - {r['candidate_id']}  {r['label']}")
            for e in r["errors"]:
                print(f"      ! {e}")
        print()

    print("=" * 60)
    print("  [DRY_RUN 完了] Sheets・WordPress への書き込みは行っていません")
    print("=" * 60)
    return 0


# ---------------------------------------------------------------------------
# CLI エントリポイント
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="セール候補JSON をプレビュー（DRY_RUN専用）"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"候補JSONファイルのパス（デフォルト: {DEFAULT_INPUT}）",
    )
    args = parser.parse_args()
    sys.exit(preview(args.input))


if __name__ == "__main__":
    main()
