from __future__ import annotations

# sale_next_step_builder.py
# セール記事向けの「次のステップ」導線を定義するユーティリティ。
# sale_journey_adapter と連携して使用する。
# 「価格確認型」「比較購入型」の 2 パターンの導線テンプレートを提供する。

from typing import Any


# ------------------------------------------------------------------ #
# 導線パターン定義
# ------------------------------------------------------------------ #

# 価格確認型の導線
# セール記事を見る → 現在価格を確認 → 全巻 / 最新巻 / 対象巻を確認 → 購入
PRICE_CHECK_FLOW: list[dict[str, str]] = [
    {"step": "price_check", "label": "現在価格を確認する"},
    {"step": "all_volumes", "label": "全巻・対象巻をまとめて確認"},
    {"step": "latest_volume", "label": "最新巻ページを確認"},
    {"step": "purchase", "label": "ストアで購入"},
]

# 比較購入型の導線
# セール記事を見る → 値下げ幅を確認 → 全巻まとめ / 最新巻 / 巻数ガイドを見る → 購入
COMPARE_PURCHASE_FLOW: list[dict[str, str]] = [
    {"step": "discount_check", "label": "値下げ幅を確認する"},
    {"step": "all_volumes", "label": "全巻まとめ買い情報を見る"},
    {"step": "volume_guide", "label": "巻数ガイドで購入範囲を確認"},
    {"step": "latest_volume", "label": "最新巻を確認する"},
    {"step": "purchase", "label": "ストアで購入"},
]


# ------------------------------------------------------------------ #
# 導線テンプレート選択
# ------------------------------------------------------------------ #

def select_sale_flow(
    article_output: dict[str, Any],
) -> list[dict[str, str]]:
    """記事データに基づいてセール導線テンプレートを選択する。

    price_diff が大きい（-100 円以上の値下がり）場合は比較購入型、
    それ以外は価格確認型を返す。

    Args:
        article_output: 記事データ辞書。

    Returns:
        導線ステップのリスト。各要素は {"step": str, "label": str} 形式。
    """
    try:
        price_diff = float(article_output.get("price_diff", 0.0) or 0.0)
    except (TypeError, ValueError):
        price_diff = 0.0

    if price_diff <= -100:
        return list(COMPARE_PURCHASE_FLOW)
    return list(PRICE_CHECK_FLOW)


# ------------------------------------------------------------------ #
# next_articles への導線変換
# ------------------------------------------------------------------ #

def build_sale_next_articles(
    article_output: dict[str, Any],
    related_links: list[dict[str, str]],
) -> list[dict[str, str]]:
    """セール導線テンプレートと related_links を組み合わせて next_articles を生成する。

    導線テンプレートの step 順に、related_links から最も近いリンクをマッチングする。
    マッチしなかった step は無視する（空 URL を生成しない）。

    Args:
        article_output: 記事データ辞書。
        related_links: 候補リンクリスト（{"title": str, "url": str} 形式）。

    Returns:
        導線順に並んだ next_articles リスト（最大 4 件）。
    """
    if not isinstance(related_links, list):
        return []

    flow = select_sale_flow(article_output)

    # step ごとのキーワードにリンクをマッチング
    step_keywords: dict[str, list[str]] = {
        "price_check": ["価格", "現在価格", "セール", "割引"],
        "discount_check": ["値下げ", "価格差", "セール", "割引"],
        "all_volumes": ["全巻", "まとめ買い"],
        "latest_volume": ["最新巻", "新刊"],
        "volume_guide": ["巻数", "ガイド", "何巻まで"],
        "work_info": ["作品", "紹介", "評価", "感想"],
        "purchase": ["購入", "ストア", "買う"],
    }

    result: list[dict[str, str]] = []
    used_urls: set[str] = set()

    for step_def in flow:
        step = step_def["step"]
        keywords = step_keywords.get(step, [])

        for link in related_links:
            if not isinstance(link, dict):
                continue
            title = str(link.get("title", "")).strip()
            url = str(link.get("url", "")).strip()
            if not title or not url or url in used_urls:
                continue
            if any(kw in title for kw in keywords):
                result.append({"title": title, "url": url})
                used_urls.add(url)
                break

        if len(result) >= 4:
            break

    return result


# ------------------------------------------------------------------ #
# 導線サマリー生成（確認用）
# ------------------------------------------------------------------ #

def describe_sale_flow(article_output: dict[str, Any]) -> str:
    """選択した導線テンプレートをテキストで説明する（デバッグ / ログ用）。

    Args:
        article_output: 記事データ辞書。

    Returns:
        導線の説明文字列。
    """
    flow = select_sale_flow(article_output)
    steps = " → ".join(step["label"] for step in flow)

    try:
        price_diff = float(article_output.get("price_diff", 0.0) or 0.0)
    except (TypeError, ValueError):
        price_diff = 0.0

    flow_type = "比較購入型" if price_diff <= -100 else "価格確認型"
    return f"[sale_flow: {flow_type}] {steps}"
