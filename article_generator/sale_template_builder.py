from __future__ import annotations

# sale_template_builder.py
# sale_article 向けの本文 HTML テンプレートを組み立てる。

from datetime import datetime
from html import escape
from typing import Any


def _to_float(value: Any) -> float | None:
    """数値を float へ安全に変換する。"""
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_price(value: Any) -> str:
    """価格を円表記に整形する。"""
    number = _to_float(value)
    if number is None:
        return "不明"
    return f"{int(round(number)):,}円"


def _format_discount(value: Any) -> str:
    """割引率を % 表記に整形する。"""
    number = _to_float(value)
    if number is None:
        return "不明"
    return f"{number:.1f}%"


def _extract_work_name(article_data: dict[str, Any]) -> str:
    """keyword / title から作品名を推定する。"""
    keyword = str(article_data.get("keyword", "")).strip()
    title = str(article_data.get("title", "")).strip()

    work = keyword.replace("セール", "").replace("最新巻", "").strip()
    if work:
        return work

    if title:
        return title.replace("セール情報まとめ", "").strip() or title

    return "この作品"


def _build_checked_at_text(article_data: dict[str, Any]) -> str:
    """checked_at を表示向けの文字列へ変換する。"""
    raw = str(article_data.get("checked_at", "")).strip()
    if not raw:
        return "確認時刻は記録されていません"

    try:
        # ISO8601 を想定。Z は +00:00 に寄せる。
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return escape(raw)


def _classify_nav_link(title: str) -> str:
    text = (title or "").strip()
    if "最新巻" in text or "新刊" in text or "\u5dfb" in text:
        return "latest"
    if "全巻" in text or "まとめ買い" in text:
        return "fullset"
    if "セール" in text or "割引" in text:
        return "sale"
    return "other"


def _nav_rank(title: str) -> int:
    category = _classify_nav_link(title)
    ranks = {
        "latest": 300,
        "fullset": 200,
        "sale": 100,
        "other": 0,
    }
    return ranks.get(category, 0)


def _fallback_url_from_title(title: str) -> str:
    text = title.replace("\u3000", " ").strip()
    text = "-".join(x for x in text.split(" ") if x)
    return f"/related/{text or 'sale-related'}"


def _select_sale_navigation_links(article_data: dict[str, Any], max_items: int = 3) -> list[dict[str, str]]:
    """関連記事から sale 記事末尾の導線リンクを抽出する。"""
    ranked: list[tuple[int, dict[str, str]]] = []

    related = article_data.get("related_links", [])
    if isinstance(related, list):
        for row in related:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "")).strip()
            url = str(row.get("url", "")).strip()
            if not title or not url:
                continue
            ranked.append((_nav_rank(title), {"title": title, "url": url}))

    hints = article_data.get("internal_link_hints", [])
    if isinstance(hints, list):
        for hint in hints:
            title = str(hint).strip()
            if not title:
                continue
            ranked.append((_nav_rank(title), {"title": title, "url": _fallback_url_from_title(title)}))

    ranked.sort(key=lambda x: x[0], reverse=True)
    selected: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for _, row in ranked:
        key = (row["title"], row["url"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= max_items:
            break
    return selected


def build_price_alert_box(article_data: dict[str, Any]) -> str:
    """price_changed 記事向けの価格変動強調ボックスを返す。"""
    work_name = _extract_work_name(article_data)
    price_changed = bool(article_data.get("price_changed", False))

    prev_price = _format_price(article_data.get("previous_price"))
    current_price = _format_price(article_data.get("current_price"))
    price_diff = _to_float(article_data.get("price_diff"))
    discount_rate = _format_discount(article_data.get("discount_rate"))
    checked_at = _build_checked_at_text(article_data)

    if price_diff is None:
        diff_line = "<p>値下げ幅: 不明</p>"
    elif price_diff < 0:
        diff_line = f"<p>値下げ幅: <strong>{int(abs(price_diff)):,}円</strong></p>"
    elif price_diff > 0:
        diff_line = f"<p>価格変動: <strong>+{int(price_diff):,}円</strong></p>"
    else:
        diff_line = "<p>価格変動: なし</p>"

    changed_line = (
        "<p class=\"sale-updated-notice\">※ 価格情報が更新されました。最新価格を優先して確認してください。</p>"
        if price_changed
        else ""
    )

    return (
        '<div class="price-alert-box sale-alert-box">\n'
        "  <h2>セール価格更新</h2>\n"
        f"  <p>{escape(work_name)}の価格情報を確認しました。</p>\n"
        f"  <p>前回価格: <strong>{escape(prev_price)}</strong></p>\n"
        f"  <p>現在価格: <strong>{escape(current_price)}</strong></p>\n"
        f"  {diff_line}\n"
        f"  <p>割引率: <strong>{escape(discount_rate)}</strong></p>\n"
        f"  <p>確認時刻: {escape(checked_at)}</p>\n"
        f"  {changed_line}\n"
        "</div>"
    )


def build_sale_alert_box(article_data: dict[str, Any]) -> str:
    """後方互換: 旧関数名。"""
    return build_price_alert_box(article_data)


def build_sale_price_section(article_data: dict[str, Any]) -> str:
    """sale 記事の現在価格セクションを返す。"""
    current_price = _format_price(article_data.get("current_price"))
    previous_price = _format_price(article_data.get("previous_price"))
    checked_at = _build_checked_at_text(article_data)
    return (
        "<h2>現在価格と前回価格</h2>"
        f"<p>前回価格は <strong>{escape(previous_price)}</strong> でした。</p>"
        f"<p>現在価格は <strong>{escape(current_price)}</strong> です。</p>"
        f"<p>最終確認時刻: {escape(checked_at)}</p>"
    )


def build_current_price_section(article_data: dict[str, Any]) -> str:
    """後方互換: 旧関数名。"""
    return build_sale_price_section(article_data)


def build_sale_diff_section(article_data: dict[str, Any]) -> str:
    """sale 記事の値下げ差分セクションを返す。"""
    previous_price = _format_price(article_data.get("previous_price"))
    current_price = _format_price(article_data.get("current_price"))
    price_diff = _to_float(article_data.get("price_diff"))
    changed = bool(article_data.get("price_changed", False))

    lines = [
        f"<p>前回価格: <strong>{escape(previous_price)}</strong></p>",
        f"<p>現在価格: <strong>{escape(current_price)}</strong></p>",
    ]

    if price_diff is None:
        lines.append("<p>値下げ幅は確認中です。</p>")
    elif price_diff < 0:
        lines.append(f"<p>値下げ幅: <strong>{int(abs(price_diff)):,}円</strong></p>")
    elif price_diff > 0:
        lines.append(f"<p>価格は <strong>{int(price_diff):,}円</strong> 上昇しています。</p>")
    else:
        lines.append("<p>価格は前回から変わっていません。</p>")

    if changed:
        lines.append("<p>値下げが確認できたため、価格が戻る前に早めのチェックがおすすめです。</p>")

    return "<h2>値下げ情報</h2>" + "".join(lines)


def build_price_diff_section(article_data: dict[str, Any]) -> str:
    """後方互換: 旧関数名。"""
    return build_sale_diff_section(article_data)


def build_discount_section(article_data: dict[str, Any]) -> str:
    """割引率セクションを返す。"""
    discount_rate = _to_float(article_data.get("discount_rate"))
    discount_rate_diff = _to_float(article_data.get("discount_rate_diff"))

    lines: list[str] = [
        f"<p>現在の割引率: <strong>{escape(_format_discount(discount_rate))}</strong></p>"
    ]

    if discount_rate_diff is not None:
        if discount_rate_diff > 0:
            lines.append(f"<p>前回比で <strong>+{discount_rate_diff:.1f}pt</strong> 変化しています。</p>")
        elif discount_rate_diff < 0:
            lines.append(f"<p>前回比で <strong>{discount_rate_diff:.1f}pt</strong> 変化しています。</p>")
        else:
            lines.append("<p>割引率は前回と同じです。</p>")

    if discount_rate is not None and discount_rate >= 20.0:
        lines.append("<p>割引率が高いため、早めに確認しておくのがおすすめです。</p>")

    return "<h2>割引率</h2>" + "".join(lines)


def build_reason_section(article_data: dict[str, Any]) -> str:
    """今チェックすべき理由セクションを返す。"""
    reason = str(article_data.get("change_reason", "")).strip()
    price_changed = bool(article_data.get("price_changed", False))

    base = [
        "<h2>今チェックすべき理由</h2>",
        "<p>セール価格は短期間で変わることがあるため、いまの価格を確認しておくと安心です。</p>",
    ]

    if price_changed:
        base.append("<p>値下げが確認できたため、価格が変わる前にストアで最新状況を確認してください。</p>")

    if reason == "discount_rate_threshold":
        base.append("<p>割引率が変化したため、最新価格を優先して確認してください。</p>")

    # 買い時判定を明示
    discount_rate = _to_float(article_data.get("discount_rate"))
    price_diff = _to_float(article_data.get("price_diff"))
    if (discount_rate is not None and discount_rate >= 25.0) or (
        price_diff is not None and price_diff <= -150
    ):
        base.append("<p><strong>今が買い時の可能性が高い</strong>ため、在庫・価格の両方を早めに確認してください。</p>")
    elif (discount_rate is not None and discount_rate >= 10.0) or (
        price_diff is not None and price_diff < 0
    ):
        base.append("<p>値下げ傾向が見られるため、購入検討中なら今の価格を確認する価値があります。</p>")
    else:
        base.append("<p>大幅な変動ではない可能性がありますが、購入前に最新価格を再確認してください。</p>")

    return "".join(base)


def build_sale_navigation_section(article_data: dict[str, Any]) -> str:
    """記事下の回遊導線（最新巻 / 全巻 / 関連セール）を返す。"""
    links = _select_sale_navigation_links(article_data, max_items=3)
    if not links:
        return (
            "<h2>次に確認したい情報</h2>"
            "<p>最新巻・全巻・セール情報をあわせて確認すると、購入判断がしやすくなります。</p>"
        )

    items = "".join(
        f'<li><a href="{escape(row["url"])}">{escape(row["title"])}</a></li>'
        for row in links
    )
    return (
        "<h2>次に確認したい情報</h2>"
        "<p>最新巻・全巻・関連セールを順に確認すると、買い逃しを防ぎやすくなります。</p>"
        f"<ul>{items}</ul>"
    )


def build_sale_article_html(article_data: dict[str, Any]) -> str:
    """sale_article 用の完全 HTML 本文を組み立てる。"""
    try:
        title = escape(str(article_data.get("title", "セール情報まとめ")).strip())
        keyword = escape(str(article_data.get("keyword", "")).strip())

        parts: list[str] = [
            f"<h1>{title}</h1>",
            "<h2>結論</h2>"
            f"<p>この記事では「{keyword}」の最新セール価格と値下げ状況を整理します。</p>"
            "<p>まずは冒頭の価格変動ボックスで前回価格と現在価格を確認してください。</p>",
            build_price_alert_box(article_data),
            build_sale_price_section(article_data),
            build_sale_diff_section(article_data),
            build_discount_section(article_data),
            build_reason_section(article_data),
            build_sale_navigation_section(article_data),
            "<h2>購入リンク</h2>"
            "<p>価格は随時更新されるため、購入前にストアで最新価格をご確認ください。</p>",
        ]

        return "\n".join(parts)
    except Exception as exc:
        # 例外時も生成を止めず、最小限の本文を返す。
        safe_title = escape(str(article_data.get("title", "セール情報まとめ")).strip())
        return (
            f"<h1>{safe_title}</h1>"
            "<h2>結論</h2>"
            "<p>価格情報の整形中に問題が発生したため、ストアで最新価格を直接ご確認ください。</p>"
            f"<p class=\"template-warning\">template_error: {escape(str(exc))}</p>"
        )
