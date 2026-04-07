from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from buyer_journey_ai.journey_builder import (
    build_journey,
    build_journey_html,
    insert_journey_block,
)

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ARTICLE_OUTPUT_WITH_LINKS_PATH = DATA_DIR / "article_output_with_links.json"
ARTICLE_OUTPUT_WITH_JOURNEY_PATH = DATA_DIR / "article_output_with_journey.json"


def load_article_output(path: Path) -> dict[str, Any]:
    """article_output_with_links.json を読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"article_output_with_links.json のJSON形式が不正です: {exc}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(
            f"article_output_with_links.json の読み込みに失敗しました: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise ValueError(
            "article_output_with_links.json はオブジェクト形式である必要があります"
        )

    return data


def enrich_article_with_journey(article_output: dict[str, Any]) -> dict[str, Any]:
    """Buyer Journey AI を適用し、journey-box を記事末尾へ追加する。

    price_changed = True の場合は sale_journey_adapter を通じて
    セール向けに journey を最適化する。
    release_changed = True の場合は release_journey_adapter で新刊補正を行う。
    """
    content_html = str(article_output.get("content_html", "")).strip()
    if not content_html:
        raise ValueError("article_output_with_links.json に content_html がありません")

    journey = build_journey(article_output)
    journey_html = build_journey_html(journey)
    enriched_html = insert_journey_block(content_html, journey_html)

    # ---- 連動確認ログ ----
    price_changed = bool(article_output.get("price_changed", False))
    release_changed = bool(article_output.get("release_changed", False))

    print(
        "[journey] sale_journey_adapter_called:",
        bool(journey.get("is_sale_optimized", False)),
    )
    print(
        "[journey] release_journey_adapter_called:",
        bool(journey.get("is_release_optimized", False)),
    )
    print("[journey] journey_mode:", journey.get("journey_mode", "standard"))
    print("[journey] is_sale_optimized:", journey.get("is_sale_optimized", False))
    print("[journey] is_release_optimized:", journey.get("is_release_optimized", False))

    next_articles = journey.get("next_articles", [])
    if isinstance(next_articles, list):
        print("[journey] next_articles_count:", len(next_articles))

    if price_changed:
        print("[journey] price_changed: True")
        print("[journey] discount_rate:", article_output.get("discount_rate"))
        print("[journey] price_diff:", article_output.get("price_diff"))
        print("[journey] sale_journey_title:", journey.get("sale_journey_title", ""))

    if release_changed:
        print("[journey] release_changed: True")
        print("[journey] release_journey_title:", journey.get("release_journey_title", ""))
        print("[journey] current_latest_volume_number:", journey.get("current_latest_volume_number"))
        print("[journey] current_latest_release_date:", journey.get("current_latest_release_date"))
        print("[journey] current_availability_status:", journey.get("current_availability_status"))

    enriched = dict(article_output)
    enriched["journey"] = journey
    enriched["journey_mode"] = journey.get("journey_mode", "standard")
    enriched["journey_stage"] = journey.get("stage", "")
    enriched["journey_cta_text"] = journey.get("cta_text", "")
    enriched["journey_next_articles_summary"] = [
        str(row.get("title", "")).strip()
        for row in journey.get("next_articles", [])
        if isinstance(row, dict) and str(row.get("title", "")).strip()
    ]
    enriched["content_html"] = enriched_html
    return enriched


def save_output(data: dict[str, Any], path: Path) -> None:
    """article_output_with_journey.json を保存する。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(
            f"article_output_with_journey.json 保存に失敗しました: {exc}"
        ) from exc


def run() -> dict[str, Any]:
    """読み込み -> journey付与 -> 保存の一連処理を実行する。"""
    article_output = load_article_output(ARTICLE_OUTPUT_WITH_LINKS_PATH)
    enriched = enrich_article_with_journey(article_output)
    save_output(enriched, ARTICLE_OUTPUT_WITH_JOURNEY_PATH)
    return enriched


def main() -> None:
    """Buyer Journey AI パイプライン実行。"""
    try:
        enriched = run()
        journey = enriched.get("journey", {})
        print(f"保存先: {ARTICLE_OUTPUT_WITH_JOURNEY_PATH}")
        print(f"stage: {journey.get('stage', '')}")
        print(f"journey_mode: {journey.get('journey_mode', '')}")
        print(f"cta_text: {journey.get('cta_text', '')}")
        print(json.dumps(journey.get("next_articles", []), ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"エラー: {exc}")


if __name__ == "__main__":
    main()
