from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from internal_link_ai.link_engine import build_related_links
from internal_link_ai.link_inserter import insert_related_links


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
ARTICLE_OUTPUT_PATH = DATA_DIR / "article_output.json"
ARTICLE_OUTPUT_WITH_LINKS_PATH = DATA_DIR / "article_output_with_links.json"


def load_article_output(path: Path) -> dict[str, Any]:
    """article_output.json を読み込む。"""
    if not path.exists():
        raise FileNotFoundError(f"入力ファイルが見つかりません: {path}")

    try:
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"article_output.json のJSON形式が不正です: {exc}") from exc
    except OSError as exc:
        raise RuntimeError(f"article_output.json の読み込みに失敗しました: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("article_output.json はオブジェクト形式である必要があります")

    return data


def enrich_article(article_output: dict[str, Any]) -> dict[str, Any]:
    """Internal Link AI を適用して関連記事リンクを付与する。"""
    content_html = str(article_output.get("content_html", "")).strip()
    if not content_html:
        raise ValueError("article_output に content_html がありません")

    related_links = build_related_links(article_output)
    enriched_html = insert_related_links(content_html, related_links)

    enriched = dict(article_output)
    enriched["related_links"] = related_links
    enriched["content_html"] = enriched_html
    return enriched


def save_enriched_output(data: dict[str, Any], path: Path) -> None:
    """article_output_with_links.json を保存する。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(f"article_output_with_links.json 保存に失敗しました: {exc}") from exc


def run() -> dict[str, Any]:
    """読込 -> 内部リンク付与 -> 保存の一連処理を実行する。"""
    article_output = load_article_output(ARTICLE_OUTPUT_PATH)
    enriched = enrich_article(article_output)
    save_enriched_output(enriched, ARTICLE_OUTPUT_WITH_LINKS_PATH)
    return enriched


def main() -> None:
    """Internal Link AI 最小パイプライン実行。"""
    try:
        enriched = run()
        print(f"保存先: {ARTICLE_OUTPUT_WITH_LINKS_PATH}")
        print(f"関連記事件数: {len(enriched.get('related_links', []))}")
        preview = {
            "title": enriched.get("title", ""),
            "related_links": enriched.get("related_links", []),
            "content_html_preview": str(enriched.get("content_html", ""))[:400],
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"エラー: {exc}")


if __name__ == "__main__":
    main()
