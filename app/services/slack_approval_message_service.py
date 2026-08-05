from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import hmac
import json
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy.orm import Session

from app.db.models import (
    EbookItem,
    WorkflowApprovalRequest,
)
from app.db.repositories.workflow_approval_repository import (
    WorkflowApprovalRepository,
)


_ACTION_VALUE_VERSION = 1

_ALLOWED_DECISIONS = frozenset(
    {
        "APPROVE",
        "REJECT",
        "HOLD",
    }
)

MAX_MESSAGE_BLOCKS = 50
MAX_ACTION_ELEMENTS = 25
MAX_ACTION_ID_LENGTH = 255
MAX_BLOCK_ID_LENGTH = 255
MAX_BUTTON_TEXT_LENGTH = 75
MAX_BUTTON_VALUE_LENGTH = 2000
MAX_BUTTON_URL_LENGTH = 3000


class SlackApprovalMessageError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SlackApprovalAction:
    request_id: str
    token: str
    decision: str


@dataclass(frozen=True)
class SlackApprovalMessageContext:
    request_id: str
    approval_type: str
    expected_current_status: str
    requested_status: str
    expires_at: datetime
    item_id: str
    title: str
    release_date: date | datetime | str | None
    wordpress_status: str
    x_status: str
    review_status: str
    affiliate_status: str
    image_status: str
    publish_ready: bool


@dataclass(frozen=True)
class SlackMessageBindingResult:
    request_id: str
    team_id: str
    channel_id: str
    message_ts: str
    created: bool


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def _clip(value: Any, max_length: int) -> str:
    text = str(value or "")

    if len(text) <= max_length:
        return text

    if max_length <= 1:
        return text[:max_length]

    return text[: max_length - 1] + "…"


def _slack_escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_release_date(
    value: date | datetime | str | None,
) -> str:
    if value is None:
        return "未設定"

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    normalized = str(value).strip()
    return normalized or "未設定"


def _format_expiration(value: datetime) -> str:
    utc_value = _as_utc(value)

    return utc_value.strftime(
        "%Y-%m-%d %H:%M UTC"
    )


def _plain_text(text: str) -> dict[str, Any]:
    return {
        "type": "plain_text",
        "text": text,
        "emoji": True,
    }


def _confirm_object(
    *,
    title: str,
    text: str,
    confirm: str,
    style: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "title": _plain_text(_clip(title, 100)),
        "text": {
            "type": "mrkdwn",
            "text": _clip(text, 300),
        },
        "confirm": _plain_text(_clip(confirm, 30)),
        "deny": _plain_text("キャンセル"),
    }

    if style is not None:
        result["style"] = style

    return result


def encode_slack_approval_action(
    *,
    request_id: str,
    token: str,
    decision: str,
) -> str:
    normalized_request_id = (
        request_id or ""
    ).strip()

    normalized_token = (token or "").strip()
    normalized_decision = (
        decision or ""
    ).strip().upper()

    if not normalized_request_id:
        raise SlackApprovalMessageError(
            "invalid_request_id",
            "request_id is required.",
        )

    if not normalized_token:
        raise SlackApprovalMessageError(
            "invalid_token",
            "approval token is required.",
        )

    if normalized_decision not in _ALLOWED_DECISIONS:
        raise SlackApprovalMessageError(
            "invalid_decision",
            "approval decision is not supported.",
        )

    encoded = json.dumps(
        {
            "v": _ACTION_VALUE_VERSION,
            "r": normalized_request_id,
            "t": normalized_token,
            "d": normalized_decision,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    if len(encoded) > MAX_BUTTON_VALUE_LENGTH:
        raise SlackApprovalMessageError(
            "action_value_too_long",
            "Slack button action value is too long.",
        )

    return encoded


def decode_slack_approval_action(
    value: str,
) -> SlackApprovalAction:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SlackApprovalMessageError(
            "invalid_action_value",
            "Slack action value is not valid JSON.",
        ) from exc

    if not isinstance(decoded, dict):
        raise SlackApprovalMessageError(
            "invalid_action_value",
            "Slack action value must be an object.",
        )

    if decoded.get("v") != _ACTION_VALUE_VERSION:
        raise SlackApprovalMessageError(
            "unsupported_action_version",
            "Slack action value version is unsupported.",
        )

    request_id = str(decoded.get("r") or "").strip()
    token = str(decoded.get("t") or "").strip()
    decision = str(
        decoded.get("d") or ""
    ).strip().upper()

    if not request_id or not token:
        raise SlackApprovalMessageError(
            "invalid_action_value",
            "Slack action value is incomplete.",
        )

    if decision not in _ALLOWED_DECISIONS:
        raise SlackApprovalMessageError(
            "invalid_decision",
            "Slack action decision is unsupported.",
        )

    return SlackApprovalAction(
        request_id=request_id,
        token=token,
        decision=decision,
    )


def _validate_gui_url(
    gui_url: str | None,
) -> str | None:
    normalized = (gui_url or "").strip()

    if not normalized:
        return None

    parsed = urlsplit(normalized)

    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise SlackApprovalMessageError(
            "invalid_gui_url",
            "GUI URL must be an HTTPS URL "
            "without embedded credentials.",
        )

    if len(normalized) > MAX_BUTTON_URL_LENGTH:
        raise SlackApprovalMessageError(
            "gui_url_too_long",
            "GUI URL exceeds Slack button limit.",
        )

    return normalized


def _button(
    *,
    text: str,
    action_id: str,
    value: str,
    confirm: dict[str, Any],
    style: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "button",
        "text": _plain_text(
            _clip(text, MAX_BUTTON_TEXT_LENGTH)
        ),
        "action_id": action_id,
        "value": value,
        "confirm": confirm,
    }

    if style is not None:
        result["style"] = style

    return result


def build_slack_approval_message(
    context: SlackApprovalMessageContext,
    *,
    token: str,
    gui_url: str | None = None,
) -> dict[str, Any]:
    normalized_gui_url = _validate_gui_url(gui_url)

    title = _clip(
        context.title or "タイトル未設定",
        180,
    )
    release_date = _format_release_date(
        context.release_date
    )

    escaped_title = _slack_escape(title)

    approve_value = encode_slack_approval_action(
        request_id=context.request_id,
        token=token,
        decision="APPROVE",
    )

    reject_value = encode_slack_approval_action(
        request_id=context.request_id,
        token=token,
        decision="REJECT",
    )

    hold_value = encode_slack_approval_action(
        request_id=context.request_id,
        token=token,
        decision="HOLD",
    )

    action_elements: list[dict[str, Any]] = [
        _button(
            text=(
                f"承認して"
                f"{context.requested_status}へ"
            ),
            action_id="ebook_approval_approve",
            value=approve_value,
            style="primary",
            confirm=_confirm_object(
                title="承認確認",
                text=(
                    f"*{escaped_title}* を "
                    f"`{context.requested_status}` "
                    "へ進めます。"
                ),
                confirm="承認する",
                style="primary",
            ),
        ),
        _button(
            text="差戻し",
            action_id="ebook_approval_reject",
            value=reject_value,
            style="danger",
            confirm=_confirm_object(
                title="差戻し確認",
                text=(
                    f"*{escaped_title}* を"
                    "差戻し状態にします。"
                ),
                confirm="差戻す",
                style="danger",
            ),
        ),
        _button(
            text="保留",
            action_id="ebook_approval_hold",
            value=hold_value,
            confirm=_confirm_object(
                title="保留確認",
                text=(
                    f"*{escaped_title}* の"
                    "ワークフローを保留します。"
                ),
                confirm="保留する",
            ),
        ),
    ]

    if normalized_gui_url is not None:
        action_elements.append(
            {
                "type": "button",
                "text": _plain_text("GUIで確認"),
                "action_id": "ebook_approval_open_gui",
                "url": normalized_gui_url,
            }
        )

    fallback_text = (
        "電子書籍記事の承認待ち: "
        f"{title} / "
        f"{context.expected_current_status}"
        f" → {context.requested_status}"
    )

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "block_id": (
                f"ebook_approval_header_"
                f"{context.request_id}"
            ),
            "text": _plain_text(
                "電子書籍記事 承認待ち"
            ),
        },
        {
            "type": "section",
            "block_id": (
                f"ebook_approval_item_"
                f"{context.request_id}"
            ),
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*作品名*\n{escaped_title}\n"
                    f"*発売日*\n`{release_date}`"
                ),
            },
        },
        {
            "type": "section",
            "block_id": (
                f"ebook_approval_state_a_"
                f"{context.request_id}"
            ),
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "*Workflow*\n"
                        f"`{context.expected_current_status}`"
                        f" → `{context.requested_status}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*Review*\n"
                        f"`{context.review_status}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*WordPress*\n"
                        f"`{context.wordpress_status}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*X*\n"
                        f"`{context.x_status}`"
                    ),
                },
            ],
        },
        {
            "type": "section",
            "block_id": (
                f"ebook_approval_state_b_"
                f"{context.request_id}"
            ),
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "*Affiliate*\n"
                        f"`{context.affiliate_status}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*Image*\n"
                        f"`{context.image_status}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*Publish Ready*\n"
                        f"`{str(context.publish_ready).upper()}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "*承認種別*\n"
                        f"`{context.approval_type}`"
                    ),
                },
            ],
        },
        {
            "type": "context",
            "block_id": (
                f"ebook_approval_context_"
                f"{context.request_id}"
            ),
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        "承認要求ID: "
                        f"`{context.request_id}`"
                    ),
                },
                {
                    "type": "mrkdwn",
                    "text": (
                        "有効期限: "
                        f"`{_format_expiration(context.expires_at)}`"
                    ),
                },
            ],
        },
        {
            "type": "divider",
            "block_id": (
                f"ebook_approval_divider_"
                f"{context.request_id}"
            ),
        },
        {
            "type": "actions",
            "block_id": (
                f"ebook_approval_actions_"
                f"{context.request_id}"
            ),
            "elements": action_elements,
        },
    ]

    payload = {
        "text": fallback_text,
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }

    validate_slack_message_payload(payload)

    return payload


def validate_slack_message_payload(
    payload: dict[str, Any],
) -> None:
    text = payload.get("text")

    if not isinstance(text, str) or not text.strip():
        raise SlackApprovalMessageError(
            "missing_fallback_text",
            "Slack message fallback text is required.",
        )

    blocks = payload.get("blocks")

    if not isinstance(blocks, list):
        raise SlackApprovalMessageError(
            "invalid_blocks",
            "Slack message blocks must be a list.",
        )

    if len(blocks) > MAX_MESSAGE_BLOCKS:
        raise SlackApprovalMessageError(
            "too_many_blocks",
            "Slack message contains too many blocks.",
        )

    for block in blocks:
        if not isinstance(block, dict):
            raise SlackApprovalMessageError(
                "invalid_block",
                "Slack block must be an object.",
            )

        block_id = str(
            block.get("block_id") or ""
        )

        if len(block_id) > MAX_BLOCK_ID_LENGTH:
            raise SlackApprovalMessageError(
                "block_id_too_long",
                "Slack block_id exceeds limit.",
            )

        if block.get("type") != "actions":
            continue

        elements = block.get("elements")

        if not isinstance(elements, list):
            raise SlackApprovalMessageError(
                "invalid_actions",
                "Slack actions elements must be a list.",
            )

        if len(elements) > MAX_ACTION_ELEMENTS:
            raise SlackApprovalMessageError(
                "too_many_actions",
                "Slack actions block contains too "
                "many elements.",
            )

        for element in elements:
            if element.get("type") != "button":
                continue

            action_id = str(
                element.get("action_id") or ""
            )

            if len(action_id) > MAX_ACTION_ID_LENGTH:
                raise SlackApprovalMessageError(
                    "action_id_too_long",
                    "Slack action_id exceeds limit.",
                )

            button_text = str(
                element.get("text", {}).get(
                    "text",
                    "",
                )
            )

            if (
                len(button_text)
                > MAX_BUTTON_TEXT_LENGTH
            ):
                raise SlackApprovalMessageError(
                    "button_text_too_long",
                    "Slack button text exceeds limit.",
                )

            value = element.get("value")

            if (
                value is not None
                and len(str(value))
                > MAX_BUTTON_VALUE_LENGTH
            ):
                raise SlackApprovalMessageError(
                    "button_value_too_long",
                    "Slack button value exceeds limit.",
                )

            url = element.get("url")

            if (
                url is not None
                and len(str(url))
                > MAX_BUTTON_URL_LENGTH
            ):
                raise SlackApprovalMessageError(
                    "button_url_too_long",
                    "Slack button URL exceeds limit.",
                )


def redact_slack_approval_message(
    payload: dict[str, Any],
) -> dict[str, Any]:
    redacted = deepcopy(payload)

    for block in redacted.get("blocks", []):
        if block.get("type") != "actions":
            continue

        for element in block.get("elements", []):
            raw_value = element.get("value")

            if raw_value is None:
                continue

            try:
                action = decode_slack_approval_action(
                    raw_value
                )

                element["value"] = json.dumps(
                    {
                        "v": _ACTION_VALUE_VERSION,
                        "r": action.request_id,
                        "t": "[REDACTED]",
                        "d": action.decision,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            except SlackApprovalMessageError:
                element["value"] = "[REDACTED]"

    return redacted


class SlackApprovalMessageService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = WorkflowApprovalRepository(
            session
        )

    def _load_context(
        self,
        *,
        request_id: str,
        token: str,
    ) -> SlackApprovalMessageContext:
        request = self.repository.get(request_id)

        if request is None:
            raise SlackApprovalMessageError(
                "request_not_found",
                "Approval request was not found.",
            )

        if request.status != "PENDING":
            raise SlackApprovalMessageError(
                "request_not_pending",
                "Approval request is no longer pending.",
            )

        supplied_hash = _hash_token(token or "")

        if not hmac.compare_digest(
            supplied_hash,
            request.request_nonce_hash,
        ):
            raise SlackApprovalMessageError(
                "invalid_token",
                "Approval token is invalid.",
            )

        if _as_utc(request.expires_at) <= _utc_now():
            raise SlackApprovalMessageError(
                "request_expired",
                "Approval request has expired.",
            )

        item = self.session.get(
            EbookItem,
            request.ebook_item_id,
        )

        if item is None:
            raise SlackApprovalMessageError(
                "item_not_found",
                "Referenced ebook item was not found.",
            )

        if (
            item.workflow_status
            != request.expected_current_status
        ):
            raise SlackApprovalMessageError(
                "stale_workflow_state",
                "Workflow state no longer matches "
                "the approval request.",
            )

        return SlackApprovalMessageContext(
            request_id=request.id,
            approval_type=request.approval_type,
            expected_current_status=(
                request.expected_current_status
            ),
            requested_status=request.requested_status,
            expires_at=request.expires_at,
            item_id=item.id,
            title=item.title,
            release_date=item.release_date,
            wordpress_status=item.wordpress_status,
            x_status=item.x_status,
            review_status=item.review_status,
            affiliate_status=item.affiliate_status,
            image_status=item.image_status,
            publish_ready=item.publish_ready,
        )

    def build_message(
        self,
        *,
        request_id: str,
        token: str,
        gui_url: str | None = None,
    ) -> dict[str, Any]:
        context = self._load_context(
            request_id=request_id,
            token=token,
        )

        return build_slack_approval_message(
            context,
            token=token,
            gui_url=gui_url,
        )

    def register_sent_message(
        self,
        *,
        request_id: str,
        team_id: str,
        channel_id: str,
        message_ts: str,
    ) -> SlackMessageBindingResult:
        try:
            request, created = (
                self.repository.bind_slack_message(
                    request_id=request_id,
                    team_id=team_id,
                    channel_id=channel_id,
                    message_ts=message_ts,
                )
            )

            self.session.commit()

        except ValueError as exc:
            self.session.rollback()

            raise SlackApprovalMessageError(
                "message_binding_failed",
                str(exc),
            ) from exc

        except Exception:
            self.session.rollback()
            raise

        return SlackMessageBindingResult(
            request_id=request.id,
            team_id=request.slack_team_id or "",
            channel_id=request.slack_channel_id or "",
            message_ts=request.slack_message_ts or "",
            created=created,
        )
