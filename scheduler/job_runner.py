from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

from monitoring.log_helper import get_failure_logger
from main import run_pipeline
from scheduler.config import SchedulerConfig
from scheduler.report_hook import run_daily_report_hook


@contextmanager
def _temporary_env(overrides: dict[str, str | None]) -> Iterator[None]:
    """実行中のみ環境変数を一時上書きする。"""
    originals: dict[str, str | None] = {key: os.environ.get(key) for key in overrides}
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in originals.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def run_once(config: SchedulerConfig) -> dict[str, Any]:
    """main.py パイプラインを1回分実行する。"""
    logger = get_failure_logger()
    env_overrides: dict[str, str | None] = {}
    if config.dry_run is not None:
        env_overrides["WP_DRY_RUN"] = "1" if config.dry_run else "0"
    if config.only_sale_articles is not None:
        env_overrides["ONLY_SALE_ARTICLES"] = "1" if config.only_sale_articles else "0"

    with _temporary_env(env_overrides):
        logger.info(
            "[SCHEDULER] job_runner start dry_run=%s max_items=%s only_sale_articles=%s",
            config.dry_run,
            config.max_items,
            config.only_sale_articles,
        )
        result = run_pipeline(
            max_items=config.max_items,
            only_sale_articles=config.only_sale_articles,
            save_per_item_files=config.save_per_item_files,
        )

    logger.info(
        "[SCHEDULER] job_runner finish success=%s skipped=%s failed=%s",
        result.get("success_count", 0),
        result.get("skipped_count", 0),
        result.get("failed_count", 0),
    )

    failed_count = int(result.get("failed_count", 0) or 0)
    job_success = failed_count == 0

    hook_result: dict[str, Any] | None = None
    if config.run_daily_report_after_job:
        if config.run_daily_report_on_success_only and not job_success:
            hook_result = {
                "success": False,
                "skipped": True,
                "reason": "job_failed_and_success_only_enabled",
            }
        else:
            try:
                hook_result = run_daily_report_hook()
            except Exception as exc:
                hook_result = {
                    "success": False,
                    "error": str(exc),
                }

    return {
        "job_result": result,
        "job_success": job_success,
        "report_hook": hook_result,
    }
