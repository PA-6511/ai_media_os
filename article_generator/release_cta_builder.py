from __future__ import annotations

# release_cta_builder.py
# 新刊系記事向けの CTA 文言・HTML ブロックを生成するモジュール。
# availability_status / release_changed の組み合わせで文言を切り替える。

from html import escape
from typing import Any


# ---------------------------------------------------------------------------
# CTA テキストマップ（状態 → メッセージ）
# ---------------------------------------------------------------------------

_CTA_TEXT_MAP: dict[str, str] = {
    # 配信中かつ新刊更新あり（最優先）
    "release_changed_available": (
        "新刊情報が更新されました。最新巻を今すぐチェックしたい方はストアページをご確認ください。"
        "すぐに続きを読みたい方は最新巻リンクを確認してください。"
    ),
    # 予約中かつ新刊更新あり
    "release_changed_preorder": (
        "新刊情報が更新されたため、最新情報を優先して確認してください。"
        "最新巻の予約受付状況を確認してください。配信開始前に予約できる場合があります。"
    ),
    # 新刊更新あり（availability 不明）
    "release_changed": (
        "新刊情報が更新されたため、最新情報を優先して確認してください。"
    ),
    # 配信中（通常）
    "available": (
        "最新巻を今すぐチェックしたい方はストアページをご確認ください。"
        "すぐに続きを読みたい方は最新巻リンクを確認してください。"
    ),
    # 予約受付中（通常）
    "preorder": (
        "最新巻の予約受付状況を確認してください。"
        "配信開始前に予約できる場合があります。"
    ),
    # フォールバック
    "default": "最新巻を今すぐチェックしたい方はストアページをご確認ください。",
}


# ---------------------------------------------------------------------------
# パブリック関数
# ---------------------------------------------------------------------------


def build_release_cta_text(article_data: dict[str, Any]) -> str:
    """article_data の状態に応じた CTA 文言（プレーンテキスト）を返す。

    優先順位:
      1. release_changed=True && availability == "available"
      2. release_changed=True && availability == "preorder"
      3. release_changed=True（その他）
      4. availability == "available"
      5. availability == "preorder"
      6. デフォルト
    """
    availability = str(article_data.get("current_availability_status", "")).strip().lower()
    release_changed = bool(article_data.get("release_changed", False))

    if release_changed:
        key = f"release_changed_{availability}"
        if key in _CTA_TEXT_MAP:
            return _CTA_TEXT_MAP[key]
        return _CTA_TEXT_MAP["release_changed"]

    if availability in _CTA_TEXT_MAP:
        return _CTA_TEXT_MAP[availability]

    return _CTA_TEXT_MAP["default"]


def build_release_cta_html(article_data: dict[str, Any]) -> str:
    """article_data の状態に応じた CTA HTML ブロックを返す。

    クラス名:
      - cta-box release-updated  : release_changed=True
      - cta-box available         : 配信中（通常）
      - cta-box preorder          : 予約受付中
      - cta-box                   : その他
    """
    cta_text = build_release_cta_text(article_data)
    availability = str(article_data.get("current_availability_status", "")).strip().lower()
    release_changed = bool(article_data.get("release_changed", False))

    if release_changed:
        extra_class = " release-updated"
    elif availability == "available":
        extra_class = " available"
    elif availability == "preorder":
        extra_class = " preorder"
    else:
        extra_class = ""

    return (
        f'<div class="cta-box{extra_class}">'
        f"<p>{escape(cta_text)}</p>"
        f"</div>"
    )
