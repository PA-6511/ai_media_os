from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import (
    EbookItem,
    StoreOffer,
    WorkflowApprovalRequest,
)
from app.db.repositories.workflow_state_repository import (
    WorkflowStateRepository,
)
from app.integrations.wordpress_rest_client import (
    WordPressDraftResponse,
)
from app.services.wordpress_draft_execution_service import (
    WordPressDraftExecutionStore,
    execute_approved_wordpress_draft_once,
)


EBOOK_ITEM_ID = "e2029b2f-f44a-462f-abc8-86c4bc74b818"
APPROVAL_REQUEST_ID = "99999999-9999-4999-8999-999999999999"
ACTOR = "human:local_gui:wordpress_draft_lite"


class FakeWordPressClient:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def create_draft(
        self,
        payload: dict[str, object],
    ) -> WordPressDraftResponse:
        self.payloads.append(dict(payload))
        return WordPressDraftResponse(
            post_id=987654321,
            status="draft",
            link="https://wordpress.example.test/?p=987654321",
        )


def test_wordpress_post_id_avoids_disallowed_history_field(
    tmp_path: Path,
) -> None:
    temporary_database = (
        tmp_path
        / "ebook_affiliate_test.db"
    )

    engine = create_engine(
        f"sqlite:///{temporary_database}",
        future=True,
    )
    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        future=True,
    )
    client = FakeWordPressClient()

    try:
        with Session() as session:
            now = datetime.now(timezone.utc)
            item = EbookItem(
                id=EBOOK_ITEM_ID,
                source_name="pytest-fixture",
                source_item_id="x-r13-fixture-item",
                title="X-R13 fixture title",
                item_type="tankobon",
                workflow_status="READY",
                review_status="APPROVED",
                wordpress_status="NOT_CREATED",
                wordpress_post_id=None,
                x_status="NOT_CREATED",
                publish_ready=False,
                is_excluded=False,
            )
            offer = StoreOffer(
                ebook_item=item,
                store_name="rakuten_kobo",
                store_item_id="x-r13-fixture-store-item",
                product_url=None,
                affiliate_url=(
                    "https://affiliate.example.test/"
                    "x-r13-fixture-item"
                ),
            )
            approval_request = WorkflowApprovalRequest(
                id=APPROVAL_REQUEST_ID,
                ebook_item_id=EBOOK_ITEM_ID,
                approval_type="REVIEW_READY",
                expected_current_status="REVIEW",
                requested_status="READY",
                status="APPROVED",
                request_nonce_hash="9" * 64,
                requested_by="pytest",
                requested_at=now - timedelta(minutes=5),
                expires_at=now + timedelta(minutes=55),
                decided_by="pytest",
                decided_at=now,
                decision_note="fixture approval",
            )
            session.add_all(
                [item, offer, approval_request]
            )
            session.commit()

            assert item.workflow_status == "READY"
            assert item.review_status == "APPROVED"
            assert item.wordpress_status == "NOT_CREATED"
            assert item.wordpress_post_id is None
            assert item.publish_ready is False
            assert item.is_excluded is False
            assert approval_request.status == "APPROVED"
            assert approval_request.approval_type == "REVIEW_READY"

            result = execute_approved_wordpress_draft_once(
                ebook_item_id=EBOOK_ITEM_ID,
                item=item,
                approval_request=approval_request,
                offer=offer,
                wordpress_client=client,
                state_repository=WorkflowStateRepository(
                    session
                ),
                commit=session.commit,
                rollback=session.rollback,
                execution_store=WordPressDraftExecutionStore(
                    tmp_path / "execution-artifacts"
                ),
            )

            assert result.wordpress_post_id == 987654321
            assert result.wordpress_status == "DRAFT"
            assert result.publish_executed is False
            assert len(client.payloads) == 1
            assert client.payloads[0]["status"] == "draft"
            assert "publish" not in client.payloads[0].values()

    finally:
        engine.dispose()

    connection = sqlite3.connect(
        temporary_database
    )

    try:
        item_state = connection.execute(
            """
            SELECT
                wordpress_status,
                wordpress_post_id,
                wordpress_updated_at
            FROM ebook_items
            WHERE id = ?
            """,
            (EBOOK_ITEM_ID,),
        ).fetchone()

        history_fields = [
            row[0]
            for row in connection.execute(
                """
                SELECT field_name
                FROM workflow_history
                WHERE ebook_item_id = ?
                  AND changed_by = ?
                ORDER BY changed_at, id
                """,
                (
                    EBOOK_ITEM_ID,
                    ACTOR,
                ),
            ).fetchall()
        ]

        preserved_state = connection.execute(
            """
            SELECT
                workflow_status,
                review_status,
                publish_ready,
                is_excluded,
                x_status
            FROM ebook_items
            WHERE id = ?
            """,
            (EBOOK_ITEM_ID,),
        ).fetchone()

        approval_state = connection.execute(
            """
            SELECT
                approval_type,
                status,
                expected_current_status,
                requested_status,
                decided_at
            FROM workflow_approval_requests
            WHERE id = ?
            """,
            (APPROVAL_REQUEST_ID,),
        ).fetchone()

    finally:
        connection.close()

    assert item_state is not None
    assert item_state[0] == "DRAFT"
    assert item_state[1] == "987654321"
    assert item_state[2] is not None

    assert preserved_state == (
        "READY",
        "APPROVED",
        0,
        0,
        "NOT_CREATED",
    )
    assert approval_state is not None
    assert approval_state[:4] == (
        "REVIEW_READY",
        "APPROVED",
        "REVIEW",
        "READY",
    )
    assert approval_state[4] is not None

    assert history_fields == [
        "wordpress_status",
        "image_status",
    ]
    assert "wordpress_post_id" not in history_fields
