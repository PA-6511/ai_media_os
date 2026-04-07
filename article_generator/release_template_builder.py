from __future__ import annotations

# release_template_builder.py
# latest_volume / release_changed 向けの専用 HTML テンプレートを組み立てるモジュール。
# 通常の content_formatter.py から呼び出される。

from html import escape
from typing import Any


# ---------------------------------------------------------------------------
# 内部ユーティリティ
# ---------------------------------------------------------------------------

_AVAILABILITY_LABELS: dict[str, str] = {
    "available": "配信中",
    "preorder": "予約受付中",
    "upcoming": "配信予定",
    "unavailable": "配信終了",
}


def _availability_label(status: str) -> str:
    """availability_status を日本語ラベルに変換する。"""
    return _AVAILABILITY_LABELS.get(str(status).lower(), str(status))


def _vol_str(vol: Any) -> str:
    """巻番号を「〇巻」形式に変換する。None の場合は「最新巻」を返す。"""
    if vol is not None:
        try:
            return f"{int(vol)}巻"
        except (ValueError, TypeError):
            return str(vol)
    return "最新巻"


# ---------------------------------------------------------------------------
# パブリック関数
# ---------------------------------------------------------------------------


def build_release_alert_box(article_data: dict[str, Any]) -> str:
    """新刊速報ボックスの HTML を返す。

    release_changed=True の場合は更新通知を追加する。
    latest_volume 記事の冒頭に挿入する。
    """
    # キーワードから作品名を抽出（末尾の検索トークンを除去）
    keyword = str(article_data.get("keyword", "")).strip()
    _search_tokens = ["最新巻", "何巻まで", "全巻", "セール", "評価", "あらすじ", "発売日"]
    work_name = keyword
    for token in _search_tokens:
        work_name = work_name.replace(token, "").strip()
    if not work_name:
        work_name = str(article_data.get("title", "本作品")).strip()

    current_vol = article_data.get("current_latest_volume_number")
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    availability = str(article_data.get("current_availability_status", "")).strip()
    release_changed = bool(article_data.get("release_changed", False))
    release_change_reason = str(article_data.get("release_change_reason", "")).strip()

    vol_label = _vol_str(current_vol)
    avail_label = _availability_label(availability)
    date_display = escape(release_date) if release_date else "未定"

    # release_changed の場合は更新通知行を追加
    changed_notice = ""
    if release_changed:
        reason_display = escape(release_change_reason) if release_change_reason else "新刊検知"
        changed_notice = (
            f'\n  <p class="release-updated-notice">'
            f"※ 新刊情報が更新されました（{reason_display}）。最新情報を優先して確認してください。"
            f"</p>"
        )

    return (
        '<div class="release-alert-box">\n'
        "  <h2>最新巻速報</h2>\n"
        f"  <p>{escape(work_name)}の最新巻は<strong>{escape(vol_label)}</strong>です。</p>\n"
        f"  <p>発売日 / 配信日: <strong>{date_display}</strong></p>\n"
        f"  <p>現在の配信状態: <strong>{escape(avail_label)}</strong></p>"
        f"{changed_notice}\n"
        "</div>"
    )


def build_release_info_section(article_data: dict[str, Any]) -> str:
    """最新巻情報セクション（h2 + 本文）の HTML を返す。"""
    current_vol = article_data.get("current_latest_volume_number")
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    availability = str(article_data.get("current_availability_status", "")).strip()

    vol_label = _vol_str(current_vol)
    avail_label = _availability_label(availability)
    date_display = escape(release_date) if release_date else "未定"

    lines: list[str] = [
        f"<p>最新刊は<strong>{escape(vol_label)}</strong>です。</p>",
        f"<p>配信日: <strong>{date_display}</strong></p>",
        f"<p>配信状態: <strong>{escape(avail_label)}</strong></p>",
    ]

    if availability == "available":
        lines.append("<p>現在すぐに読むことができます。電子書籍ストアで確認してみてください。</p>")
    elif availability == "preorder":
        lines.append("<p>現在は予約受付中です。配信開始前に予約しておくと安心です。</p>")
    else:
        lines.append("<p>配信状況は電子書籍ストアの最新情報をご確認ください。</p>")

    return "<h2>最新巻情報</h2>" + "".join(lines)


def build_release_date_section(article_data: dict[str, Any]) -> str:
    """発売日 / 配信日セクションの HTML を返す。"""
    release_date = str(article_data.get("current_latest_release_date", "")).strip()
    availability = str(article_data.get("current_availability_status", "")).strip()

    date_display = escape(release_date) if release_date else "未定"
    avail_label = _availability_label(availability)

    return (
        "<h2>発売日 / 配信日</h2>"
        f"<p>発売日 / 配信日は <strong>{date_display}</strong> です。</p>"
        f"<p>現在の配信状態: <strong>{escape(avail_label)}</strong></p>"
        "<p>情報は変わることがありますので、最新状況は電子書籍ストアでご確認ください。</p>"
    )


def build_release_diff_section(article_data: dict[str, Any]) -> str:
    """前巻からの更新ポイントセクションの HTML を返す。

    release_changed=True の場合にのみ挿入される。
    """
    prev_vol = article_data.get("previous_latest_volume_number")
    current_vol = article_data.get("current_latest_volume_number")
    prev_date = str(article_data.get("previous_latest_release_date", "")).strip()
    current_date = str(article_data.get("current_latest_release_date", "")).strip()
    prev_avail = str(article_data.get("previous_availability_status", "")).strip()
    current_avail = str(article_data.get("current_availability_status", "")).strip()

    lines: list[str] = []

    # 巻数の変化
    if prev_vol is not None and current_vol is not None:
        lines.append(
            f"<p>前巻: <strong>{_vol_str(prev_vol)}</strong>"
            f" → 最新巻: <strong>{_vol_str(current_vol)}</strong></p>"
        )

    # 発売日の変化
    if prev_date and current_date:
        lines.append(
            f"<p>前巻発売日: {escape(prev_date)} → 最新発売日: {escape(current_date)}</p>"
        )

    # 配信状態の変化
    if prev_avail and current_avail and prev_avail != current_avail:
        lines.append(
            f"<p>配信状態が変わりました: "
            f"{escape(_availability_label(prev_avail))}"
            f" → <strong>{escape(_availability_label(current_avail))}</strong></p>"
        )

    if not lines:
        lines.append(
            "<p>前巻との変更点は現時点では確認中です。"
            "最新情報はストアページでご確認ください。</p>"
        )

    return "<h2>前巻からの更新ポイント</h2>" + "".join(lines)


def build_how_to_read_section(article_data: dict[str, Any]) -> str:
    """今すぐ確認する方法セクションの HTML を返す。"""
    availability = str(article_data.get("current_availability_status", "")).strip()
    current_vol = article_data.get("current_latest_volume_number")
    vol_label = _vol_str(current_vol)

    if availability == "available":
        body = (
            f"<p>最新の{escape(vol_label)}は現在すぐに読めます。</p>"
            "<p>Kindleや電子書籍ストアで検索すると最新巻のページを確認できます。</p>"
            "<p>お得なセール対象になっていることもあるので、購入前に確認しましょう。</p>"
        )
    elif availability == "preorder":
        body = (
            f"<p>{escape(vol_label)}は現在予約受付中です。</p>"
            "<p>予約購入しておけば配信開始と同時に読めます。</p>"
            "<p>ストアページで予約受付状況を確認してください。</p>"
        )
    else:
        body = (
            "<p>配信状況は随時更新されます。</p>"
            "<p>電子書籍ストアの最新情報をご確認ください。</p>"
        )

    return f"<h2>今すぐ確認する方法</h2>{body}"


def build_latest_volume_article_html(article_data: dict[str, Any]) -> str:
    """latest_volume 用の完全 HTML 本文を組み立てて返す。

    release_changed=True のときは「前巻からの更新ポイント」セクションも追加。
    Internal Link AI / Buyer Journey AI の後段と自然につながる構造にしている。
    """
    title = escape(str(article_data.get("title", "最新巻まとめ")).strip())
    keyword = str(article_data.get("keyword", "")).strip()
    release_changed = bool(article_data.get("release_changed", False))

    parts: list[str] = []

    # ---- <h1> タイトル ----
    parts.append(f"<h1>{title}</h1>")

    # ---- 結論 ----
    parts.append(
        "<h2>結論</h2>"
        f"<p>この記事では「{escape(keyword)}」について、"
        "最新の巻数・発売日・配信状態を整理します。</p>"
        "<p>まず結論から確認していきます。</p>"
    )

    # ---- 新刊速報ボックス（latest_volume なら常に挿入。release_changed=True でさらに強調）----
    parts.append(build_release_alert_box(article_data))

    # ---- 最新巻情報 ----
    parts.append(build_release_info_section(article_data))

    # ---- 発売日 / 配信日 ----
    parts.append(build_release_date_section(article_data))

    # ---- 前巻からの更新ポイント（release_changed=True のみ）----
    if release_changed:
        parts.append(build_release_diff_section(article_data))

    # ---- 今すぐ確認する方法 ----
    parts.append(build_how_to_read_section(article_data))

    # ---- 関連記事（後段の Internal Link AI がリンクを埋め込む想定のプレースホルダ）----
    parts.append(
        "<h2>関連記事</h2>"
        "<p>関連情報として他の記事もあわせて確認できます。</p>"
        "<p>続き・全巻・セール情報も参考になります。</p>"
    )

    # ---- 購入リンク ----
    parts.append(
        "<h2>購入リンク</h2>"
        "<p>気になる巻は電子書籍ストアで確認してください。</p>"
        "<p>お得なセール対象になっている場合もあります。</p>"
    )

    # ---- journey-box は Buyer Journey AI が後段で挿入するため、ここではプレースホルダのみ ----
    # （buyer_journey_ai/journey_builder.py の insert_journey_block が付け足す）

    return "\n".join(parts)
