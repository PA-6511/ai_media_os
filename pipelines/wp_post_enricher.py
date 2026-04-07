from __future__ import annotations

import re
from typing import Any


CATEGORY_MAP: dict[str, str] = {
    "volume_guide": "巻数ガイド",
    "latest_volume": "最新巻",
    "summary": "全巻まとめ",
    "sale_article": "セール情報",
    "work_article": "作品紹介",
}

ARTICLE_TYPE_TAG_MAP: dict[str, str] = {
    "volume_guide": "巻数ガイド",
    "latest_volume": "最新巻",
    "summary": "全巻",
    "sale_article": "セール",
    "work_article": "作品紹介",
}

ARTICLE_TYPE_SLUG_MAP: dict[str, str] = {
    "volume_guide": "volume-guide",
    "latest_volume": "latest-volume",
    "summary": "summary",
    "sale_article": "sale-article",
    "work_article": "work-article",
}


def extract_work_title(article_output: dict[str, Any]) -> str:
    """記事データから作品名に近い文字列を抽出する。"""
    keyword = str(article_output.get("keyword", "")).strip()
    if keyword:
        # 例: "呪術廻戦 何巻まで" -> "呪術廻戦"
        first = keyword.split()[0].strip()
        if first:
            return first

    title = str(article_output.get("title", "")).strip()
    if title:
        # 例: "呪術廻戦は何巻まで..." -> "呪術廻戦"
        parts = re.split(r"は|って|とは|\s", title, maxsplit=1)
        candidate = parts[0].strip() if parts else ""
        if candidate:
            return candidate

    # 最後のフォールバック
    return str(article_output.get("work_id", "作品")).strip() or "作品"


def map_category_names(article_type: str) -> list[str]:
    """article_type からカテゴリ名配列を返す。"""
    normalized = (article_type or "").strip()
    category = CATEGORY_MAP.get(normalized, "作品紹介")
    return [category]


def _normalize_hint_tag(hint: str, work_title: str) -> str:
    """internal_link_hints から補助タグを抽出しやすい形に整える。"""
    text = hint.strip()
    if not text:
        return ""

    # 作品名を先頭から除去し、汎用タグ化する。
    if work_title and text.startswith(work_title):
        text = text[len(work_title) :].strip()

    text = text.replace("　", " ").strip()
    return text


def build_tag_names(article_output: dict[str, Any]) -> list[str]:
    """タイトル・article_type・internal_link_hints からタグ名配列を生成する。"""
    work_title = extract_work_title(article_output)
    article_type = str(article_output.get("article_type", "")).strip()

    raw_tags: list[str] = []

    # 1) 作品タグ
    raw_tags.append(work_title)

    # 2) article_type タグ
    raw_tags.append(ARTICLE_TYPE_TAG_MAP.get(article_type, "作品紹介"))

    # 3) internal_link_hints から補助タグ
    hints = article_output.get("internal_link_hints", [])
    if isinstance(hints, list):
        for hint in hints:
            normalized = _normalize_hint_tag(str(hint), work_title)
            if normalized:
                raw_tags.append(normalized)

    # 重複と空を除去し、最大5件程度に制限
    deduped: list[str] = []
    seen: set[str] = set()
    for tag in raw_tags:
        text = tag.strip()
        if not text:
            continue
        if text in seen:
            continue
        seen.add(text)
        deduped.append(text)
        if len(deduped) >= 5:
            break

    return deduped


def build_slug(article_output: dict[str, Any]) -> str:
    """work_id と article_type を基に安全な slug を生成する。"""
    work_id = str(article_output.get("work_id", "work")).strip().lower()
    article_type = str(article_output.get("article_type", "work_article")).strip()

    slug_type = ARTICLE_TYPE_SLUG_MAP.get(article_type, "work-article")

    # 英数字・アンダースコア・ハイフンのみ残す（最小安全化）
    safe_work_id = re.sub(r"[^a-z0-9_-]", "-", work_id)
    safe_work_id = re.sub(r"-{2,}", "-", safe_work_id).strip("-") or "work"

    return f"{safe_work_id}-{slug_type}"


def enrich_wp_post(article_output: dict[str, Any]) -> dict[str, Any]:
    """article_output から WordPress 投稿用の拡張データを構築する。"""
    title = str(article_output.get("title", "")).strip()
    content_html = str(article_output.get("content_html", "")).strip()

    if not title:
        raise ValueError("article_output に title がありません")
    if not content_html:
        raise ValueError("article_output に content_html がありません")

    article_type = str(article_output.get("article_type", "work_article")).strip()

    return {
        "title": title,
        "content": content_html,
        "slug": build_slug(article_output),
        "category_names": map_category_names(article_type),
        "tag_names": build_tag_names(article_output),
        # ログ・将来拡張の補助フィールド
        "work_id": str(article_output.get("work_id", "")).strip(),
        "keyword": str(article_output.get("keyword", "")).strip(),
        "article_type": article_type,
        "content_html": content_html,
    }
