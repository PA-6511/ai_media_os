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

from core.database.db_utils import get_intent_analysis_path, get_keywords_path

RULES: list[dict[str, str]] = [
    {"token": "何巻まで", "article_type": "volume_guide", "intent": "巻数確認"},
    {"token": "何巻", "article_type": "volume_guide", "intent": "巻数確認"},
    {"token": "最新巻", "article_type": "latest_volume", "intent": "最新巻確認"},
    {"token": "全巻", "article_type": "summary", "intent": "まとめ買い"},
    {"token": "セール", "article_type": "sale_article", "intent": "安く買いたい"},
    {"token": "評価", "article_type": "work_article", "intent": "評判確認"},
]


def load_keywords(path: Path) -> list[dict[str, Any]]:
    """keywords.json を読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON形式が不正です: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"ファイル読み込みに失敗しました: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError("入力JSONは配列形式である必要があります。")
    return data


def classify_keyword(keyword: str) -> tuple[str, str]:
    """キーワードを article_type と intent に分類する。"""
    text = (keyword or "").strip()
    for rule in RULES:
        if rule["token"] in text:
            return rule["article_type"], rule["intent"]
    return "work_article", "情報収集"


def analyze_keywords(data: list[dict[str, Any]]) -> list[dict[str, str]]:
    """作品キーワード配列を展開して解析結果を返す。"""
    results: list[dict[str, str]] = []

    for row in data:
        work_id = str(row.get("work_id", "")).strip()
        title = str(row.get("title", "")).strip()
        keywords = row.get("keywords", [])

        if not isinstance(keywords, list):
            continue

        for kw in keywords:
            keyword = str(kw).strip()
            if not keyword:
                continue
            article_type, intent = classify_keyword(keyword)
            results.append(
                {
                    "work_id": work_id,
                    "title": title,
                    "keyword": keyword,
                    "article_type": article_type,
                    "intent": intent,
                }
            )

    return results


def save_analysis_to_json(data: list[dict[str, str]], path: Path) -> None:
    """解析結果を UTF-8 JSON で保存する。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(f"intent_analysis.json 保存に失敗しました: {exc}") from exc


def run() -> list[dict[str, str]]:
    """keywords.json 読み込み -> 判定 -> intent_analysis.json 保存を行う。"""
    raw = load_keywords(get_keywords_path())
    analyzed = analyze_keywords(raw)
    save_analysis_to_json(analyzed, get_intent_analysis_path())
    return analyzed


if __name__ == "__main__":
    try:
        results = run()
        print(f"保存先: {get_intent_analysis_path()}")
        print(f"解析件数: {len(results)}")
        for item in results[:5]:
            print(json.dumps(item, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"エラー: {exc}")
