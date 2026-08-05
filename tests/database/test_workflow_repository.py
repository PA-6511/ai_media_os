from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models import EbookItem, WorkflowHistory
from app.db.repositories.workflow_repository import (
    WorkflowRepository,
)


def create_session(tmp_path):
    db = tmp_path / "workflow_repository.db"
    engine = create_engine(f"sqlite:///{db}")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_transition_and_history(tmp_path):

    with create_session(tmp_path) as session:

        item = EbookItem(
            source_name="test",
            source_item_id="001",
            title="sample",
            item_type="tankobon",
        )

        session.add(item)
        session.commit()

        repo = WorkflowRepository(session)

        repo.set_workflow_status(
            item,
            "REVIEW",
            changed_by="pytest",
            note="review",
        )

        session.commit()

        session.refresh(item)

        assert item.workflow_status == "REVIEW"

        history = session.scalars(
            select(WorkflowHistory)
        ).all()

        assert len(history) == 1
        assert history[0].before_value == "NEW"
        assert history[0].after_value == "REVIEW"


def test_illegal_transition(tmp_path):

    with create_session(tmp_path) as session:

        item = EbookItem(
            source_name="test",
            source_item_id="002",
            title="sample",
            item_type="tankobon",
        )

        session.add(item)
        session.commit()

        repo = WorkflowRepository(session)

        try:
            repo.set_workflow_status(
                item,
                "PUBLISHED",
                changed_by="pytest",
            )
            assert False
        except ValueError:
            pass
