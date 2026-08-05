from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Mapping
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.models import EbookItem
from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
)
from app.integrations.wordpress_rest_client import WordPressCategory


TOKYO = ZoneInfo("Asia/Tokyo")
ACTIVE_DRAFT_EXECUTION_STATUSES = {"CLAIMED", "EXTERNAL_CALL_STARTED"}
DEFAULT_WORDPRESS_CATEGORY_ALLOWLIST = frozenset({"comic-new-release"})


class WordPressPostScheduleError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.evidence = dict(evidence or {})


@dataclass(frozen=True)
class WordPressPostScheduleResult:
    operation: str
    ebook_item_id: str
    wordpress_post_id: int
    previous_wordpress_status: str
    new_wordpress_status: str
    publish_at_local: str | None
    publish_at_utc: str | None
    previous_category_ids: tuple[int, ...] = ()
    requested_category_id: int | None = None
    confirmed_category_ids: tuple[int, ...] = ()
    category_name: str | None = None
    category_slug: str | None = None


@dataclass(frozen=True)
class WordPressRemoteStatusSyncResult:
    operation: str
    ebook_item_id: str
    wordpress_post_id: int
    previous_local_status: str
    remote_status: str
    new_local_status: str
    remote_date: str | None
    remote_date_gmt: str | None
    checked_at: str
    success: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _error_summary(exc: Exception) -> str:
    text = str(exc).strip()
    return (f"{type(exc).__name__}: {text}" if text else type(exc).__name__)[:500]


def _http_status(exc: Exception) -> int | None:
    current: BaseException | None = exc
    while current is not None:
        code = getattr(current, "code", None)
        if isinstance(code, int):
            return code
        current = current.__cause__
    return None


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(name)
    try:
        content = (
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8")
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, content)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


class WordPressPostScheduleExecutionStore:
    def __init__(self, repository_root: Path | str) -> None:
        root = Path(repository_root).resolve()
        self.claim_directory = root / "exchange/locks/wordpress_post_schedule"
        self.evidence_directory = root / "exchange/logs/wordpress_post_schedule"

    @staticmethod
    def _key(ebook_item_id: str) -> str:
        return sha256(ebook_item_id.encode("utf-8")).hexdigest()

    def claim_path(self, ebook_item_id: str) -> Path:
        return self.claim_directory / f"{self._key(ebook_item_id)}.json"

    def evidence_path(self, execution_id: str) -> Path:
        return self.evidence_directory / f"{execution_id}.json"

    def latest_success_path(self, ebook_item_id: str) -> Path:
        return self.evidence_directory / f"{self._key(ebook_item_id)}.latest.json"

    def acquire(
        self,
        *,
        ebook_item_id: str,
        wordpress_post_id: int,
        operation: str,
    ) -> dict[str, Any]:
        now = _iso(_utc_now())
        claim = {
            "execution_id": str(uuid.uuid4()),
            "ebook_item_id": ebook_item_id,
            "wordpress_post_id": wordpress_post_id,
            "operation": operation,
            "status": "CLAIMED",
            "requested_at": now,
            "completed": False,
        }
        path = self.claim_path(ebook_item_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (json.dumps(claim, ensure_ascii=False, indent=2) + "\n").encode(
            "utf-8"
        )
        try:
            descriptor = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
            )
        except FileExistsError as exc:
            raise WordPressPostScheduleError(
                "execution_claim_exists",
                "WordPress schedule operation is already in progress",
            ) from exc
        try:
            os.write(descriptor, content)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        _atomic_write(self.evidence_path(claim["execution_id"]), claim)
        return claim

    def update(self, claim: Mapping[str, Any], **changes: Any) -> dict[str, Any]:
        updated = {**claim, **changes}
        _atomic_write(self.claim_path(str(claim["ebook_item_id"])), updated)
        _atomic_write(self.evidence_path(str(claim["execution_id"])), updated)
        return updated

    def finish(
        self,
        claim: Mapping[str, Any],
        *,
        success: bool,
        **changes: Any,
    ) -> dict[str, Any]:
        completed = {
            **claim,
            **changes,
            "completed": success,
            "success": success,
            "completed_at": _iso(_utc_now()),
            "status": "COMPLETED" if success else "FAILED",
        }
        _atomic_write(
            self.evidence_path(str(claim["execution_id"])), completed
        )
        if success:
            _atomic_write(
                self.latest_success_path(str(claim["ebook_item_id"])),
                completed,
            )
        try:
            self.claim_path(str(claim["ebook_item_id"])).unlink()
        except FileNotFoundError:
            pass
        return completed

    def read_latest_success(self, ebook_item_id: str) -> dict[str, Any] | None:
        try:
            value = json.loads(
                self.latest_success_path(ebook_item_id).read_text(encoding="utf-8")
            )
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None

    def read_claim(self, ebook_item_id: str) -> dict[str, Any] | None:
        try:
            value = json.loads(
                self.claim_path(ebook_item_id).read_text(encoding="utf-8")
            )
        except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None


class WordPressPostScheduleService:
    def __init__(
        self,
        session: Session,
        *,
        wordpress_client: Any,
        execution_store: WordPressPostScheduleExecutionStore,
        draft_execution_store: Any | None = None,
        now: Callable[[], datetime] = _utc_now,
        category_allowlist: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.session = session
        self.wordpress_client = wordpress_client
        self.execution_store = execution_store
        self.draft_execution_store = draft_execution_store
        self.now = now
        self.category_allowlist = frozenset(
            category_allowlist
            if category_allowlist is not None
            else DEFAULT_WORDPRESS_CATEGORY_ALLOWLIST
        )

    def sync_remote_status(
        self,
        *,
        ebook_item_id: str,
        wordpress_post_id: int | str,
    ) -> WordPressRemoteStatusSyncResult:
        item, post_id = self._validate_item(
            ebook_item_id,
            wordpress_post_id,
            expected_status={"DRAFT", "SCHEDULED"},
        )
        claim = self.execution_store.acquire(
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            operation="SYNC_REMOTE_STATUS",
        )
        previous_local_status = item.wordpress_status
        checked_at = _iso(self.now())
        try:
            self._validate_draft_execution(item.id)
            remote = self.wordpress_client.get_post_state(post_id=post_id)
            if remote.post_id != post_id:
                raise WordPressPostScheduleError(
                    "post_item_mismatch",
                    "WordPress response returned a different post id",
                )
            status_mapping = {
                "draft": "DRAFT",
                "future": "SCHEDULED",
                "publish": "PUBLISHED",
            }
            new_local_status = status_mapping.get(remote.status)
            if new_local_status is None:
                raise WordPressPostScheduleError(
                    "remote_state_mismatch",
                    "WordPress status is not synchronizable",
                )
            WorkflowStateRepository(self.session).set_wordpress_status(
                item,
                new_local_status,
                changed_by="system:wordpress_remote_status_sync",
                note=(
                    "WordPress remote status confirmed: "
                    f"{remote.status}."
                ),
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            evidence = self.execution_store.finish(
                claim,
                success=False,
                operation="SYNC_REMOTE_STATUS",
                wordpress_post_id=post_id,
                previous_local_status=previous_local_status,
                remote_status=getattr(locals().get("remote", None), "status", None),
                new_local_status=previous_local_status,
                remote_date=getattr(locals().get("remote", None), "date", None),
                remote_date_gmt=getattr(locals().get("remote", None), "date_gmt", None),
                checked_at=checked_at,
                error_type=type(exc).__name__,
                http_status=_http_status(exc),
                wordpress_response_summary=_error_summary(exc),
            )
            if isinstance(exc, WordPressPostScheduleError):
                exc.evidence.update(evidence)
                raise
            raise WordPressPostScheduleError(
                str(getattr(exc, "code", "remote_unavailable")),
                str(exc),
                evidence=evidence,
            ) from exc

        result = WordPressRemoteStatusSyncResult(
            operation="SYNC_REMOTE_STATUS",
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            previous_local_status=previous_local_status,
            remote_status=remote.status,
            new_local_status=new_local_status,
            remote_date=remote.date,
            remote_date_gmt=remote.date_gmt,
            checked_at=checked_at,
            success=True,
        )
        self.execution_store.finish(claim, **asdict(result))
        return result

    def schedule_post(
        self,
        *,
        ebook_item_id: str,
        wordpress_post_id: int | str,
        publish_at_local: str,
        category_id: int | str | None = None,
    ) -> WordPressPostScheduleResult:
        return self._change_schedule(
            operation=("SCHEDULE_WITH_CATEGORY" if category_id is not None else "SCHEDULE"),
            ebook_item_id=ebook_item_id,
            wordpress_post_id=wordpress_post_id,
            publish_at_local=publish_at_local,
            expected_local_status="DRAFT",
            expected_remote_status="draft",
            category_id=category_id,
        )

    def reschedule_post(
        self,
        *,
        ebook_item_id: str,
        wordpress_post_id: int | str,
        publish_at_local: str,
        category_id: int | str | None = None,
    ) -> WordPressPostScheduleResult:
        return self._change_schedule(
            operation=("SCHEDULE_WITH_CATEGORY" if category_id is not None else "RESCHEDULE"),
            ebook_item_id=ebook_item_id,
            wordpress_post_id=wordpress_post_id,
            publish_at_local=publish_at_local,
            expected_local_status="SCHEDULED",
            expected_remote_status="future",
            category_id=category_id,
        )

    def update_category(
        self,
        *,
        ebook_item_id: str,
        wordpress_post_id: int | str,
        category_id: int | str,
    ) -> WordPressPostScheduleResult:
        item, post_id = self._validate_item(
            ebook_item_id,
            wordpress_post_id,
            expected_status={"DRAFT", "SCHEDULED"},
        )
        category = self._validate_category(category_id)
        claim = self.execution_store.acquire(
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            operation="CATEGORY_UPDATE",
        )
        try:
            self._validate_draft_execution(item.id)
            remote = self.wordpress_client.get_post_state(post_id=post_id)
            expected_remote = "draft" if item.wordpress_status == "DRAFT" else "future"
            if remote.status != expected_remote:
                raise WordPressPostScheduleError(
                    "remote_state_mismatch",
                    f"WordPress post status must be {expected_remote}",
                )
            previous_category_ids = tuple(remote.categories)
            response = self.wordpress_client.update_category(
                post_id=post_id,
                category_id=category.category_id,
            )
            if (
                response.status != expected_remote
                or category.category_id not in response.categories
            ):
                raise WordPressPostScheduleError(
                    "response_mismatch",
                    "WordPress did not confirm the requested category",
                )
        except Exception as exc:
            self.session.rollback()
            evidence = self.execution_store.finish(
                claim,
                success=False,
                previous_category_ids=list(locals().get("previous_category_ids", ())),
                requested_category_id=category.category_id,
                confirmed_category_ids=list(getattr(locals().get("response", None), "categories", ())),
                category_name=category.name,
                category_slug=category.slug,
                publish_at_local=None,
                publish_at_utc=None,
                error_type=type(exc).__name__,
                http_status=_http_status(exc),
                wordpress_response_summary=_error_summary(exc),
            )
            if isinstance(exc, WordPressPostScheduleError):
                exc.evidence.update(evidence)
                raise
            raise WordPressPostScheduleError(
                "category_update_failed", str(exc), evidence=evidence
            ) from exc
        result = WordPressPostScheduleResult(
            operation="CATEGORY_UPDATE",
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            previous_wordpress_status=item.wordpress_status,
            new_wordpress_status=item.wordpress_status,
            publish_at_local=None,
            publish_at_utc=None,
            previous_category_ids=previous_category_ids,
            requested_category_id=category.category_id,
            confirmed_category_ids=tuple(response.categories),
            category_name=category.name,
            category_slug=category.slug,
        )
        self.execution_store.finish(
            claim,
            success=True,
            **asdict(result),
            wordpress_response_summary={
                "id": post_id,
                "status": response.status,
                "categories": list(response.categories),
            },
        )
        return result

    def cancel_schedule(
        self,
        *,
        ebook_item_id: str,
        wordpress_post_id: int | str,
    ) -> WordPressPostScheduleResult:
        item, post_id = self._validate_item(
            ebook_item_id, wordpress_post_id, expected_status="SCHEDULED"
        )
        claim = self.execution_store.acquire(
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            operation="CANCEL_SCHEDULE",
        )
        previous = self.execution_store.read_latest_success(item.id) or {}
        try:
            self._validate_draft_execution(item.id)
            remote = self.wordpress_client.get_post_state(post_id=post_id)
            if remote.status != "future":
                raise WordPressPostScheduleError(
                    "remote_state_mismatch",
                    "WordPress post status must be future",
                )
            response = self.wordpress_client.cancel_schedule(post_id=post_id)
            if response.status != "draft":
                raise WordPressPostScheduleError(
                    "response_mismatch", "WordPress did not confirm draft status"
                )
            WorkflowStateRepository(self.session).set_wordpress_status(
                item,
                "DRAFT",
                changed_by="human:local_gui",
                note="WordPress schedule cancelled after remote confirmation.",
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            evidence = self.execution_store.finish(
                claim,
                success=False,
                error_type=type(exc).__name__,
                http_status=_http_status(exc),
                wordpress_response_summary=_error_summary(exc),
            )
            if isinstance(exc, WordPressPostScheduleError):
                exc.evidence.update(evidence)
                raise
            raise WordPressPostScheduleError(
                "schedule_failed", str(exc), evidence=evidence
            ) from exc
        result = WordPressPostScheduleResult(
            operation="CANCEL_SCHEDULE",
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            previous_wordpress_status="SCHEDULED",
            new_wordpress_status="DRAFT",
            publish_at_local=None,
            publish_at_utc=None,
        )
        self.execution_store.finish(
            claim,
            success=True,
            **asdict(result),
            previous_publish_at=previous.get("publish_at_local"),
        )
        return result

    def _change_schedule(
        self,
        *,
        operation: str,
        ebook_item_id: str,
        wordpress_post_id: int | str,
        publish_at_local: str,
        expected_local_status: str,
        expected_remote_status: str,
        category_id: int | str | None,
    ) -> WordPressPostScheduleResult:
        item, post_id = self._validate_item(
            ebook_item_id,
            wordpress_post_id,
            expected_status=expected_local_status,
        )
        category = self._validate_category(category_id) if category_id is not None else None
        local_datetime, utc_datetime = self._parse_publish_at(publish_at_local)
        claim = self.execution_store.acquire(
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            operation=operation,
        )
        previous = self.execution_store.read_latest_success(item.id) or {}
        local_text = local_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        utc_text = utc_datetime.strftime("%Y-%m-%dT%H:%M:%S")
        try:
            self._validate_draft_execution(item.id)
            remote = self.wordpress_client.get_post_state(post_id=post_id)
            if remote.status != expected_remote_status:
                raise WordPressPostScheduleError(
                    "remote_state_mismatch",
                    f"WordPress post status must be {expected_remote_status}",
                )
            previous_category_ids = tuple(remote.categories)
            schedule_arguments = {
                "post_id": post_id,
                "date": local_text,
                "date_gmt": utc_text,
            }
            if category is not None:
                schedule_arguments["category_id"] = category.category_id
            response = self.wordpress_client.schedule_post(
                **schedule_arguments,
            )
            if (
                response.status != "future"
                or response.date != local_text
                or response.date_gmt != utc_text
                or (
                    category is not None
                    and category.category_id not in response.categories
                )
            ):
                raise WordPressPostScheduleError(
                    "response_mismatch",
                    "WordPress schedule response did not match the request",
                )
            WorkflowStateRepository(self.session).set_wordpress_status(
                item,
                "SCHEDULED",
                changed_by="human:local_gui",
                note=f"WordPress {operation.lower()} confirmed for {local_text}+09:00.",
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            evidence = self.execution_store.finish(
                claim,
                success=False,
                publish_at_local=local_text,
                publish_at_utc=utc_text + "+00:00",
                previous_category_ids=list(locals().get("previous_category_ids", ())),
                requested_category_id=(category.category_id if category is not None else None),
                confirmed_category_ids=list(getattr(locals().get("response", None), "categories", ())),
                category_name=(category.name if category is not None else None),
                category_slug=(category.slug if category is not None else None),
                error_type=type(exc).__name__,
                http_status=_http_status(exc),
                wordpress_response_summary=_error_summary(exc),
            )
            if isinstance(exc, WordPressPostScheduleError):
                exc.evidence.update(evidence)
                raise
            raise WordPressPostScheduleError(
                "schedule_failed", str(exc), evidence=evidence
            ) from exc
        result = WordPressPostScheduleResult(
            operation=operation,
            ebook_item_id=item.id,
            wordpress_post_id=post_id,
            previous_wordpress_status=expected_local_status,
            new_wordpress_status="SCHEDULED",
            publish_at_local=local_text + "+09:00",
            publish_at_utc=utc_text + "+00:00",
            previous_category_ids=previous_category_ids,
            requested_category_id=(category.category_id if category is not None else None),
            confirmed_category_ids=tuple(response.categories),
            category_name=(category.name if category is not None else None),
            category_slug=(category.slug if category is not None else None),
        )
        self.execution_store.finish(
            claim,
            success=True,
            **asdict(result),
            old_publish_at=previous.get("publish_at_local"),
            new_publish_at=result.publish_at_local,
            wordpress_response_summary={
                "id": post_id,
                "status": response.status,
                "categories": list(response.categories),
                "date": response.date,
                "date_gmt": response.date_gmt,
            },
        )
        return result

    def _parse_publish_at(self, value: str) -> tuple[datetime, datetime]:
        text = str(value or "").strip()
        try:
            if len(text) != 16:
                raise ValueError
            local = datetime.strptime(text, "%Y-%m-%dT%H:%M").replace(
                tzinfo=TOKYO
            )
        except ValueError as exc:
            raise WordPressPostScheduleError(
                "invalid_publish_at", "publish_at must be a minute-precision datetime"
            ) from exc
        now = self.now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        if local.astimezone(timezone.utc) <= now.astimezone(timezone.utc) + timedelta(seconds=60):
            raise WordPressPostScheduleError(
                "publish_at_too_soon",
                "publish_at must be more than 60 seconds in the future",
            )
        return local, local.astimezone(timezone.utc)

    def _validate_item(
        self,
        ebook_item_id: str,
        wordpress_post_id: int | str,
        *,
        expected_status: str | set[str],
    ) -> tuple[EbookItem, int]:
        item_id = str(ebook_item_id or "").strip()
        try:
            post_id = int(wordpress_post_id)
        except (TypeError, ValueError) as exc:
            raise WordPressPostScheduleError(
                "invalid_request", "wordpress_post_id must be a positive integer"
            ) from exc
        if not item_id or post_id <= 0:
            raise WordPressPostScheduleError("invalid_request", "invalid item or post id")
        item = self.session.get(EbookItem, item_id)
        if item is None:
            raise WordPressPostScheduleError("item_not_found", "ebook item was not found")
        if str(item.wordpress_post_id or "") != str(post_id):
            raise WordPressPostScheduleError(
                "post_item_mismatch", "WordPress post does not belong to the ebook item"
            )
        if item.review_status != "APPROVED":
            raise WordPressPostScheduleError("not_approved", "review_status must be APPROVED")
        if item.workflow_status not in {"READY", "SCHEDULED"}:
            raise WordPressPostScheduleError(
                "invalid_state", "workflow_status does not permit scheduling"
            )
        allowed_statuses = {expected_status} if isinstance(expected_status, str) else expected_status
        if item.wordpress_status not in allowed_statuses:
            raise WordPressPostScheduleError(
            "invalid_state", "wordpress_status does not permit this operation"
            )
        if item.is_excluded:
            raise WordPressPostScheduleError("excluded_item", "excluded item cannot be scheduled")
        return item, post_id

    def _validate_category(self, category_id: int | str) -> WordPressCategory:
        try:
            normalized_id = int(category_id)
        except (TypeError, ValueError) as exc:
            raise WordPressPostScheduleError(
                "invalid_category", "category_id must be a positive integer"
            ) from exc
        if isinstance(category_id, bool) or normalized_id <= 0:
            raise WordPressPostScheduleError(
                "invalid_category", "category_id must be a positive integer"
            )
        categories = self.wordpress_client.list_categories(per_page=100)
        category = next(
            (value for value in categories if value.category_id == normalized_id),
            None,
        )
        if category is None:
            raise WordPressPostScheduleError(
                "category_not_found", "category_id does not exist in WordPress"
            )
        if category.slug not in self.category_allowlist:
            raise WordPressPostScheduleError(
                "category_not_allowed", "category is not allowed for this GUI"
            )
        return category

    def _validate_draft_execution(self, ebook_item_id: str) -> None:
        if self.draft_execution_store is None:
            return
        state = self.draft_execution_store.read_for_item(ebook_item_id)
        if state and state.get("status") in ACTIVE_DRAFT_EXECUTION_STATUSES:
            raise WordPressPostScheduleError(
                "draft_execution_in_progress",
                "WordPress draft execution is in progress",
            )


def default_wordpress_post_schedule_execution_store() -> WordPressPostScheduleExecutionStore:
    return WordPressPostScheduleExecutionStore(Path(__file__).resolve().parents[2])