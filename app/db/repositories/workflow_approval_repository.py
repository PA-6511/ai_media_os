from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import WorkflowApprovalRequest


class WorkflowApprovalRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _required(
        value: str,
        field_name: str,
        *,
        max_length: int,
    ) -> str:
        normalized = (value or "").strip()

        if not normalized:
            raise ValueError(
                f"{field_name} is required"
            )

        if len(normalized) > max_length:
            raise ValueError(
                f"{field_name} exceeds maximum length"
            )

        return normalized

    def add(
        self,
        request: WorkflowApprovalRequest,
    ) -> WorkflowApprovalRequest:
        self.session.add(request)
        self.session.flush()
        return request

    def get(
        self,
        request_id: str,
    ) -> WorkflowApprovalRequest | None:
        return self.session.get(
            WorkflowApprovalRequest,
            request_id,
        )

    def get_for_update(
        self,
        request_id: str,
    ) -> WorkflowApprovalRequest | None:
        statement = (
            select(WorkflowApprovalRequest)
            .where(
                WorkflowApprovalRequest.id == request_id
            )
            .with_for_update()
        )

        return self.session.scalar(statement)

    def find_pending(
        self,
        *,
        ebook_item_id: str,
        approval_type: str,
    ) -> WorkflowApprovalRequest | None:
        statement = (
            select(WorkflowApprovalRequest)
            .where(
                WorkflowApprovalRequest.ebook_item_id
                == ebook_item_id,
                WorkflowApprovalRequest.approval_type
                == approval_type,
                WorkflowApprovalRequest.status
                == "PENDING",
            )
            .order_by(
                WorkflowApprovalRequest.requested_at.desc()
            )
            .limit(1)
        )

        return self.session.scalar(statement)

    def find_by_slack_message(
        self,
        *,
        team_id: str,
        channel_id: str,
        message_ts: str,
    ) -> WorkflowApprovalRequest | None:
        normalized_team = self._required(
            team_id,
            "team_id",
            max_length=64,
        )
        normalized_channel = self._required(
            channel_id,
            "channel_id",
            max_length=64,
        )
        normalized_ts = self._required(
            message_ts,
            "message_ts",
            max_length=64,
        )

        statement = (
            select(WorkflowApprovalRequest)
            .where(
                WorkflowApprovalRequest.slack_team_id
                == normalized_team,
                WorkflowApprovalRequest.slack_channel_id
                == normalized_channel,
                WorkflowApprovalRequest.slack_message_ts
                == normalized_ts,
            )
            .limit(1)
        )

        return self.session.scalar(statement)

    def bind_slack_message(
        self,
        *,
        request_id: str,
        team_id: str,
        channel_id: str,
        message_ts: str,
    ) -> tuple[WorkflowApprovalRequest, bool]:
        normalized_team = self._required(
            team_id,
            "team_id",
            max_length=64,
        )
        normalized_channel = self._required(
            channel_id,
            "channel_id",
            max_length=64,
        )
        normalized_ts = self._required(
            message_ts,
            "message_ts",
            max_length=64,
        )

        request = self.get_for_update(request_id)

        if request is None:
            raise ValueError(
                "approval request was not found"
            )

        if request.status != "PENDING":
            raise ValueError(
                "only pending approval requests can "
                "be bound to a Slack message"
            )

        existing = (
            request.slack_team_id,
            request.slack_channel_id,
            request.slack_message_ts,
        )

        target = (
            normalized_team,
            normalized_channel,
            normalized_ts,
        )

        if any(value is not None for value in existing):
            if existing == target:
                return request, False

            raise ValueError(
                "approval request is already bound "
                "to another Slack message"
            )

        request.slack_team_id = normalized_team
        request.slack_channel_id = normalized_channel
        request.slack_message_ts = normalized_ts

        self.session.flush()

        return request, True
