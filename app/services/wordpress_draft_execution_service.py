from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from app.services.new_release_wordpress_draft_lite import (
    NewReleaseWordPressDraftLiteError,
    create_new_release_wordpress_draft_lite,
    normalize_wordpress_store_offers,
)


CLAIMED = "CLAIMED"
EXTERNAL_CALL_STARTED = "EXTERNAL_CALL_STARTED"
FAILED_PRE_EXTERNAL = "FAILED_PRE_EXTERNAL"
OUTCOME_UNKNOWN = (
    "WORDPRESS_DRAFT_POST_OUTCOME_UNKNOWN_RECONCILIATION_REQUIRED"
)
RECONCILIATION_REQUIRED = (
    "WORDPRESS_DRAFT_CREATED_DB_RECONCILIATION_REQUIRED"
)
COMPLETED = "WORDPRESS_DRAFT_CREATED"

BLOCKING_STATUSES = {
    CLAIMED,
    EXTERNAL_CALL_STARTED,
    FAILED_PRE_EXTERNAL,
    OUTCOME_UNKNOWN,
    RECONCILIATION_REQUIRED,
    COMPLETED,
}


class WordPressDraftExecutionError(RuntimeError):
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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(name, default)
    return getattr(source, name, default)


def _required_text(value: Any, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise WordPressDraftExecutionError(
            "invalid_request",
            f"{field_name} is required",
        )
    return normalized


def _error_summary(exc: Exception) -> str:
    detail = str(exc).strip()
    if detail:
        return f"{type(exc).__name__}: {detail}"[:500]
    return type(exc).__name__


def _atomic_create_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise WordPressDraftExecutionError(
            "execution_claim_exists",
            "WordPress draft execution claim already exists",
        ) from exc

    try:
        os.write(descriptor, content)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    directory_descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def _atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        content = (
            json.dumps(
                value,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, content)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary_path, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            pass


class WordPressDraftExecutionStore:
    """Restart-safe one-shot claim and recovery evidence store."""

    def __init__(self, repository_root: Path | str) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.claim_directory = (
            self.repository_root
            / "exchange"
            / "locks"
            / "wordpress_draft_creation"
        )
        self.evidence_directory = (
            self.repository_root
            / "exchange"
            / "logs"
            / "wordpress_draft_creation"
        )

    @staticmethod
    def _item_key(ebook_item_id: str) -> str:
        normalized = _required_text(ebook_item_id, "ebook_item_id")
        return sha256(normalized.encode("utf-8")).hexdigest()

    def claim_path(self, ebook_item_id: str) -> Path:
        return self.claim_directory / f"{self._item_key(ebook_item_id)}.json"

    def evidence_path(self, execution_claim_id: str) -> Path:
        normalized = _required_text(
            execution_claim_id,
            "execution_claim_id",
        )
        try:
            canonical = str(uuid.UUID(normalized))
        except ValueError as exc:
            raise WordPressDraftExecutionError(
                "invalid_claim",
                "execution_claim_id is invalid",
            ) from exc
        return self.evidence_directory / f"{canonical}.json"

    def read_for_item(self, ebook_item_id: str) -> dict[str, Any] | None:
        path = self.claim_path(ebook_item_id)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return {
                "ebook_item_id": ebook_item_id,
                "status": "INCONSISTENT_EVIDENCE",
                "error": _error_summary(exc),
            }

        if not isinstance(value, dict):
            return {
                "ebook_item_id": ebook_item_id,
                "status": "INCONSISTENT_EVIDENCE",
                "error": "claim evidence must be a JSON object",
            }
        if value.get("ebook_item_id") != ebook_item_id:
            return {
                "ebook_item_id": ebook_item_id,
                "status": "INCONSISTENT_EVIDENCE",
                "error": "claim evidence item binding mismatch",
            }
        return value

    def acquire(
        self,
        *,
        ebook_item_id: str,
        source_item_id: str,
        approval_request_id: str,
    ) -> dict[str, Any]:
        existing = self.read_for_item(ebook_item_id)
        if existing is not None:
            raise WordPressDraftExecutionError(
                "execution_claim_exists",
                "WordPress draft execution is already claimed",
                evidence=existing,
            )

        now = _utc_now()
        value: dict[str, Any] = {
            "lock_type": "GUI_WORDPRESS_DRAFT_CREATION_EXECUTION_CLAIM",
            "execution_claim_id": str(uuid.uuid4()),
            "ebook_item_id": _required_text(
                ebook_item_id,
                "ebook_item_id",
            ),
            "source_item_id": _required_text(
                source_item_id,
                "source_item_id",
            ),
            "approval_request_id": _required_text(
                approval_request_id,
                "approval_request_id",
            ),
            "status": CLAIMED,
            "created_at": now,
            "updated_at": now,
            "external_post_attempted": False,
            "external_post_succeeded": False,
            "wordpress_post_id": None,
            "wordpress_status": None,
            "wordpress_url": None,
            "database_update_result": "NOT_STARTED",
            "error": None,
            "reexecution_allowed": False,
        }
        _atomic_create_json(self.claim_path(ebook_item_id), value)
        _atomic_write_json(
            self.evidence_path(value["execution_claim_id"]),
            value,
        )
        return value

    def update(
        self,
        claim: Mapping[str, Any],
        **changes: Any,
    ) -> dict[str, Any]:
        ebook_item_id = _required_text(
            claim.get("ebook_item_id"),
            "claim.ebook_item_id",
        )
        execution_claim_id = _required_text(
            claim.get("execution_claim_id"),
            "claim.execution_claim_id",
        )
        current = self.read_for_item(ebook_item_id)
        if current is None:
            raise WordPressDraftExecutionError(
                "invalid_claim",
                "execution claim disappeared",
            )
        if current.get("execution_claim_id") != execution_claim_id:
            raise WordPressDraftExecutionError(
                "invalid_claim",
                "execution claim binding mismatch",
                evidence=current,
            )

        updated = {
            **current,
            **changes,
            "ebook_item_id": ebook_item_id,
            "execution_claim_id": execution_claim_id,
            "updated_at": _utc_now(),
            "reexecution_allowed": False,
        }
        _atomic_write_json(self.claim_path(ebook_item_id), updated)
        _atomic_write_json(
            self.evidence_path(execution_claim_id),
            updated,
        )
        return updated


def validate_approved_review_ready_request(
    approval_request: Any,
    *,
    ebook_item_id: str,
) -> None:
    _required_text(_value(approval_request, "id"), "approval_request.id")
    if _value(approval_request, "ebook_item_id") != ebook_item_id:
        raise WordPressDraftExecutionError(
            "approval_item_mismatch",
            "approval request does not belong to the ebook item",
        )
    checks = (
        ("approval_type", "REVIEW_READY"),
        ("status", "APPROVED"),
        ("expected_current_status", "REVIEW"),
        ("requested_status", "READY"),
    )
    for field_name, expected in checks:
        if _value(approval_request, field_name) != expected:
            raise WordPressDraftExecutionError(
                "approval_not_eligible",
                f"approval request {field_name} must be {expected}",
            )
    if _value(approval_request, "decided_at") is None:
        raise WordPressDraftExecutionError(
            "approval_not_eligible",
            "approval request decided_at is required",
        )


def validate_wordpress_draft_preflight(
    *,
    ebook_item_id: str,
    item: Any,
    approval_request: Any,
    offers: Iterable[Any] | None = None,
    preferred_offer: Any | None = None,
    offer: Any | None = None,
) -> None:
    normalized_item_id = _required_text(ebook_item_id, "ebook_item_id")
    if _value(item, "id") != normalized_item_id:
        raise WordPressDraftExecutionError(
            "item_mismatch",
            "ebook item binding mismatch",
        )
    state_checks = (
        ("workflow_status", "READY"),
        ("review_status", "APPROVED"),
    )
    for field_name, expected in state_checks:
        if _value(item, field_name) != expected:
            raise WordPressDraftExecutionError(
                "invalid_state",
                f"{field_name} must be {expected}",
            )
    if bool(_value(item, "is_excluded", False)):
        raise WordPressDraftExecutionError(
            "excluded_item",
            "excluded ebook item cannot create a WordPress draft",
        )
    if bool(_value(item, "publish_ready", False)):
        raise WordPressDraftExecutionError(
            "invalid_state",
            "publish_ready must remain false",
        )
    if str(_value(item, "wordpress_post_id") or "").strip():
        raise WordPressDraftExecutionError(
            "already_created",
            "WordPress draft already exists",
        )
    wordpress_status = str(
        _value(item, "wordpress_status", "NOT_CREATED") or "NOT_CREATED"
    ).upper()
    if wordpress_status not in {"", "NOT_CREATED"}:
        raise WordPressDraftExecutionError(
            "already_created",
            "wordpress_status must be NOT_CREATED",
        )
    raw_offers = list(offers or ([] if offer is None else [offer]))
    try:
        normalized_offers = normalize_wordpress_store_offers(raw_offers)
    except NewReleaseWordPressDraftLiteError as exc:
        raise WordPressDraftExecutionError(
            "invalid_offer",
            str(exc),
        ) from exc
    representative = preferred_offer or offer or normalized_offers[0]
    representative_identity = (
        str(_value(representative, "store_name") or "").strip().lower(),
        str(_value(representative, "store_item_id") or "").strip(),
    )
    if representative_identity not in {
        (candidate.store_name, candidate.store_item_id)
        for candidate in normalized_offers
    }:
        raise WordPressDraftExecutionError(
            "invalid_offer",
            "preferred_offer must belong to the eligible offer set",
        )
    validate_approved_review_ready_request(
        approval_request,
        ebook_item_id=normalized_item_id,
    )


def execute_approved_wordpress_draft_once(
    *,
    ebook_item_id: str,
    item: Any,
    approval_request: Any,
    wordpress_client: Any,
    state_repository: Any,
    commit: Callable[[], None],
    rollback: Callable[[], None],
    execution_store: WordPressDraftExecutionStore,
    offers: Iterable[Any] | None = None,
    preferred_offer: Any | None = None,
    offer: Any | None = None,
    cover_fetcher: Any = None,
    refresh_current_state: Callable[
        [], tuple[Any, ...]
    ] | None = None,
) -> Any:
    """Create one draft, persisting evidence before and after each boundary."""

    current_offers = list(offers or ([] if offer is None else [offer]))
    current_preferred_offer = preferred_offer or offer
    validate_wordpress_draft_preflight(
        ebook_item_id=ebook_item_id,
        item=item,
        approval_request=approval_request,
        offers=current_offers,
        preferred_offer=current_preferred_offer,
    )

    claim = execution_store.acquire(
        ebook_item_id=ebook_item_id,
        source_item_id=_required_text(
            _value(item, "source_item_id"),
            "item.source_item_id",
        ),
        approval_request_id=_required_text(
            _value(approval_request, "id"),
            "approval_request.id",
        ),
    )
    external_started = False
    external_response: Any | None = None

    if refresh_current_state is not None:
        try:
            refreshed = refresh_current_state()
            if len(refreshed) == 3:
                item, approval_request, refreshed_offer = refreshed
                current_offers = [refreshed_offer]
                current_preferred_offer = refreshed_offer
            elif len(refreshed) == 4:
                (
                    item,
                    approval_request,
                    refreshed_offers,
                    current_preferred_offer,
                ) = refreshed
                current_offers = list(refreshed_offers)
            else:
                raise WordPressDraftExecutionError(
                    "invalid_request",
                    "refresh_current_state returned an invalid result",
                )
            validate_wordpress_draft_preflight(
                ebook_item_id=ebook_item_id,
                item=item,
                approval_request=approval_request,
                offers=current_offers,
                preferred_offer=current_preferred_offer,
            )
            if claim.get("approval_request_id") != _value(
                approval_request,
                "id",
            ):
                raise WordPressDraftExecutionError(
                    "approval_item_mismatch",
                    "refreshed approval request does not match claim",
                )
            if claim.get("source_item_id") != _value(
                item,
                "source_item_id",
            ):
                raise WordPressDraftExecutionError(
                    "item_mismatch",
                    "refreshed source item does not match claim",
                )
        except Exception as exc:
            evidence = execution_store.update(
                claim,
                status=FAILED_PRE_EXTERNAL,
                database_update_result="NOT_STARTED",
                error=_error_summary(exc),
                failed_at=_utc_now(),
            )
            raise WordPressDraftExecutionError(
                "pre_external_failure",
                "current database state failed pre-external revalidation",
                evidence=evidence,
            ) from exc

    def before_external_create() -> None:
        nonlocal claim, external_started
        external_started = True
        claim = execution_store.update(
            claim,
            status=EXTERNAL_CALL_STARTED,
            external_post_attempted=True,
            external_post_started_at=_utc_now(),
        )

    def after_external_create(response: Any) -> None:
        nonlocal claim, external_response
        external_response = response
        claim = execution_store.update(
            claim,
            status=RECONCILIATION_REQUIRED,
            external_post_succeeded=True,
            external_post_succeeded_at=_utc_now(),
            wordpress_post_id=_value(response, "post_id"),
            wordpress_status=_value(response, "status"),
            wordpress_url=_value(response, "link"),
            database_update_result="PENDING",
        )

    service_arguments: dict[str, Any] = {
        "ebook_item_id": ebook_item_id,
        "item": item,
        "offers": current_offers,
        "preferred_offer": current_preferred_offer,
        "wordpress_client": wordpress_client,
        "state_repository": state_repository,
        "commit": commit,
        "rollback": rollback,
        "before_external_create": before_external_create,
        "after_external_create": after_external_create,
    }
    if cover_fetcher is not None:
        service_arguments["cover_fetcher"] = cover_fetcher

    try:
        result = create_new_release_wordpress_draft_lite(
            **service_arguments,
        )
    except Exception as exc:
        error = _error_summary(exc)
        if external_response is not None:
            evidence = execution_store.update(
                claim,
                status=RECONCILIATION_REQUIRED,
                database_update_result="FAILED",
                error=error,
                failed_at=_utc_now(),
            )
            raise WordPressDraftExecutionError(
                "reconciliation_required",
                RECONCILIATION_REQUIRED,
                evidence=evidence,
            ) from exc
        if external_started:
            evidence = execution_store.update(
                claim,
                status=OUTCOME_UNKNOWN,
                database_update_result="NOT_STARTED",
                error=error,
                failed_at=_utc_now(),
            )
            raise WordPressDraftExecutionError(
                "reconciliation_required",
                OUTCOME_UNKNOWN,
                evidence=evidence,
            ) from exc

        evidence = execution_store.update(
            claim,
            status=FAILED_PRE_EXTERNAL,
            database_update_result="NOT_STARTED",
            error=error,
            failed_at=_utc_now(),
        )
        raise WordPressDraftExecutionError(
            "pre_external_failure",
            "WordPress draft creation failed before external POST",
            evidence=evidence,
        ) from exc

    result_values = asdict(result) if is_dataclass(result) else {}
    evidence = execution_store.update(
        claim,
        status=COMPLETED,
        database_update_result="COMMITTED",
        database_updated_at=_utc_now(),
        image_status=result_values.get(
            "image_status",
            _value(result, "image_status"),
        ),
        image_media_id=result_values.get(
            "image_media_id",
            _value(result, "image_media_id"),
        ),
        image_media_url=result_values.get(
            "image_media_url",
            _value(result, "image_media_url"),
        ),
        image_error_summary=result_values.get(
            "image_error_summary",
            _value(result, "image_error_summary"),
        ),
        featured_media_set=bool(
            result_values.get(
                "featured_media_set",
                _value(result, "featured_media_set", False),
            )
        ),
        price_status=result_values.get(
            "price_status",
            _value(result, "price_status"),
        ),
        unified_price_yen=result_values.get(
            "unified_price_yen",
            _value(result, "unified_price_yen"),
        ),
        missing_price_stores=list(
            result_values.get(
                "missing_price_stores",
                _value(result, "missing_price_stores", ()),
            )
            or ()
        ),
        price_review_reasons=list(
            result_values.get(
                "price_review_reasons",
                _value(result, "price_review_reasons", ()),
            )
            or ()
        ),
        publish_executed=False,
        completed_at=_utc_now(),
        error=None,
    )
    if evidence.get("wordpress_post_id") != _value(
        result,
        "wordpress_post_id",
    ):
        raise WordPressDraftExecutionError(
            "evidence_mismatch",
            "WordPress result does not match execution evidence",
            evidence=evidence,
        )
    return result


def default_wordpress_draft_execution_store() -> WordPressDraftExecutionStore:
    return WordPressDraftExecutionStore(
        Path(__file__).resolve().parents[2]
    )
