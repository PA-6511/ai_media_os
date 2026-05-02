from __future__ import annotations

import pytest

from scheduler.job_runner import main
from scheduler.config import SchedulerConfig
from pathlib import Path


def _make_config(**kwargs) -> SchedulerConfig:
    defaults = dict(
        mode="interval",
        interval_seconds=3600,
        daily_time="09:00",
        dry_run=True,
        log_path=Path("/tmp/scheduler_test.log"),
        lock_path=Path("/tmp/scheduler_test.lock"),
        max_items=None,
        only_sale_articles=None,
        save_per_item_files=True,
        run_once=False,
        run_daily_report_after_job=False,
        run_daily_report_on_success_only=False,
    )
    defaults.update(kwargs)
    return SchedulerConfig(**defaults)


def _stub_run_once(config: SchedulerConfig):
    """run_once の代替。実処理を一切実行しない。"""
    return {
        "job_result": {
            "success_count": 1,
            "skipped_count": 0,
            "failed_count": 0,
        },
        "job_success": True,
        "report_hook": None,
        "_captured_config": config,
    }


def test_dry_run_flag_sets_config(monkeypatch):
    captured = {}

    def fake_load():
        return _make_config(dry_run=False)

    def fake_run_once(config):
        captured["config"] = config
        return {"job_result": {"success_count": 1, "skipped_count": 0, "failed_count": 0}, "job_success": True, "report_hook": None}

    monkeypatch.setattr("scheduler.job_runner.load_scheduler_config", fake_load)
    monkeypatch.setattr("scheduler.job_runner.run_once", fake_run_once)

    exit_code = main(["--dry-run"])

    assert exit_code == 0
    assert captured["config"].dry_run is True


def test_real_run_flag_sets_config(monkeypatch):
    captured = {}

    def fake_load():
        return _make_config(dry_run=True)

    def fake_run_once(config):
        captured["config"] = config
        return {"job_result": {"success_count": 1, "skipped_count": 0, "failed_count": 0}, "job_success": True, "report_hook": None}

    monkeypatch.setattr("scheduler.job_runner.load_scheduler_config", fake_load)
    monkeypatch.setattr("scheduler.job_runner.run_once", fake_run_once)

    exit_code = main(["--real-run"])

    assert exit_code == 0
    assert captured["config"].dry_run is False


def test_max_items_is_passed_to_config(monkeypatch):
    captured = {}

    def fake_load():
        return _make_config(max_items=None)

    def fake_run_once(config):
        captured["config"] = config
        return {"job_result": {"success_count": 1, "skipped_count": 0, "failed_count": 0}, "job_success": True, "report_hook": None}

    monkeypatch.setattr("scheduler.job_runner.load_scheduler_config", fake_load)
    monkeypatch.setattr("scheduler.job_runner.run_once", fake_run_once)

    exit_code = main(["--dry-run", "--max-items", "5"])

    assert exit_code == 0
    assert captured["config"].max_items == 5


def test_only_sale_articles_is_passed_to_config(monkeypatch):
    captured = {}

    def fake_load():
        return _make_config(only_sale_articles=None)

    def fake_run_once(config):
        captured["config"] = config
        return {"job_result": {"success_count": 1, "skipped_count": 0, "failed_count": 0}, "job_success": True, "report_hook": None}

    monkeypatch.setattr("scheduler.job_runner.load_scheduler_config", fake_load)
    monkeypatch.setattr("scheduler.job_runner.run_once", fake_run_once)

    exit_code = main(["--dry-run", "--only-sale-articles"])

    assert exit_code == 0
    assert captured["config"].only_sale_articles is True


def test_dry_run_and_real_run_conflict_raises(monkeypatch):
    def fake_load():
        return _make_config()

    def fake_run_once(config):
        return {"job_result": {}, "job_success": True, "report_hook": None}

    monkeypatch.setattr("scheduler.job_runner.load_scheduler_config", fake_load)
    monkeypatch.setattr("scheduler.job_runner.run_once", fake_run_once)

    with pytest.raises(SystemExit) as exc_info:
        main(["--dry-run", "--real-run"])

    assert exc_info.value.code != 0
