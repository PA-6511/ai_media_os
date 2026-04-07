from __future__ import annotations


def build_cta_text(
    stage: str,
    release_changed: bool = False,
    availability_status: str | None = None,
    article_type: str | None = None,
    price_changed: bool = False,
    discount_rate: float | None = None,
    price_diff: float | None = None,
    variant_tone: str | None = None,
) -> str:
    """購買段階に応じたCTA文言を返す。

    優先順位:
        1. price_changed = True → セール向け CTA（variant_tone で文言トーンを調整）
        2. 高割引率（20% 以上） → 割引強調 CTA
        3. price_diff が大きい負値（-100 円以上の値下がり） → 値下がり強調 CTA
        4. release_changed / availability_status / article_type → 新刊向け CTA
        5. stage ベースのデフォルト CTA

    Args:
        stage: 購買段階。
        release_changed: 新刊情報が更新されたか。
        availability_status: 現在の配信状態。
        article_type: 記事種別。
        price_changed: 価格変動が検知されたか。
        discount_rate: 割引率（%）。
        price_diff: 価格差（負値が値下がり）。
        variant_tone: CTA AB テストのトーン識別子。
                      "direct" / "discount" / "compare" のいずれか。
                      指定時は補助文をトーンに合わせて差し替える。
    """
    availability = (availability_status or "").strip().lower()
    kind = (article_type or "").strip().lower()
    _discount_rate = float(discount_rate or 0.0)
    _price_diff = float(price_diff or 0.0)

    # ---- 1. price_changed 優先 ----
    if price_changed:
        # variant_tone がある場合はトーンに合わせた補助文を返す
        if variant_tone == "direct":
            return (
                "値下げが確認できたため、まずは最新価格をストアで確認してください。"
                "価格が戻る前に早めに確認するのがおすすめです。"
            )
        if variant_tone == "discount":
            return (
                "割引率が変化しているため、対象巻や全巻をあわせて確認するのがおすすめです。"
                "セール価格は短期間で変わることがあります。"
            )
        if variant_tone == "compare":
            return (
                "現在価格だけでなく、全巻情報や最新巻もあわせて確認すると判断しやすくなります。"
                "購入前に他の巻の価格状況もあわせて見てください。"
            )
        # variant_tone 未指定の場合は既存ロジック
        sentences: list[str] = [
            "値下げが確認できたため、まずは最新価格をストアで確認してください。",
            "価格が戻る前に対象巻や全巻情報もあわせて確認するのがおすすめです。",
        ]
        if _discount_rate >= 20.0:
            sentences.append(
                "割引率が高いため、購入候補なら早めに確認しておくのがおすすめです。"
            )
        if _price_diff <= -100:
            sentences.append(
                "前回より値下がりしているため、今の価格状況を優先して確認してください。"
            )
        return "".join(sentences)

    # ---- 2. 割引率が高い（price_changed なくても sale_article の場合）----
    if kind == "sale_article" and _discount_rate >= 20.0:
        return (
            "割引率が高いため、購入候補なら早めに確認しておくのがおすすめです。"
            "対象巻や全巻情報もあわせて確認してください。"
        )

    # ---- 3. 値下がり幅が大きい場合 ----
    if kind == "sale_article" and _price_diff <= -100:
        return (
            "前回より値下がりしているため、今の価格状況を優先して確認してください。"
        )

    # ---- 4. latest_volume 向け（新刊） ----
    if kind == "latest_volume":
        if availability == "available":
            base = (
                "最新巻はすぐ読める可能性があるため、ストアで配信状況を確認してください。"
                "続きを今すぐ読みたい方は最新巻ページをチェックしてください。"
            )
        elif availability == "preorder":
            base = (
                "最新巻の予約受付状況を確認してください。"
                "配信開始前に予約できる場合があります。"
            )
        else:
            base = "最新巻の配信状況をストアページで確認してください。"

        if release_changed:
            return "新刊情報が更新されたため、最新情報を優先して確認してください。" + base
        return base

    if release_changed:
        return "新刊情報が更新されたため、最新情報を優先して確認してください。"

    # ---- 5. stage ベースのデフォルト ----
    if stage == "information_gathering":
        return "まずは関連記事から作品情報をチェックしてください。気になる作品は詳細ページで確認できます。"
    if stage == "comparison":
        return "続きや最新巻が気になる方は関連記事も確認してください。全巻まとめやセール情報もあわせて見るのがおすすめです。"
    return "続きが気になる方は今すぐ最新巻を確認してください。セール中なら早めのチェックがおすすめです。"


class CTAOptimizer:
    """既存コード互換ラッパー。"""

    def optimize(self, stage: str, article_type: str, keyword: str) -> dict[str, str]:
        _ = keyword
        return {
            "cta_text": build_cta_text(
                stage,
                release_changed=False,
                availability_status=None,
                article_type=article_type,
            ),
            "cta_subtext": "",
            "button_style": "primary-large",
            "cta_placement": "after_summary",
        }
