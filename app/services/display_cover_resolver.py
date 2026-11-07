from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    EbookItem,
    ImageRightsEvidence,
    StoreCoverPolicyAgreement,
)
from app.services.official_cover_automation_service import (
    RAKUTEN_KOBO_COVER_POLICY_VERSION,
    store_cover_policy_version,
)


SOURCE_PRIORITY = {
    "RAKUTEN_KOBO": 0,
    "DMM": 1,
    "AMAZON": 2,
}
SOURCE_TO_STORE = {
    "RAKUTEN_KOBO": "rakuten_kobo",
    "DMM": "dmm",
    "AMAZON": "amazon",
}
PERSISTED_SOURCE_MAP = {
    "RAKUTEN_KOBO_API": "RAKUTEN_KOBO",
    "DMM_AFFILIATE_API": "DMM",
    "AMAZON_PA_API": "AMAZON",
}


@dataclass(frozen=True)
class DisplayCoverCandidate:
    source: str
    image_url: str | None
    available: bool
    reason: str = ""


@dataclass(frozen=True)
class DisplayCover:
    display_cover_url: str | None
    display_cover_source: str
    display_cover_status: str
    display_cover_reason: str
    candidate_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "display_cover_url": self.display_cover_url,
            "display_cover_source": self.display_cover_source,
            "display_cover_status": self.display_cover_status,
            "display_cover_reason": self.display_cover_reason,
            "candidate_count": self.candidate_count,
        }


def valid_display_url(value: object) -> str | None:
    text = str(value or "").strip()
    if not text or len(text) > 4096:
        return None
    try:
        parsed = urlsplit(text)
        port = parsed.port
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 80, 443}
    ):
        return None
    return text


def resolve_display_cover_candidates(
    candidates: Iterable[DisplayCoverCandidate],
) -> DisplayCover:
    ordered = sorted(
        (
            candidate
            for candidate in candidates
            if candidate.source in SOURCE_PRIORITY
        ),
        key=lambda candidate: SOURCE_PRIORITY[candidate.source],
    )
    candidate_count = sum(
        valid_display_url(candidate.image_url) is not None
        for candidate in ordered
    )
    for candidate in ordered:
        image_url = valid_display_url(candidate.image_url)
        if candidate.available and image_url is not None:
            return DisplayCover(
                display_cover_url=image_url,
                display_cover_source=candidate.source,
                display_cover_status="AVAILABLE",
                display_cover_reason="",
                candidate_count=candidate_count,
            )
    if candidate_count:
        return DisplayCover(
            display_cover_url=None,
            display_cover_source="NONE",
            display_cover_status="PENDING",
            display_cover_reason="API確認待ち",
            candidate_count=candidate_count,
        )
    return DisplayCover(
        display_cover_url=None,
        display_cover_source="NONE",
        display_cover_status="MISSING",
        display_cover_reason="書影候補なし",
        candidate_count=0,
    )


def cover_error_result() -> DisplayCover:
    return DisplayCover(
        display_cover_url=None,
        display_cover_source="NONE",
        display_cover_status="ERROR",
        display_cover_reason="書影取得エラー",
        candidate_count=0,
    )


class DisplayCoverResolver:
    """Resolve display-only cover metadata without network access or writes."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def resolve(self, ebook_item_id: str) -> DisplayCover:
        try:
            item = self.session.scalar(
                select(EbookItem)
                .options(selectinload(EbookItem.offers))
                .where(EbookItem.id == str(ebook_item_id or "").strip())
            )
            if item is None:
                return DisplayCover(
                    None, "NONE", "MISSING", "書影候補なし", 0
                )
            return self.resolve_many((item,)).get(item.id, cover_error_result())
        except Exception:
            return cover_error_result()

    def resolve_many(
        self,
        items: Sequence[EbookItem],
    ) -> dict[str, DisplayCover]:
        if not items:
            return {}
        try:
            item_ids = tuple(str(item.id) for item in items)
            evidence_rows = list(
                self.session.scalars(
                    select(ImageRightsEvidence)
                    .where(ImageRightsEvidence.candidate_id.in_(item_ids))
                    .order_by(
                        ImageRightsEvidence.candidate_id,
                        ImageRightsEvidence.verified_at.desc(),
                        ImageRightsEvidence.created_at.desc(),
                        ImageRightsEvidence.id.desc(),
                    )
                )
            )
            latest_rights: dict[str, str] = {}
            for evidence in evidence_rows:
                latest_rights.setdefault(
                    evidence.candidate_id,
                    str(evidence.rights_status or "").upper(),
                )
            agreements = {
                str(row.store_name): row
                for row in self.session.scalars(
                    select(StoreCoverPolicyAgreement)
                )
            }
            policy = agreements.get("rakuten_kobo")
            kobo_policy_allowed = bool(
                policy
                and policy.agreed
                and policy.policy_version
                == RAKUTEN_KOBO_COVER_POLICY_VERSION
            )
            agreed_stores = frozenset(
                name
                for name, row in agreements.items()
                if row.agreed
                and row.policy_version == store_cover_policy_version(name)
            )
            return {
                item.id: self._resolve_loaded_item(
                    item,
                    rights_status=latest_rights.get(item.id),
                    kobo_policy_allowed=kobo_policy_allowed,
                    agreed_stores=agreed_stores,
                )
                for item in items
            }
        except Exception:
            return {item.id: cover_error_result() for item in items}

    @staticmethod
    def _resolve_loaded_item(
        item: EbookItem,
        *,
        rights_status: str | None,
        kobo_policy_allowed: bool,
        # Omitting this leaves every non-Kobo store unapproved.
        agreed_stores: frozenset[str] | None = None,
    ) -> DisplayCover:
        persisted_source = str(item.cover_source or "UNKNOWN").upper()

        # MANUAL_DISPLAY_COVER_V1
        # An explicit human URL registration is a separate display path.
        # Explicitly disallowed/unresolved rights evidence still fails closed.
        if persisted_source == "MANUAL":
            image_url = valid_display_url(item.cover_image_url)
            rights_allowed = rights_status not in {
                "VERIFIED_NOT_ALLOWED",
                "UNRESOLVED",
            }

            if (
                str(item.cover_status or "").upper() == "MANUAL_ALLOWED"
                and image_url is not None
                and rights_allowed
            ):
                return DisplayCover(
                    image_url,
                    "MANUAL",
                    "AVAILABLE",
                    "",
                    1,
                )

            if image_url is not None:
                return DisplayCover(
                    None,
                    "NONE",
                    "PENDING",
                    "手動確認待ち",
                    1,
                )

            return resolve_display_cover_candidates(())

        source = PERSISTED_SOURCE_MAP.get(persisted_source)
        if source is None:
            has_kobo_offer = any(
                str(offer.store_name or "").strip().casefold()
                == "rakuten_kobo"
                for offer in item.offers
            )
            if (
                str(item.cover_status or "").upper()
                == "HIDDEN_UNVERIFIED"
                and has_kobo_offer
            ):
                return DisplayCover(
                    None, "NONE", "PENDING", "API確認待ち", 0
                )
            if valid_display_url(item.cover_image_url):
                return DisplayCover(
                    None, "NONE", "PENDING", "API確認待ち", 1
                )
            return resolve_display_cover_candidates(())
        store_name = SOURCE_TO_STORE[source]
        matching_offers = [
            offer
            for offer in item.offers
            if str(offer.store_name or "").strip().casefold() == store_name
            and str(offer.store_item_id or "").strip()
            == str(item.cover_source_item_id or "").strip()
        ]
        destination = valid_display_url(item.cover_destination_url)
        rights_allowed = rights_status not in {
            "VERIFIED_NOT_ALLOWED",
            "UNRESOLVED",
        }
        current_policy_version = store_cover_policy_version(store_name)
        available = bool(
            str(item.cover_status or "").upper() == "AUTO_ALLOWED"
            and matching_offers
            and destination is not None
            and rights_allowed
            and (source != "RAKUTEN_KOBO" or kobo_policy_allowed)
            and (
                source == "RAKUTEN_KOBO"
                or store_name in (agreed_stores or frozenset())
            )
            and current_policy_version is not None
            and str(item.cover_policy_version or "") == current_policy_version
        )
        return resolve_display_cover_candidates(
            (
                DisplayCoverCandidate(
                    source=source,
                    image_url=item.cover_image_url,
                    available=available,
                    reason="" if available else "API確認待ち",
                ),
            )
        )