from pipelines.retry_queue_store import (
    build_retry_record,
    enqueue_failed_item,
    get_queue_item_by_slug,
    increment_retry_count,
    validate_transition,
)


def test_validate_transition_rejects_invalid_transition() -> None:
    assert validate_transition("give_up", "queued", item_id="x") is False


def test_increment_retry_count_reaches_give_up_on_max(tmp_path) -> None:
    db_path = tmp_path / "publish_history.db"
    record = build_retry_record(
        slug="test-slug",
        work_id="w1",
        keyword="k1",
        article_type="sale_article",
        title="title",
        last_error="init",
        retry_count=2,
        max_retry_count=3,
        retry_status="retrying",
        next_retry_at=None,
    )
    enqueue_failed_item(record, db_path=db_path, event_id="evt1")

    increment_retry_count("test-slug", "boom", None, db_path=db_path, event_id="evt1")

    updated = get_queue_item_by_slug("test-slug", db_path=db_path)
    assert updated is not None
    assert updated["retry_status"] == "give_up"
    assert int(updated["retry_count"]) == 3
    assert updated["next_retry_at"] is None
