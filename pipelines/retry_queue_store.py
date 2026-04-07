from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from config.core_runtime_config import get_core_runtime_int


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "publish_history.db"

RETRY_STATUSES = {"queued", "retrying", "resolved", "give_up"}
RetryState = Literal["queued", "retrying", "resolved", "give_up"]

# retry_queue の遷移はここに集約し、許可遷移のみ通す。
ALLOWED_RETRY_TRANSITIONS: dict[RetryState, set[RetryState]] = {
    "queued": {"retrying", "give_up"},
    "retrying": {"queued", "resolved", "give_up"},
    "resolved": {"queued"},
    "give_up": set(),
}

# 設定不備時は fail-safe なデフォルトへ倒す。
MAX_SAFE_RETRY_COUNT = get_core_runtime_int("retry.max_retry_count_clamp_max", 10, minimum=1, maximum=100)
MIN_SAFE_RETRY_COUNT = get_core_runtime_int("retry.max_retry_count_clamp_min", 1, minimum=1, maximum=MAX_SAFE_RETRY_COUNT)
DEFAULT_MAX_RETRY_COUNT = get_core_runtime_int(
    "retry.max_retry_count",
    3,
    minimum=MIN_SAFE_RETRY_COUNT,
    maximum=MAX_SAFE_RETRY_COUNT,
)

logger = logging.getLogger(__name__)


def _new_event_id() -> str:
    # 軽量な相関ID。外部依存なしで追跡可能性を担保する。
    return uuid4().hex[:12]


def _sanitize_reason(reason: str | None, max_length: int = 160) -> str:
    compact = " ".join(str(reason or "").split())
    if len(compact) <= max_length:
        return compact
    return f"{compact[:max_length]}..."


def _audit_retry_event(
    *,
    level: int,
    event_name: str,
    item_id: str,
    current_state: str,
    next_state: str,
    retry_count: int,
    max_retry_count: int,
    reason: str,
    event_id: str | None = None,
) -> str:
    resolved_event_id = (event_id or "").strip() or _new_event_id()
    logger.log(
        level,
        "[retry_queue_audit] event_name=%s item_id=%s current_state=%s next_state=%s retry_count=%s max_retry_count=%s reason=%s event_id=%s",
        event_name,
        (item_id or "").strip(),
        (current_state or "").strip(),
        (next_state or "").strip(),
        _normalize_retry_count(retry_count),
        _normalize_max_retry_count(max_retry_count),
        _sanitize_reason(reason),
        resolved_event_id,
    )
    return resolved_event_id


@dataclass
class RetryQueueRecord:
    """再試行キュー1件分。"""

    slug: str
    work_id: str
    keyword: str
    article_type: str
    title: str
    last_error: str
    retry_count: int
    max_retry_count: int
    retry_status: str
    next_retry_at: str | None
    created_at: str
    updated_at: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_retry_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, count)


def _normalize_max_retry_count(value: Any) -> int:
    try:
        count = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_RETRY_COUNT
    # 過剰再試行を避けるために上限をかける（fail-safe）。
    return max(MIN_SAFE_RETRY_COUNT, min(count, MAX_SAFE_RETRY_COUNT))


def validate_transition(
    current_state: str,
    next_state: str,
    *,
    item_id: str = "",
    retry_count: int = 0,
    max_retry_count: int = 0,
    event_id: str | None = None,
) -> bool:
    current = (current_state or "").strip().lower()
    nxt = (next_state or "").strip().lower()

    if current not in ALLOWED_RETRY_TRANSITIONS:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=item_id,
            current_state=current,
            next_state=nxt,
            retry_count=retry_count,
            max_retry_count=max_retry_count,
            reason="unknown_current_state",
            event_id=event_id,
        )
        return False

    if nxt not in RETRY_STATUSES:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=item_id,
            current_state=current,
            next_state=nxt,
            retry_count=retry_count,
            max_retry_count=max_retry_count,
            reason="invalid_next_state",
            event_id=event_id,
        )
        return False

    allowed = ALLOWED_RETRY_TRANSITIONS[current]
    if nxt not in allowed:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=item_id,
            current_state=current,
            next_state=nxt,
            retry_count=retry_count,
            max_retry_count=max_retry_count,
            reason=f"transition_not_allowed allowed={','.join(sorted(allowed))}",
            event_id=event_id,
        )
        return False

    return True


def _get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db_path))
    connection.row_factory = sqlite3.Row
    return connection


def create_tables(db_path: Path = DB_PATH) -> None:
    """retry_queue テーブルを作成する。"""
    sql = """
    CREATE TABLE IF NOT EXISTS retry_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        work_id TEXT,
        keyword TEXT,
        article_type TEXT,
        title TEXT,
        last_error TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retry_count INTEGER NOT NULL DEFAULT 3,
        retry_status TEXT NOT NULL,
        next_retry_at TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql)
        connection.commit()


def get_queue_item_by_slug(slug: str, db_path: Path = DB_PATH) -> dict[str, Any] | None:
    create_tables(db_path)
    query = """
    SELECT id, slug, work_id, keyword, article_type, title,
           last_error, retry_count, max_retry_count, retry_status,
           next_retry_at, created_at, updated_at
    FROM retry_queue
    WHERE slug = ?
    LIMIT 1
    """
    with _get_connection(db_path) as connection:
        row = connection.execute(query, ((slug or "").strip(),)).fetchone()

    if row is None:
        return None

    return {key: row[key] for key in row.keys()}


def enqueue_failed_item(record: RetryQueueRecord, db_path: Path = DB_PATH, event_id: str | None = None) -> None:
    """failed 記事を retry_queue へ投入または更新する。"""
    create_tables(db_path)
    if record.retry_status not in RETRY_STATUSES:
        raise ValueError(f"不正な retry_status です: {record.retry_status}")

    existing = get_queue_item_by_slug(record.slug, db_path=db_path)
    if existing:
        # give_up 済みは誤って復帰しないよう維持する（手動解除前提）。
        current_status = str(existing.get("retry_status", "queued")).strip().lower()
        current_retry_count = _normalize_retry_count(existing.get("retry_count", 0))
        current_max_retry_count = _normalize_max_retry_count(existing.get("max_retry_count", record.max_retry_count))
        if not validate_transition(
            current_status,
            "queued",
            item_id=record.slug,
            retry_count=current_retry_count,
            max_retry_count=current_max_retry_count,
            event_id=event_id,
        ):
            return

        sql = """
        UPDATE retry_queue
        SET work_id = ?,
            keyword = ?,
            article_type = ?,
            title = ?,
            last_error = ?,
            max_retry_count = ?,
            retry_status = 'queued',
            updated_at = ?
        WHERE slug = ?
        """
        with _get_connection(db_path) as connection:
            connection.execute(
                sql,
                (
                    record.work_id,
                    record.keyword,
                    record.article_type,
                    record.title,
                    record.last_error,
                    _normalize_max_retry_count(record.max_retry_count),
                    _utc_now(),
                    record.slug,
                ),
            )
            connection.commit()
        _audit_retry_event(
            level=logging.INFO,
            event_name="enqueue_failed_item",
            item_id=record.slug,
            current_state=current_status,
            next_state="queued",
            retry_count=current_retry_count,
            max_retry_count=current_max_retry_count,
            reason="upsert_existing",
            event_id=event_id,
        )
        return

    insert_sql = """
    INSERT INTO retry_queue (
        slug, work_id, keyword, article_type, title,
        last_error, retry_count, max_retry_count, retry_status,
        next_retry_at, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    with _get_connection(db_path) as connection:
        connection.execute(
            insert_sql,
            (
                record.slug,
                record.work_id,
                record.keyword,
                record.article_type,
                record.title,
                record.last_error,
                _normalize_retry_count(record.retry_count),
                _normalize_max_retry_count(record.max_retry_count),
                record.retry_status,
                record.next_retry_at,
                record.created_at,
                record.updated_at,
            ),
        )
        connection.commit()
    _audit_retry_event(
        level=logging.INFO,
        event_name="enqueue_failed_item",
        item_id=record.slug,
        current_state="missing",
        next_state=record.retry_status,
        retry_count=record.retry_count,
        max_retry_count=record.max_retry_count,
        reason="insert_new",
        event_id=event_id,
    )


def get_retry_candidates(now_iso: str, limit: int | None = None, db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    """再試行候補を取得する。"""
    create_tables(db_path)

    base_query = """
    SELECT id, slug, work_id, keyword, article_type, title,
           last_error, retry_count, max_retry_count, retry_status,
           next_retry_at, created_at, updated_at
    FROM retry_queue
    WHERE retry_status = 'queued'
      AND retry_count < max_retry_count
      AND (next_retry_at IS NULL OR next_retry_at <= ?)
    ORDER BY updated_at ASC
    """

    params: list[Any] = [now_iso]
    if limit is not None and limit > 0:
        base_query += " LIMIT ?"
        params.append(limit)

    with _get_connection(db_path) as connection:
        rows = connection.execute(base_query, tuple(params)).fetchall()

    return [{key: row[key] for key in row.keys()} for row in rows]


def mark_retrying(slug: str, db_path: Path = DB_PATH, event_id: str | None = None) -> None:
    create_tables(db_path)
    current = get_queue_item_by_slug(slug, db_path=db_path)
    if not current:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=slug,
            current_state="missing",
            next_state="retrying",
            retry_count=0,
            max_retry_count=0,
            reason="slug_not_found",
            event_id=event_id,
        )
        return
    current_state = str(current.get("retry_status", "")).strip().lower()
    retry_count = _normalize_retry_count(current.get("retry_count", 0))
    max_retry_count = _normalize_max_retry_count(current.get("max_retry_count", 0))
    if not validate_transition(
        current_state,
        "retrying",
        item_id=slug,
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        event_id=event_id,
    ):
        return
    sql = """
    UPDATE retry_queue
    SET retry_status = 'retrying', updated_at = ?
    WHERE slug = ?
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql, (_utc_now(), (slug or "").strip()))
        connection.commit()
    _audit_retry_event(
        level=logging.INFO,
        event_name="mark_retrying",
        item_id=slug,
        current_state=current_state,
        next_state="retrying",
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        reason="state_transition",
        event_id=event_id,
    )


def mark_resolved(slug: str, db_path: Path = DB_PATH, event_id: str | None = None) -> None:
    create_tables(db_path)
    current = get_queue_item_by_slug(slug, db_path=db_path)
    if not current:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=slug,
            current_state="missing",
            next_state="resolved",
            retry_count=0,
            max_retry_count=0,
            reason="slug_not_found",
            event_id=event_id,
        )
        return
    current_state = str(current.get("retry_status", "")).strip().lower()
    retry_count = _normalize_retry_count(current.get("retry_count", 0))
    max_retry_count = _normalize_max_retry_count(current.get("max_retry_count", 0))
    if not validate_transition(
        current_state,
        "resolved",
        item_id=slug,
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        event_id=event_id,
    ):
        return
    sql = """
    UPDATE retry_queue
    SET retry_status = 'resolved', updated_at = ?
    WHERE slug = ?
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql, (_utc_now(), (slug or "").strip()))
        connection.commit()
    _audit_retry_event(
        level=logging.INFO,
        event_name="mark_resolved",
        item_id=slug,
        current_state=current_state,
        next_state="resolved",
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        reason="state_transition",
        event_id=event_id,
    )


def increment_retry_count(
    slug: str,
    error_message: str,
    next_retry_at: str | None,
    db_path: Path = DB_PATH,
    event_id: str | None = None,
) -> None:
    create_tables(db_path)
    current = get_queue_item_by_slug(slug, db_path=db_path)
    if not current:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=slug,
            current_state="missing",
            next_state="queued",
            retry_count=0,
            max_retry_count=0,
            reason="slug_not_found",
            event_id=event_id,
        )
        return

    current_status = str(current.get("retry_status", "")).strip().lower()
    current_retry_count = _normalize_retry_count(current.get("retry_count", 0))
    current_max_retry_count = _normalize_max_retry_count(current.get("max_retry_count", 0))
    if not validate_transition(
        current_status,
        "queued",
        item_id=slug,
        retry_count=current_retry_count,
        max_retry_count=current_max_retry_count,
        event_id=event_id,
    ):
        return

    next_count = min(current_retry_count + 1, current_max_retry_count)
    next_state = "give_up" if current_retry_count + 1 >= current_max_retry_count else "queued"

    sql = """
    UPDATE retry_queue
    SET retry_count = CASE
            WHEN retry_count + 1 > max_retry_count THEN max_retry_count
            ELSE retry_count + 1
        END,
        last_error = ?,
        retry_status = CASE
            WHEN retry_count + 1 >= max_retry_count THEN 'give_up'
            ELSE 'queued'
        END,
        next_retry_at = CASE
            WHEN retry_count + 1 >= max_retry_count THEN NULL
            ELSE ?
        END,
        updated_at = ?
    WHERE slug = ?
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql, (error_message, next_retry_at, _utc_now(), (slug or "").strip()))
        connection.commit()
    _audit_retry_event(
        level=logging.INFO,
        event_name="increment_retry_count",
        item_id=slug,
        current_state=current_status,
        next_state=next_state,
        retry_count=next_count,
        max_retry_count=current_max_retry_count,
        reason="error_retry_scheduled",
        event_id=event_id,
    )


def mark_give_up(slug: str, error_message: str, db_path: Path = DB_PATH, event_id: str | None = None) -> None:
    create_tables(db_path)
    current = get_queue_item_by_slug(slug, db_path=db_path)
    if not current:
        _audit_retry_event(
            level=logging.WARNING,
            event_name="validate_transition_rejected",
            item_id=slug,
            current_state="missing",
            next_state="give_up",
            retry_count=0,
            max_retry_count=0,
            reason="slug_not_found",
            event_id=event_id,
        )
        return
    current_state = str(current.get("retry_status", "")).strip().lower()
    retry_count = _normalize_retry_count(current.get("retry_count", 0))
    max_retry_count = _normalize_max_retry_count(current.get("max_retry_count", 0))
    if not validate_transition(
        current_state,
        "give_up",
        item_id=slug,
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        event_id=event_id,
    ):
        return
    sql = """
    UPDATE retry_queue
    SET retry_status = 'give_up',
        last_error = ?,
        updated_at = ?
    WHERE slug = ?
    """
    with _get_connection(db_path) as connection:
        connection.execute(sql, (error_message, _utc_now(), (slug or "").strip()))
        connection.commit()
    _audit_retry_event(
        level=logging.ERROR,
        event_name="mark_give_up",
        item_id=slug,
        current_state=current_state,
        next_state="give_up",
        retry_count=retry_count,
        max_retry_count=max_retry_count,
        reason="manual_or_limit_reached",
        event_id=event_id,
    )


def list_queue_items(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    create_tables(db_path)
    sql = """
    SELECT id, slug, work_id, keyword, article_type, title,
           last_error, retry_count, max_retry_count, retry_status,
           next_retry_at, created_at, updated_at
    FROM retry_queue
    ORDER BY updated_at DESC
    """
    with _get_connection(db_path) as connection:
        rows = connection.execute(sql).fetchall()

    return [{key: row[key] for key in row.keys()} for row in rows]


def build_retry_record(
    *,
    slug: str,
    work_id: str,
    keyword: str,
    article_type: str,
    title: str,
    last_error: str,
    retry_count: int = 0,
    max_retry_count: int = 3,
    retry_status: str = "queued",
    next_retry_at: str | None = None,
) -> RetryQueueRecord:
    now = _utc_now()
    normalized_retry_count = _normalize_retry_count(retry_count)
    normalized_max_retry_count = _normalize_max_retry_count(max_retry_count)
    if normalized_retry_count > normalized_max_retry_count:
        normalized_retry_count = normalized_max_retry_count

    return RetryQueueRecord(
        slug=slug.strip(),
        work_id=work_id.strip(),
        keyword=keyword.strip(),
        article_type=article_type.strip(),
        title=title.strip(),
        last_error=last_error.strip(),
        retry_count=normalized_retry_count,
        max_retry_count=normalized_max_retry_count,
        retry_status=retry_status,
        next_retry_at=next_retry_at,
        created_at=now,
        updated_at=now,
    )
