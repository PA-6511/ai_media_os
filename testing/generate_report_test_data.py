from __future__ import annotations

# testing/generate_report_test_data.py
# レポート生成テスト用のダミーデータを生成する。

import json
from datetime import datetime, timedelta
from pathlib import Path


def generate_post_status_tracking(target_date: datetime) -> Path:
    """post_status_tracking ファイルを生成する。"""
    db_dir = Path(__file__).resolve().parents[1] / "data"
    db_dir.mkdir(parents=True, exist_ok=True)

    file_path = db_dir / "post_status_tracking"

    # JSON Lines 形式でデータを生成
    records = []

    # 成功を15、スキップを3、失敗を2、draft を2 件生成
    for i in range(15):
        records.append(
            {
                "slug": f"manga_{i:04d}-sale-article",
                "status": "success",
                "checked_at": (target_date + timedelta(hours=i % 24)).isoformat(),
                "signal_type": ("combined" if i % 3 == 0 else "price_only"),
            }
        )

    for i in range(3):
        records.append(
            {
                "slug": f"skip_{i:04d}-sale-article",
                "status": "skipped",
                "checked_at": (target_date + timedelta(hours=12 + i)).isoformat(),
                "signal_type": "release_only",
            }
        )

    for i in range(2):
        records.append(
            {
                "slug": f"fail_{i:04d}-sale-article",
                "status": "failed",
                "checked_at": (target_date + timedelta(hours=15 + i)).isoformat(),
                "signal_type": "price_only",
            }
        )

    for i in range(2):
        records.append(
            {
                "slug": f"draft_{i:04d}-sale-article",
                "status": "draft",
                "checked_at": (target_date + timedelta(hours=18 + i)).isoformat(),
                "signal_type": "combined",
            }
        )

    # JSON Lines で保存
    with file_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return file_path


def generate_retry_queue_store(target_date: datetime) -> Path:
    """retry_queue_store ファイルを生成する。"""
    db_dir = Path(__file__).resolve().parents[1] / "data"
    file_path = db_dir / "retry_queue_store"

    # JSON Lines 形式でリトライキューを生成 (5件)
    records = []
    for i in range(5):
        records.append(
            {
                "slug": f"retry_{i:04d}-sale-article",
                "queued_at": (target_date + timedelta(hours=20 + i)).isoformat(),
                "attempt_count": i + 1,
            }
        )

    with file_path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return file_path


def main() -> None:
    """テストデータを生成する。"""
    # テスト対象日 (前日)
    target_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    print()
    print("=" * 70)
    print("レポート生成テスト用ダミーデータ生成")
    print("=" * 70)
    print()

    # post_status_tracking を生成
    status_file = generate_post_status_tracking(target_date)
    print(f"✓ post_status_tracking 生成: {status_file}")

    # retry_queue_store を生成
    retry_file = generate_retry_queue_store(target_date)
    print(f"✓ retry_queue_store 生成: {retry_file}")

    print()
    print("テストデータ生成完了")
    print()


if __name__ == "__main__":
    main()
