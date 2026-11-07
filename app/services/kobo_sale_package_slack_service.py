from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

from app.services.slack_approval_socket_service import (
    SlackApprovalInteraction,
    SlackApprovalSocketConfig,
)


APPROVE_ACTION_ID = "kobo_sale_package_approve"
REJECT_ACTION_ID = "kobo_sale_package_reject"

ACTION_IDS = (
    APPROVE_ACTION_ID,
    REJECT_ACTION_ID,
)

PENDING_ROOT = Path(
    "exchange/approvals/"
    "kobo_sale_selection/pending"
)

EXECUTED_ROOT = Path(
    "exchange/approvals/"
    "kobo_sale_selection/executed"
)

REJECTED_ROOT = Path(
    "exchange/approvals/"
    "kobo_sale_selection/rejected"
)

EXECUTOR = Path(
    "scripts/run_kobo_sale_approval_execute.py"
)


class KoboSalePackageSlackError(
    RuntimeError
):
    def __init__(
        self,
        code: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class KoboSalePackageSlackResult:
    code: str
    decision: str
    approval_id: str
    update_payload: dict[str, Any]
    ephemeral_text: str


def _load_json(
    path: Path,
) -> dict[str, Any]:
    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        data,
        dict,
    ):
        raise KoboSalePackageSlackError(
            "package_invalid",
            "Approval package is invalid.",
        )

    return data


def _atomic_write(
    path: Path,
    data: dict[str, Any],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )

    try:
        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                data,
                handle,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            handle.write("\n")

        os.replace(
            temp_name,
            path,
        )

    finally:
        temp = Path(temp_name)

        if temp.exists():
            temp.unlink()


def _decode_action(
    raw: str,
) -> dict[str, Any]:
    try:
        data = json.loads(raw)

    except json.JSONDecodeError as exc:
        raise KoboSalePackageSlackError(
            "invalid_action_value",
            "Slack action value is invalid.",
        ) from exc

    if not isinstance(
        data,
        dict,
    ):
        raise KoboSalePackageSlackError(
            "invalid_action_value",
            "Slack action value is invalid.",
        )

    approval_id = str(
        data.get(
            "approval_id"
        )
        or ""
    ).strip()

    manifest_hash = str(
        data.get(
            "manifest_sha256"
        )
        or ""
    ).strip()

    if (
        len(approval_id) != 24
        or not all(
            value in "0123456789abcdef"
            for value in approval_id
        )
    ):
        raise KoboSalePackageSlackError(
            "invalid_approval_id",
            "Approval ID is invalid.",
        )

    if (
        len(manifest_hash) != 64
        or not all(
            value in "0123456789abcdef"
            for value in manifest_hash
        )
    ):
        raise KoboSalePackageSlackError(
            "invalid_manifest_hash",
            "Manifest hash is invalid.",
        )

    return {
        "approval_id":
            approval_id,
        "manifest_sha256":
            manifest_hash,
    }


def _authorize(
    *,
    config: SlackApprovalSocketConfig,
    interaction: SlackApprovalInteraction,
) -> None:
    if interaction.team_id != config.team_id:
        raise KoboSalePackageSlackError(
            "unauthorized_team",
            "Slack workspace is not authorized.",
        )

    if (
        interaction.channel_id
        != config.channel_id
    ):
        raise KoboSalePackageSlackError(
            "unauthorized_channel",
            "Slack channel is not authorized.",
        )

    if (
        interaction.user_id
        not in config.approver_user_ids
    ):
        raise KoboSalePackageSlackError(
            "unauthorized_user",
            "Slack user is not an approver.",
        )


def _manifest_sha256(
    path: Path,
) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def _pending_package(
    approval_id: str,
) -> Path:
    return (
        PENDING_ROOT
        / f"{approval_id}.json"
    )


def _validate_package(
    *,
    package_path: Path,
    action: dict[str, Any],
    interaction: SlackApprovalInteraction,
) -> dict[str, Any]:
    if not package_path.is_file():
        raise KoboSalePackageSlackError(
            "package_not_pending",
            "Approval package is not pending.",
        )

    package = _load_json(
        package_path
    )

    if package.get("status") != "PENDING":
        raise KoboSalePackageSlackError(
            "package_not_pending",
            "Approval package is not pending.",
        )

    if (
        package.get(
            "approval_id"
        )
        != action[
            "approval_id"
        ]
    ):
        raise KoboSalePackageSlackError(
            "approval_id_mismatch",
            "Approval ID does not match.",
        )

    expected_hash = str(
        package.get(
            "manifest_sha256"
        )
        or ""
    )

    if (
        expected_hash
        != action[
            "manifest_sha256"
        ]
    ):
        raise KoboSalePackageSlackError(
            "manifest_binding_mismatch",
            "Manifest binding does not match.",
        )

    manifest_path = Path(
        str(
            package.get(
                "manifest_path"
            )
            or ""
        )
    )

    if not manifest_path.is_file():
        raise KoboSalePackageSlackError(
            "manifest_missing",
            "Manifest file is missing.",
        )

    if (
        _manifest_sha256(
            manifest_path
        )
        != expected_hash
    ):
        raise KoboSalePackageSlackError(
            "manifest_changed",
            "Manifest changed after Slack notification.",
        )

    slack = package.get(
        "slack"
    )

    if not isinstance(
        slack,
        dict,
    ):
        raise KoboSalePackageSlackError(
            "slack_binding_missing",
            "Slack binding is missing.",
        )

    expected_binding = (
        str(
            slack.get(
                "team_id"
            )
            or ""
        ),
        str(
            slack.get(
                "channel_id"
            )
            or ""
        ),
        str(
            slack.get(
                "message_ts"
            )
            or ""
        ),
    )

    actual_binding = (
        interaction.team_id,
        interaction.channel_id,
        interaction.message_ts,
    )

    if expected_binding != actual_binding:
        raise KoboSalePackageSlackError(
            "message_binding_mismatch",
            "Slack message binding does not match.",
        )

    return package


def _update_payload(
    *,
    package: dict[str, Any],
    decision: str,
    actor: str,
) -> dict[str, Any]:
    approval_id = str(
        package.get(
            "approval_id"
        )
        or ""
    )

    selected_count = int(
        package.get(
            "selected_count"
        )
        or 0
    )

    execution = (
        package.get(
            "execution"
        )
        or {}
    )

    if decision == "APPROVE":
        heading = (
            "✅ Koboセール SQL登録完了"
        )

        detail = (
            f"*{selected_count}冊* を登録しました。\n"
            f"Campaign count: "
            f"`{execution.get('campaign_count_before')}`"
            f" → "
            f"`{execution.get('campaign_count_after')}`"
        )

    else:
        heading = (
            "❌ Koboセール候補を却下"
        )

        detail = (
            f"*{selected_count}冊* は"
            "SQL登録していません。"
        )

    return {
        "text":
            f"{heading} [{approval_id}]",
        "blocks": [
            {
                "type":
                    "header",
                "text": {
                    "type":
                        "plain_text",
                    "text":
                        heading,
                },
            },
            {
                "type":
                    "section",
                "text": {
                    "type":
                        "mrkdwn",
                    "text": (
                        f"*Approval ID*\n"
                        f"`{approval_id}`\n\n"
                        f"{detail}\n\n"
                        f"*Decision by*\n"
                        f"`slack:{actor}`"
                    ),
                },
            },
        ],
    }


class KoboSalePackageSlackService:
    def __init__(
        self,
        config: SlackApprovalSocketConfig,
    ) -> None:
        self.config = config

    def process_interaction(
        self,
        interaction: SlackApprovalInteraction,
    ) -> KoboSalePackageSlackResult:
        _authorize(
            config=self.config,
            interaction=interaction,
        )

        if (
            interaction.action_id
            == APPROVE_ACTION_ID
        ):
            decision = "APPROVE"

        elif (
            interaction.action_id
            == REJECT_ACTION_ID
        ):
            decision = "REJECT"

        else:
            raise KoboSalePackageSlackError(
                "unsupported_action",
                "Slack action is not supported.",
            )

        action = _decode_action(
            interaction.action_value
        )

        approval_id = action[
            "approval_id"
        ]

        pending_path = (
            _pending_package(
                approval_id
            )
        )

        package = _validate_package(
            package_path=pending_path,
            action=action,
            interaction=interaction,
        )

        now = datetime.now(
            timezone.utc
        ).isoformat()

        #
        # Package-level Slack actions must obey
        # the same LIVE/DRY_RUN contract as the
        # existing ebook approval worker.
        #
        if (
            self.config.mode != "LIVE"
            or not self.config.live_confirmed
        ):
            raise KoboSalePackageSlackError(
                "dry_run_no_execution",
                "Slack approval runtime is not LIVE.",
            )

        if decision == "REJECT":
            slack = dict(
                package.get(
                    "slack"
                )
                or {}
            )

            slack.update(
                {
                    "decision":
                        "REJECT",
                    "decided_by":
                        f"slack:{interaction.user_id}",
                    "decided_at_utc":
                        now,
                }
            )

            package["slack"] = slack
            package["status"] = "REJECTED"

            REJECTED_ROOT.mkdir(
                parents=True,
                exist_ok=True,
            )

            rejected_path = (
                REJECTED_ROOT
                / pending_path.name
            )

            _atomic_write(
                pending_path,
                package,
            )

            os.replace(
                pending_path,
                rejected_path,
            )

            return KoboSalePackageSlackResult(
                code="rejected",
                decision="REJECT",
                approval_id=approval_id,
                update_payload=_update_payload(
                    package=package,
                    decision="REJECT",
                    actor=interaction.user_id,
                ),
                ephemeral_text=(
                    "Koboセール候補を却下しました。"
                ),
            )

        command = [
            sys.executable,
            str(EXECUTOR),
            "--approval-package",
            str(pending_path),
            "--approve",
            "--approved-by",
            f"slack:{interaction.user_id}",
        ]

        completed = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
            env=os.environ.copy(),
        )

        if completed.returncode != 0:
            raise KoboSalePackageSlackError(
                "c1j2_execute_failed",
                "C1J-2 execution failed.",
            )

        executed_path = (
            EXECUTED_ROOT
            / pending_path.name
        )

        if not executed_path.is_file():
            raise KoboSalePackageSlackError(
                "executed_package_missing",
                "EXECUTED package is missing.",
            )

        package = _load_json(
            executed_path
        )

        if package.get("status") != "EXECUTED":
            raise KoboSalePackageSlackError(
                "execution_status_invalid",
                "Package did not reach EXECUTED.",
            )

        slack = dict(
            package.get(
                "slack"
            )
            or {}
        )

        slack.update(
            {
                "decision":
                    "APPROVE",
                "decided_by":
                    f"slack:{interaction.user_id}",
                "decided_at_utc":
                    now,
                "c1j2_returncode":
                    completed.returncode,
            }
        )

        package["slack"] = slack

        _atomic_write(
            executed_path,
            package,
        )

        return KoboSalePackageSlackResult(
            code="executed",
            decision="APPROVE",
            approval_id=approval_id,
            update_payload=_update_payload(
                package=package,
                decision="APPROVE",
                actor=interaction.user_id,
            ),
            ephemeral_text=(
                "承認を受け付け、"
                "Koboセール候補を登録しました。"
            ),
        )
