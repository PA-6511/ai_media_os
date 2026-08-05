from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    DailySummaryRun,
    DailySummaryRunHistory,
    EbookItem,
    SupplementImportCandidate,
    SupplementImportRun,
    SupplementRegistrationCancellationHistory,
)
from app.db.repositories.ebook_repository import EbookRepository
from app.services.supplement_import_service import SOURCE_TYPE
from app.services.wordpress_draft_execution_service import WordPressDraftExecutionStore
from app.services.wordpress_post_schedule_service import (
    WordPressPostScheduleExecutionStore,
)


class SupplementImportCancellationError(ValueError):
    pass


@dataclass(frozen=True)
class SupplementCancellationPreview:
    ebook_item_id: str
    title: str
    candidate_id: str | None
    import_run_id: str | None
    source: str | None
    current_state: str | None
    resulting_state: str
    cancellable: bool
    block_reasons: tuple[str, ...]
    dependency_checks: dict[str, Any]


@dataclass(frozen=True)
class SupplementCancellationResult:
    code: str
    ebook_item_id: str
    candidate_id: str
    import_run_id: str
    idempotent: bool = False


class SupplementImportCancellationService:
    def __init__(self, session: Session, *, repository_root: Path | str) -> None:
        self.session = session
        self.repository_root = Path(repository_root).resolve()
        self.ebooks = EbookRepository(session)
        self.wordpress_draft_store = WordPressDraftExecutionStore(
            self.repository_root
        )
        self.wordpress_schedule_store = WordPressPostScheduleExecutionStore(
            self.repository_root
        )

    def _candidate_for_item(
        self, ebook_item_id: str
    ) -> SupplementImportCandidate | None:
        return self.session.scalar(
            select(SupplementImportCandidate)
            .where(
                SupplementImportCandidate.imported_ebook_item_id
                == ebook_item_id
            )
            .with_for_update()
        )

    @staticmethod
    def _json_contains_item(raw_value: str | None, ebook_item_id: str) -> bool:
        try:
            value = json.loads(raw_value or "[]")
        except (TypeError, json.JSONDecodeError):
            return True
        return isinstance(value, list) and ebook_item_id in value

    def _daily_summary_run_count(self, ebook_item_id: str) -> int:
        count = 0
        for model in (DailySummaryRun, DailySummaryRunHistory):
            values = self.session.scalars(select(model.selected_item_ids_json))
            count += sum(
                self._json_contains_item(value, ebook_item_id) for value in values
            )
        return count

    def _external_evidence_count(self, ebook_item_id: str) -> int:
        item_key = self.wordpress_draft_store._item_key(ebook_item_id)
        paths = {
            self.wordpress_draft_store.claim_path(ebook_item_id),
            self.wordpress_schedule_store.claim_path(ebook_item_id),
            self.wordpress_schedule_store.latest_success_path(ebook_item_id),
        }
        paths.update(
            self.wordpress_draft_store.claim_directory.glob(
                f"history/{item_key}.*.json"
            )
        )
        count = sum(path.exists() for path in paths)
        evidence_directories = (
            self.wordpress_draft_store.evidence_directory,
            self.wordpress_schedule_store.evidence_directory,
        )
        for directory in evidence_directories:
            if not directory.exists():
                continue
            for path in directory.glob("*.json"):
                try:
                    value = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                if isinstance(value, dict) and value.get("ebook_item_id") == ebook_item_id:
                    count += 1
        return count

    def _direct_reference_counts(
        self,
        ebook_item_id: str,
        candidate: SupplementImportCandidate | None,
    ) -> dict[str, int]:
        counts: dict[str, int] = {}
        for table in Base.metadata.sorted_tables:
            for column in table.columns:
                if not any(
                    foreign_key.target_fullname == "ebook_items.id"
                    for foreign_key in column.foreign_keys
                ):
                    continue
                if table.name == "supplement_import_candidates":
                    continue
                count = int(
                    self.session.scalar(
                        select(func.count()).select_from(table).where(
                            column == ebook_item_id
                        )
                    )
                    or 0
                )
                if count:
                    counts[f"{table.name}.{column.name}"] = count
        if candidate is not None:
            other_candidate_count = int(
                self.session.scalar(
                    select(func.count())
                    .select_from(SupplementImportCandidate)
                    .where(
                        SupplementImportCandidate.id != candidate.id,
                        SupplementImportCandidate.imported_ebook_item_id
                        == ebook_item_id,
                    )
                )
                or 0
            )
            if other_candidate_count:
                counts["supplement_import_candidates.other"] = other_candidate_count
        return counts

    def preview_cancel(self, ebook_item_id: str) -> SupplementCancellationPreview:
        item = self.session.scalar(
            select(EbookItem)
            .where(EbookItem.id == ebook_item_id)
            .with_for_update()
        )
        candidate = self._candidate_for_item(ebook_item_id)
        if item is None:
            return SupplementCancellationPreview(
                ebook_item_id=ebook_item_id,
                title="",
                candidate_id=None,
                import_run_id=None,
                source=None,
                current_state=None,
                resulting_state="PENDING",
                cancellable=False,
                block_reasons=("CANCEL_BLOCKED_ITEM_NOT_FOUND",),
                dependency_checks={},
            )

        direct_counts = self._direct_reference_counts(ebook_item_id, candidate)
        store_offer_count = direct_counts.pop("store_offers.ebook_item_id", 0)
        approval_count = direct_counts.pop(
            "workflow_approval_requests.ebook_item_id", 0
        )
        daily_selection_count = sum(
            direct_counts.pop(key, 0)
            for key in (
                "daily_summary_selections.ebook_item_id",
                "daily_summary_selection_history.ebook_item_id",
            )
        )
        daily_summary_reference_count = (
            daily_selection_count + self._daily_summary_run_count(ebook_item_id)
        )
        external_evidence_count = self._external_evidence_count(ebook_item_id)
        checks: dict[str, Any] = {
            "store_offer_count": store_offer_count,
            "approval_count": approval_count,
            "daily_summary_reference_count": daily_summary_reference_count,
            "x_draft_count": int(
                item.x_status != "NOT_CREATED" or bool(item.x_post_id)
            ),
            "external_evidence_count": external_evidence_count,
            "other_reference_counts": direct_counts,
        }
        reasons: list[str] = []
        if item.source_discovery != SOURCE_TYPE or candidate is None:
            reasons.append("CANCEL_BLOCKED_NOT_SUPPLEMENT_ITEM")
        if item.workflow_status != "NEW" or item.review_status != "NOT_REVIEWED":
            reasons.append("CANCEL_BLOCKED_REVIEW_STARTED")
        if (
            item.wordpress_status != "NOT_CREATED"
            or bool(str(item.wordpress_post_id or "").strip())
        ):
            reasons.append("CANCEL_BLOCKED_WORDPRESS_EXISTS")
        if store_offer_count:
            reasons.append("CANCEL_BLOCKED_STORE_OFFER_EXISTS")
        if approval_count:
            reasons.append("CANCEL_BLOCKED_APPROVAL_EXISTS")
        if daily_summary_reference_count:
            reasons.append("CANCEL_BLOCKED_DAILY_SUMMARY_REFERENCE")
        if checks["x_draft_count"]:
            reasons.append("CANCEL_BLOCKED_X_DRAFT_EXISTS")
        if external_evidence_count:
            reasons.append("CANCEL_BLOCKED_EXTERNAL_EVIDENCE")
        if direct_counts:
            reasons.append("CANCEL_BLOCKED_OTHER_REFERENCE")
        return SupplementCancellationPreview(
            ebook_item_id=item.id,
            title=item.title,
            candidate_id=candidate.id if candidate else None,
            import_run_id=candidate.import_run_id if candidate else None,
            source=item.source_discovery,
            current_state=candidate.import_status if candidate else None,
            resulting_state="PENDING",
            cancellable=not reasons,
            block_reasons=tuple(dict.fromkeys(reasons)),
            dependency_checks=checks,
        )

    def _reset_candidate(self, candidate: SupplementImportCandidate) -> None:
        candidate.imported_ebook_item_id = None
        candidate.import_status = "PENDING"
        candidate.selected = False
        candidate.parser_confidence = "REVIEW_REQUIRED"
        self.session.flush()

    def _clear_candidate_match_references(self, ebook_item_id: str) -> None:
        matched_candidates = self.session.scalars(
            select(SupplementImportCandidate).where(
                SupplementImportCandidate.matched_ebook_item_id
                == ebook_item_id
            )
        )
        for matched_candidate in matched_candidates:
            matched_candidate.matched_ebook_item_id = None
        self.session.flush()

    def _idempotent_result(
        self,
        *,
        ebook_item_id: str,
        candidate_id: str,
        expected_title: str,
    ) -> SupplementCancellationResult | None:
        history = self.session.scalar(
            select(SupplementRegistrationCancellationHistory).where(
                SupplementRegistrationCancellationHistory.ebook_item_id
                == ebook_item_id,
                SupplementRegistrationCancellationHistory.candidate_id
                == candidate_id,
            )
        )
        if history is None:
            return None
        if history.title != expected_title.strip():
            raise SupplementImportCancellationError("TITLE_MISMATCH")
        return SupplementCancellationResult(
            code="SUPPLEMENT_REGISTRATION_CANCELLED",
            ebook_item_id=ebook_item_id,
            candidate_id=candidate_id,
            import_run_id=history.import_run_id,
            idempotent=True,
        )

    def cancel_registration(
        self,
        *,
        ebook_item_id: str,
        candidate_id: str,
        expected_title: str,
        operator: str,
    ) -> SupplementCancellationResult:
        idempotent = self._idempotent_result(
            ebook_item_id=ebook_item_id,
            candidate_id=candidate_id,
            expected_title=expected_title,
        )
        if idempotent is not None:
            return idempotent
        candidate = self.session.scalar(
            select(SupplementImportCandidate)
            .where(SupplementImportCandidate.id == candidate_id)
            .with_for_update()
        )
        if candidate is None:
            raise SupplementImportCancellationError("CANDIDATE_NOT_FOUND")
        preview = self.preview_cancel(ebook_item_id)
        if preview.candidate_id != candidate.id:
            raise SupplementImportCancellationError("CANDIDATE_MISMATCH")
        item = self.session.get(EbookItem, ebook_item_id)
        if item is None:
            raise SupplementImportCancellationError("ITEM_NOT_FOUND")
        if item.title != expected_title.strip():
            raise SupplementImportCancellationError("TITLE_MISMATCH")
        normalized_operator = operator.strip()
        if not normalized_operator:
            raise SupplementImportCancellationError("OPERATOR_MISSING")
        if not preview.cancellable:
            raise SupplementImportCancellationError(preview.block_reasons[0])

        history = SupplementRegistrationCancellationHistory(
            operation="REGISTRATION_CANCELLED",
            import_run_id=candidate.import_run_id,
            candidate_id=candidate.id,
            ebook_item_id=item.id,
            title=item.title,
            operator=normalized_operator,
            cancellation_reason="補完登録の取消・候補への差し戻し",
            previous_workflow_status=item.workflow_status,
            previous_review_status=item.review_status,
            previous_wordpress_status=item.wordpress_status,
            dependency_checks_json=json.dumps(
                preview.dependency_checks, ensure_ascii=False, sort_keys=True
            ),
        )
        run = self.session.get(SupplementImportRun, candidate.import_run_id)
        self.session.add(history)
        self._reset_candidate(candidate)
        self._clear_candidate_match_references(item.id)
        if run is not None:
            run.imported_count = max(0, run.imported_count - 1)
            run.selected_count = max(0, run.selected_count - 1)
            run.status = "IMPORTED" if run.imported_count else "PARSED"
        self.ebooks.delete(item)
        self.session.flush()
        return SupplementCancellationResult(
            code="SUPPLEMENT_REGISTRATION_CANCELLED",
            ebook_item_id=ebook_item_id,
            candidate_id=candidate.id,
            import_run_id=candidate.import_run_id,
        )