from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.access_guard import assert_database_target_allowed
from app.db.base import Base
from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
    WorkflowHistory,
)

# TST-5D-W1 immutable historical source fixture.
import importlib.util as _tst_5d_w1_importlib_util
from pathlib import Path as _Tst5dW1Path

_TST_5D_W1_FIXTURE_PATH = (
    _Tst5dW1Path(__file__).resolve().parents[2]
    / "tests/fixtures/tst_5d_w1/workflow_state_repository_pre_w2b.py"
)

_TST_5D_W1_SPEC = (
    _tst_5d_w1_importlib_util.spec_from_file_location(
        "tst_5d_w1_workflow_state_repository_pre_w2b",
        _TST_5D_W1_FIXTURE_PATH,
    )
)

assert _TST_5D_W1_SPEC is not None
assert _TST_5D_W1_SPEC.loader is not None

_TST_5D_W1_MODULE = (
    _tst_5d_w1_importlib_util.module_from_spec(
        _TST_5D_W1_SPEC
    )
)

_TST_5D_W1_SPEC.loader.exec_module(
    _TST_5D_W1_MODULE
)

WorkflowStateRepository = (
    _TST_5D_W1_MODULE.WorkflowStateRepository
)
from app.services.slack_approval_message_service import (
    encode_slack_approval_action,
)
from app.services.slack_approval_socket_service import (
    SlackApprovalSocketConfig,
    SlackApprovalSocketError,
    SlackApprovalSocketService,
    parse_slack_approval_interaction,
)
from app.services.workflow_approval_service import WorkflowApprovalService
from app.services.wordpress_draft_execution_service import (
    WordPressDraftExecutionError,
    validate_wordpress_draft_preflight,
)


ACTOR = "pytest:tst-5d-w1"


@pytest.fixture
def isolated_database(tmp_path: Path):
    database_path = tmp_path / "tst-5d-w1-workflow-state.db"
    database_url = f"sqlite:///{database_path}"
    allowed = assert_database_target_allowed(
        database_url,
        testing=True,
        temporary_directory=Path("/tmp"),
        operation="TST-5D-W1 isolated workflow-state test",
    )
    assert allowed == database_path.resolve()

    engine = create_engine(database_url, future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(
        bind=engine,
        expire_on_commit=False,
        future=True,
    )
    try:
        yield session_factory
    finally:
        engine.dispose()


def _item(
    source_item_id: str,
    *,
    workflow_status: str = "READY",
    review_status: str = "APPROVED",
    wordpress_status: str = "NOT_CREATED",
    wordpress_post_id: str | None = None,
) -> EbookItem:
    return EbookItem(
        source_name="tst-5d-w1",
        source_item_id=source_item_id,
        title=f"TST-5D-W1 {source_item_id}",
        item_type="tankobon",
        workflow_status=workflow_status,
        review_status=review_status,
        wordpress_status=wordpress_status,
        wordpress_post_id=wordpress_post_id,
        publish_ready=False,
        is_excluded=False,
    )


def _approval(item: EbookItem, suffix: str) -> WorkflowApprovalRequest:
    now = datetime.now(timezone.utc)
    return WorkflowApprovalRequest(
        ebook_item=item,
        approval_type="REVIEW_READY",
        expected_current_status="REVIEW",
        requested_status="READY",
        status="PENDING",
        request_nonce_hash=(suffix * 64)[:64],
        requested_by=ACTOR,
        requested_at=now,
        expires_at=now + timedelta(hours=1),
    )


def _persisted_state(
    session_factory,
    item_id: str,
    approval_id: str | None = None,
) -> tuple[str | None, str, str, int, str | None]:
    with session_factory() as verification_session:
        item = verification_session.get(EbookItem, item_id)
        assert item is not None
        history_count = verification_session.scalar(
            select(func.count(WorkflowHistory.id)).where(
                WorkflowHistory.ebook_item_id == item_id
            )
        )
        approval_status = None
        if approval_id is not None:
            approval = verification_session.get(
                WorkflowApprovalRequest,
                approval_id,
            )
            assert approval is not None
            approval_status = approval.status
        return (
            item.wordpress_post_id,
            item.wordpress_status,
            item.workflow_status,
            int(history_count or 0),
            approval_status,
        )


def test_different_workflows_accept_duplicate_post_id_and_expose_gap(
    isolated_database,
) -> None:
    """Passing reproduction: the required fail-closed behavior is absent."""
    with isolated_database() as session:
        item_a = _item("DUPLICATE-A", wordpress_post_id="12345")
        item_b = _item("DUPLICATE-B")
        approval_a = _approval(item_a, "a")
        approval_b = _approval(item_b, "b")
        session.add_all([item_a, item_b, approval_a, approval_b])
        session.commit()
        before_a = _persisted_state(
            isolated_database, item_a.id, approval_a.id
        )
        before_b = _persisted_state(
            isolated_database, item_b.id, approval_b.id
        )

        changed = WorkflowStateRepository(session).set_wordpress_post_id(
            item_b,
            12345,
            changed_by=ACTOR,
        )
        session.commit()

        after_a = _persisted_state(
            isolated_database, item_a.id, approval_a.id
        )
        after_b = _persisted_state(
            isolated_database, item_b.id, approval_b.id
        )

    assert changed is True
    assert before_a == after_a
    assert before_b == (None, "NOT_CREATED", "READY", 0, "PENDING")
    assert after_b == ("12345", "NOT_CREATED", "READY", 0, "PENDING")
    assert after_a[0] == after_b[0] == "12345"


def test_same_workflow_same_post_id_is_idempotent(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item = _item("IDEMPOTENT", wordpress_post_id="12345")
        session.add(item)
        session.commit()
        original_updated_at = item.updated_at
        original_checked_at = item.last_checked_at
        original_wordpress_updated_at = item.wordpress_updated_at

        changed = WorkflowStateRepository(session).set_wordpress_post_id(
            item,
            "12345",
            changed_by=ACTOR,
        )
        session.commit()

        assert changed is False
        assert item.updated_at == original_updated_at
        assert item.last_checked_at == original_checked_at
        assert item.wordpress_updated_at == original_wordpress_updated_at
        assert session.scalar(select(func.count(WorkflowHistory.id))) == 0


@pytest.mark.parametrize(
    "value",
    [True, False, 0, -1, "", "   ", "0", "-9", "1.5", "abc"],
)
def test_invalid_post_ids_fail_closed_without_partial_mutation(
    isolated_database,
    value,
) -> None:
    with isolated_database() as session:
        item = _item("INVALID")
        approval = _approval(item, "c")
        session.add_all([item, approval])
        session.commit()
        before = _persisted_state(isolated_database, item.id, approval.id)

        with pytest.raises(ValueError, match="positive integer"):
            WorkflowStateRepository(session).set_wordpress_post_id(
                item,
                value,
                changed_by=ACTOR,
            )
        session.rollback()

        assert _persisted_state(
            isolated_database, item.id, approval.id
        ) == before


def test_null_and_numeric_string_follow_current_nullable_string_contract(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item = _item("NULLABLE", wordpress_post_id="44")
        session.add(item)
        session.commit()
        repository = WorkflowStateRepository(session)

        assert repository.set_wordpress_post_id(
            item, None, changed_by=ACTOR
        ) is True
        assert repository.set_wordpress_post_id(
            item, " 00123 ", changed_by=ACTOR
        ) is True
        session.commit()

        assert item.wordpress_post_id == "00123"


def test_extreme_integer_is_accepted_and_exposes_length_validation_gap(
    isolated_database,
) -> None:
    extreme_value = "9" * 65
    with isolated_database() as session:
        item = _item("EXTREME")
        session.add(item)
        session.commit()

        changed = WorkflowStateRepository(session).set_wordpress_post_id(
            item,
            extreme_value,
            changed_by=ACTOR,
        )
        session.commit()

        assert changed is True
        assert item.wordpress_post_id == extreme_value


def test_post_id_flush_failure_rolls_back_and_session_can_retry(
    isolated_database,
) -> None:
    with isolated_database() as setup_session:
        item = _item("FLUSH-POST-ID")
        approval = _approval(item, "d")
        setup_session.add_all([item, approval])
        setup_session.commit()
        item_id, approval_id = item.id, approval.id

    with isolated_database() as session:
        item = session.get(EbookItem, item_id)
        armed = {"value": True}

        def fail_flush(*_args) -> None:
            if armed["value"]:
                raise RuntimeError("TST-5D-W1 injected flush failure")

        event.listen(session, "before_flush", fail_flush)
        with pytest.raises(RuntimeError, match="injected flush failure"):
            WorkflowStateRepository(session).set_wordpress_post_id(
                item,
                456,
                changed_by=ACTOR,
            )
        session.rollback()
        armed["value"] = False
        assert _persisted_state(
            isolated_database, item_id, approval_id
        ) == (None, "NOT_CREATED", "READY", 0, "PENDING")

        item = session.get(EbookItem, item_id)
        WorkflowStateRepository(session).set_wordpress_post_id(
            item,
            456,
            changed_by=ACTOR,
        )
        session.commit()

    assert _persisted_state(
        isolated_database, item_id, approval_id
    ) == ("456", "NOT_CREATED", "READY", 0, "PENDING")


def test_second_flush_failure_rolls_back_post_id_state_and_history(
    isolated_database,
) -> None:
    with isolated_database() as setup_session:
        item = _item("FLUSH-PARTIAL")
        approval = _approval(item, "e")
        setup_session.add_all([item, approval])
        setup_session.commit()
        item_id, approval_id = item.id, approval.id

    with isolated_database() as session:
        item = session.get(EbookItem, item_id)
        flushes = {"count": 0}

        def fail_second_flush(*_args) -> None:
            flushes["count"] += 1
            if flushes["count"] == 2:
                raise RuntimeError("TST-5D-W1 second flush failure")

        event.listen(session, "before_flush", fail_second_flush)
        with pytest.raises(RuntimeError, match="second flush failure"):
            WorkflowStateRepository(session).mark_wordpress_draft_created(
                item,
                789,
                changed_by=ACTOR,
            )
        session.rollback()

    assert _persisted_state(
        isolated_database, item_id, approval_id
    ) == (None, "NOT_CREATED", "READY", 0, "PENDING")


def test_commit_failure_rolls_back_and_new_session_retry_is_atomic(
    isolated_database,
    monkeypatch,
) -> None:
    with isolated_database() as setup_session:
        item = _item("COMMIT-FAILURE")
        approval = _approval(item, "f")
        setup_session.add_all([item, approval])
        setup_session.commit()
        item_id, approval_id = item.id, approval.id

    with isolated_database() as session:
        item = session.get(EbookItem, item_id)
        WorkflowStateRepository(session).mark_wordpress_draft_created(
            item,
            987,
            changed_by=ACTOR,
        )

        def fail_commit() -> None:
            raise RuntimeError("TST-5D-W1 injected commit failure")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="injected commit failure"):
            session.commit()
        session.rollback()

    assert _persisted_state(
        isolated_database, item_id, approval_id
    ) == (None, "NOT_CREATED", "READY", 0, "PENDING")

    with isolated_database() as retry_session:
        item = retry_session.get(EbookItem, item_id)
        WorkflowStateRepository(retry_session).mark_wordpress_draft_created(
            item,
            987,
            changed_by=ACTOR,
        )
        retry_session.commit()

    assert _persisted_state(
        isolated_database, item_id, approval_id
    ) == ("987", "DRAFT", "READY", 1, "PENDING")


def test_mark_draft_retry_after_success_does_not_duplicate_history(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item = _item("HISTORY-IDEMPOTENCY")
        session.add(item)
        session.commit()
        repository = WorkflowStateRepository(session)

        assert repository.mark_wordpress_draft_created(
            item, 321, changed_by=ACTOR
        ) is True
        session.commit()
        assert repository.mark_wordpress_draft_created(
            item, 321, changed_by=ACTOR
        ) is False
        session.commit()

        histories = session.scalars(
            select(WorkflowHistory).where(
                WorkflowHistory.ebook_item_id == item.id
            )
        ).all()
        assert [history.field_name for history in histories] == [
            "wordpress_status"
        ]


def test_direct_published_binding_replacement_exposes_state_guard_gap(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item = _item(
            "PUBLISHED-REPLACE",
            workflow_status="PUBLISHED",
            wordpress_status="PUBLISHED",
            wordpress_post_id="100",
        )
        session.add(item)
        session.commit()

        changed = WorkflowStateRepository(session).set_wordpress_post_id(
            item,
            200,
            changed_by=ACTOR,
        )
        session.commit()

        assert changed is True
        assert item.wordpress_post_id == "200"
        assert item.workflow_status == "PUBLISHED"


@pytest.mark.parametrize(
    ("workflow_status", "review_status"),
    [("READY", "NOT_REVIEWED"), ("PUBLISHED", "APPROVED")],
)
def test_wordpress_draft_service_preflight_protects_disallowed_states(
    workflow_status: str,
    review_status: str,
) -> None:
    item = SimpleNamespace(
        id="item-1",
        workflow_status=workflow_status,
        review_status=review_status,
        is_excluded=False,
        publish_ready=False,
        wordpress_post_id=None,
        wordpress_status="NOT_CREATED",
    )
    approval = SimpleNamespace(
        id="approval-1",
        ebook_item_id="item-1",
        approval_type="REVIEW_READY",
        status="APPROVED",
        expected_current_status="REVIEW",
        requested_status="READY",
        decided_at=datetime.now(timezone.utc),
    )
    offer = SimpleNamespace(affiliate_url="https://example.test/item")

    with pytest.raises(WordPressDraftExecutionError, match="must be"):
        validate_wordpress_draft_preflight(
            ebook_item_id="item-1",
            item=item,
            approval_request=approval,
            offer=offer,
        )


def test_slack_extra_post_id_payload_cannot_mutate_wordpress_binding(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item = _item(
            "SLACK-BOUNDARY",
            workflow_status="REVIEW",
            review_status="NOT_REVIEWED",
            wordpress_status="DRAFT",
            wordpress_post_id="555",
        )
        session.add(item)
        session.commit()
        ticket = WorkflowApprovalService(session).create_request(
            item_id=item.id,
            approval_type="REVIEW_READY",
            requested_by=ACTOR,
        )
        request = session.get(WorkflowApprovalRequest, ticket.request_id)
        request.slack_team_id = "T123"
        request.slack_channel_id = "C123"
        request.slack_message_ts = "1720000000.000100"
        session.commit()
        history_count_before = session.scalar(
            select(func.count(WorkflowHistory.id)).where(
                WorkflowHistory.ebook_item_id == item.id
            )
        )

        interaction = parse_slack_approval_interaction(
            {
                "team": {"id": "T123"},
                "channel": {"id": "C123"},
                "user": {"id": "U123"},
                "container": {"message_ts": "1720000000.000100"},
                "wordpress_post_id": "999999",
                "workflow_status": "PUBLISHED",
                "actions": [
                    {
                        "action_id": "ebook_approval_approve",
                        "value": encode_slack_approval_action(
                            request_id=ticket.request_id,
                            token=ticket.token,
                            decision="APPROVE",
                        ),
                        "wordpress_post_id": "999999",
                    }
                ],
            }
        )
        config = SlackApprovalSocketConfig.from_mapping(
            {
                "SLACK_BOT_TOKEN": "xoxb-isolated-test",
                "SLACK_APP_TOKEN": "xapp-isolated-test",
                "SLACK_APPROVAL_TEAM_ID": "T123",
                "SLACK_APPROVAL_CHANNEL_ID": "C123",
                "SLACK_APPROVER_USER_IDS": "U123",
                "SLACK_APPROVAL_MODE": "DRY_RUN",
            }
        )
        result = SlackApprovalSocketService(session, config).process_interaction(
            interaction
        )
        session.expire_all()
        refreshed = session.get(EbookItem, item.id)
        request = session.get(WorkflowApprovalRequest, ticket.request_id)

        assert result.code == "dry_run_no_mutation"
        assert refreshed.wordpress_post_id == "555"
        assert refreshed.workflow_status == "REVIEW"
        assert request.status == "PENDING"
        assert session.scalar(
            select(func.count(WorkflowHistory.id)).where(
                WorkflowHistory.ebook_item_id == item.id
            )
        ) == history_count_before


def _slack_config(*, mode: str = "DRY_RUN") -> SlackApprovalSocketConfig:
    values = {
        "SLACK_BOT_TOKEN": "xoxb-isolated-test",
        "SLACK_APP_TOKEN": "xapp-isolated-test",
        "SLACK_APPROVAL_TEAM_ID": "T123",
        "SLACK_APPROVAL_CHANNEL_ID": "C123",
        "SLACK_APPROVER_USER_IDS": "U123",
        "SLACK_APPROVAL_MODE": mode,
    }
    if mode == "LIVE":
        values["SLACK_APPROVAL_LIVE_CONFIRM"] = "I_UNDERSTAND_DB_WRITES"
    return SlackApprovalSocketConfig.from_mapping(values)


def _bound_slack_request(session: Session, source_item_id: str):
    item = _item(
        source_item_id,
        workflow_status="REVIEW",
        review_status="NOT_REVIEWED",
        wordpress_status="DRAFT",
        wordpress_post_id="777",
    )
    session.add(item)
    session.commit()
    ticket = WorkflowApprovalService(session).create_request(
        item_id=item.id,
        approval_type="REVIEW_READY",
        requested_by=ACTOR,
    )
    request = session.get(WorkflowApprovalRequest, ticket.request_id)
    request.slack_team_id = "T123"
    request.slack_channel_id = "C123"
    request.slack_message_ts = "1720000000.000100"
    session.commit()
    return item, ticket, request


def _slack_body(*, request_id: str, token: str, decision: str = "APPROVE"):
    action_ids = {
        "APPROVE": "ebook_approval_approve",
        "REJECT": "ebook_approval_reject",
        "HOLD": "ebook_approval_hold",
    }
    return {
        "team": {"id": "T123"},
        "channel": {"id": "C123"},
        "user": {"id": "U123"},
        "container": {"message_ts": "1720000000.000100"},
        "actions": [
            {
                "action_id": action_ids[decision],
                "value": encode_slack_approval_action(
                    request_id=request_id,
                    token=token,
                    decision=decision,
                ),
            }
        ],
    }


def test_malformed_slack_decision_fails_closed() -> None:
    body = _slack_body(request_id="request", token="token")
    body["actions"][0]["value"] = "not-a-valid-action"
    interaction = parse_slack_approval_interaction(body)
    with pytest.raises(SlackApprovalSocketError):
        SlackApprovalSocketService(
            SimpleNamespace(), _slack_config()
        ).process_interaction(interaction)


def test_nonexistent_slack_request_fails_closed(isolated_database) -> None:
    with isolated_database() as session:
        interaction = parse_slack_approval_interaction(
            _slack_body(request_id="00000000-0000-4000-8000-000000000000", token="x")
        )
        with pytest.raises(SlackApprovalSocketError) as error:
            SlackApprovalSocketService(session, _slack_config()).process_interaction(
                interaction
            )
        assert error.value.code == "request_not_found"


def test_expired_slack_request_fails_closed_without_post_id_mutation(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item, ticket, request = _bound_slack_request(session, "SLACK-EXPIRED")
        now = datetime.now(timezone.utc)
        request.requested_at = now - timedelta(minutes=2)
        request.expires_at = now - timedelta(minutes=1)
        session.commit()
        interaction = parse_slack_approval_interaction(
            _slack_body(request_id=ticket.request_id, token=ticket.token)
        )
        with pytest.raises(SlackApprovalSocketError) as error:
            SlackApprovalSocketService(session, _slack_config()).process_interaction(
                interaction
            )
        session.expire_all()
        assert error.value.code == "request_expired"
        assert session.get(EbookItem, item.id).wordpress_post_id == "777"
        assert session.get(WorkflowApprovalRequest, request.id).status == "PENDING"


def test_slack_replay_is_rejected_without_post_id_mutation(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item, ticket, _ = _bound_slack_request(session, "SLACK-REPLAY")
        interaction = parse_slack_approval_interaction(
            _slack_body(request_id=ticket.request_id, token=ticket.token)
        )
        first = SlackApprovalSocketService(
            session, _slack_config(mode="LIVE")
        ).process_interaction(interaction)
        with pytest.raises(SlackApprovalSocketError) as error:
            SlackApprovalSocketService(
                session, _slack_config(mode="LIVE")
            ).process_interaction(interaction)
        session.expire_all()
        assert first.code == "decision_applied"
        assert error.value.code == "request_not_pending"
        assert session.get(EbookItem, item.id).wordpress_post_id == "777"


def test_slack_request_for_other_workflow_is_rejected_by_binding(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item_a, _, _ = _bound_slack_request(session, "SLACK-BIND-A")
        item_b, ticket_b, request_b = _bound_slack_request(session, "SLACK-BIND-B")
        request_b.slack_message_ts = "1720000000.999999"
        session.commit()
        interaction = parse_slack_approval_interaction(
            _slack_body(request_id=ticket_b.request_id, token=ticket_b.token)
        )
        with pytest.raises(SlackApprovalSocketError) as error:
            SlackApprovalSocketService(session, _slack_config()).process_interaction(
                interaction
            )
        session.expire_all()
        assert error.value.code == "message_binding_mismatch"
        assert session.get(EbookItem, item_a.id).workflow_status == "REVIEW"
        assert session.get(EbookItem, item_b.id).workflow_status == "REVIEW"


def test_slack_reject_only_applies_allowed_transition_and_preserves_post_id(
    isolated_database,
) -> None:
    with isolated_database() as session:
        item, ticket, request = _bound_slack_request(session, "SLACK-REJECT")
        interaction = parse_slack_approval_interaction(
            _slack_body(
                request_id=ticket.request_id,
                token=ticket.token,
                decision="REJECT",
            )
        )
        result = SlackApprovalSocketService(
            session, _slack_config(mode="LIVE")
        ).process_interaction(interaction)
        session.expire_all()
        refreshed = session.get(EbookItem, item.id)
        assert result.request_status == "REJECTED"
        assert refreshed.workflow_status == "REVIEW"
        assert refreshed.review_status == "REJECTED"
        assert refreshed.wordpress_post_id == "777"
        assert session.get(WorkflowApprovalRequest, request.id).status == "REJECTED"
