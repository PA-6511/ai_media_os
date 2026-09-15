from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

XNR_EXECUTION_CONTEXT = "XNR_ROUNDUP_WORDPRESS_DRAFT"
PUBLIC_SCHEMA_VERSION = "1.0"
MAX_SOURCE_AGE = timedelta(hours=24)
MAX_CLOCK_SKEW = timedelta(minutes=5)
JST = ZoneInfo("Asia/Tokyo")
_DIGEST_PATTERN = re.compile(r"[0-9a-f]{64}")


class XnrRoundupMetadataGateError(RuntimeError):
    """Structured fail-closed error for the XNR WordPress boundary."""

    def __init__(
        self,
        code: str,
        *,
        blocking_reasons: Sequence[str] = (),
        candidate_id: str | None = None,
        detail: str = "",
    ) -> None:
        self.code = str(code or "XNR_METADATA_GATE_UNAVAILABLE")
        self.blocking_reasons = tuple(
            str(reason) for reason in blocking_reasons if str(reason).strip()
        )
        self.candidate_id = str(candidate_id or "").strip() or None
        self.detail = str(detail or "").strip()
        super().__init__(self.code)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "BLOCKED",
            "code": self.code,
            "candidate_id": self.candidate_id,
            "blocking_reasons": list(self.blocking_reasons),
            "detail": self.detail,
            "wordpress_write_authorized": False,
        }


@dataclass(frozen=True)
class XnrRoundupSelection:
    candidate_ids: tuple[str, ...]
    candidate_digests: Mapping[str, str]
    source_digest: str
    item_count: int
    target_date: str
    generated_at: str


@dataclass(frozen=True)
class XnrRoundupAuthorization:
    candidate_digests: Mapping[str, str]
    source_digest: str
    item_count: int
    target_date: str
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "execution_context": XNR_EXECUTION_CONTEXT,
            "candidate_ids": list(self.candidate_digests),
            "candidate_digests": dict(self.candidate_digests),
            "source_digest": self.source_digest,
            "item_count": self.item_count,
            "target_date": self.target_date,
            "generated_at": self.generated_at,
            "historical_evidence_authorizes": False,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "XnrRoundupAuthorization":
        if value.get("schema_version") != "1.0":
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        if value.get("execution_context") != XNR_EXECUTION_CONTEXT:
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        raw_digests = value.get("candidate_digests")
        raw_ids = value.get("candidate_ids")
        if not isinstance(raw_digests, Mapping) or not isinstance(raw_ids, list):
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        digests = {str(key): str(digest) for key, digest in raw_digests.items()}
        candidate_ids = [str(candidate_id) for candidate_id in raw_ids]
        if candidate_ids != list(digests) or not candidate_ids:
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        if any(not _DIGEST_PATTERN.fullmatch(digest) for digest in digests.values()):
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        source_digest = str(value.get("source_digest") or "")
        if not _DIGEST_PATTERN.fullmatch(source_digest):
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        try:
            item_count = int(value.get("item_count"))
        except (TypeError, ValueError) as exc:
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION") from exc
        if item_count != len(candidate_ids):
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        target_date = str(value.get("target_date") or "")
        generated_at = str(value.get("generated_at") or "")
        if not target_date or not generated_at:
            raise XnrRoundupMetadataGateError("MALFORMED_AUTHORIZATION")
        return cls(
            candidate_digests=digests,
            source_digest=source_digest,
            item_count=item_count,
            target_date=target_date,
            generated_at=generated_at,
        )


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _valid_public_url(value: Any) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc)


def select_roundup_candidates(
    payload: Mapping[str, Any],
    *,
    target_date: str,
    max_items: int,
    now: datetime | None = None,
) -> XnrRoundupSelection:
    if payload.get("schema_version") != PUBLIC_SCHEMA_VERSION:
        raise XnrRoundupMetadataGateError("INVALID_PUBLIC_SCHEMA")
    if max_items < 1 or max_items > 200:
        raise XnrRoundupMetadataGateError("INVALID_MAX_ITEMS")
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise XnrRoundupMetadataGateError("INVALID_TARGET_DATE") from exc
    generated_at = str(payload.get("generated_at") or "").strip()
    try:
        generated = datetime.fromisoformat(generated_at)
    except ValueError as exc:
        raise XnrRoundupMetadataGateError("INVALID_GENERATED_AT") from exc
    if generated.tzinfo is None:
        raise XnrRoundupMetadataGateError("INVALID_GENERATED_AT")
    generated_jst = generated.astimezone(JST)
    current_jst = (now or datetime.now(JST)).astimezone(JST)
    if (
        generated_jst.date() != target
        or generated_jst > current_jst + MAX_CLOCK_SKEW
        or current_jst - generated_jst > MAX_SOURCE_AGE
    ):
        raise XnrRoundupMetadataGateError("STALE_PUBLIC_SOURCE")
    releases = payload.get("new_releases")
    if not isinstance(releases, list):
        raise XnrRoundupMetadataGateError(
            "MALFORMED_PUBLIC_SOURCE",
            detail="new_releases must be a list",
        )
    all_candidate_ids: list[str] = []
    for item in releases:
        if not isinstance(item, Mapping):
            raise XnrRoundupMetadataGateError(
                "MALFORMED_PUBLIC_SOURCE",
                detail="every new_releases entry must be an object",
            )
        candidate_id = str(item.get("item_id") or "").strip()
        if not candidate_id:
            raise XnrRoundupMetadataGateError(
                "CANDIDATE_IDENTITY_UNRESOLVED",
                detail="public item has no item_id",
            )
        all_candidate_ids.append(candidate_id)
    if len(all_candidate_ids) != len(set(all_candidate_ids)):
        raise XnrRoundupMetadataGateError("CANDIDATE_IDENTITY_AMBIGUOUS")
    target_items = [
        item
        for item in releases
        if isinstance(item, Mapping)
        and str(item.get("release_date") or "") == target_date
    ]
    if not target_items:
        raise XnrRoundupMetadataGateError("NO_TARGET_ITEMS")
    if len(target_items) > max_items:
        raise XnrRoundupMetadataGateError(
            "SOURCE_ITEM_LIMIT_EXCEEDED",
            detail=f"target item count exceeds {max_items}",
        )

    candidate_ids: list[str] = []
    for item in target_items:
        candidate_id = str(item.get("item_id") or "").strip()
        if item.get("approval_state") != "APPROVED":
            raise XnrRoundupMetadataGateError(
                "SOURCE_ITEM_NOT_APPROVED",
                candidate_id=candidate_id,
            )
        if not str(item.get("title") or "").strip():
            raise XnrRoundupMetadataGateError(
                "MALFORMED_PUBLIC_ITEM",
                candidate_id=candidate_id,
                detail="title is required",
            )
        stores = item.get("stores")
        if not isinstance(stores, Mapping):
            raise XnrRoundupMetadataGateError(
                "MALFORMED_PUBLIC_ITEM",
                candidate_id=candidate_id,
                detail="stores must be an object",
            )
        usable_store_urls = [
            store.get("url")
            for store in stores.values()
            if isinstance(store, Mapping) and _valid_public_url(store.get("url"))
        ]
        if not usable_store_urls:
            raise XnrRoundupMetadataGateError(
                "MALFORMED_PUBLIC_ITEM",
                candidate_id=candidate_id,
                detail="at least one HTTPS store URL is required",
            )
        candidate_ids.append(candidate_id)
    selected = target_items
    selected_ids = tuple(str(item["item_id"]).strip() for item in selected)
    candidate_digests = {
        candidate_id: _digest(item)
        for candidate_id, item in zip(selected_ids, selected)
    }
    return XnrRoundupSelection(
        candidate_ids=selected_ids,
        candidate_digests=candidate_digests,
        source_digest=_digest(payload),
        item_count=len(selected_ids),
        target_date=target_date,
        generated_at=generated_at,
    )


class XnrRoundupMetadataGate:
    """Gate for secondary use of an already safe-published public payload."""

    def authorize(
        self,
        selection: XnrRoundupSelection,
    ) -> XnrRoundupAuthorization:
        return XnrRoundupAuthorization(
            candidate_digests=dict(selection.candidate_digests),
            source_digest=selection.source_digest,
            item_count=selection.item_count,
            target_date=selection.target_date,
            generated_at=selection.generated_at,
        )

    def revalidate(
        self,
        selection: XnrRoundupSelection,
        authorization: XnrRoundupAuthorization,
    ) -> XnrRoundupAuthorization:
        if (
            selection.candidate_ids != tuple(authorization.candidate_digests)
            or dict(selection.candidate_digests)
            != dict(authorization.candidate_digests)
            or selection.source_digest != authorization.source_digest
            or selection.item_count != authorization.item_count
            or selection.target_date != authorization.target_date
            or selection.generated_at != authorization.generated_at
        ):
            raise XnrRoundupMetadataGateError(
                "STALE_ROUNDUP_SOURCE",
                blocking_reasons=("STALE_ROUNDUP_SOURCE",),
            )
        return authorization


def execute_guarded_wordpress_step(
    *,
    gate: XnrRoundupMetadataGate,
    selection_loader: Callable[[], XnrRoundupSelection],
    wordpress_step: Callable[[], Any],
) -> Any:
    """Evaluate current state twice before any WordPress callable can run."""
    authorization = gate.authorize(selection_loader())
    gate.revalidate(selection_loader(), authorization)
    return wordpress_step()
