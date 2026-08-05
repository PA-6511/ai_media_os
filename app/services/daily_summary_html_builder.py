from __future__ import annotations

import html
from datetime import date

from app.services.daily_summary_query_service import DailySummaryItem, safe_https_url


STORE_LINKS = (
    ("Amazon Kindleで読む", "kindle_url"),
    ("楽天Koboで読む", "rakuten_kobo_url"),
    ("DMMブックスで読む", "dmm_url"),
)


def build_daily_summary_title(summary_date: date) -> str:
    return (
        f"{summary_date.year}年{summary_date.month}月{summary_date.day}日発売の"
        "電子コミック新刊まとめ"
    )


def build_daily_summary_slug(summary_date: date) -> str:
    return f"comic-new-releases-{summary_date.isoformat()}"


class DailySummaryHtmlBuilder:
    def build(self, *, summary_date: date, items: tuple[DailySummaryItem, ...]) -> str:
        ordered = sorted(
            items,
            key=lambda item: (
                item.release_date,
                item.title,
                item.volume_label,
                item.ebook_item_id,
            ),
        )
        cards = "".join(self._card(item) for item in ordered)
        display_date = f"{summary_date.year}年{summary_date.month}月{summary_date.day}日"
        return (
            '<p class="pr-notice"><strong>PR</strong> 本記事には広告リンクが含まれます。</p>'
            f"<p>{html.escape(display_date)}発売の電子コミック新刊をまとめました。</p>"
            f"<p>掲載件数: {len(ordered)}件</p>"
            f'<section class="daily-new-releases">{cards}</section>'
            "<p>価格・配信状況は変更される場合があります。各ストアで最新情報をご確認ください。</p>"
        )

    def _card(self, item: DailySummaryItem) -> str:
        image = ""
        image_url = safe_https_url(item.image_url)
        if image_url:
            image = (
                f'<img src="{html.escape(image_url, quote=True)}" '
                f'alt="{html.escape(item.title, quote=True)}" loading="lazy">'
            )
        title = html.escape(item.title)
        internal_url = safe_https_url(item.internal_url)
        heading = (
            f'<h2><a href="{html.escape(internal_url, quote=True)}">{title}</a></h2>'
            if internal_url
            else f"<h2>{title}</h2>"
        )
        details = (
            f"<li>巻数: {html.escape(item.volume_label or '-')}</li>"
            f"<li>著者: {html.escape(item.author_name or '-')}</li>"
            f"<li>出版社: {html.escape(item.publisher_name or '-')}</li>"
            f"<li>発売日: {item.release_date.isoformat()}</li>"
        )
        buttons = "".join(self._store_button(item, label, field) for label, field in STORE_LINKS)
        return f'<article class="daily-new-release">{image}{heading}<ul>{details}</ul><div>{buttons}</div></article>'

    @staticmethod
    def _store_button(item: DailySummaryItem, label: str, field: str) -> str:
        url = safe_https_url(getattr(item, field))
        if not url:
            return f'<span class="store-link-pending">{html.escape(label)}: 準備中</span>'
        return (
            f'<a href="{html.escape(url, quote=True)}" target="_blank" '
            'rel="nofollow sponsored noopener noreferrer">'
            f"{html.escape(label)}</a>"
        )