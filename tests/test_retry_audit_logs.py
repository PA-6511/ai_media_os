import logging

from pipelines import retry_queue_store as target


def _build_record(*, retry_status: str = "queued", retry_count: int = 0, max_retry_count: int = 3):
    return target.build_retry_record(
        slug="audit-slug",
        work_id="w-audit",
        keyword="k-audit",
        article_type="sale_article",
        title="audit-title",
        last_error="seed-error",
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        retry_status=retry_status,
        next_retry_at=None,
    )


def _messages(caplog) -> str:
    return "\n".join(record.getMessage() for record in caplog.records)


def test_validate_transition_rejected_logs_warning_with_required_fields(caplog) -> None:
    event_id = "evt-warning-001"

    with caplog.at_level(logging.WARNING, logger=target.__name__):
        ok = target.validate_transition(
            "give_up",
            "queued",
            item_id="audit-slug",
            retry_count=2,
            max_retry_count=3,
            event_id=event_id,
        )

    assert ok is False
    assert any(record.levelno == logging.WARNING for record in caplog.records)
    text = _messages(caplog)
    assert "event_name=validate_transition_rejected" in text
    assert f"event_id={event_id}" in text
    assert "current_state=give_up" in text
    assert "next_state=queued" in text
    assert "reason=transition_not_allowed" in text


def test_enqueue_failed_item_logs_info_with_event_id_and_states(tmp_path, caplog) -> None:
    db_path = tmp_path / "publish_history.db"
    event_id = "evt-info-enqueue-001"
    record = _build_record(retry_status="queued", retry_count=0, max_retry_count=3)

    with caplog.at_level(logging.INFO, logger=target.__name__):
        target.enqueue_failed_item(record, db_path=db_path, event_id=event_id)

    assert any(record.levelno == logging.INFO for record in caplog.records)
    text = _messages(caplog)
    assert "event_name=enqueue_failed_item" in text
    assert f"event_id={event_id}" in text
    assert "current_state=missing" in text
    assert "next_state=queued" in text
    assert "reason=insert_new" in text


def test_increment_retry_count_logs_info_with_retry_fields(tmp_path, caplog) -> None:
    db_path = tmp_path / "publish_history.db"
    event_id = "evt-info-increment-001"
    record = _build_record(retry_status="retrying", retry_count=1, max_retry_count=3)
    target.enqueue_failed_item(record, db_path=db_path, event_id="seed")

    with caplog.at_level(logging.INFO, logger=target.__name__):
        target.increment_retry_count(
            "audit-slug",
            "temporary error",
            "2026-04-07T00:00:00+00:00",
            db_path=db_path,
            event_id=event_id,
        )

    assert any(record.levelno == logging.INFO for record in caplog.records)
    text = _messages(caplog)
    assert "event_name=increment_retry_count" in text
    assert f"event_id={event_id}" in text
    assert "current_state=retrying" in text
    assert "next_state=queued" in text
    assert "reason=error_retry_scheduled" in text


def test_mark_give_up_logs_error_with_reason_and_states(tmp_path, caplog) -> None:
    db_path = tmp_path / "publish_history.db"
    event_id = "evt-error-giveup-001"
    record = _build_record(retry_status="retrying", retry_count=2, max_retry_count=3)
    target.enqueue_failed_item(record, db_path=db_path, event_id="seed")

    with caplog.at_level(logging.ERROR, logger=target.__name__):
        target.mark_give_up("audit-slug", "fatal error", db_path=db_path, event_id=event_id)

    assert any(record.levelno == logging.ERROR for record in caplog.records)
    text = _messages(caplog)
    assert "event_name=mark_give_up" in text
    assert f"event_id={event_id}" in text
    assert "current_state=retrying" in text
    assert "next_state=give_up" in text
    assert "reason=manual_or_limit_reached" in text
