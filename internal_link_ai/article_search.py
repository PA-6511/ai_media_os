from __future__ import annotations

import os
import re
from typing import Any

import requests


def normalize_hint_to_fallback_url(hint: str) -> str:
    """internal_link_hint を仮URLへ正規化する。"""
    text = (hint or "").strip()
    if not text:
        return "/related/unknown"

    # 全角空白を吸収し、空白をハイフンに寄せる。
    text = text.replace("　", " ")
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return f"/related/{text or 'unknown'}"


def search_posts_by_hint(hint: str, per_page: int = 5, timeout_sec: int = 10) -> list[dict[str, Any]]:
    """WordPress REST API で hint に一致する投稿候補を検索する。"""
    keyword = (hint or "").strip()
    if not keyword:
        return []

    base_url = os.getenv("WP_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        return []

    username = os.getenv("WP_USERNAME", "").strip()
    app_password = os.getenv("WP_APP_PASSWORD", "").strip()
    auth = (username, app_password) if username and app_password else None

    url = f"{base_url}/wp-json/wp/v2/posts"
    params = {
        "search": keyword,
        "per_page": per_page,
        "status": "publish",
        "_fields": "id,link,title",
    }

    try:
        response = requests.get(url, params=params, auth=auth, timeout=timeout_sec)
        if response.status_code >= 400:
            return []
        payload = response.json()
    except Exception:
        return []

    if not isinstance(payload, list):
        return []

    normalized: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict):
            continue

        title_rendered = ""
        title_obj = row.get("title")
        if isinstance(title_obj, dict):
            title_rendered = str(title_obj.get("rendered", "")).strip()

        normalized.append(
            {
                "id": row.get("id"),
                "title": title_rendered,
                "link": str(row.get("link", "")).strip(),
            }
        )

    return normalized


def score_candidate(post: dict[str, Any], hint: str) -> int:
    """候補投稿の関連度を簡易スコアリングする。"""
    title = str(post.get("title", "")).strip()
    if not title:
        return 0

    normalized_hint = (hint or "").strip()
    if not normalized_hint:
        return 0

    score = 0

    # 完全一致に近いタイトルを最優先。
    if title == normalized_hint:
        score += 100
    if normalized_hint in title:
        score += 50

    # hint の単語を多く含むほど加点。
    tokens = [tok for tok in re.split(r"\s+", normalized_hint) if tok]
    for token in tokens:
        if token in title:
            score += 10

    return score


def select_best_post(posts: list[dict[str, Any]], hint: str) -> dict[str, Any] | None:
    """検索候補から最適な投稿1件を選択する。"""
    if not posts:
        return None

    scored = sorted(posts, key=lambda row: score_candidate(row, hint), reverse=True)
    top = scored[0]

    if score_candidate(top, hint) <= 0:
        return posts[0]
    return top


def build_link_candidate(hint: str) -> dict[str, str]:
    """1つのヒントから内部リンク候補データを作る（実URL優先）。"""
    title = (hint or "").strip() or "関連記事"

    posts = search_posts_by_hint(title)
    best = select_best_post(posts, title)
    if best and str(best.get("link", "")).strip():
        return {
            "title": title,
            "url": str(best.get("link", "")).strip(),
            "source": "wordpress",
        }

    return {
        "title": title,
        "url": normalize_hint_to_fallback_url(title),
        "source": "fallback",
    }


# 既存参照との互換性維持

def normalize_hint_to_url(hint: str) -> str:
    return normalize_hint_to_fallback_url(hint)


class ArticleSearch:
    """将来のWP検索差し替えを想定した最小互換ラッパー。"""

    def search(self, hints: list[str], per_keyword: int = 3) -> list[dict[str, Any]]:
        _ = per_keyword
        return [build_link_candidate(hint) for hint in hints if str(hint).strip()]
