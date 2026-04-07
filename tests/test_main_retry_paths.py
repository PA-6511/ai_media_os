from pathlib import Path

import main as app_main


def _base_item() -> dict:
    return {
        "work_id": "w1",
        "keyword": "k1",
        "article_type": "sale_article",
        "title": "t1",
    }


def _base_config(tmp_path) -> app_main.BatchConfig:
    return app_main.BatchConfig(save_per_item_files=False, per_item_dir=Path(tmp_path))


def test_process_one_item_pre_publish_failure_returns_safe_fallback(tmp_path, monkeypatch) -> None:
    calls = {"upsert": 0, "enqueue": 0}

    monkeypatch.setattr(app_main, "build_slug", lambda _item: "slug1")
    monkeypatch.setattr(app_main, "generate_plan", lambda _item: (_ for _ in ()).throw(RuntimeError("planner boom")))
    monkeypatch.setattr(app_main, "build_status_record", lambda **kwargs: kwargs)
    monkeypatch.setattr(app_main, "upsert_status", lambda _record: calls.__setitem__("upsert", calls["upsert"] + 1))
    monkeypatch.setattr(app_main, "_to_bool", lambda _v, default=True: True)
    monkeypatch.setattr(app_main, "enqueue_failed_item", lambda _record: calls.__setitem__("enqueue", calls["enqueue"] + 1))

    result = app_main.process_one_item(_base_item(), _base_config(tmp_path))

    assert result["success"] is False
    assert "planner boom" in str(result["error"])
    assert calls["upsert"] == 1
    assert calls["enqueue"] == 0


def test_process_one_item_pre_publish_failure_enqueues_when_retryable(tmp_path, monkeypatch) -> None:
    calls = {"enqueue": 0}

    monkeypatch.setattr(app_main, "build_slug", lambda _item: "slug1")
    monkeypatch.setattr(app_main, "generate_plan", lambda _item: (_ for _ in ()).throw(RuntimeError("planner boom")))
    monkeypatch.setattr(app_main, "build_status_record", lambda **kwargs: kwargs)
    monkeypatch.setattr(app_main, "upsert_status", lambda _record: None)
    monkeypatch.setattr(app_main, "_to_bool", lambda _v, default=True: False)
    monkeypatch.setattr(app_main, "get_retry_max_retry_count", lambda: 3)
    monkeypatch.setattr(
        app_main,
        "should_retry",
        lambda *_args, **_kwargs: {
            "retryable": True,
            "max_retry_count": 3,
            "next_retry_at": "2026-04-07T00:00:00+00:00",
        },
    )
    monkeypatch.setattr(app_main, "build_retry_record", lambda **kwargs: kwargs)
    monkeypatch.setattr(app_main, "enqueue_failed_item", lambda _record: calls.__setitem__("enqueue", calls["enqueue"] + 1))

    result = app_main.process_one_item(_base_item(), _base_config(tmp_path))

    assert result["success"] is False
    assert calls["enqueue"] == 1
