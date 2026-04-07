from pipelines import retry_failed_items as target


def _queue_item() -> dict:
    return {
        "slug": "s1",
        "retry_count": 1,
        "max_retry_count": 3,
        "work_id": "w1",
        "keyword": "k1",
        "article_type": "sale_article",
        "title": "t1",
    }


def test_retry_one_item_dry_run_returns_would_retry() -> None:
    result = target.retry_one_item(_queue_item(), dry_run=True)
    assert result["success"] is True
    assert result["dry_run"] is True
    assert result["decision"] == "would_retry"


def test_retry_one_item_exception_retryable_increments(monkeypatch) -> None:
    calls = {"increment": 0, "give_up": 0}

    monkeypatch.setattr(target, "mark_retrying", lambda _slug: None)
    monkeypatch.setattr(target, "generate_plan", lambda _item: (_ for _ in ()).throw(RuntimeError("503 temporary")))
    monkeypatch.setattr(
        target,
        "should_retry",
        lambda **_kwargs: {
            "retryable": True,
            "reason": "temporary_server_error",
            "next_retry_at": "2026-04-07T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(
        target,
        "increment_retry_count",
        lambda _slug, _error, _next: calls.__setitem__("increment", calls["increment"] + 1),
    )
    monkeypatch.setattr(target, "report_failed_item", lambda _item: None)
    monkeypatch.setattr(target, "mark_give_up", lambda _slug, _error: calls.__setitem__("give_up", calls["give_up"] + 1))

    result = target.retry_one_item(_queue_item(), dry_run=False)

    assert result["success"] is False
    assert result["give_up"] is False
    assert calls["increment"] == 1
    assert calls["give_up"] == 0


def test_retry_one_item_exception_non_retryable_marks_give_up(monkeypatch) -> None:
    calls = {"increment": 0, "give_up": 0}

    monkeypatch.setattr(target, "mark_retrying", lambda _slug: None)
    monkeypatch.setattr(target, "generate_plan", lambda _item: (_ for _ in ()).throw(RuntimeError("401 unauthorized")))
    monkeypatch.setattr(
        target,
        "should_retry",
        lambda **_kwargs: {
            "retryable": False,
            "reason": "non_retryable_permanent_error",
            "next_retry_at": None,
        },
    )
    monkeypatch.setattr(
        target,
        "increment_retry_count",
        lambda _slug, _error, _next: calls.__setitem__("increment", calls["increment"] + 1),
    )
    monkeypatch.setattr(target, "mark_give_up", lambda _slug, _error: calls.__setitem__("give_up", calls["give_up"] + 1))
    monkeypatch.setattr(target, "report_give_up", lambda _item: None)

    result = target.retry_one_item(_queue_item(), dry_run=False)

    assert result["success"] is False
    assert result["give_up"] is True
    assert calls["increment"] == 0
    assert calls["give_up"] == 1


def test_run_retry_batch_aggregates_loop_results(monkeypatch) -> None:
    queue_items = [{"slug": "a"}, {"slug": "b"}, {"slug": "c"}]

    monkeypatch.setattr(target, "get_retry_candidates", lambda _now, limit=None: queue_items[: limit or None])
    monkeypatch.setattr(target, "_to_bool", lambda _v, default=True: False)

    def _fake_retry_one_item(item: dict, dry_run: bool) -> dict:
        if item["slug"] == "a":
            return {"slug": "a", "success": True, "dry_run": False}
        if item["slug"] == "b":
            return {"slug": "b", "success": False, "give_up": True}
        return {"slug": "c", "success": True, "dry_run": True}

    monkeypatch.setattr(target, "retry_one_item", _fake_retry_one_item)

    summary = target.run_retry_batch()

    assert summary["total"] == 3
    assert summary["resolved_count"] == 1
    assert summary["failed_count"] == 1
    assert summary["give_up_count"] == 1
