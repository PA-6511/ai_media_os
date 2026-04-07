from __future__ import annotations

import json
from collections import Counter

from pipelines.post_status_store import (
    list_by_status,
    list_failed_items,
    list_skipped_items,
)


def _count_statuses() -> Counter[str]:
    """ステータス別件数を集計する。"""
    statuses = ["draft", "published", "skipped", "failed", "pending", "processing"]
    counter: Counter[str] = Counter()
    for status in statuses:
        counter[status] = len(list_by_status(status))
    return counter


def main() -> None:
    """現在ステータスの簡易レポートを表示する。"""
    counts = _count_statuses()

    print("status 集計:")
    print(f"draft: {counts['draft']}")
    print(f"published: {counts['published']}")
    print(f"skipped: {counts['skipped']}")
    print(f"failed: {counts['failed']}")

    failed_items = list_failed_items()
    print("\nfailed items:")
    if not failed_items:
        print("- なし")
    else:
        for row in failed_items:
            print(f"- {row.get('slug', '')} :: {row.get('error_message', '')}")

    skipped_items = list_skipped_items()
    print("\nskipped items:")
    if not skipped_items:
        print("- なし")
    else:
        for row in skipped_items:
            print(f"- {row.get('slug', '')} :: post_id={row.get('post_id')}")

    # 解析連携しやすいように JSON も末尾に出しておく。
    payload = {
        "counts": dict(counts),
        "failed_items": failed_items,
        "skipped_items": skipped_items,
    }
    print("\njson:")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
