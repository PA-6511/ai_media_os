import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipelines.enrich_article_with_links import PR_NOTICE_TEXT, enrich_article  # noqa: E402


def test_enrich_article_adds_pr_notice_for_volume_guide(monkeypatch):
    monkeypatch.setattr("pipelines.enrich_article_with_links.build_related_links", lambda article_output: [])
    monkeypatch.setattr("pipelines.enrich_article_with_links.insert_related_links", lambda html, links: html)

    article_output = {
        "title": "volume guide",
        "content_html": "<h1>volume guide</h1><h2>結論</h2><p>巻数情報を整理します。</p>",
    }

    result = enrich_article(article_output)

    assert PR_NOTICE_TEXT in result["content_html"]
    assert result["content_html"].count(PR_NOTICE_TEXT) == 1


def test_enrich_article_adds_pr_notice_for_summary(monkeypatch):
    monkeypatch.setattr("pipelines.enrich_article_with_links.build_related_links", lambda article_output: [])
    monkeypatch.setattr("pipelines.enrich_article_with_links.insert_related_links", lambda html, links: html)

    article_output = {
        "title": "summary",
        "content_html": "<h1>summary</h1><h2>まとめ買い</h2><p>全巻情報を整理します。</p>",
    }

    result = enrich_article(article_output)

    assert PR_NOTICE_TEXT in result["content_html"]
    assert result["content_html"].count(PR_NOTICE_TEXT) == 1


def test_enrich_article_adds_pr_notice_for_latest_volume(monkeypatch):
    monkeypatch.setattr("pipelines.enrich_article_with_links.build_related_links", lambda article_output: [])
    monkeypatch.setattr("pipelines.enrich_article_with_links.insert_related_links", lambda html, links: html)

    article_output = {
        "title": "latest volume",
        "content_html": "<h1>latest volume</h1><h2>最新巻</h2><p>発売日情報を整理します。</p>",
    }

    result = enrich_article(article_output)

    assert PR_NOTICE_TEXT in result["content_html"]
    assert result["content_html"].count(PR_NOTICE_TEXT) == 1


def test_enrich_article_keeps_pr_notice_idempotent(monkeypatch):
    monkeypatch.setattr("pipelines.enrich_article_with_links.build_related_links", lambda article_output: [])
    monkeypatch.setattr("pipelines.enrich_article_with_links.insert_related_links", lambda html, links: html)

    article_output = {
        "title": "idempotent",
        "content_html": f"<h1>idempotent</h1><p class=\"pr-notice\">{PR_NOTICE_TEXT}</p><p>本文です。</p>",
    }

    result = enrich_article(article_output)

    assert result["content_html"].count(PR_NOTICE_TEXT) == 1