from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Any, Mapping

from app.services.slack_approval_message_service import (
    MAX_BUTTON_VALUE_LENGTH,
    validate_slack_message_payload,
)


APPROVE_ACTION_ID = "sale_campaign_approve"
HOLD_ACTION_ID = "sale_campaign_hold"
REJECT_ACTION_ID = "sale_campaign_reject"
ACTION_IDS = (APPROVE_ACTION_ID, HOLD_ACTION_ID, REJECT_ACTION_ID)
_ALLOWED_DECISIONS = frozenset({"APPROVE", "HOLD", "REJECT"})


class SlackSaleApprovalMessageError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class SlackSaleApprovalAction:
    request_id: str
    campaign_id: str
    nonce: str
    decision: str


def _required(value: Any, name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise SlackSaleApprovalMessageError(
            f"invalid_{name}", f"{name} is required."
        )
    return normalized


def _escape(value: Any) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _plain(value: str) -> dict[str, Any]:
    return {"type": "plain_text", "text": value, "emoji": True}


def encode_sale_approval_action(
    *, request_id: str, campaign_id: str, nonce: str, decision: str
) -> str:
    normalized_decision = _required(decision, "decision").upper()
    if normalized_decision not in _ALLOWED_DECISIONS:
        raise SlackSaleApprovalMessageError(
            "invalid_decision", "Sale approval decision is unsupported."
        )
    value = json.dumps(
        {
            "v": 1,
            "r": _required(request_id, "request_id"),
            "c": _required(campaign_id, "campaign_id"),
            "t": _required(nonce, "nonce"),
            "d": normalized_decision,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(value) > MAX_BUTTON_VALUE_LENGTH:
        raise SlackSaleApprovalMessageError(
            "action_value_too_long", "Slack action value is too long."
        )
    return value


def decode_sale_approval_action(value: str) -> SlackSaleApprovalAction:
    try:
        decoded = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SlackSaleApprovalMessageError(
            "invalid_action_value", "Slack action value is invalid."
        ) from exc
    if not isinstance(decoded, dict) or decoded.get("v") != 1:
        raise SlackSaleApprovalMessageError(
            "invalid_action_value", "Slack action value version is invalid."
        )
    decision = _required(decoded.get("d"), "decision").upper()
    if decision not in _ALLOWED_DECISIONS:
        raise SlackSaleApprovalMessageError(
            "invalid_decision", "Sale approval decision is unsupported."
        )
    return SlackSaleApprovalAction(
        request_id=_required(decoded.get("r"), "request_id"),
        campaign_id=_required(decoded.get("c"), "campaign_id"),
        nonce=_required(decoded.get("t"), "nonce"),
        decision=decision,
    )


def _button(label: str, action_id: str, value: str, style=None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": "button",
        "text": _plain(label),
        "action_id": action_id,
        "value": value,
        "confirm": {
            "title": _plain(f"{label}確認"),
            "text": {"type": "mrkdwn", "text": f"この候補を*{label}*します。"},
            "confirm": _plain(label),
            "deny": _plain("キャンセル"),
        },
    }
    if style:
        result["style"] = style
    return result


# SALE_APPROVAL_STORE_AWARE_LABEL_V1


def _sale_candidate_label(
    *,
    snapshot: Mapping[str, Any] | None = None,
    campaign_id: str = "",
) -> str:
    source = snapshot or {}

    store = str(
        source.get(
            "campaign_store"
        )
        or ""
    ).strip().casefold()

    normalized_campaign_id = str(
        campaign_id or ""
    ).strip().casefold()

    if (
        store == "dmm"
        or normalized_campaign_id.startswith(
            "dmm-"
        )
    ):
        return "DMMブックス セール候補"

    if (
        store == "rakuten_kobo"
        or normalized_campaign_id.startswith(
            "rakuten-kobo"
        )
    ):
        return "楽天Kobo セール候補"

    # Preserve the existing Amazon/legacy display.
    return "Kindle大型セール候補"


def build_sale_approval_message(
    *,
    snapshot: Mapping[str, Any],
    request_id: str,
    campaign_id: str,
    nonce: str,
    status: str,
    expires_at: datetime,
) -> dict[str, Any]:
    snapshot_campaign_id = _required(snapshot.get("campaign_id"), "campaign_id")
    normalized_campaign_id = _required(campaign_id, "campaign_id")
    label = _sale_candidate_label(
        snapshot=snapshot,
        campaign_id=normalized_campaign_id,
    )
    if snapshot_campaign_id != normalized_campaign_id:
        raise SlackSaleApprovalMessageError(
            "campaign_mismatch",
            "Snapshot campaign_id does not match the approval request.",
        )
    rows = snapshot.get("series") or []
    if not isinstance(rows, list):
        raise SlackSaleApprovalMessageError(
            "invalid_series", "Snapshot series must be a list."
        )
    title = _escape(snapshot.get("title") or "タイトル未設定")
    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": _plain(f"【{label}】")},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*Campaign*\n{title}\n"
                    f"*campaign_id* `{_escape(normalized_campaign_id)}`\n"
                    f"*detected_at* `{_escape(snapshot.get('detected_at'))}`"
                ),
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Checked*\n`{snapshot.get('checked_item_count', 0)}`"},
                {"type": "mrkdwn", "text": f"*Verified*\n`{snapshot.get('verified_signal_count', 0)}`"},
                {"type": "mrkdwn", "text": f"*Series*\n`{snapshot.get('series_count', 0)}`"},
                {"type": "mrkdwn", "text": f"*Status*\n`{_escape(status)}`"},
            ],
        },
    ]
    for index, row in enumerate(rows[:5], start=1):
        if not isinstance(row, Mapping):
            raise SlackSaleApprovalMessageError(
                "invalid_series", "Snapshot series entry must be an object."
            )
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*#{index} {_escape(row.get('series_name') or '不明')}*\n"
                        f"Score `{row.get('simple_sale_score', 0)}` / "
                        f"Coverage `{_escape(row.get('sale_coverage') or 'UNKNOWN')}` / "
                        f"Volumes `{row.get('sale_volume_count', 0)}/{row.get('known_volume_count', 0)}` / "
                        f"Max savings `{row.get('max_savings_percentage', 0)}%`"
                    ),
                },
            }
        )
    values = {
        decision: encode_sale_approval_action(
            request_id=request_id,
            campaign_id=normalized_campaign_id,
            nonce=nonce,
            decision=decision,
        )
        for decision in _ALLOWED_DECISIONS
    }
    blocks.extend(
        [
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"承認要求ID: `{_escape(request_id)}`"},
                    {
                        "type": "mrkdwn",
                        "text": "有効期限: `"
                        + _as_utc(expires_at).strftime("%Y-%m-%d %H:%M UTC")
                        + "`",
                    },
                ],
            },
            {
                "type": "actions",
                "elements": [
                    _button("承認", APPROVE_ACTION_ID, values["APPROVE"], "primary"),
                    _button("保留", HOLD_ACTION_ID, values["HOLD"]),
                    _button("否認", REJECT_ACTION_ID, values["REJECT"], "danger"),
                ],
            },
        ]
    )
    payload = {
        "text": f"【{label}】 {snapshot.get('title')} / {status}",
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    validate_slack_message_payload(payload)
    return payload


def build_sale_approval_update(
    *,
    campaign_id: str,
    campaign_title: str,
    status: str,
    actor_user_id: str,
    decided_at: datetime,
) -> dict[str, Any]:
    symbol = {
        "APPROVED": "✅",
        "ON_HOLD": "⏸️",
        "REJECTED": "❌",
        "EXPIRED": "⌛",
    }.get(status, "ℹ️")

    label = _sale_candidate_label(
        campaign_id=campaign_id,
    )

    payload = {
        "text": f"{symbol} 【{label}】 {status}",
        "blocks": [
            {"type": "header", "text": _plain(f"{symbol} 【{label}】")},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*Campaign*\n{_escape(campaign_title)}\n\n"
                        f"*campaign_id* `{_escape(campaign_id)}`\n"
                        f"*状態* `{_escape(status)}`\n"
                        f"*処理者* `{_escape(actor_user_id)}`\n"
                        f"*決定時刻* `{_as_utc(decided_at).isoformat()}`"
                    ),
                },
            },
        ],
        "unfurl_links": False,
        "unfurl_media": False,
    }
    validate_slack_message_payload(payload)
    return payload
