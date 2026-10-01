from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.models.ebook import EbookItem  # noqa: F401
from app.db.models.x_post_draft import XPostDraft
from app.services.slack_approval_socket_service import (
    SlackApprovalSocketConfig,
)
from app.services.x_post_draft_slack_preset_service import (
    DATE_ACTION_ID,
    DATE_BLOCK_ID,
    PAID_ACTION_ID,
    PAID_BLOCK_ID,
    TIME_ACTION_ID,
    TIME_BLOCK_ID,
    X_POST_DRAFT_OPEN_ACTION_ID,
    X_POST_DRAFT_VIEW_CALLBACK_ID,
    SlackXPostDraftPresetError,
    XPostDraftSlackPresetService,
    build_x_post_draft_settings_message,
    build_x_post_draft_settings_modal,
)


def config() -> SlackApprovalSocketConfig:
    return SlackApprovalSocketConfig(
        bot_token="xoxb-test",
        app_token="xapp-test",
        team_id="TTEST",
        channel_id="CTEST",
        approver_user_ids=frozenset(
            {"UTEST"}
        ),
        mode="LIVE",
        live_confirmed=True,
    )


def make_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:"
    )
    Base.metadata.create_all(
        engine
    )
    return Session(engine)


def add_draft(
    session: Session,
    *,
    scheduled_at=None,
    paid=True,
) -> XPostDraft:
    draft = XPostDraft(
        source_type="new_release",
        source_id="book-001",
        generated_text=(
            "テスト投稿 #PR "
            "https://example.test/"
        ),
        scheduled_at=scheduled_at,
        paid_partnership=paid,
        status="DRAFT",
    )
    session.add(draft)
    session.flush()
    return draft


def test_message_contains_settings_button():
    with make_session() as session:
        draft = add_draft(
            session
        )

        payload = (
            build_x_post_draft_settings_message(
                draft
            )
        )

        button = (
            payload["blocks"][-1]
            ["elements"][0]
        )

        assert (
            button["action_id"]
            == X_POST_DRAFT_OPEN_ACTION_ID
        )
        assert button["value"] == draft.id
        assert "☑ ON" in str(
            payload
        )


def test_modal_preloads_jst_and_paid_checkbox():
    jst = timezone(
        timedelta(hours=9)
    )

    with make_session() as session:
        draft = add_draft(
            session,
            scheduled_at=datetime(
                2026,
                9,
                29,
                12,
                15,
                tzinfo=jst,
            ),
            paid=True,
        )

        modal = (
            build_x_post_draft_settings_modal(
                draft,
                channel_id="CTEST",
                message_ts="123.456",
            )
        )

        assert (
            modal["callback_id"]
            == X_POST_DRAFT_VIEW_CALLBACK_ID
        )

        date_element = (
            modal["blocks"][1]["element"]
        )
        time_element = (
            modal["blocks"][2]["element"]
        )
        paid_element = (
            modal["blocks"][3]["element"]
        )

        assert (
            date_element["initial_date"]
            == "2026-09-29"
        )
        assert (
            time_element["initial_time"]
            == "12:15"
        )
        assert (
            paid_element["initial_options"][0]
            ["value"]
            == "paid_partnership_enabled"
        )


def test_open_action_builds_modal():
    with make_session() as session:
        draft = add_draft(
            session
        )

        body = {
            "team": {
                "id": "TTEST",
            },
            "user": {
                "id": "UTEST",
            },
            "channel": {
                "id": "CTEST",
            },
            "trigger_id": "TRIGGER",
            "container": {
                "channel_id": "CTEST",
                "message_ts": "123.456",
            },
            "actions": [
                {
                    "action_id": (
                        X_POST_DRAFT_OPEN_ACTION_ID
                    ),
                    "value": draft.id,
                }
            ],
        }

        trigger_id, modal = (
            XPostDraftSlackPresetService(
                session,
                config(),
            ).build_open_view(
                body
            )
        )

        assert trigger_id == "TRIGGER"
        assert (
            modal["callback_id"]
            == X_POST_DRAFT_VIEW_CALLBACK_ID
        )


def test_submission_saves_jst_as_aware_datetime():
    with make_session() as session:
        draft = add_draft(
            session,
            paid=True,
        )

        body = {
            "team": {
                "id": "TTEST",
            },
            "user": {
                "id": "UTEST",
            },
            "view": {
                "callback_id": (
                    X_POST_DRAFT_VIEW_CALLBACK_ID
                ),
                "private_metadata": (
                    '{"draft_id":"'
                    + draft.id
                    + '","channel_id":"CTEST",'
                    '"message_ts":"123.456"}'
                ),
                "state": {
                    "values": {
                        DATE_BLOCK_ID: {
                            DATE_ACTION_ID: {
                                "selected_date": (
                                    "2026-09-29"
                                )
                            }
                        },
                        TIME_BLOCK_ID: {
                            TIME_ACTION_ID: {
                                "selected_time": (
                                    "12:15"
                                )
                            }
                        },
                        PAID_BLOCK_ID: {
                            PAID_ACTION_ID: {
                                "selected_options": []
                            }
                        },
                    }
                },
            },
        }

        result = (
            XPostDraftSlackPresetService(
                session,
                config(),
            ).apply_submission(
                body
            )
        )

        session.commit()
        session.expire_all()

        stored = session.get(
            XPostDraft,
            draft.id,
        )

        assert stored is not None
        assert stored.scheduled_at == datetime(
            2026,
            9,
            29,
            3,
            15,
            tzinfo=timezone.utc,
        )
        assert (
            stored.paid_partnership
            is False
        )

        assert (
            result.channel_id
            == "CTEST"
        )
        assert (
            result.message_ts
            == "123.456"
        )


def test_submission_requires_date_and_time_together():
    with make_session() as session:
        draft = add_draft(
            session
        )

        body = {
            "team": {
                "id": "TTEST",
            },
            "user": {
                "id": "UTEST",
            },
            "view": {
                "callback_id": (
                    X_POST_DRAFT_VIEW_CALLBACK_ID
                ),
                "private_metadata": (
                    '{"draft_id":"'
                    + draft.id
                    + '","channel_id":"CTEST",'
                    '"message_ts":"123.456"}'
                ),
                "state": {
                    "values": {
                        DATE_BLOCK_ID: {
                            DATE_ACTION_ID: {
                                "selected_date": (
                                    "2026-09-29"
                                )
                            }
                        },
                        TIME_BLOCK_ID: {
                            TIME_ACTION_ID: {
                                "selected_time": None
                            }
                        },
                        PAID_BLOCK_ID: {
                            PAID_ACTION_ID: {
                                "selected_options": []
                            }
                        },
                    }
                },
            },
        }

        with pytest.raises(
            SlackXPostDraftPresetError
        ) as exc:
            XPostDraftSlackPresetService(
                session,
                config(),
            ).apply_submission(
                body
            )

        assert (
            exc.value.code
            == "incomplete_schedule"
        )
        assert (
            TIME_BLOCK_ID
            in exc.value.field_errors
        )


def test_unauthorized_user_is_rejected():
    with make_session() as session:
        draft = add_draft(
            session
        )

        body = {
            "team": {
                "id": "TTEST",
            },
            "user": {
                "id": "UNAUTHORIZED",
            },
            "channel": {
                "id": "CTEST",
            },
            "trigger_id": "TRIGGER",
            "container": {
                "channel_id": "CTEST",
                "message_ts": "123.456",
            },
            "actions": [
                {
                    "action_id": (
                        X_POST_DRAFT_OPEN_ACTION_ID
                    ),
                    "value": draft.id,
                }
            ],
        }

        with pytest.raises(
            SlackXPostDraftPresetError,
            match="approver",
        ):
            XPostDraftSlackPresetService(
                session,
                config(),
            ).build_open_view(
                body
            )


def test_dry_run_submission_does_not_mutate_draft():
    dry_config = SlackApprovalSocketConfig(
        bot_token="xoxb-test",
        app_token="xapp-test",
        team_id="TTEST",
        channel_id="CTEST",
        approver_user_ids=frozenset(
            {"UTEST"}
        ),
        mode="DRY_RUN",
        live_confirmed=False,
    )

    with make_session() as session:
        draft = add_draft(
            session,
            scheduled_at=None,
            paid=True,
        )

        draft_id = draft.id

        # Persist the baseline draft first.
        # The DRY_RUN rollback below must only prove that
        # the preset change itself is not written.
        session.commit()
        session.expire_all()

        draft = session.get(
            XPostDraft,
            draft_id,
        )

        assert draft is not None
        assert draft.scheduled_at is None
        assert draft.paid_partnership is True

        body = {
            "team": {
                "id": "TTEST",
            },
            "user": {
                "id": "UTEST",
            },
            "view": {
                "callback_id": (
                    X_POST_DRAFT_VIEW_CALLBACK_ID
                ),
                "private_metadata": (
                    '{"draft_id":"'
                    + draft_id
                    + '","channel_id":"CTEST",'
                    '"message_ts":"123.456"}'
                ),
                "state": {
                    "values": {
                        DATE_BLOCK_ID: {
                            DATE_ACTION_ID: {
                                "selected_date": (
                                    "2026-09-29"
                                )
                            }
                        },
                        TIME_BLOCK_ID: {
                            TIME_ACTION_ID: {
                                "selected_time": (
                                    "12:15"
                                )
                            }
                        },
                        PAID_BLOCK_ID: {
                            PAID_ACTION_ID: {
                                "selected_options": []
                            }
                        },
                    }
                },
            },
        }

        result = (
            XPostDraftSlackPresetService(
                session,
                dry_config,
            ).apply_submission(
                body
            )
        )

        assert result.scheduled_at is not None
        assert (
            result.paid_partnership
            is False
        )

        assert draft.scheduled_at is None
        assert (
            draft.paid_partnership
            is True
        )

        assert not session.dirty

        session.rollback()
        session.expire_all()

        stored = session.get(
            XPostDraft,
            draft_id,
        )

        assert stored is not None
        assert stored.scheduled_at is None
        assert (
            stored.paid_partnership
            is True
        )
