from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from config.core_runtime_config import get_core_runtime_str


BASE_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = BASE_DIR / "data" / "logs" / "pipeline_failures.log"
PRICE_CHANGE_LOG_PATH = BASE_DIR / "data" / "logs" / "price_change.log"
RELEASE_CHANGE_LOG_PATH = BASE_DIR / "data" / "logs" / "release_change.log"
COMBINED_SIGNAL_LOG_PATH = BASE_DIR / "data" / "logs" / "combined_signal.log"


def _resolve_log_level() -> int:
    configured = get_core_runtime_str("logging.level", "INFO").strip().upper()
    if configured == "DEBUG":
        return logging.DEBUG
    if configured == "WARNING":
        return logging.WARNING
    if configured == "ERROR":
        return logging.ERROR
    if configured == "CRITICAL":
        return logging.CRITICAL
    return logging.INFO


def get_failure_logger() -> logging.Logger:
    """失敗監視用ロガーを返す。"""
    logger = logging.getLogger("pipeline.failure")
    if logger.handlers:
        return logger

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(_resolve_log_level())
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_price_change_logger() -> logging.Logger:
    """価格変動監視用ロガーを返す。"""
    logger = logging.getLogger("pipeline.price_change")
    if logger.handlers:
        return logger

    PRICE_CHANGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(_resolve_log_level())
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = logging.FileHandler(PRICE_CHANGE_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_release_change_logger() -> logging.Logger:
    """新刊イベント監視用ロガーを返す。"""
    logger = logging.getLogger("pipeline.release_change")
    if logger.handlers:
        return logger

    RELEASE_CHANGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(_resolve_log_level())
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = logging.FileHandler(RELEASE_CHANGE_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def get_combined_signal_logger() -> logging.Logger:
    """複合シグナル監視用ロガーを返す。"""
    logger = logging.getLogger("pipeline.combined_signal")
    if logger.handlers:
        return logger

    COMBINED_SIGNAL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(_resolve_log_level())
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    file_handler = logging.FileHandler(COMBINED_SIGNAL_LOG_PATH, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def log_failed_item(item: dict[str, Any]) -> None:
    logger = get_failure_logger()
    logger.error(
        "[FAILED] slug=%s work_id=%s keyword=%s article_type=%s error=%s retryable=%s retry_count=%s dry_run=%s",
        item.get("slug", ""),
        item.get("work_id", ""),
        item.get("keyword", ""),
        item.get("article_type", ""),
        item.get("error_message", ""),
        item.get("retryable", ""),
        item.get("retry_count", ""),
        item.get("dry_run", ""),
    )


def log_batch_summary(summary: dict[str, Any]) -> None:
    logger = get_failure_logger()
    logger.info(
        "[BATCH] executed_at=%s success=%s skipped=%s failed=%s failed_slugs=%s dry_run=%s",
        summary.get("executed_at", ""),
        summary.get("success_count", 0),
        summary.get("skipped_count", 0),
        summary.get("failed_count", 0),
        ",".join(summary.get("failed_slugs", [])),
        summary.get("dry_run", ""),
    )


def log_retry_enqueued(item: dict[str, Any]) -> None:
    logger = get_failure_logger()
    logger.warning(
        "[RETRY_ENQUEUED] slug=%s reason=%s retry_count=%s max_retry_count=%s next_retry_at=%s",
        item.get("slug", ""),
        item.get("reason", ""),
        item.get("retry_count", ""),
        item.get("max_retry_count", ""),
        item.get("next_retry_at", ""),
    )


def log_give_up(item: dict[str, Any]) -> None:
    logger = get_failure_logger()
    logger.error(
        "[GIVE_UP] slug=%s keyword=%s retry_count=%s error=%s",
        item.get("slug", ""),
        item.get("keyword", ""),
        item.get("retry_count", ""),
        item.get("error_message", ""),
    )


def log_price_change_event(event: dict[str, Any]) -> None:
    logger = get_price_change_logger()
    logger.info(
        "[PRICE_CHANGE] checked_at=%s work_id=%s keyword=%s article_type=%s slug=%s previous_price=%s current_price=%s price_diff=%s discount_rate=%s change_reason=%s price_changed=%s priority=%s decision=%s dry_run=%s",
        event.get("checked_at", ""),
        event.get("work_id", ""),
        event.get("keyword", ""),
        event.get("article_type", ""),
        event.get("slug", ""),
        event.get("previous_price", ""),
        event.get("current_price", ""),
        event.get("price_diff", ""),
        event.get("discount_rate", ""),
        event.get("change_reason", ""),
        event.get("price_changed", ""),
        event.get("priority", ""),
        event.get("decision", ""),
        event.get("dry_run", ""),
    )


def log_price_change_batch_summary(summary: dict[str, Any]) -> None:
    logger = get_price_change_logger()
    logger.info(
        "[BATCH_SUMMARY] executed_at=%s checked_count=%s changed_count=%s refresh_target_count=%s skipped_count=%s dry_run=%s",
        summary.get("executed_at", ""),
        summary.get("checked_count", 0),
        summary.get("changed_count", 0),
        summary.get("refresh_target_count", 0),
        summary.get("skipped_count", 0),
        summary.get("dry_run", ""),
    )


def log_release_change_event(event: dict[str, Any]) -> None:
    logger = get_release_change_logger()
    logger.info(
        "[RELEASE_CHANGE] checked_at=%s work_id=%s title=%s keyword=%s article_type=%s slug=%s previous_latest_volume_number=%s current_latest_volume_number=%s previous_latest_release_date=%s current_latest_release_date=%s availability_status=%s release_change_reason=%s release_changed=%s priority=%s decision=%s dry_run=%s",
        event.get("checked_at", ""),
        event.get("work_id", ""),
        event.get("title", ""),
        event.get("keyword", ""),
        event.get("article_type", ""),
        event.get("slug", ""),
        event.get("previous_latest_volume_number", ""),
        event.get("current_latest_volume_number", ""),
        event.get("previous_latest_release_date", ""),
        event.get("current_latest_release_date", ""),
        event.get("current_availability_status", event.get("availability_status", "")),
        event.get("release_change_reason", ""),
        event.get("release_changed", ""),
        event.get("priority", ""),
        event.get("decision", ""),
        event.get("dry_run", ""),
    )


def log_release_change_batch_summary(summary: dict[str, Any]) -> None:
    logger = get_release_change_logger()
    logger.info(
        "[BATCH_SUMMARY] executed_at=%s checked_count=%s release_changed_count=%s refresh_target_count=%s skipped_count=%s dry_run=%s",
        summary.get("executed_at", ""),
        summary.get("checked_count", 0),
        summary.get("release_changed_count", 0),
        summary.get("refresh_target_count", 0),
        summary.get("skipped_count", 0),
        summary.get("dry_run", ""),
    )


def log_combined_signal_event(event: dict[str, Any]) -> None:
    logger = get_combined_signal_logger()
    sub_reasons = event.get("sub_reasons", [])
    if isinstance(sub_reasons, list):
        sub_reason_text = ",".join(str(x) for x in sub_reasons)
    else:
        sub_reason_text = str(sub_reasons or "")

    next_summary = event.get("next_articles_summary", [])
    if isinstance(next_summary, list):
        next_summary_text = "/".join(str(x) for x in next_summary if str(x).strip())
    else:
        next_summary_text = str(next_summary or "")

    logger.info(
        "[COMBINED_SIGNAL] checked_at=%s event_type=%s work_id=%s title=%s keyword=%s article_type=%s slug=%s price_changed=%s release_changed=%s previous_price=%s current_price=%s price_diff=%s previous_latest_volume_number=%s current_latest_volume_number=%s priority=%s decision=%s reason=%s sub_reasons=%s stage=%s journey_mode=%s is_release_optimized=%s is_sale_optimized=%s cta_text=%s next_articles_summary=%s dry_run=%s",
        event.get("checked_at", ""),
        event.get("event_type", ""),
        event.get("work_id", ""),
        event.get("title", ""),
        event.get("keyword", ""),
        event.get("article_type", ""),
        event.get("slug", ""),
        event.get("price_changed", ""),
        event.get("release_changed", ""),
        event.get("previous_price", ""),
        event.get("current_price", ""),
        event.get("price_diff", ""),
        event.get("previous_latest_volume_number", ""),
        event.get("current_latest_volume_number", ""),
        event.get("priority", ""),
        event.get("decision", ""),
        event.get("reason", ""),
        sub_reason_text,
        event.get("stage", ""),
        event.get("journey_mode", ""),
        event.get("is_release_optimized", False),
        event.get("is_sale_optimized", False),
        event.get("cta_text", ""),
        next_summary_text,
        event.get("dry_run", ""),
    )


def log_combined_signal_batch_summary(summary: dict[str, Any]) -> None:
    logger = get_combined_signal_logger()
    logger.info(
        "[BATCH_SUMMARY] executed_at=%s checked_count=%s combined_count=%s price_only_count=%s release_only_count=%s refresh_target_count=%s skipped_count=%s failed_count=%s dry_run=%s",
        summary.get("executed_at", ""),
        summary.get("checked_count", 0),
        summary.get("combined_count", 0),
        summary.get("price_only_count", 0),
        summary.get("release_only_count", 0),
        summary.get("refresh_target_count", 0),
        summary.get("skipped_count", 0),
        summary.get("failed_count", 0),
        summary.get("dry_run", ""),
    )
