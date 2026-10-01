from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone
import json
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.db.models.x_post_draft import XPostDraft
from app.services.slack_approval_socket_service import (
    SlackApprovalSocketConfig,
)


X_POST_DRAFT_OPEN_ACTION_ID = (
    "x_post_draft_open_preset"
)

X_POST_DRAFT_VIEW_CALLBACK_ID = (
    "x_post_draft_preset_submit"
)

DATE_BLOCK_ID = "x_post_draft_schedule_date"
DATE_ACTION_ID = "x_post_draft_schedule_date_value"

TIME_BLOCK_ID = "x_post_draft_schedule_time"
TIME_ACTION_ID = "x_post_draft_schedule_time_value"

PAID_BLOCK_ID = "x_post_draft_paid_partnership"
PAID_ACTION_ID = "x_post_draft_paid_partnership_value"

PAID_OPTION_VALUE = "paid_partnership_enabled"

JST = ZoneInfo("Asia/Tokyo")


class SlackXPostDraftPresetError(
    ValueError
):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.field_errors = (
            field_errors or {}
        )


@dataclass(frozen=True)
class XPostDraftPresetResult:
    draft_id: str
    scheduled_at: datetime | None
    paid_partnership: bool
    channel_id: str
    message_ts: str
    update_payload: dict[str, Any]


def _required(
    value: Any,
    field_name: str,
) -> str:
    normalized = str(
        value or ""
    ).strip()

    if not normalized:
        raise SlackXPostDraftPresetError(
            "invalid_interaction",
            f"{field_name} is missing.",
        )

    return normalized


def _team_id(
    body: dict[str, Any],
) -> str:
    team = body.get("team")

    if isinstance(team, dict):
        return _required(
            team.get("id"),
            "team.id",
        )

    return _required(
        body.get("team_id"),
        "team_id",
    )


def _user_id(
    body: dict[str, Any],
) -> str:
    user = body.get("user")

    if not isinstance(user, dict):
        raise SlackXPostDraftPresetError(
            "invalid_interaction",
            "user is missing.",
        )

    return _required(
        user.get("id"),
        "user.id",
    )


def _authorize(
    body: dict[str, Any],
    config: SlackApprovalSocketConfig,
) -> str:
    team_id = _team_id(body)
    user_id = _user_id(body)

    if team_id != config.team_id:
        raise SlackXPostDraftPresetError(
            "wrong_team",
            "Slack team does not match.",
        )

    if (
        user_id
        not in config.approver_user_ids
    ):
        raise SlackXPostDraftPresetError(
            "unauthorized_user",
            "Slack user is not an approver.",
        )

    return user_id


def _draft(
    session: Session,
    draft_id: str,
) -> XPostDraft:
    draft = session.get(
        XPostDraft,
        draft_id,
    )

    if draft is None:
        raise SlackXPostDraftPresetError(
            "draft_not_found",
            "X post draft was not found.",
        )

    if draft.status == "POSTED":
        raise SlackXPostDraftPresetError(
            "draft_already_posted",
            "Posted draft cannot be edited.",
        )

    return draft


def _scheduled_jst(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if (
        value.tzinfo is None
        or value.utcoffset() is None
    ):
        value = value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(JST)


def _schedule_label(
    value: datetime | None,
) -> str:
    jst_value = _scheduled_jst(value)

    if jst_value is None:
        return "未設定"

    return jst_value.strftime(
        "%Y-%m-%d %H:%M JST"
    )


def _clip(
    value: str,
    limit: int = 1200,
) -> str:
    if len(value) <= limit:
        return value

    return (
        value[: limit - 1]
        + "…"
    )


def build_x_post_draft_settings_message(
    draft: XPostDraft,
) -> dict[str, Any]:
    paid_label = (
        "☑ ON"
        if draft.paid_partnership
        else "☐ OFF"
    )

    body = _clip(
        draft.generated_text
    )

    text = (
        "X下書き設定 "
        f"{draft.source_type}/"
        f"{draft.source_id}"
    )

    return {
        "text": text,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "X下書き設定",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*本文*\n"
                        f"{body}"
                    ),
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*予約日時*\n"
                            f"`{_schedule_label(draft.scheduled_at)}`"
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*有料パートナーシップ*\n"
                            f"`{paid_label}`"
                        ),
                    },
                ],
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"`{draft.source_type}` / "
                            f"`{draft.source_id}`"
                        ),
                    },
                ],
            },
            {
                "type": "actions",
                "block_id": (
                    "x_post_draft_preset_actions"
                ),
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": (
                                "予約・パートナー設定"
                            ),
                        },
                        "style": "primary",
                        "action_id": (
                            X_POST_DRAFT_OPEN_ACTION_ID
                        ),
                        "value": draft.id,
                    },
                ],
            },
        ],
    }


def build_x_post_draft_settings_modal(
    draft: XPostDraft,
    *,
    channel_id: str,
    message_ts: str,
) -> dict[str, Any]:
    initial = _scheduled_jst(
        draft.scheduled_at
    )

    date_element: dict[str, Any] = {
        "type": "datepicker",
        "action_id": DATE_ACTION_ID,
        "placeholder": {
            "type": "plain_text",
            "text": "予約日を選択",
        },
    }

    time_element: dict[str, Any] = {
        "type": "timepicker",
        "action_id": TIME_ACTION_ID,
        "placeholder": {
            "type": "plain_text",
            "text": "予約時刻を選択",
        },
    }

    if initial is not None:
        date_element["initial_date"] = (
            initial.strftime("%Y-%m-%d")
        )
        time_element["initial_time"] = (
            initial.strftime("%H:%M")
        )

    paid_element: dict[str, Any] = {
        "type": "checkboxes",
        "action_id": PAID_ACTION_ID,
        "options": [
            {
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*有料パートナーシップを有効にする*"
                    ),
                },
                "value": PAID_OPTION_VALUE,
            }
        ],
    }

    if draft.paid_partnership:
        paid_element["initial_options"] = [
            paid_element["options"][0]
        ]

    private_metadata = json.dumps(
        {
            "draft_id": draft.id,
            "channel_id": channel_id,
            "message_ts": message_ts,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return {
        "type": "modal",
        "callback_id": (
            X_POST_DRAFT_VIEW_CALLBACK_ID
        ),
        "private_metadata": private_metadata,
        "title": {
            "type": "plain_text",
            "text": "X下書き設定",
        },
        "submit": {
            "type": "plain_text",
            "text": "保存",
        },
        "close": {
            "type": "plain_text",
            "text": "キャンセル",
        },
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*予約日時と有料パートナーシップを"
                        "設定します。*\n"
                        "予約日時は日本時間（JST）です。"
                    ),
                },
            },
            {
                "type": "input",
                "block_id": DATE_BLOCK_ID,
                "optional": True,
                "label": {
                    "type": "plain_text",
                    "text": "予約日（JST）",
                },
                "element": date_element,
            },
            {
                "type": "input",
                "block_id": TIME_BLOCK_ID,
                "optional": True,
                "label": {
                    "type": "plain_text",
                    "text": "予約時刻（JST）",
                },
                "element": time_element,
            },
            {
                "type": "input",
                "block_id": PAID_BLOCK_ID,
                "optional": True,
                "label": {
                    "type": "plain_text",
                    "text": "有料パートナーシップ",
                },
                "element": paid_element,
            },
        ],
    }


def _selected(
    values: dict[str, Any],
    block_id: str,
    action_id: str,
) -> dict[str, Any]:
    block = values.get(
        block_id,
        {},
    )

    if not isinstance(block, dict):
        return {}

    selected = block.get(
        action_id,
        {},
    )

    return (
        selected
        if isinstance(selected, dict)
        else {}
    )


class XPostDraftSlackPresetService:
    def __init__(
        self,
        session: Session,
        config: SlackApprovalSocketConfig,
    ) -> None:
        self.session = session
        self.config = config

    def build_open_view(
        self,
        body: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        _authorize(
            body,
            self.config,
        )

        actions = body.get("actions")

        if (
            not isinstance(actions, list)
            or not actions
            or not isinstance(
                actions[0],
                dict,
            )
        ):
            raise SlackXPostDraftPresetError(
                "invalid_interaction",
                "Slack action is missing.",
            )

        action = actions[0]

        if (
            action.get("action_id")
            != X_POST_DRAFT_OPEN_ACTION_ID
        ):
            raise SlackXPostDraftPresetError(
                "wrong_action",
                "Unexpected Slack action.",
            )

        draft_id = _required(
            action.get("value"),
            "actions[0].value",
        )

        trigger_id = _required(
            body.get("trigger_id"),
            "trigger_id",
        )

        channel = body.get(
            "channel",
            {},
        )
        container = body.get(
            "container",
            {},
        )
        message = body.get(
            "message",
            {},
        )

        channel_id = str(
            (
                channel.get("id")
                if isinstance(
                    channel,
                    dict,
                )
                else None
            )
            or (
                container.get(
                    "channel_id"
                )
                if isinstance(
                    container,
                    dict,
                )
                else None
            )
            or ""
        ).strip()

        message_ts = str(
            (
                container.get(
                    "message_ts"
                )
                if isinstance(
                    container,
                    dict,
                )
                else None
            )
            or (
                message.get("ts")
                if isinstance(
                    message,
                    dict,
                )
                else None
            )
            or ""
        ).strip()

        if (
            channel_id
            != self.config.channel_id
        ):
            raise SlackXPostDraftPresetError(
                "wrong_channel",
                "Slack channel does not match.",
            )

        if not message_ts:
            raise SlackXPostDraftPresetError(
                "invalid_interaction",
                "message_ts is missing.",
            )

        draft = _draft(
            self.session,
            draft_id,
        )

        view = (
            build_x_post_draft_settings_modal(
                draft,
                channel_id=channel_id,
                message_ts=message_ts,
            )
        )

        return trigger_id, view

    def apply_submission(
        self,
        body: dict[str, Any],
    ) -> XPostDraftPresetResult:
        _authorize(
            body,
            self.config,
        )

        view = body.get("view")

        if not isinstance(view, dict):
            raise SlackXPostDraftPresetError(
                "invalid_submission",
                "view is missing.",
            )

        if (
            view.get("callback_id")
            != X_POST_DRAFT_VIEW_CALLBACK_ID
        ):
            raise SlackXPostDraftPresetError(
                "wrong_callback",
                "Unexpected modal callback.",
            )

        raw_metadata = _required(
            view.get("private_metadata"),
            "view.private_metadata",
        )

        try:
            metadata = json.loads(
                raw_metadata
            )
        except json.JSONDecodeError as exc:
            raise SlackXPostDraftPresetError(
                "invalid_metadata",
                "Modal metadata is invalid.",
            ) from exc

        if not isinstance(
            metadata,
            dict,
        ):
            raise SlackXPostDraftPresetError(
                "invalid_metadata",
                "Modal metadata must be an object.",
            )

        draft_id = _required(
            metadata.get("draft_id"),
            "draft_id",
        )

        channel_id = _required(
            metadata.get("channel_id"),
            "channel_id",
        )

        message_ts = _required(
            metadata.get("message_ts"),
            "message_ts",
        )

        if (
            channel_id
            != self.config.channel_id
        ):
            raise SlackXPostDraftPresetError(
                "wrong_channel",
                "Slack channel does not match.",
            )

        state = view.get(
            "state",
            {},
        )

        values = (
            state.get("values", {})
            if isinstance(
                state,
                dict,
            )
            else {}
        )

        if not isinstance(
            values,
            dict,
        ):
            values = {}

        date_state = _selected(
            values,
            DATE_BLOCK_ID,
            DATE_ACTION_ID,
        )
        time_state = _selected(
            values,
            TIME_BLOCK_ID,
            TIME_ACTION_ID,
        )
        paid_state = _selected(
            values,
            PAID_BLOCK_ID,
            PAID_ACTION_ID,
        )

        selected_date = str(
            date_state.get(
                "selected_date"
            )
            or ""
        ).strip()

        selected_time = str(
            time_state.get(
                "selected_time"
            )
            or ""
        ).strip()

        if bool(selected_date) != bool(
            selected_time
        ):
            field_errors = {}

            if not selected_date:
                field_errors[
                    DATE_BLOCK_ID
                ] = (
                    "予約時刻を使う場合は"
                    "予約日も指定してください。"
                )

            if not selected_time:
                field_errors[
                    TIME_BLOCK_ID
                ] = (
                    "予約日を使う場合は"
                    "予約時刻も指定してください。"
                )

            raise SlackXPostDraftPresetError(
                "incomplete_schedule",
                "Date and time must be set together.",
                field_errors=field_errors,
            )

        scheduled_at: datetime | None = None

        if selected_date:
            try:
                parsed_date = (
                    date.fromisoformat(
                        selected_date
                    )
                )
                parsed_time = (
                    time.fromisoformat(
                        selected_time
                    )
                )
            except ValueError as exc:
                raise SlackXPostDraftPresetError(
                    "invalid_schedule",
                    "Schedule is invalid.",
                    field_errors={
                        DATE_BLOCK_ID: (
                            "予約日時の形式が"
                            "正しくありません。"
                        )
                    },
                ) from exc

            scheduled_at = datetime.combine(
                parsed_date,
                parsed_time,
                tzinfo=JST,
            )

        selected_options = (
            paid_state.get(
                "selected_options",
                [],
            )
        )

        paid_partnership = False

        if isinstance(
            selected_options,
            list,
        ):
            paid_partnership = any(
                isinstance(
                    option,
                    dict,
                )
                and option.get("value")
                == PAID_OPTION_VALUE
                for option
                in selected_options
            )

        draft = _draft(
            self.session,
            draft_id,
        )

        if self.config.mode == "DRY_RUN":
            return XPostDraftPresetResult(
                draft_id=draft.id,
                scheduled_at=scheduled_at,
                paid_partnership=(
                    paid_partnership
                ),
                channel_id=channel_id,
                message_ts=message_ts,
                update_payload=(
                    build_x_post_draft_settings_message(
                        draft
                    )
                ),
            )

        draft.scheduled_at = scheduled_at
        draft.paid_partnership = (
            paid_partnership
        )
        draft.updated_at = datetime.now(
            timezone.utc
        )

        self.session.flush()

        payload = (
            build_x_post_draft_settings_message(
                draft
            )
        )

        return XPostDraftPresetResult(
            draft_id=draft.id,
            scheduled_at=draft.scheduled_at,
            paid_partnership=(
                draft.paid_partnership
            ),
            channel_id=channel_id,
            message_ts=message_ts,
            update_payload=payload,
        )
