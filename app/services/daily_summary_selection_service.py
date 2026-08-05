from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import DailySummarySelection, EbookItem
from app.db.repositories.daily_summary_selection_repository import (
    DailySummarySelectionRepository,
)


AUTO_INCLUDED = "AUTO_INCLUDED"
HUMAN_INCLUDED = "HUMAN_INCLUDED"
HUMAN_EXCLUDED = "HUMAN_EXCLUDED"
HUMAN_STATES = frozenset({HUMAN_INCLUDED, HUMAN_EXCLUDED})


class DailySummarySelectionError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SelectionUpdateResult:
    ebook_item_id: str
    summary_date: date
    before_state: str | None
    after_state: str | None
    changed: bool


def is_auto_inclusion_candidate(item: EbookItem) -> bool:
    return bool(
        item.release_date is not None
        and not item.is_excluded
        and item.workflow_status == "READY"
        and item.review_status == "APPROVED"
        and item.wordpress_status == "PUBLISHED"
        and str(item.wordpress_post_id or "").strip()
    )


class DailySummarySelectionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DailySummarySelectionRepository(session)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    def set_human_selection(
        self,
        *,
        ebook_item_id: str,
        summary_date: date,
        included: bool,
        selected_by: str,
    ) -> SelectionUpdateResult:
        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            raise DailySummarySelectionError("item_not_found", "ebook item not found")
        if item.release_date != summary_date:
            raise DailySummarySelectionError(
                "summary_date_mismatch", "summary date must match release date"
            )
        normalized_actor = str(selected_by or "").strip()
        if not normalized_actor:
            raise DailySummarySelectionError("invalid_actor", "selected_by is required")

        desired = HUMAN_INCLUDED if included else HUMAN_EXCLUDED
        selection = self.repository.get(
            ebook_item_id=ebook_item_id, summary_date=summary_date
        )
        before = selection.inclusion_state if selection else None
        if selection is None:
            selection = DailySummarySelection(
                ebook_item_id=ebook_item_id,
                summary_date=summary_date,
                inclusion_state=desired,
                selection_source="HUMAN",
                selected_by=normalized_actor,
            )
            self.session.add(selection)
        else:
            selection.inclusion_state = desired
            selection.selection_source = "HUMAN"
            selection.selected_by = normalized_actor
            selection.selected_at = self._now()
        self.repository.add_history(
            ebook_item_id=ebook_item_id,
            summary_date=summary_date,
            before_state=before,
            after_state=desired,
            changed_by=normalized_actor,
        )
        self.session.flush()
        return SelectionUpdateResult(
            ebook_item_id, summary_date, before, desired, before != desired
        )

    def sync_auto_candidates(
        self, *, summary_date: date, selected_by: str = "daily_summary_auto"
    ) -> list[SelectionUpdateResult]:
        results: list[SelectionUpdateResult] = []
        existing = {
            selection.ebook_item_id: selection
            for selection in self.repository.list_for_date(summary_date)
        }
        items = self.repository.list_items_for_date(summary_date)
        eligible_ids = {item.id for item in items if is_auto_inclusion_candidate(item)}

        for item in items:
            selection = existing.get(item.id)
            if selection is not None and selection.inclusion_state in HUMAN_STATES:
                continue
            if item.id in eligible_ids and selection is None:
                selection = DailySummarySelection(
                    ebook_item_id=item.id,
                    summary_date=summary_date,
                    inclusion_state=AUTO_INCLUDED,
                    selection_source="AUTO",
                    selected_by=selected_by,
                )
                self.session.add(selection)
                self.repository.add_history(
                    ebook_item_id=item.id,
                    summary_date=summary_date,
                    before_state=None,
                    after_state=AUTO_INCLUDED,
                    changed_by=selected_by,
                )
                results.append(
                    SelectionUpdateResult(
                        item.id, summary_date, None, AUTO_INCLUDED, True
                    )
                )
            elif item.id not in eligible_ids and selection is not None:
                self.session.delete(selection)
                self.repository.add_history(
                    ebook_item_id=item.id,
                    summary_date=summary_date,
                    before_state=AUTO_INCLUDED,
                    after_state=None,
                    changed_by=selected_by,
                )
                results.append(
                    SelectionUpdateResult(
                        item.id, summary_date, AUTO_INCLUDED, None, True
                    )
                )
        self.session.flush()
        return results

    def set_all_excluded(
        self, *, summary_date: date, selected_by: str
    ) -> list[SelectionUpdateResult]:
        return [
            self.set_human_selection(
                ebook_item_id=item.id,
                summary_date=summary_date,
                included=False,
                selected_by=selected_by,
            )
            for item in self.repository.list_items_for_date(summary_date)
        ]

    def reset_to_auto(
        self, *, summary_date: date, selected_by: str
    ) -> list[SelectionUpdateResult]:
        results: list[SelectionUpdateResult] = []
        for selection in self.repository.list_for_date(summary_date):
            before = selection.inclusion_state
            self.session.delete(selection)
            self.repository.add_history(
                ebook_item_id=selection.ebook_item_id,
                summary_date=summary_date,
                before_state=before,
                after_state=None,
                changed_by=selected_by,
            )
            results.append(
                SelectionUpdateResult(
                    selection.ebook_item_id, summary_date, before, None, True
                )
            )
        self.session.flush()
        results.extend(
            self.sync_auto_candidates(
                summary_date=summary_date, selected_by="daily_summary_auto"
            )
        )
        return results