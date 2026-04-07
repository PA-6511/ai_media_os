from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from config.ops_settings_loader import get_ops_setting


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


@dataclass
class SchedulerConfig:
    """定期実行の設定値。"""

    mode: str
    interval_seconds: int
    daily_time: str
    dry_run: bool | None
    log_path: Path
    lock_path: Path
    max_items: int | None
    only_sale_articles: bool | None
    save_per_item_files: bool
    run_once: bool
    run_daily_report_after_job: bool
    run_daily_report_on_success_only: bool


def _to_bool(value: str, default: bool) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_optional_int(value: str) -> int | None:
    text = (value or "").strip().lower()
    if text in {"", "none", "all", "*"}:
        return None
    parsed = int(text)
    if parsed <= 0:
        raise ValueError("max_items は 1 以上の整数か None/all を指定してください")
    return parsed


def _parse_dry_run(value: str) -> bool | None:
    text = (value or "").strip().lower()
    if text in {"", "env"}:
        return None
    return _to_bool(text, default=True)


def _parse_only_sale_articles(value: str) -> bool | None:
    text = (value or "").strip().lower()
    if text in {"", "env"}:
        return None
    return _to_bool(text, default=False)


def load_scheduler_config() -> SchedulerConfig:
    """環境変数から SchedulerConfig を構築する。"""
    mode = os.getenv("SCHEDULER_MODE", "interval").strip().lower()
    if mode not in {"interval", "daily"}:
        raise ValueError("SCHEDULER_MODE は interval または daily を指定してください")

    interval_seconds = int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "3600"))
    if interval_seconds <= 0:
        raise ValueError("SCHEDULER_INTERVAL_SECONDS は 1 以上を指定してください")

    daily_time = os.getenv("SCHEDULER_DAILY_TIME", "09:00").strip()
    if len(daily_time) != 5 or daily_time[2] != ":":
        raise ValueError("SCHEDULER_DAILY_TIME は HH:MM 形式で指定してください")

    default_dry_run = bool(get_ops_setting("ops.default_dry_run", True))
    default_run_daily_report_after_job = bool(
        get_ops_setting("scheduler.run_daily_report_after_job", True)
    )
    default_run_daily_report_on_success_only = bool(
        get_ops_setting("scheduler.run_daily_report_on_success_only", False)
    )

    parsed_dry_run = _parse_dry_run(os.getenv("SCHEDULER_DRY_RUN", "env"))

    config = SchedulerConfig(
        mode=mode,
        interval_seconds=interval_seconds,
        daily_time=daily_time,
        dry_run=parsed_dry_run if parsed_dry_run is not None else default_dry_run,
        log_path=Path(os.getenv("SCHEDULER_LOG_PATH", str(DATA_DIR / "logs" / "scheduler.log"))),
        lock_path=Path(os.getenv("SCHEDULER_LOCK_PATH", str(DATA_DIR / "locks" / "scheduler.lock"))),
        max_items=_parse_optional_int(os.getenv("SCHEDULER_MAX_ITEMS", "None")),
        only_sale_articles=_parse_only_sale_articles(os.getenv("SCHEDULER_ONLY_SALE_ARTICLES", "env")),
        save_per_item_files=_to_bool(os.getenv("SCHEDULER_SAVE_PER_ITEM_FILES", "1"), default=True),
        run_once=_to_bool(os.getenv("SCHEDULER_RUN_ONCE", "0"), default=False),
        run_daily_report_after_job=_to_bool(
            os.getenv("SCHEDULER_RUN_DAILY_REPORT_AFTER_JOB", ""),
            default=default_run_daily_report_after_job,
        ),
        run_daily_report_on_success_only=_to_bool(
            os.getenv("SCHEDULER_RUN_DAILY_REPORT_ON_SUCCESS_ONLY", ""),
            default=default_run_daily_report_on_success_only,
        ),
    )
    return config
