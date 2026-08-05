from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    SupplementImportCandidate,
    SupplementImportHistory,
    SupplementImportRun,
    SupplementParseHistory,
)
from app.db.repositories.ebook_repository import EbookRepository
from app.services.rakuten_comic_calendar_parser import (
    ParsedSupplementCandidate,
    normalize_text,
    parse_rakuten_comic_calendar_text,
)
from app.services.supplement_candidate_match_service import (
    SupplementCandidateMatchService,
    normalize_match_title,
)


SOURCE_TYPE = "RAKUTEN_BOOKS_COMIC_CALENDAR"
SOURCE_NAME = "rakuten_books_comic_calendar"
SOURCE_URL = "https://books.rakuten.co.jp/event/book/comic/calendar/"


class SupplementImportError(ValueError):
    pass


@dataclass(frozen=True)
class SupplementImportResult:
    import_run_id: str
    imported_ebook_item_ids: tuple[str, ...]
    duplicate_skipped_count: int
    idempotent: bool = False


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _candidate_key(candidate: ParsedSupplementCandidate) -> str:
    return _sha256(
        "\0".join(
            (
                normalize_match_title(candidate.title),
                str(candidate.volume_label or ""),
                candidate.release_date.isoformat(),
                normalize_match_title(candidate.publisher_name),
                normalize_match_title(candidate.author_name),
            )
        )
    )


class SupplementImportService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.matcher = SupplementCandidateMatchService(session)
        self.ebooks = EbookRepository(session)

    def parse_text(
        self,
        *,
        raw_text: str,
        target_release_date: date,
        changed_by: str,
    ) -> SupplementImportRun:
        raw_text_hash = _sha256(raw_text)
        existing = self.session.scalar(
            select(SupplementImportRun).where(
                SupplementImportRun.source_type == SOURCE_TYPE,
                SupplementImportRun.target_release_date == target_release_date,
                SupplementImportRun.raw_text_hash == raw_text_hash,
            )
        )
        if existing is not None:
            return existing

        parsed_candidates = parse_rakuten_comic_calendar_text(
            raw_text, target_release_date=target_release_date
        )
        run = SupplementImportRun(
            source_type=SOURCE_TYPE,
            source_url=SOURCE_URL,
            target_release_date=target_release_date,
            raw_text_hash=raw_text_hash,
            candidate_count=len(parsed_candidates),
            status="PARSED",
            created_by=changed_by,
        )
        self.session.add(run)
        self.session.flush()

        duplicate_count = 0
        unparsed_count = 0
        for parsed in parsed_candidates:
            match = self.matcher.match(
                title=parsed.title,
                volume_label=parsed.volume_label,
                release_date=parsed.release_date,
                publisher_name=parsed.publisher_name,
            )
            warnings = tuple(dict.fromkeys(parsed.parser_warnings + match.warnings))
            if match.status in {"EXACT_DUPLICATE", "POSSIBLE_DUPLICATE"}:
                duplicate_count += 1
            if parsed.parser_confidence == "UNPARSED":
                unparsed_count += 1
            candidate = SupplementImportCandidate(
                import_run_id=run.id,
                candidate_key=_candidate_key(parsed),
                normalized_title=normalize_match_title(parsed.title),
                title=parsed.title,
                volume_label=parsed.volume_label,
                release_date=parsed.release_date,
                publisher_name=parsed.publisher_name,
                author_name=parsed.author_name,
                imprint_name=parsed.imprint_name,
                raw_text=parsed.raw_text,
                parser_confidence=parsed.parser_confidence,
                parser_warnings=json.dumps(warnings, ensure_ascii=False),
                match_status=match.status,
                matched_ebook_item_id=match.matched_ebook_item_id,
                selected=(
                    parsed.parser_confidence == "HIGH"
                    and match.status == "NEW_CANDIDATE"
                ),
                import_status="PENDING",
            )
            self.session.add(candidate)

        self.session.add(
            SupplementParseHistory(
                operation="SUPPLEMENT_TEXT_PARSE",
                import_run_id=run.id,
                source_type=SOURCE_TYPE,
                target_release_date=target_release_date,
                raw_text_hash=raw_text_hash,
                parsed_count=len(parsed_candidates) - unparsed_count,
                unparsed_count=unparsed_count,
                duplicate_count=duplicate_count,
                success=True,
            )
        )
        self.session.flush()
        return run

    def list_candidates(self, import_run_id: str) -> tuple[SupplementImportCandidate, ...]:
        return tuple(
            self.session.scalars(
                select(SupplementImportCandidate)
                .where(SupplementImportCandidate.import_run_id == import_run_id)
                .order_by(SupplementImportCandidate.created_at, SupplementImportCandidate.id)
            )
        )

    def update_candidate(
        self,
        *,
        candidate_id: str,
        title: str,
        volume_label: str | None,
        release_date: date,
        publisher_name: str | None,
        author_name: str | None,
        imprint_name: str | None,
    ) -> SupplementImportCandidate:
        candidate = self.session.get(SupplementImportCandidate, candidate_id)
        if candidate is None:
            raise SupplementImportError("CANDIDATE_NOT_FOUND")
        title = normalize_text(title)
        if not title:
            raise SupplementImportError("TITLE_MISSING")
        match = self.matcher.match(
            title=title,
            volume_label=volume_label,
            release_date=release_date,
            publisher_name=publisher_name,
        )
        parsed = ParsedSupplementCandidate(
            title=title,
            volume_label=normalize_text(volume_label or "") or None,
            release_date=release_date,
            publisher_name=normalize_text(publisher_name or "") or None,
            author_name=normalize_text(author_name or "") or None,
            imprint_name=normalize_text(imprint_name or "") or None,
            raw_text=candidate.raw_text,
            parser_confidence="HIGH",
            parser_warnings=(),
        )
        candidate.candidate_key = _candidate_key(parsed)
        candidate.normalized_title = normalize_match_title(title)
        candidate.title = parsed.title
        candidate.volume_label = parsed.volume_label
        candidate.release_date = release_date
        candidate.publisher_name = parsed.publisher_name
        candidate.author_name = parsed.author_name
        candidate.imprint_name = parsed.imprint_name
        candidate.parser_confidence = "HIGH"
        candidate.parser_warnings = json.dumps(match.warnings, ensure_ascii=False)
        candidate.match_status = match.status
        candidate.matched_ebook_item_id = match.matched_ebook_item_id
        if match.status != "NEW_CANDIDATE":
            candidate.selected = False
        self.session.flush()
        return candidate

    def set_selected(
        self, *, candidate_id: str, selected: bool
    ) -> SupplementImportCandidate:
        candidate = self.session.get(SupplementImportCandidate, candidate_id)
        if candidate is None:
            raise SupplementImportError("CANDIDATE_NOT_FOUND")
        if selected and candidate.match_status != "NEW_CANDIDATE":
            raise SupplementImportError(candidate.match_status)
        if candidate.import_status == "IMPORTED":
            raise SupplementImportError("ALREADY_IMPORTED")
        candidate.selected = selected
        self.session.flush()
        return candidate

    def import_selected(
        self,
        *,
        import_run_id: str,
        changed_by: str,
    ) -> SupplementImportResult:
        run = self.session.get(SupplementImportRun, import_run_id)
        if run is None:
            raise SupplementImportError("IMPORT_RUN_NOT_FOUND")
        candidates = tuple(
            candidate
            for candidate in self.list_candidates(import_run_id)
            if candidate.selected
        )
        if not candidates:
            raise SupplementImportError("NO_CANDIDATES_SELECTED")

        if all(candidate.import_status == "IMPORTED" for candidate in candidates):
            return SupplementImportResult(
                import_run_id=run.id,
                imported_ebook_item_ids=tuple(
                    candidate.imported_ebook_item_id
                    for candidate in candidates
                    if candidate.imported_ebook_item_id
                ),
                duplicate_skipped_count=0,
                idempotent=True,
            )

        run.status = "IMPORTING"
        imported_ids: list[str] = []
        for candidate in candidates:
            if candidate.import_status == "IMPORTED":
                if candidate.imported_ebook_item_id:
                    imported_ids.append(candidate.imported_ebook_item_id)
                continue
            match = self.matcher.match(
                title=candidate.title,
                volume_label=candidate.volume_label,
                release_date=candidate.release_date,
                publisher_name=candidate.publisher_name,
            )
            if match.status != "NEW_CANDIDATE":
                raise SupplementImportError(match.status)
            item = self.ebooks.create(
                source_name=SOURCE_NAME,
                source_item_id=candidate.id,
                title=candidate.title,
                normalized_title=candidate.normalized_title,
                volume_label=candidate.volume_label,
                author_name=candidate.author_name,
                publisher_name=candidate.publisher_name,
                series_name=candidate.imprint_name,
                release_date=candidate.release_date,
                item_type="tankobon",
            )
            item.source_discovery = SOURCE_TYPE
            item.source_url = SOURCE_URL
            item.workflow_status = "NEW"
            item.review_status = "NOT_REVIEWED"
            item.wordpress_status = "NOT_CREATED"
            item.is_excluded = False
            candidate.import_status = "IMPORTED"
            candidate.imported_ebook_item_id = item.id
            imported_ids.append(item.id)

        run.selected_count = len(candidates)
        run.imported_count = len(imported_ids)
        run.status = "IMPORTED"
        self.session.add(
            SupplementImportHistory(
                operation="SUPPLEMENT_ITEMS_IMPORT",
                import_run_id=run.id,
                selected_candidate_ids=json.dumps(
                    [candidate.id for candidate in candidates]
                ),
                selected_count=len(candidates),
                imported_ebook_item_ids=json.dumps(imported_ids),
                imported_count=len(imported_ids),
                duplicate_skipped_count=0,
                changed_by=changed_by,
                success=True,
            )
        )
        self.session.flush()
        return SupplementImportResult(run.id, tuple(imported_ids), 0)
