from __future__ import annotations

# combined_template_builder.py
# 複合シグナル（price_changed AND release_changed）向けの HTML テンプレートを
# 組み立てるモジュール。
# sale_template_builder / release_template_builder の部品を再利用しつつ、
# 複合専用のアラートボックス・情報セクション・CTA を生成する。

from html import escape
from typing import Any

from article_generator.release_template_builder import (
    _availability_label,
    _vol_str,
    build_release_diff_section,
    build_how_to_read_section,
)
from article_generator.sale_template_builder import (
    _format_price,
    _format_discount,
    _to_float,
    _extract_work_name,
    build_discount_section,
)
from article_generator.release_cta_builder import build_release_cta_html
from article_generator.sale_cta_builder import build_sale_cta_html
from article_generator.template_mode_resolver import (
    TEMPLATE_MODE_COMBINED_SALE_RELEASE,
    TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE,
    TEMPLATE_MODE_VOLUME_GUIDE_RELEASE,
    TEMPLATE_MODE_SUMMARY_RELEASE,
)
from article_generator.signal_template_router import detect_signal_mode


# ------------------------------------------------------------------ #
# combined-alert-box
# ------------------------------------------------------------------ #

def build_combined_alert_box(article_data: dict[str, Any]) -> str:
    """価格変動 + 新刊情報の両方を含む複合アラートボックスを返す。

    combined_sale_release / combined_latest_release_price の両モードで使用。

    Args:
        article_data: 記事データ辞書。

    Returns:
        複合アラートボックスの HTML 文字列。
    """
    work_name = escape(_extract_work_name(article_data))

    # --- 新刊系情報 ---
    current_vol = article_data.get("current_latest_volume_number")
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    availability = str(article_data.get("current_availability_status", "")).strip()
    vol_label = escape(_vol_str(current_vol))
    avail_label = escape(_availability_label(availability))
    date_display = escape(release_date) if release_date else "未定"

    # --- 価格系情報 ---
    current_price = escape(_format_price(article_data.get("current_price")))
    previous_price = escape(_format_price(article_data.get("previous_price")))
    discount_rate = escape(_format_discount(article_data.get("discount_rate")))
    price_diff = _to_float(article_data.get("price_diff"))

    if price_diff is None:
        diff_line = "<p>値下げ幅: 不明</p>"
    elif price_diff < 0:
        diff_line = f"<p>値下げ幅: <strong>{int(abs(price_diff)):,}円</strong></p>"
    elif price_diff > 0:
        diff_line = f"<p>価格変動: <strong>+{int(price_diff):,}円</strong></p>"
    else:
        diff_line = "<p>価格変動: なし</p>"

    return (
        '<div class="combined-alert-box">\n'
        "  <h2>最新情報更新</h2>\n"
        f"  <p>{work_name}の新刊情報と価格情報が更新されました。</p>\n"
        "  <p class=\"combined-updated-notice\">※ 新刊情報と価格情報が同時に更新されています。最新情報を優先して確認してください。</p>\n"
        f"  <p>最新巻: <strong>{vol_label}</strong></p>\n"
        f"  <p>発売日 / 配信日: <strong>{date_display}</strong></p>\n"
        f"  <p>配信状態: <strong>{avail_label}</strong></p>\n"
        f"  <p>現在価格: <strong>{current_price}</strong></p>\n"
        f"  <p>前回価格: {previous_price}</p>\n"
        f"  {diff_line}\n"
        f"  <p>割引率: <strong>{discount_rate}</strong></p>\n"
        "</div>"
    )


# ------------------------------------------------------------------ #
# combined 情報セクション
# ------------------------------------------------------------------ #

def build_combined_info_section(article_data: dict[str, Any]) -> str:
    """複合モード向けの本文情報セクション（h2 ブロック群）を返す。

    価格情報セクション + 新刊情報セクションを組み合わせて返す。

    Args:
        article_data: 記事データ辞書。

    Returns:
        複合情報セクションの HTML 文字列。
    """
    parts: list[str] = []

    # ---- 新刊情報 ----
    current_vol = article_data.get("current_latest_volume_number")
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    availability = str(article_data.get("current_availability_status", "")).strip()
    vol_label = escape(_vol_str(current_vol))
    avail_label = escape(_availability_label(availability))
    date_display = escape(release_date) if release_date else "未定"

    parts.append(
        "<h2>最新巻情報</h2>"
        f"<p>最新刊は<strong>{vol_label}</strong>です。</p>"
        f"<p>配信日: <strong>{date_display}</strong></p>"
        f"<p>配信状態: <strong>{avail_label}</strong></p>"
    )

    # ---- 前巻との差分（release_changed がある場合）----
    if bool(article_data.get("release_changed", False)):
        parts.append(build_release_diff_section(article_data))

    # ---- 価格情報 ----
    current_price = escape(_format_price(article_data.get("current_price")))
    previous_price = escape(_format_price(article_data.get("previous_price")))
    price_diff = _to_float(article_data.get("price_diff"))

    price_lines: list[str] = [
        f"<p>前回価格: <strong>{previous_price}</strong></p>",
        f"<p>現在価格: <strong>{current_price}</strong></p>",
    ]
    if price_diff is not None and price_diff < 0:
        price_lines.append(
            f"<p>値下げ幅: <strong>{int(abs(price_diff)):,}円</strong></p>"
        )
    elif price_diff is not None and price_diff > 0:
        price_lines.append(
            f"<p>価格は <strong>{int(price_diff):,}円</strong> 上昇しています。</p>"
        )
    parts.append("<h2>現在価格・値下げ情報</h2>" + "".join(price_lines))

    # ---- 割引率 ----
    parts.append(build_discount_section(article_data))

    return "\n".join(parts)


# ------------------------------------------------------------------ #
# combined CTA セクション
# ------------------------------------------------------------------ #

def build_combined_cta_section(
    article_data: dict[str, Any],
    template_mode: str,
) -> str:
    """複合モード向けの CTA セクション HTML を返す。

    template_mode に応じて文言を切り替える。

    Args:
        article_data: 記事データ辞書。
        template_mode: テンプレモード文字列。

    Returns:
        CTA セクションの HTML 文字列。
    """
    if template_mode == TEMPLATE_MODE_COMBINED_SALE_RELEASE:
        cta_text = (
            "新刊情報と価格情報が同時に更新されています。"
            "まずは最新巻の配信状況と現在価格を確認してください。"
            "値下げが続いている可能性があるため、全巻や関連巻もあわせて確認するのがおすすめです。"
        )
        cls = "cta-box combined-updated sale-release"
    elif template_mode == TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE:
        cta_text = (
            "最新巻情報が更新され、価格面の変化もあるため、今のうちに最新状況を確認してください。"
            "最新巻だけでなく、前巻や全巻情報もあわせて見ると判断しやすくなります。"
        )
        cls = "cta-box combined-updated latest-release-price"
    else:
        # フォールバック: release + sale それぞれの CTA を組み合わせる
        release_html = build_release_cta_html(article_data)
        sale_html = build_sale_cta_html(article_data)
        return release_html + "\n" + sale_html

    return f'<div class="{cls}"><p>{escape(cta_text)}</p></div>'


def build_combined_cta_html(article_data: dict[str, Any]) -> str:
    """signal_mode=combined 用の CTA HTML を返す。

    既存 API 互換のため、内部的には template_mode を推定して
    build_combined_cta_section を呼び出す。
    """
    article_type = str(article_data.get("article_type", "")).strip()
    if article_type == "sale_article":
        mode = TEMPLATE_MODE_COMBINED_SALE_RELEASE
    elif article_type == "latest_volume":
        mode = TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE
    elif article_type == "volume_guide":
        mode = TEMPLATE_MODE_VOLUME_GUIDE_RELEASE
    elif article_type == "summary":
        mode = TEMPLATE_MODE_SUMMARY_RELEASE
    else:
        mode = TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE
    return build_combined_cta_section(article_data, mode)


# ------------------------------------------------------------------ #
# 今すぐ確認する理由セクション
# ------------------------------------------------------------------ #

def build_combined_reason_section(
    article_data: dict[str, Any],
    template_mode: str,
) -> str:
    """複合モード向けの「今すぐ確認する理由」セクションを返す。

    Args:
        article_data: 記事データ辞書。
        template_mode: テンプレモード文字列。

    Returns:
        HTML 文字列。
    """
    price_diff = _to_float(article_data.get("price_diff"))
    discount_rate = _to_float(article_data.get("discount_rate"))
    availability = str(article_data.get("current_availability_status", "")).strip().lower()

    lines: list[str] = ["<h2>今すぐ確認する理由</h2>"]

    if template_mode == TEMPLATE_MODE_COMBINED_SALE_RELEASE:
        lines.append("<p>新刊情報と価格情報が同時に更新されています。セール価格は短期間で変わるため、今のうちに最新価格を確認しておくことをおすすめします。</p>")
        if price_diff is not None and price_diff < 0:
            lines.append(f"<p>前回より<strong>{int(abs(price_diff)):,}円</strong>値下がりしているため、価格が戻る前に確認してください。</p>")
        if discount_rate is not None and discount_rate >= 20.0:
            lines.append("<p>割引率が高いため、購入を検討しているなら今が判断のタイミングです。</p>")

    elif template_mode == TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE:
        lines.append("<p>最新巻情報が更新され、さらに価格の変動もあります。最新巻の配信状況と価格を一緒に確認しておきましょう。</p>")
        if availability == "available":
            lines.append("<p>現在すぐに読める状態です。価格が戻る前に確認してください。</p>")
        elif availability == "preorder":
            lines.append("<p>現在は予約受付中です。価格変動に注意しながら予約を検討してください。</p>")
        if price_diff is not None and price_diff < 0:
            lines.append(f"<p>価格が<strong>{int(abs(price_diff)):,}円</strong>値下がりしているため、このタイミングでの確認がおすすめです。</p>")

    else:
        lines.append("<p>複合的な情報更新が検知されました。最新の配信状況と価格を優先して確認してください。</p>")

    return "".join(lines)


# ------------------------------------------------------------------ #
# combined_sale_release 向けの完全 HTML
# ------------------------------------------------------------------ #

def _build_combined_sale_release_html(article_data: dict[str, Any]) -> str:
    """combined_sale_release モード用の完全 HTML を組み立てる。"""
    title = escape(str(article_data.get("title", "セール・新刊情報まとめ")).strip())
    keyword = escape(str(article_data.get("keyword", "")).strip())

    parts: list[str] = [
        f"<h1>{title}</h1>",
        "<h2>結論</h2>"
        f"<p>この記事では「{keyword}」について、"
        "最新の価格変動と新刊情報を同時にお伝えします。</p>"
        "<p>価格と新刊の両方が更新されているため、まずは複合情報を確認してください。</p>",

        # 複合アラートボックス（価格 + 新刊）
        build_combined_alert_box(article_data),

        # 個別情報セクション
        build_combined_info_section(article_data),

        # 今すぐ確認する理由
        build_combined_reason_section(article_data, TEMPLATE_MODE_COMBINED_SALE_RELEASE),

        # 今すぐ確認する方法（新刊向け）
        build_how_to_read_section(article_data),

        # 購入リンク導線
        '<div class="related-links">'
        "<h2>関連記事</h2>"
        "<p>全巻情報・最新巻情報・巻数ガイド・セール情報もあわせて確認すると購入判断しやすくなります。</p>"
        "</div>",

        "<h2>購入リンク</h2>"
        "<p>最新巻・全巻まとめ・セール対象はストアページで確認してください。</p>",

        # CTA
        build_combined_cta_section(article_data, TEMPLATE_MODE_COMBINED_SALE_RELEASE),
    ]

    return "\n".join(parts)


# ------------------------------------------------------------------ #
# combined_latest_release_price 向けの完全 HTML
# ------------------------------------------------------------------ #

def _build_combined_latest_release_price_html(article_data: dict[str, Any]) -> str:
    """combined_latest_release_price モード用の完全 HTML を組み立てる。"""
    title = escape(str(article_data.get("title", "最新巻・価格情報まとめ")).strip())
    keyword = escape(str(article_data.get("keyword", "")).strip())

    parts: list[str] = [
        f"<h1>{title}</h1>",
        "<h2>結論</h2>"
        f"<p>この記事では「{keyword}」について、"
        "最新巻の配信情報と価格変動を整理します。</p>"
        "<p>最新巻情報と価格変動が同時に検知されたため、あわせて確認することをおすすめします。</p>",

        # 複合アラートボックス
        build_combined_alert_box(article_data),

        # 新刊 + 差分情報
        build_combined_info_section(article_data),

        # 今すぐ確認する理由
        build_combined_reason_section(article_data, TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE),

        # 今すぐ確認する方法
        build_how_to_read_section(article_data),

        # 関連記事導線（全巻 / セール / 巻数ガイド）
        '<div class="related-links">'
        "<h2>関連記事</h2>"
        "<p>全巻情報・セール情報・巻数ガイドもあわせて確認すると、購入範囲の判断がしやすくなります。</p>"
        "</div>",

        "<h2>購入リンク</h2>"
        "<p>最新巻・全巻まとめ・巻数ガイドはストアページで確認してください。</p>",

        # CTA
        build_combined_cta_section(article_data, TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE),
    ]

    return "\n".join(parts)


# ------------------------------------------------------------------ #
# volume_guide_release 向けの完全 HTML
# ------------------------------------------------------------------ #

def _build_volume_guide_release_html(article_data: dict[str, Any]) -> str:
    """volume_guide_release モード用の完全 HTML を組み立てる。"""
    title = escape(str(article_data.get("title", "巻数ガイド")).strip())
    keyword = escape(str(article_data.get("keyword", "")).strip())

    current_vol = article_data.get("current_latest_volume_number")
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    availability = str(article_data.get("current_availability_status", "")).strip()
    vol_label = escape(_vol_str(current_vol))
    avail_label = escape(_availability_label(availability))
    date_display = escape(release_date) if release_date else "未定"

    # 価格情報（price_changed がある場合は表示）
    price_changed = bool(article_data.get("price_changed", False))
    price_section = ""
    if price_changed:
        current_price = escape(_format_price(article_data.get("current_price")))
        price_section = (
            "<h2>価格情報</h2>"
            f"<p>現在価格: <strong>{current_price}</strong></p>"
            "<p>価格変動が検知されました。価格が戻る前に確認してください。</p>"
        )

    parts: list[str] = [
        f"<h1>{title}</h1>",
        "<h2>結論</h2>"
        f"<p>この記事では「{keyword}」について、"
        "最新の巻数情報と配信状況を整理します。</p>",

        # 新刊速報（簡易版）
        '<div class="release-alert-box">'
        "<h2>最新巻速報</h2>"
        f"<p>最新刊は<strong>{vol_label}</strong>です。</p>"
        f"<p>発売日 / 配信日: <strong>{date_display}</strong></p>"
        f"<p>現在の配信状態: <strong>{avail_label}</strong></p>"
        "<p class=\"release-updated-notice\">※ 新刊情報が更新されました。最新情報を優先して確認してください。</p>"
        "</div>",

        # 前巻差分
        build_release_diff_section(article_data),
    ]

    if price_section:
        parts.append(price_section)

    parts.extend([
        "<h2>今すぐ確認する方法</h2>"
        "<p>最新の巻数情報や購入対象はストアページで確認してください。</p>"
        "<p>全巻まとめ買いを検討している方は全巻情報もあわせてご確認ください。</p>",

        '<div class="related-links">'
        "<h2>関連記事</h2>"
        "<p>全巻情報・最新巻情報・セール情報もあわせて確認できます。</p>"
        "</div>",

        "<h2>購入リンク</h2>"
        "<p>気になる巻は電子書籍ストアで確認してください。</p>",

        build_release_cta_html(article_data),
    ])

    return "\n".join(parts)


# ------------------------------------------------------------------ #
# summary_release 向けの完全 HTML
# ------------------------------------------------------------------ #

def _build_summary_release_html(article_data: dict[str, Any]) -> str:
    """summary_release モード用の完全 HTML を組み立てる。"""
    title = escape(str(article_data.get("title", "作品情報まとめ")).strip())
    keyword = escape(str(article_data.get("keyword", "")).strip())

    current_vol = article_data.get("current_latest_volume_number")
    vol_label = escape(_vol_str(current_vol))
    availability = str(article_data.get("current_availability_status", "")).strip()
    avail_label = escape(_availability_label(availability))
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    date_display = escape(release_date) if release_date else "未定"

    parts: list[str] = [
        f"<h1>{title}</h1>",
        "<h2>結論</h2>"
        f"<p>この記事では「{keyword}」について、"
        "最新の巻数・配信情報をあわせて整理します。</p>",

        # 新刊更新通知（インライン簡易版）
        '<div class="release-alert-box">'
        "<h2>最新巻速報</h2>"
        f"<p>最新刊は<strong>{vol_label}</strong>です。</p>"
        f"<p>発売日 / 配信日: <strong>{date_display}</strong></p>"
        f"<p>現在の配信状態: <strong>{avail_label}</strong></p>"
        "<p class=\"release-updated-notice\">※ 新刊情報が更新されました。</p>"
        "</div>",

        "<h2>作品概要</h2>"
        "<p>この作品の基本情報を簡単に整理します。</p>"
        "<p>はじめて読む方にもわかりやすくまとめます。</p>",

        "<h2>最新巻情報</h2>"
        f"<p>現在は{vol_label}まで刊行されています。</p>"
        f"<p>配信状態: <strong>{avail_label}</strong></p>",

        "<h2>関連記事</h2>"
        "<p>続き・全巻・セール情報も参考になります。</p>",

        "<h2>購入リンク</h2>"
        "<p>気になる巻は電子書籍ストアで確認してください。</p>",

        build_release_cta_html(article_data),
    ]

    return "\n".join(parts)


# ------------------------------------------------------------------ #
# メイン公開関数
# ------------------------------------------------------------------ #

def build_combined_article_html(
    article_data: dict[str, Any],
    template_mode: str | None = None,
) -> str:
    """テンプレモードに応じた複合 HTML を組み立てて返す。

    Args:
        article_data: 記事データ辞書。
        template_mode: resolve_template_mode() が返したテンプレモード文字列。
            省略時は article_type と signal_mode から自動判定する。

    Returns:
        本文 HTML 文字列。テンプレモードが非複合の場合は空文字を返す。

    Raises:
        RuntimeError: HTML 組み立てで予期しないエラーが発生した場合。
    """
    try:
        resolved_mode = template_mode
        if not resolved_mode:
            signal_mode = detect_signal_mode(article_data)
            article_type = str(article_data.get("article_type", "")).strip()
            if signal_mode == "combined":
                if article_type == "sale_article":
                    resolved_mode = TEMPLATE_MODE_COMBINED_SALE_RELEASE
                elif article_type == "latest_volume":
                    resolved_mode = TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE
                elif article_type == "volume_guide":
                    resolved_mode = TEMPLATE_MODE_VOLUME_GUIDE_RELEASE
                elif article_type == "summary":
                    resolved_mode = TEMPLATE_MODE_SUMMARY_RELEASE
                else:
                    resolved_mode = TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE
            elif signal_mode == "release_only":
                if article_type == "volume_guide":
                    resolved_mode = TEMPLATE_MODE_VOLUME_GUIDE_RELEASE
                elif article_type == "summary":
                    resolved_mode = TEMPLATE_MODE_SUMMARY_RELEASE
                else:
                    resolved_mode = ""
            else:
                resolved_mode = ""

        if resolved_mode == TEMPLATE_MODE_COMBINED_SALE_RELEASE:
            return _build_combined_sale_release_html(article_data)
        if resolved_mode == TEMPLATE_MODE_COMBINED_LATEST_RELEASE_PRICE:
            return _build_combined_latest_release_price_html(article_data)
        if resolved_mode == TEMPLATE_MODE_VOLUME_GUIDE_RELEASE:
            return _build_volume_guide_release_html(article_data)
        if resolved_mode == TEMPLATE_MODE_SUMMARY_RELEASE:
            return _build_summary_release_html(article_data)
        # 非複合モードは空文字（content_formatter 側で処理）
        return ""
    except Exception as exc:
        raise RuntimeError(
            f"combined_template_builder で HTML 組み立てに失敗しました "
            f"(template_mode={resolved_mode}): {exc}"
        ) from exc
