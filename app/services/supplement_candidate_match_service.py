from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import EbookItem
from app.services.rakuten_comic_calendar_parser import split_title_volume_imprint


@dataclass(frozen=True)
class SupplementMatchResult:
    status: str
    matched_ebook_item_id: str | None
    warnings: tuple[str, ...] = ()


def normalize_match_title(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[\W_]+", "", normalized)


def normalize_volume(value: str | None) -> str | None:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    match = re.search(r"(\d+)", normalized)
    return str(int(match.group(1))) if match else None


def _catalog_identity(item: EbookItem) -> tuple[str, str | None]:
    parsed_title, parsed_volume, _, _ = split_title_volume_imprint(item.title)
    title = item.normalized_title or parsed_title
    volume = normalize_volume(item.volume_label) or normalize_volume(parsed_volume)
    return normalize_match_title(title), volume


class SupplementCandidateMatchService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def match(
        self,
        *,
        title: str,
        volume_label: str | None,
        release_date: date | None,
        publisher_name: str | None,
    ) -> SupplementMatchResult:
        normalized_title = normalize_match_title(title)
        if not normalized_title or release_date is None:
            return SupplementMatchResult("INVALID", None, ("REQUIRED_FIELD_MISSING",))

        normalized_volume = normalize_volume(volume_label)
        normalized_publisher = normalize_match_title(publisher_name)
        items = tuple(self.session.scalars(select(EbookItem)))
        possible: list[tuple[EbookItem, str]] = []

        for item in items:
            existing_title, existing_volume = _catalog_identity(item)
            if existing_title == normalized_title:
                if (
                    existing_volume == normalized_volume
                    and item.release_date == release_date
                ):
                    return SupplementMatchResult("EXACT_DUPLICATE", item.id)
                reason = "TITLE_MATCH_METADATA_DIFFERENT"
                if existing_volume is None:
                    reason = "EXISTING_VOLUME_MISSING"
                possible.append((item, reason))

        for item in items:
            existing_title, _ = _catalog_identity(item)
            if not existing_title:
                continue
            same_publisher = bool(normalized_publisher) and (
                normalize_match_title(item.publisher_name) == normalized_publisher
            )
            similarity = SequenceMatcher(
                None, normalized_title, existing_title
            ).ratio()
            if same_publisher and similarity >= 0.82:
                possible.append((item, "SIMILAR_TITLE_SAME_PUBLISHER"))

        if possible:
            matched_item, reason = possible[0]
            return SupplementMatchResult(
                "POSSIBLE_DUPLICATE", matched_item.id, (reason,)
            )
        return SupplementMatchResult("NEW_CANDIDATE", None)
