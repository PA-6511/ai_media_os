from __future__ import annotations

import argparse
import os
import sys
from contextlib import contextmanager
from typing import Any, Iterator

from monitoring.log_helper import get_failure_logger
from main import run_pipeline
from scheduler.config import SchedulerConfig, load_scheduler_config
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


def main(argv: list[str] | None = None) -> int:
    """1回だけ scheduler job を実行する CLI 入口。"""
    parser = argparse.ArgumentParser(description="scheduler job を1回だけ実行する")
    parser.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="WordPress への実投稿を行わない",
    )
    parser.add_argument(
        "--real-run",
        dest="real_run",
        action="store_true",
        help="WordPress への実投稿を行う",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=None,
        help="今回処理する最大件数を上書きする",
    )
    parser.add_argument(
        "--only-sale-articles",
        action="store_true",
        help="sale_article のみ処理する",
    )

    args = parser.parse_args(argv)
    if args.dry_run and args.real_run:
        parser.error("--dry-run と --real-run は同時に指定できません")

    config = load_scheduler_config()
    if args.dry_run:
        config.dry_run = True
    elif args.real_run:
        config.dry_run = False

    if args.max_items is not None:
        config.max_items = args.max_items

    if args.only_sale_articles:
        config.only_sale_articles = True

    wrapped = run_once(config)
    job_result = wrapped.get("job_result", {})

    print("Scheduler job result:")
    print(f"success_count: {job_result.get('success_count', 0)}")
    print(f"skipped_count: {job_result.get('skipped_count', 0)}")
    print(f"failed_count: {job_result.get('failed_count', 0)}")
    print(f"dry_run: {config.dry_run}")
    print(f"max_items: {config.max_items}")

    return 0 if wrapped.get("job_success", False) else 1


if __name__ == "__main__":
    sys.exit(main())
