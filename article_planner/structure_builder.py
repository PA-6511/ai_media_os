from __future__ import annotations

# structure_builder.py
# 記事タイプごとの設計図テンプレートを管理する。
# latest_volume は新刊訴求向けのセクション構成に強化している。

from typing import Any


TEMPLATE_MAP: dict[str, dict[str, Any]] = {
    "volume_guide": {
        "title_suffix": "は何巻まで出てる？最新巻・関連情報まとめ",
        "sections": ["結論", "現在の巻数情報", "最新巻情報", "関連記事", "購入リンク"],
        "cta_type": "volume_purchase",
        "internal_link_tokens": ["最新巻", "全巻", "セール"],
    },
    # latest_volume: 新刊訴求向けに強化したセクション構成
    # content_formatter.py は article_type=="latest_volume" のとき
    # release_template_builder.build_latest_volume_article_html() に委譲するため、
    # ここの sections は通常フォールバック時のみ使用される。
    "latest_volume": {
        "title_suffix": "最新巻はいつ？発売日・関連情報まとめ",
        "sections": [
            "結論",
            "最新巻情報",
            "発売日 / 配信日",
            "前巻からの更新ポイント",
            "今すぐ確認する方法",
            "関連記事",
            "購入リンク",
        ],
        "cta_type": "latest_volume_purchase",
        "internal_link_tokens": ["何巻まで", "全巻", "セール"],
    },
    "summary": {
        "title_suffix": "全巻まとめ買いガイド",
        "sections": ["結論", "全巻情報", "まとめ買いメリット", "関連記事", "購入リンク"],
        "cta_type": "fullset_purchase",
        "internal_link_tokens": ["何巻まで", "最新巻", "セール"],
    },
    "sale_article": {
        "title_suffix": "セール情報まとめ",
        "sections": [
            "結論",
            "現在価格",
            "値下げ情報",
            "割引率",
            "今チェックすべき理由",
            "関連記事",
            "購入リンク",
        ],
        "cta_type": "sale_purchase",
        "internal_link_tokens": ["全巻", "最新巻", "何巻まで", "セール"],
    },
    "work_article": {
        "title_suffix": "評価・見どころまとめ",
        "sections": ["作品概要", "あらすじ", "評価ポイント", "関連記事", "購入リンク"],
        "cta_type": "work_detail",
        "internal_link_tokens": ["何巻まで", "最新巻", "セール"],
    },
}

# release 情報として article_plan に引き継ぐフィールド一覧
_RELEASE_PASSTHROUGH_FIELDS: tuple[str, ...] = (
    "release_changed",
    "release_change_reason",
    "previous_latest_volume_number",
    "current_latest_volume_number",
    "previous_latest_release_date",
    "current_latest_release_date",
    "previous_availability_status",
    "current_availability_status",
)

# price 情報として article_plan に引き継ぐフィールド一覧
_PRICE_PASSTHROUGH_FIELDS: tuple[str, ...] = (
    "price_changed",
    "change_reason",
    "previous_price",
    "current_price",
    "price_diff",
    "discount_rate",
    "discount_rate_diff",
    "checked_at",
)


def build_structure(item: dict[str, str]) -> dict[str, Any]:
    """intent_analysis の1件から記事設計図を作成する。

    item に release / price 情報フィールドが含まれている場合は設計図にそのまま引き継ぐ。
    これにより generator.py → content_formatter.py → release_template_builder.py の
    パイプライン全体で release 情報が伝播する。
    """
    article_type = str(item.get("article_type", "work_article"))
    title = str(item.get("title", "")).strip() or "対象作品"
    keyword = str(item.get("keyword", "")).strip()
    work_id = str(item.get("work_id", "")).strip()

    template = TEMPLATE_MAP.get(article_type, TEMPLATE_MAP["work_article"])
    output_title = f"{title}{template['title_suffix']}"
    internal_link_hints = [f"{title} {token}" for token in template["internal_link_tokens"]]

    structure: dict[str, Any] = {
        "work_id": work_id,
        "keyword": keyword,
        "article_type": article_type,
        "title": output_title,
        "sections": list(template["sections"]),
        "cta_type": str(template["cta_type"]),
        "internal_link_hints": internal_link_hints,
    }

    # release 情報を上流から引き継ぐ（存在する場合のみ）
    for field in _RELEASE_PASSTHROUGH_FIELDS:
        if field in item:
            structure[field] = item[field]  # type: ignore[assignment]

    # price 情報を上流から引き継ぐ（存在する場合のみ）
    for field in _PRICE_PASSTHROUGH_FIELDS:
        if field in item:
            structure[field] = item[field]  # type: ignore[assignment]

    return structure
