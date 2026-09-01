from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.db.models.ebook import EbookItem
from app.db.repositories.store_offer_repository import StoreOfferRepository
from app.integrations.amazon_creators_api_client import AmazonCreatorsApiClient, AmazonCreatorsItem
from app.services.amazon_manual_link_service import AmazonManualLinkService


def _normalized(value: str | None) -> str:
    return re.sub(r"[^0-9a-zぁ-んァ-ン一-龥]", "", unicodedata.normalize("NFKC", value or "").lower())


def _volume(value: str | None) -> str | None:
    match = re.search(r"(?:第?\s*)?(\d+)(?:\s*(?:巻|巻目|話))?", unicodedata.normalize("NFKC", value or ""))
    return match.group(1) if match else None


@dataclass(frozen=True)
class KindleCandidateMatch:
    item: AmazonCreatorsItem
    score: int
    classification: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class KindleResolution:
    ebook_item_id: str
    status: str
    candidate_count: int
    asin: str | None = None
    product_url: str | None = None
    cover_url: str | None = None
    score: int = 0
    classification: str = "NO_MATCH"
    offer_id: str | None = None


class AmazonCreatorsKindleResolver:
    """Match Creators API candidates, then reuse the existing Amazon offer table."""

    def __init__(self, session: Session, client: AmazonCreatorsApiClient) -> None:
        self.session = session
        self.client = client
        self.offer_repository = StoreOfferRepository(session)
        self.link_service = AmazonManualLinkService()

    def resolve(self, *, ebook_item_id: str, execute: bool) -> KindleResolution:
        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            return KindleResolution(ebook_item_id, "ITEM_NOT_FOUND", 0)
        # The general Books index commonly returns the paper ISBN edition first.
        # Querying KindleStore keeps automated selection scoped to e-books; the
        # explicit format check in _match remains as a second protection.
        candidates = self.client.search_items(
            title=item.title,
            author=item.author_name,
            item_count=10,
            search_index="KindleStore",
        )
        matches = sorted((_match(item, candidate) for candidate in candidates), key=lambda value: value.score, reverse=True)
        selected = matches[0] if matches else None
        if selected is None:
            return KindleResolution(item.id, "NO_MATCH", 0)
        base = KindleResolution(item.id, selected.classification, len(candidates), selected.item.asin, selected.item.detail_page_url, selected.item.cover_url, selected.score, selected.classification)
        if not execute or selected.classification not in {"EXACT", "HIGH_CONFIDENCE"}:
            return base
        # Creators detail URLs may already contain tracking/query parameters.
        # Rebuild both URLs from the verified ASIN through the existing service
        # so URL-policy validation cannot reject an otherwise valid candidate.
        link = self.link_service.generate(asin=selected.item.asin, tracking_id=self.client.credentials.partner_tag)
        offer, _ = self.offer_repository.upsert_manual_offer(
            ebook_item_id=item.id,
            store_name="amazon",
            store_item_id=selected.item.asin,
            product_url=link.product_url,
            affiliate_url=link.affiliate_url,
            verification_method="CREATORS_API",
        )
        self.session.flush()
        return KindleResolution(item.id, "SAVED", len(candidates), selected.item.asin, link.product_url, selected.item.cover_url, selected.score, selected.classification, offer.id)


def _match(item: EbookItem, candidate: AmazonCreatorsItem) -> KindleCandidateMatch:
    score = 0
    reasons: list[str] = []
    item_isbn = re.sub(r"[^0-9X]", "", (item.isbn or "").upper())
    if item_isbn and item_isbn in {value.upper() for value in candidate.isbn_values}:
        score += 100
        reasons.append("ISBN_EXACT")
    if _normalized(item.title) == _normalized(candidate.title):
        score += 45
        reasons.append("TITLE_EXACT")
    item_volume = _volume(item.volume_label or item.title)
    candidate_volume = _volume(candidate.title)
    if item_volume and candidate_volume and item_volume == candidate_volume:
        score += 20
        reasons.append("VOLUME_EXACT")
    if _authors_match(item.author_name, candidate.authors):
        score += 25
        reasons.append("AUTHOR_EXACT")
    if item.publisher_name and _normalized(item.publisher_name) == _normalized(candidate.publisher):
        score += 10
        reasons.append("PUBLISHER_EXACT")
    classification = "EXACT" if score >= 100 else "HIGH_CONFIDENCE" if score >= 70 else "REVIEW_REQUIRED" if score >= 35 else "NO_MATCH"
    if classification in {"EXACT", "HIGH_CONFIDENCE"} and not candidate.is_kindle:
        classification = "REVIEW_REQUIRED"
        reasons.append("KINDLE_FORMAT_UNCONFIRMED")
    return KindleCandidateMatch(candidate, score, classification, tuple(reasons))


def _authors_match(item_authors: str | None, candidate_authors: tuple[str, ...]) -> bool:
    """Compare contributor names individually when a catalog field is multi-valued."""
    expected = {
        _normalized(part)
        for part in re.split(r"[|｜/,、]", item_authors or "")
        if _normalized(part)
    }
    observed = {_normalized(author) for author in candidate_authors if _normalized(author)}
    return bool(expected and observed and expected.intersection(observed))
