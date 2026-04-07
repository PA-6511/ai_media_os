from __future__ import annotations

# content_formatter.py
# template_mode ごとに適切な builder を呼ぶ分岐ハブ。
# template_mode_resolver でモードを確定し、
# combined / sale / release / standard の各 builder に委譲する。

from typing import Any

from article_generator.template_mode_resolver import (
    resolve_template_mode,
    is_combined_mode,
    TEMPLATE_MODE_SALE_PRICE_CHANGED,
    TEMPLATE_MODE_SALE_STANDARD,
    TEMPLATE_MODE_LATEST_VOLUME_RELEASE,
    TEMPLATE_MODE_LATEST_VOLUME_STANDARD,
    TEMPLATE_MODE_VOLUME_GUIDE_RELEASE,
    TEMPLATE_MODE_SUMMARY_RELEASE,
)
from article_generator.combined_template_builder import build_combined_article_html
from article_generator.signal_template_router import (
    detect_signal_mode,
    select_template_builder,
)
from article_generator.sale_cta_builder import build_sale_cta_html
from article_generator.sale_template_builder import build_sale_article_html
from article_generator.release_template_builder import build_latest_volume_article_html
from article_generator.release_cta_builder import build_release_cta_html
from article_generator.cta_experiment_registry import EXPERIMENT_PRICE_CHANGED_V1
from article_generator.cta_variant_selector import select_variant, get_cta_mode


SECTION_TEXTS: dict[str, list[str]] = {
    "結論": [
        "この記事では「{keyword}」についてわかりやすく整理します。",
        "まず結論から確認していきます。",
    ],
    "現在の巻数情報": [
        "{title} に関する現在の巻数情報を確認していきます。",
        "最新の刊行状況は公式ストアや出版社情報もあわせて確認してください。",
    ],
    "最新巻情報": [
        "最新巻の発売状況や配信状況をチェックしておくと安心です。",
        "続きをすぐ読みたい場合は電子書籍ストアの在庫も確認しましょう。",
    ],
    "関連記事": [
        "関連情報として他の記事もあわせて確認できます。",
        "続き・全巻・セール情報も参考になります。",
    ],
    "購入リンク": [
        "気になる巻は電子書籍ストアで確認してください。",
        "お得なセール対象になっている場合もあります。",
    ],
    "作品概要": [
        "この作品の基本情報を簡単に整理します。",
        "はじめて読む方にもわかりやすくまとめます。",
    ],
    "あらすじ": [
        "ネタバレを避けつつ大まかな魅力を紹介します。",
    ],
    "評価ポイント": [
        "読者に支持されるポイントを整理します。",
    ],
    "セール情報": [
        "現在のセール状況や価格変動を確認しておきましょう。",
    ],
    "対象巻": [
        "どの巻が対象かを事前に確認しておくと買いやすくなります。",
    ],
    "全巻情報": [
        "まとめ買いを考えている方向けに全巻情報を整理します。",
    ],
    "まとめ買いメリット": [
        "一気読みしたい場合は全巻購入のメリットがあります。",
    ],
    "発売日 / 配信日": [
        "最新巻の発売日・配信日情報を確認しておきましょう。",
        "情報は変わることがありますので、最新状況は電子書籍ストアでご確認ください。",
    ],
    "前巻からの更新ポイント": [
        "前巻と比べてどのような変化があったかを整理します。",
        "最新情報はストアページでご確認ください。",
    ],
    "今すぐ確認する方法": [
        "今すぐ読める場合はストアページで確認してください。",
        "予約受付中の場合は事前予約がおすすめです。",
    ],
}


CTA_TEXTS: dict[str, str] = {
    "volume_purchase": "続きが気になる方はKindleで最新巻を確認してください。",
    "latest_volume_purchase": "最新巻を今すぐチェックしたい方はKindleページをご確認ください。",
    "fullset_purchase": "まとめ買いしたい方は全巻セットや各巻リンクを確認してください。",
    "sale_purchase": "セール中に購入したい方は対象ページを確認してください。",
    "work_detail": "作品の詳細を知りたい方はストアページも参考にしてください。",
}


def section_to_html(section: str, title: str, keyword: str) -> str:
    """セクション名を最小テンプレでHTML化する。"""
    lines = SECTION_TEXTS.get(section, ["このセクションでは関連情報を整理します。"])
    body = "".join(f"<p>{line.format(title=title, keyword=keyword)}</p>" for line in lines)
    return f"<h2>{section}</h2>{body}"


def build_cta_html(cta_type: str) -> str:
    """CTAタイプに応じたHTMLブロックを返す。"""
    cta_text = CTA_TEXTS.get(cta_type, "詳しくは電子書籍ストアで確認してください。")
    return f'<div class="cta-box"><p>{cta_text}</p></div>'


def format_article_html(
    article_plan: dict[str, Any],
    extra_context: dict[str, Any] | None = None,
) -> str:
    """article_plan から WordPress 投稿向けHTML本文を作成する。

    template_mode_resolver でモードを決定し、各 builder に委譲する。

    優先順:
        1. 複合シグナル（combined モード） → combined_template_builder
        2. sale_article                      → sale_template_builder
        3. latest_volume                     → release_template_builder
        4. volume_guide / summary + release  → combined_template_builder
        5. 通常                              → セクションベース生成
    """
    # extra_context があれば article_plan にマージしてテンプレ判定へ渡す。
    merged_plan = dict(article_plan)
    if isinstance(extra_context, dict):
        merged_plan.update(extra_context)

    article_type = str(merged_plan.get("article_type", "work_article")).strip()
    title = str(merged_plan.get("title", "無題記事")).strip()
    keyword = str(merged_plan.get("keyword", "")).strip()
    sections = merged_plan.get("sections", [])
    cta_type = str(merged_plan.get("cta_type", "")).strip()
    release_changed = bool(merged_plan.get("release_changed", False))
    price_changed = bool(merged_plan.get("price_changed", False))

    if not isinstance(sections, list):
        sections = []

    # テンプレモードを確定
    template_mode = resolve_template_mode(merged_plan)
    combined = is_combined_mode(template_mode)
    signal_mode = detect_signal_mode(merged_plan)
    selected_builder = select_template_builder(merged_plan)

    # 確認ログ
    print(f"[content_formatter] template_mode: {template_mode}")
    print(f"[content_formatter] signal_mode: {signal_mode}")
    print(f"[content_formatter] selected_builder: {selected_builder}")
    print(f"[content_formatter] is_combined_signal: {price_changed and release_changed}")
    print(f"[content_formatter] price_changed: {price_changed}")
    print(f"[content_formatter] release_changed: {release_changed}")

    # ---- 1. signal_mode 主導の分岐 ----
    if signal_mode == "combined":
        html = build_combined_article_html(merged_plan)
        print("[content_formatter] selected_template_builder: build_combined_article_html")
        print(f"[content_formatter] content_html_head100: {html[:100]!r}")
        return html

    if signal_mode == "price_only" and article_type == "sale_article":
        html = build_sale_article_html(merged_plan)
        sale_cta = build_sale_cta_html(merged_plan)
        html = html + "\n" + sale_cta
        print("[content_formatter] selected_template_builder: build_sale_article_html")
        print(f"[content_formatter] content_html_head100: {html[:100]!r}")
        return html

    if signal_mode == "release_only":
        if article_type == "latest_volume":
            html = build_latest_volume_article_html(merged_plan)
            release_cta = build_release_cta_html(merged_plan)
            normal_cta = build_cta_html(cta_type)
            if normal_cta in html:
                html = html.replace(normal_cta, release_cta, 1)
            else:
                html = html + "\n" + release_cta
            print("[content_formatter] selected_template_builder: build_latest_volume_article_html")
            print(f"[content_formatter] content_html_head100: {html[:100]!r}")
            return html
        if article_type in {"volume_guide", "summary"}:
            html = build_combined_article_html(merged_plan, template_mode)
            print("[content_formatter] selected_template_builder: build_combined_article_html")
            print(f"[content_formatter] content_html_head100: {html[:100]!r}")
            return html

    # ---- 2. 既存 template_mode 分岐（後方互換） ----
    if combined or template_mode in {TEMPLATE_MODE_VOLUME_GUIDE_RELEASE, TEMPLATE_MODE_SUMMARY_RELEASE}:
        html = build_combined_article_html(merged_plan, template_mode)
        print("[content_formatter] selected_template_builder: build_combined_article_html")
        print(f"[content_formatter] content_html_head100: {html[:100]!r}")
        return html

    # ---- 2. sale_article 専用テンプレート ----
    if template_mode in {TEMPLATE_MODE_SALE_PRICE_CHANGED, TEMPLATE_MODE_SALE_STANDARD}:
        html = build_sale_article_html(merged_plan)
        sale_cta = build_sale_cta_html(merged_plan)
        html = html + "\n" + sale_cta
        # AB テスト駆動時は実験情報をログ出力
        if get_cta_mode(merged_plan) == "ab_test":
            variant = select_variant(EXPERIMENT_PRICE_CHANGED_V1, merged_plan)
            variant_name = variant.get("name", "") if variant else ""
            print(f"[content_formatter] cta_experiment: {EXPERIMENT_PRICE_CHANGED_V1}")
            print(f"[content_formatter] cta_variant: {variant_name}")
            print(f"[content_formatter] cta_mode: ab_test")
        print("[content_formatter] selected_template_builder: build_sale_article_html")
        print(f"[content_formatter] content_html_head100: {html[:100]!r}")
        return html

    # ---- 3. latest_volume 専用テンプレート ----
    if template_mode in {TEMPLATE_MODE_LATEST_VOLUME_RELEASE, TEMPLATE_MODE_LATEST_VOLUME_STANDARD}:
        html = build_latest_volume_article_html(merged_plan)
        release_cta = build_release_cta_html(merged_plan)
        normal_cta = build_cta_html(cta_type)
        if normal_cta in html:
            html = html.replace(normal_cta, release_cta, 1)
        else:
            html = html + "\n" + release_cta
        print("[content_formatter] selected_template_builder: build_latest_volume_article_html")
        print(f"[content_formatter] content_html_head100: {html[:100]!r}")
        return html

    # ---- 4. 通常記事テンプレート（standard）----
    html_parts: list[str] = [f"<h1>{title}</h1>"]
    for section in sections:
        html_parts.append(section_to_html(str(section), title=title, keyword=keyword))
    html_parts.append(build_cta_html(cta_type))
    html = "".join(html_parts)
    print("[content_formatter] selected_template_builder: build_default_article_html")
    print(f"[content_formatter] content_html_head100: {html[:100]!r}")
    return html
