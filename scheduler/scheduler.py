import logging
import os
import signal
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from scheduler.config import SchedulerConfig, load_scheduler_config
from scheduler.job_runner import run_once


def setup_logger(log_path: Path) -> logging.Logger:
    """scheduler 専用ロガーを初期化する。"""
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("scheduler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def _is_pid_running(pid: int) -> bool:
    """PID が生存しているかを確認する。"""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_lock(lock_path: Path) -> bool:
    """ロックファイルを取得する。既存かつ生存PIDなら False を返す。"""
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    if lock_path.exists():
        try:
            raw = lock_path.read_text(encoding="utf-8").strip().split("|")
            existing_pid = int(raw[0]) if raw and raw[0] else 0
        except Exception:
            existing_pid = 0

        if existing_pid and _is_pid_running(existing_pid):
            return False

        # stale lock の場合は上書きして回復する。
        try:
            lock_path.unlink()
        except OSError:
            return False

    payload = f"{os.getpid()}|{datetime.now().isoformat()}"
    lock_path.write_text(payload, encoding="utf-8")
    return True


def release_lock(lock_path: Path) -> None:
    """ロックファイルを解放する。"""
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        pass


def seconds_until_daily_time(target_hhmm: str) -> int:
    """次回 HH:MM までの秒数を返す。"""
    now = datetime.now()
    hour_text, minute_text = target_hhmm.split(":", maxsplit=1)
    target = now.replace(hour=int(hour_text), minute=int(minute_text), second=0, microsecond=0)
    if target <= now:
        target = target + timedelta(days=1)
    return int((target - now).total_seconds())


def _run_job_and_log(config: SchedulerConfig, logger: logging.Logger) -> None:
    """1ジョブ実行と結果ログ出力を行う。"""
    logger.info("job started")
    try:
        wrapped = run_once(config)
        job_result: dict[str, Any] = wrapped.get("job_result", {})
        job_success = bool(wrapped.get("job_success", False))
        logger.info(
            "job finished success=%s success_count=%s skipped_count=%s failed_count=%s",
            job_success,
            job_result.get("success_count", 0),
            job_result.get("skipped_count", 0),
            job_result.get("failed_count", 0),
        )

        if config.run_daily_report_after_job:
            logger.info("daily report hook started")
            hook = wrapped.get("report_hook")
            if not hook:
                logger.warning("daily report hook not executed")
                return

            if hook.get("skipped"):
                logger.info(
                    "daily report hook skipped reason=%s",
                    hook.get("reason", "unknown"),
                )
                return

            if hook.get("success"):
                txt_path = hook.get("txt_path", "")
                json_path = hook.get("json_path", "")
                logger.info(
                    "daily report generated path=%s json_path=%s",
                    txt_path,
                    json_path,
                )
                print(f"daily report generated: {txt_path}")
            else:
                logger.error(
                    "daily report hook failed error=%s",
                    hook.get("error", "unknown"),
                )
    except Exception as exc:
        logger.exception("job finished success=False error=%s", exc)


def run_interval_mode(config: SchedulerConfig, logger: logging.Logger) -> None:
    """一定間隔モードで実行する。"""
    while True:
        _run_job_and_log(config, logger)
        logger.info("next run after %s seconds", config.interval_seconds)
        time.sleep(config.interval_seconds)


def run_daily_mode(config: SchedulerConfig, logger: logging.Logger) -> None:
    """毎日決時モードで実行する。"""
    while True:
        wait_seconds = seconds_until_daily_time(config.daily_time)
        next_time = datetime.now() + timedelta(seconds=wait_seconds)
        logger.info("next run at %s", next_time.strftime("%Y-%m-%d %H:%M:%S"))
        time.sleep(wait_seconds)
        _run_job_and_log(config, logger)


def main() -> None:
    """Scheduler のエントリポイント。"""
    config = load_scheduler_config()
    logger = setup_logger(config.log_path)

    print("Scheduler started")
    print(f"mode: {config.mode}")
    print(f"dry_run: {config.dry_run if config.dry_run is not None else 'env'}")
    print(f"run_daily_report_after_job: {config.run_daily_report_after_job}")
    print(f"run_daily_report_on_success_only: {config.run_daily_report_on_success_only}")
    if config.mode == "interval":
        print(f"interval_seconds: {config.interval_seconds}")
    else:
        print(f"daily_time: {config.daily_time}")

    logger.info(
        "scheduler started mode=%s dry_run=%s run_daily_report_after_job=%s run_daily_report_on_success_only=%s",
        config.mode,
        config.dry_run,
        config.run_daily_report_after_job,
        config.run_daily_report_on_success_only,
    )

    if not acquire_lock(config.lock_path):
        logger.error("lock already exists. another scheduler may be running path=%s", config.lock_path)
        print("lock exists. scheduler already running.")
        return

    print("lock acquired")
    logger.info("lock acquired path=%s", config.lock_path)

    try:
        if config.run_once:
            _run_job_and_log(config, logger)
            logger.info("run_once enabled. scheduler exiting")
            return

        if config.mode == "interval":
            run_interval_mode(config, logger)
        elif config.mode == "daily":
            run_daily_mode(config, logger)
        else:
            raise ValueError(f"unsupported scheduler mode: {config.mode}")
    except KeyboardInterrupt:
        logger.info("scheduler stopped by keyboard interrupt")
    except Exception as exc:
        logger.exception("scheduler crashed error=%s", exc)
    finally:
        release_lock(config.lock_path)
        logger.info("lock released path=%s", config.lock_path)


if __name__ == "__main__":
    # SIGTERM で終了した場合も finally まで到達させるためデフォルトハンドラを利用する。
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    main()
