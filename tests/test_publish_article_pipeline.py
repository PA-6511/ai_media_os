import pytest

from pipelines import publish_article_pipeline as pipeline


class _DummyPublisher:
    def __init__(self, error: Exception):
        self.client = object()
        self._error = error

    def publish(self, _article, dry_run=False):
        raise self._error


def _sample_article() -> dict:
    return {
        "work_id": "w1",
        "keyword": "k1",
        "article_type": "sale_article",
        "title": "t1",
        "content_html": "<p>x</p>",
    }


def test_publish_article_enqueues_retry_when_retryable(monkeypatch) -> None:
    calls = {"enqueue": 0, "retry_report": 0}

    monkeypatch.setattr(pipeline, "build_wp_article", lambda _a: {"slug": "s1"})
    monkeypatch.setattr(
        pipeline,
        "create_publisher_from_env",
        lambda: (_DummyPublisher(RuntimeError("temporary 503")), False),
    )
    monkeypatch.setattr(
        pipeline,
        "should_publish",
        lambda _article, _client: {"should_publish": True, "decision": "publish_new", "reason": "ok"},
    )
    monkeypatch.setattr(pipeline, "build_status_record", lambda **kwargs: kwargs)
    monkeypatch.setattr(pipeline, "upsert_status", lambda _record: None)
    monkeypatch.setattr(
        pipeline,
        "should_retry",
        lambda *_args, **_kwargs: {
            "retryable": True,
            "reason": "temporary_server_error",
            "max_retry_count": 3,
            "next_retry_at": "2026-04-07T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(pipeline, "get_retry_max_retry_count", lambda: 3)
    monkeypatch.setattr(pipeline, "build_retry_record", lambda **kwargs: kwargs)
    monkeypatch.setattr(pipeline, "report_failed_item", lambda _item: None)
    monkeypatch.setattr(pipeline, "report_retry_enqueued", lambda _item: calls.__setitem__("retry_report", calls["retry_report"] + 1))
    monkeypatch.setattr(pipeline, "enqueue_failed_item", lambda _record: calls.__setitem__("enqueue", calls["enqueue"] + 1))

    with pytest.raises(RuntimeError):
        pipeline.publish_article(_sample_article())

    assert calls["enqueue"] == 1
    assert calls["retry_report"] == 1


def test_publish_article_dry_run_does_not_enqueue_retry(monkeypatch) -> None:
    calls = {"enqueue": 0, "should_retry": 0}

    monkeypatch.setattr(pipeline, "build_wp_article", lambda _a: {"slug": "s1"})
    monkeypatch.setattr(
        pipeline,
        "create_publisher_from_env",
        lambda: (_DummyPublisher(RuntimeError("temporary 503")), True),
    )
    monkeypatch.setattr(
        pipeline,
        "should_publish",
        lambda _article, _client: {"should_publish": True, "decision": "publish_new", "reason": "ok"},
    )
    monkeypatch.setattr(pipeline, "build_status_record", lambda **kwargs: kwargs)
    monkeypatch.setattr(pipeline, "upsert_status", lambda _record: None)
    monkeypatch.setattr(
        pipeline,
        "should_retry",
        lambda *_args, **_kwargs: calls.__setitem__("should_retry", calls["should_retry"] + 1),
    )
    monkeypatch.setattr(pipeline, "report_failed_item", lambda _item: None)
    monkeypatch.setattr(pipeline, "enqueue_failed_item", lambda _record: calls.__setitem__("enqueue", calls["enqueue"] + 1))

    with pytest.raises(RuntimeError):
        pipeline.publish_article(_sample_article())

    assert calls["enqueue"] == 0
    assert calls["should_retry"] == 0


def test_enforce_wp_prepublish_quality_appends_pr_block_at_end() -> None:
    article = {
        "article_type": "work_article",
        "content": (
            "<p>本文です。</p>\n"
            '<p><a href="https://example.com/item">公式ページで詳細を確認する</a></p>\n'
            "<p><small>価格・キャンペーン情報は掲載時点の内容です。最新情報は各ストアでご確認ください。</small></p>"
        ),
    }

    result = pipeline.enforce_wp_prepublish_quality(article)
    content = result["content"]
    pr_block = "<p><strong>PR</strong> 本記事にはプロモーションが含まれます。</p>"

    assert content.endswith(pr_block)
    assert content.count(pr_block) == 1


def test_enforce_wp_prepublish_quality_keeps_existing_pr_block_without_duplication() -> None:
    pr_block = "<p><strong>PR</strong> 本記事にはプロモーションが含まれます。</p>"
    article = {
        "article_type": "work_article",
        "content": (
            pr_block
            + "\n<p>本文です。</p>\n"
            + '<p><a href="https://example.com/item">公式ページで詳細を確認する</a></p>\n'
            + "<p><small>価格・キャンペーン情報は掲載時点の内容です。最新情報は各ストアでご確認ください。</small></p>"
        ),
    }

    result = pipeline.enforce_wp_prepublish_quality(article)
    assert result["content"].count(pr_block) == 1
