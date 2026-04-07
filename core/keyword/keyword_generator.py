from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 単独実行時も core パッケージを読み込めるようにルートを追加する。
if __name__ == "__main__":
    import sys

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

from core.database.db_utils import connect_db, get_keywords_path


def load_works_from_db() -> list[dict[str, Any]]:
    """works テーブルから作品一覧を読み込む。"""
    try:
        with connect_db() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT work_id, title, author, type, genre
                FROM works
                ORDER BY id ASC
                """
            )
            return [dict(row) for row in cur.fetchall()]
    except Exception as exc:
        raise RuntimeError(f"works 読み込みに失敗しました: {exc}") from exc


def generate_keywords_for_work(work: dict[str, Any]) -> dict[str, Any]:
    """1作品に対してSEOロングテールキーワードを生成する。"""
    title = str(work.get("title", "")).strip()
    if not title:
        title = "不明作品"

    return {
        "work_id": str(work.get("work_id", "")).strip(),
        "title": title,
        "keywords": [
            f"{title} 何巻まで",
            f"{title} 最新巻",
            f"{title} 全巻",
            f"{title} セール",
            f"{title} 評価",
        ],
    }


def save_keywords_to_json(data: list[dict[str, Any]], path: Path) -> None:
    """生成結果を UTF-8 JSON で保存する。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(f"keywords.json 保存に失敗しました: {exc}") from exc


def run() -> list[dict[str, Any]]:
    """DB読み込み -> キーワード生成 -> JSON保存を実行する。"""
    works = load_works_from_db()
    generated = [generate_keywords_for_work(work) for work in works]
    save_keywords_to_json(generated, get_keywords_path())
    return generated


if __name__ == "__main__":
    try:
        result = run()
        print(f"保存先: {get_keywords_path()}")
        print(f"生成件数: {len(result)}")
        if result:
            print(json.dumps(result[0], ensure_ascii=False, indent=2))
        else:
            print("worksテーブルにデータがありません。")
    except Exception as exc:
        print(f"エラー: {exc}")
