from __future__ import annotations

from dataclasses import dataclass


def classify_stage(
    keyword: str,
    article_type: str,
    release_changed: bool = False,
    availability_status: str | None = None,
    price_changed: bool = False,
    discount_rate: float = 0.0,
) -> str:
    """keyword と article_type から購買段階を判定する。

    release_changed が True の場合は新刊シナリオ向けの補正を行う。
    price_changed が True の場合はセールシナリオ向けの補正を行う。
    両方が True の場合は price_changed / セール補正を優先する。

    Args:
        keyword: 検索キーワード。
        article_type: 記事種別。
        release_changed: 新刊情報が更新されたかどうか。
        availability_status: 現在の配信状態。
        price_changed: 価格変動が検知されたかどうか。
        discount_rate: 割引率（%）。
    """
    text = (keyword or "").strip().lower()
    kind = (article_type or "").strip().lower()
    availability = (availability_status or "").strip().lower()

    purchase_tokens = ["何巻まで", "セール", "安い", "買う", "購入", "最安"]
    comparison_tokens = ["全巻", "最新巻", "どこで買う", "比較", "違い"]
    information_tokens = ["おすすめ", "面白い", "評価", "感想", "ランキング"]

    if any(token in text for token in purchase_tokens):
        base_stage = "purchase_ready"
    elif kind in {"volume_guide", "sale_article"}:
        base_stage = "purchase_ready"
    elif any(token in text for token in comparison_tokens):
        base_stage = "comparison"
    elif kind in {"latest_volume", "summary"}:
        base_stage = "comparison"
    elif any(token in text for token in information_tokens):
        base_stage = "information_gathering"
    else:
        base_stage = "information_gathering"

    # ---- price_changed による補正（release_changed より優先） ----
    if price_changed:
        if kind == "sale_article":
            # sale_article + price_changed → 常に purchase_ready
            return "purchase_ready"
        if kind == "sale_article" and (discount_rate or 0.0) >= 20.0:
            # 高割引率の sale_article → purchase_ready を強める
            return "purchase_ready"
        if kind in {"latest_volume", "summary"}:
            # latest_volume / summary + price_changed → comparison 以上
            if base_stage == "information_gathering":
                return "comparison"

    # ---- release_changed による補正 ----
    if release_changed:
        if kind == "latest_volume":
            return "purchase_ready"
        if kind == "volume_guide":
            return "comparison"
        if kind == "summary":
            if availability == "available":
                return "purchase_ready"
            return "comparison"

    return base_stage


@dataclass
class StageResult:
    keyword: str
    article_type: str
    stage: str
    scores: dict[str, int]
    matched_rules: list[str]


class StageClassifier:
    """既存コード互換の薄いラッパー。"""

    def classify(
        self,
        keyword: str,
        article_type: str,
        release_changed: bool = False,
        availability_status: str | None = None,
        price_changed: bool = False,
        discount_rate: float = 0.0,
    ) -> StageResult:
        stage = classify_stage(
            keyword=keyword,
            article_type=article_type,
            release_changed=release_changed,
            availability_status=availability_status,
            price_changed=price_changed,
            discount_rate=discount_rate,
        )
        return StageResult(
            keyword=keyword,
            article_type=article_type,
            stage=stage,
            scores={},
            matched_rules=[],
        )

    def classify_stage(
        self,
        keyword: str,
        article_type: str,
        release_changed: bool = False,
        availability_status: str | None = None,
        price_changed: bool = False,
        discount_rate: float = 0.0,
    ) -> str:
        return classify_stage(
            keyword=keyword,
            article_type=article_type,
            release_changed=release_changed,
            availability_status=availability_status,
            price_changed=price_changed,
            discount_rate=discount_rate,
        )
