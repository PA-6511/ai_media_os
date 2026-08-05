from __future__ import annotations

import hashlib
import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)
from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadError,
    WorkflowApprovedXDraftReadService,
)
from app.services.x_draft_feedback_registration_service import (
    ROOT,
    XDraftFeedbackRegistrationService,
)


def create_session(tmp_path: Path) -> Session:
    database_path = tmp_path / "x_r6.db"
    engine = create_engine(
        f"sqlite:///{database_path}"
    )
    Base.metadata.create_all(engine)

    return Session(
        engine,
        autoflush=False,
        expire_on_commit=False,
    )


def seed_approved_draft(
    session: Session,
    *,
    approval_id: str = "approval-x-r6-001",
    approval_status: str = "APPROVED",
    approval_type: str = "REVIEW_READY",
    workflow_status: str = "READY",
    review_status: str = "APPROVED",
    wordpress_status: str = "DRAFT",
    wordpress_post_id: int | None = 60001,
    item_type: str = "tankobon",
    is_excluded: bool = False,
) -> tuple[EbookItem, WorkflowApprovalRequest]:
    now = datetime.now(timezone.utc)

    item = EbookItem(
        source_name="pytest",
        source_item_id="x-r6-item-001",
        title="X-R6 DB接続テスト作品",
        normalized_title="X-R6 DB接続テスト作品",
        volume_label="第1巻",
        author_name="山田 太郎",
        publisher_name="テスト出版社",
        release_date=date(2026, 7, 17),
        item_type=item_type,
        is_excluded=is_excluded,
        workflow_status=workflow_status,
        wordpress_status=wordpress_status,
        wordpress_post_id=wordpress_post_id,
        review_status=review_status,
    )

    session.add(item)
    session.flush()

    approval = WorkflowApprovalRequest(
        id=approval_id,
        ebook_item_id=item.id,
        approval_type=approval_type,
        expected_current_status=(
            "REVIEW"
            if approval_type == "REVIEW_READY"
            else "READY"
        ),
        requested_status=(
            "READY"
            if approval_type == "REVIEW_READY"
            else "SCHEDULED"
        ),
        status=approval_status,
        request_nonce_hash=hashlib.sha256(
            approval_id.encode("utf-8")
        ).hexdigest(),
        requested_by="block:ebook",
        requested_at=now - timedelta(hours=2),
        expires_at=now + timedelta(hours=1),
        decided_by="human-reviewer",
        decided_at=now - timedelta(hours=1),
        decision_note="Approved for test",
    )

    session.add(approval)
    session.commit()

    return item, approval


def create_service(
    session: Session,
) -> WorkflowApprovedXDraftReadService:
    return WorkflowApprovedXDraftReadService(
        session,
        wordpress_base_url=(
            "https://books.example.jp"
        ),
    )


def test_approved_record_is_read_and_adapted(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session
        )

        result = create_service(
            session
        ).read_and_adapt(
            approval.id
        )

        assert result.status == (
            "PASS_READ_ONLY_WORKFLOW_TO_X_ADAPTER"
        )
        assert result.source_approval_type == (
            "REVIEW_READY"
        )
        assert result.mapped_approval_scope == (
            "X_DRAFT_GENERATION"
        )

        draft = (
            result.adapter_result.x_draft_input
        )

        assert draft.ebook_item_id == (
            "x-r6-item-001"
        )
        assert draft.wordpress_draft_id == 60001
        assert draft.wordpress_status == "DRAFT"
        assert draft.category == "コミック新刊"
        assert draft.article_url == (
            "https://books.example.jp/?p=60001"
        )


def test_missing_approval_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        service = create_service(session)

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match="approval request was not found",
        ):
            service.read_and_adapt("missing")


def test_non_approved_record_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session,
            approval_status="PENDING",
        )

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match=(
                "approval status must be APPROVED"
            ),
        ):
            create_service(
                session
            ).read_and_adapt(
                approval.id
            )


def test_publish_schedule_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session,
            approval_type="PUBLISH_SCHEDULE",
        )

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match=(
                "approval type must be REVIEW_READY"
            ),
        ):
            create_service(
                session
            ).read_and_adapt(
                approval.id
            )


def test_non_draft_wordpress_status_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session,
            wordpress_status="PUBLISHED",
        )

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match=(
                "wordpress status must be DRAFT"
            ),
        ):
            create_service(
                session
            ).read_and_adapt(
                approval.id
            )


def test_non_approved_review_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session,
            review_status="IN_REVIEW",
        )

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match=(
                "review status must be APPROVED"
            ),
        ):
            create_service(
                session
            ).read_and_adapt(
                approval.id
            )


def test_missing_wordpress_post_id_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session,
            wordpress_post_id=None,
        )

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match=(
                "wordpress_post_id must not be null"
            ),
        ):
            create_service(
                session
            ).read_and_adapt(
                approval.id
            )


def test_unsupported_item_type_is_rejected(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session,
            item_type="unknown",
        )

        with pytest.raises(
            WorkflowApprovedXDraftReadError,
            match="unsupported item_type",
        ):
            create_service(
                session
            ).read_and_adapt(
                approval.id
            )


def test_candidate_search_returns_only_eligible(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approved = seed_approved_draft(
            session,
            approval_id="approved-eligible",
        )

        second_item = EbookItem(
            source_name="pytest",
            source_item_id="ineligible-item",
            title="Ineligible",
            item_type="tankobon",
            workflow_status="READY",
            review_status="IN_REVIEW",
            wordpress_status="DRAFT",
            wordpress_post_id=60002,
        )
        session.add(second_item)
        session.flush()

        now = datetime.now(timezone.utc)

        session.add(
            WorkflowApprovalRequest(
                id="approved-ineligible",
                ebook_item_id=second_item.id,
                approval_type="REVIEW_READY",
                expected_current_status="REVIEW",
                requested_status="READY",
                status="APPROVED",
                request_nonce_hash=hashlib.sha256(
                    b"approved-ineligible"
                ).hexdigest(),
                requested_by="block:ebook",
                requested_at=(
                    now - timedelta(hours=2)
                ),
                expires_at=(
                    now + timedelta(hours=1)
                ),
                decided_by="human-reviewer",
                decided_at=(
                    now - timedelta(hours=1)
                ),
            )
        )
        session.commit()

        identifiers = create_service(
            session
        ).find_latest_candidate_ids()

        assert identifiers == [approved.id]


def test_read_service_performs_no_database_write(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session
        )

        before_item_count = session.scalar(
            select(func.count())
            .select_from(EbookItem)
        )
        before_approval_count = session.scalar(
            select(func.count())
            .select_from(
                WorkflowApprovalRequest
            )
        )

        create_service(
            session
        ).read_and_adapt(
            approval.id
        )

        assert not session.new
        assert not session.dirty
        assert not session.deleted

        after_item_count = session.scalar(
            select(func.count())
            .select_from(EbookItem)
        )
        after_approval_count = session.scalar(
            select(func.count())
            .select_from(
                WorkflowApprovalRequest
            )
        )

        assert (
            before_item_count
            == after_item_count
        )
        assert (
            before_approval_count
            == after_approval_count
        )


def test_x_r6_to_x_r4_dry_run_creates_no_x_fb_files(
    tmp_path: Path,
) -> None:
    with create_session(tmp_path) as session:
        _, approval = seed_approved_draft(
            session
        )

        read_result = create_service(
            session
        ).read_and_adapt(
            approval.id
        )

        x_fb_root = tmp_path / "x_fb_root"

        (x_fb_root / "config").mkdir(
            parents=True
        )
        (x_fb_root / "scripts").mkdir(
            parents=True
        )

        shutil.copy2(
            ROOT
            / "config/"
            "x_post_wording_feedback_schema.json",
            x_fb_root
            / "config/"
            "x_post_wording_feedback_schema.json",
        )
        shutil.copy2(
            ROOT
            / "config/"
            "x_fb_manual_operation_policy.json",
            x_fb_root
            / "config/"
            "x_fb_manual_operation_policy.json",
        )
        shutil.copy2(
            ROOT / "scripts/build_x_fb_0.py",
            x_fb_root
            / "scripts/build_x_fb_0.py",
        )

        registration = (
            XDraftFeedbackRegistrationService()
            .dry_run_register(
                read_result.adapter_result.x_draft_input,
                storage_root=x_fb_root,
            )
        )

        assert registration.status == (
            "PASS_DRY_RUN_NO_WRITE"
        )
        assert not Path(
            registration.current_record_path
        ).exists()
        assert not Path(
            registration.operation_result_path
        ).exists()

        serialized = json.dumps(
            registration.to_dict(),
            ensure_ascii=False,
        )
        assert "#PR" in serialized


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (60001, 60001),
        ("60001", 60001),
        (" 60001 ", 60001),
    ],
)
def test_wordpress_post_id_is_normalized(
    value: object,
    expected: int,
) -> None:
    from app.services.workflow_approved_x_draft_read_service import (
        normalize_wordpress_post_id,
    )

    assert normalize_wordpress_post_id(
        value
    ) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "0",
        "-1",
        "12.5",
        "post-60001",
        True,
        None,
    ],
)
def test_invalid_wordpress_post_id_is_rejected(
    value: object,
) -> None:
    from app.services.workflow_approved_x_draft_read_service import (
        WorkflowApprovedXDraftReadError,
        normalize_wordpress_post_id,
    )

    with pytest.raises(
        WorkflowApprovedXDraftReadError,
        match="wordpress_post_id",
    ):
        normalize_wordpress_post_id(value)


def test_reloaded_string_post_id_is_adapted(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "reload.db"
    engine = create_engine(
        f"sqlite:///{database_path}"
    )
    Base.metadata.create_all(engine)

    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as write_session:
            _, approval = seed_approved_draft(
                write_session,
                wordpress_post_id=60001,
            )
            approval_id = approval.id

        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as read_session:
            result = create_service(
                read_session
            ).read_and_adapt(
                approval_id
            )

            draft = (
                result.adapter_result.x_draft_input
            )

            assert draft.wordpress_draft_id == 60001
            assert isinstance(
                draft.wordpress_draft_id,
                int,
            )
            assert draft.article_url == (
                "https://books.example.jp/?p=60001"
            )
    finally:
        engine.dispose()
