from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from article_planner.structure_builder import build_structure
from article_planner.type_detector import normalize_article_type


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
INTENT_ANALYSIS_PATH = DATA_DIR / "intent_analysis.json"
ARTICLE_PLAN_PATH = DATA_DIR / "article_plan.json"


def load_intent_analysis(path: Path) -> list[dict[str, Any]]:
    """intent_analysis.json を読み込んで配列として返す。"""
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
        raise ValueError("intent_analysis.json は配列形式である必要があります")

    return data


def generate_plan(item: dict[str, Any]) -> dict[str, Any]:
    """intent_analysis の1件から記事設計図を作成する。"""
    normalized = dict(item)
    normalized["article_type"] = normalize_article_type(str(item.get("article_type", "")))
    return build_structure(normalized)


def run() -> dict[str, Any]:
    """先頭1件を対象に記事設計図を生成し、article_plan.json に保存する。"""
    data = load_intent_analysis(INTENT_ANALYSIS_PATH)
    if not data:
        raise ValueError("intent_analysis.json にデータがありません")

    plan = generate_plan(data[0])

    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with ARTICLE_PLAN_PATH.open("w", encoding="utf-8") as fp:
            json.dump(plan, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(f"article_plan.json 保存に失敗しました: {exc}") from exc

    return plan


def main() -> None:
    """Article Planner 最小実行。"""
    try:
        plan = run()
        print(f"保存先: {ARTICLE_PLAN_PATH}")
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"エラー: {exc}")


if __name__ == "__main__":
    main()
