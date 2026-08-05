from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import stat
import subprocess
from typing import Any


AUTOSTART_GATE_PATH = Path(
    "/etc/ai-media-os/"
    "slack-readiness-autostart.approved"
)

REPOSITORY_ROOT = Path(
    "/home/deploy/ai_media_os"
)

EXPECTED_APPROVAL_LABEL = (
    "APPROVED_FOR_SLACK_READINESS_AUTOSTART_ONLY"
)

EXPECTED_TARGET_UNIT = (
    "ai-media-os-slack-approval-readiness.service"
)

EXPECTED_SAFETY_SCOPE = (
    "READINESS_DRY_RUN_AUTOSTART_ONLY"
)

EXPECTED_SCHEMA_VERSION = 1
MAXIMUM_VALIDITY = timedelta(hours=24)
MAXIMUM_GATE_BYTES = 16 * 1024
MAXIMUM_CLOCK_SKEW = timedelta(minutes=5)

COMMIT_PATTERN = re.compile(
    r"^[0-9a-f]{40}$"
)

REQUIRED_FIELDS = frozenset(
    {
        "schema_version",
        "approval_label",
        "target_unit",
        "target_commit",
        "approved_by",
        "approved_at",
        "expires_at",
        "production_status",
        "safety_scope",
        "slack_mode",
        "production_database_allowed",
        "automatic_start_allowed",
    }
)


class SlackAutostartGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class SlackAutostartApproval:
    target_commit: str
    approved_by: str
    approved_at: datetime
    expires_at: datetime
    target_unit: str
    safety_scope: str
    slack_mode: str
    production_database_allowed: bool
    automatic_start_allowed: bool


def resolve_repository_commit(
    repository_root: Path = REPOSITORY_ROOT,
) -> str:
    try:
        commit = subprocess.check_output(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            cwd=repository_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        raise SlackAutostartGateError(
            "Unable to resolve repository commit"
        ) from exc

    if not COMMIT_PATTERN.fullmatch(commit):
        raise SlackAutostartGateError(
            "Repository commit format is invalid"
        )

    return commit


def _parse_datetime(
    value: Any,
    field_name: str,
) -> datetime:
    if not isinstance(value, str):
        raise SlackAutostartGateError(
            f"{field_name} must be a string"
        )

    normalized = value.strip()

    if normalized.endswith("Z"):
        normalized = (
            normalized[:-1] + "+00:00"
        )

    try:
        parsed = datetime.fromisoformat(
            normalized
        )
    except ValueError as exc:
        raise SlackAutostartGateError(
            f"{field_name} is not valid ISO-8601"
        ) from exc

    if parsed.tzinfo is None:
        raise SlackAutostartGateError(
            f"{field_name} must include timezone"
        )

    return parsed.astimezone(timezone.utc)


def _require_exact_value(
    payload: dict[str, Any],
    field_name: str,
    expected: Any,
) -> None:
    actual = payload[field_name]

    if type(actual) is not type(expected):
        raise SlackAutostartGateError(
            f"{field_name} type is invalid"
        )

    if actual != expected:
        raise SlackAutostartGateError(
            f"{field_name} does not match policy"
        )


def validate_slack_autostart_gate(
    *,
    gate_path: Path = AUTOSTART_GATE_PATH,
    expected_commit: str,
    now: datetime | None = None,
    expected_uid: int = 0,
    expected_gid: int = 0,
    maximum_validity: timedelta = (
        MAXIMUM_VALIDITY
    ),
) -> SlackAutostartApproval:
    if not COMMIT_PATTERN.fullmatch(
        expected_commit
    ):
        raise SlackAutostartGateError(
            "Expected commit format is invalid"
        )

    try:
        gate_stat = gate_path.lstat()
    except FileNotFoundError as exc:
        raise SlackAutostartGateError(
            "Autostart approval gate is missing"
        ) from exc

    if stat.S_ISLNK(gate_stat.st_mode):
        raise SlackAutostartGateError(
            "Autostart approval gate must not "
            "be a symbolic link"
        )

    if not stat.S_ISREG(gate_stat.st_mode):
        raise SlackAutostartGateError(
            "Autostart approval gate must be "
            "a regular file"
        )

    gate_mode = stat.S_IMODE(
        gate_stat.st_mode
    )

    if gate_mode != 0o644:
        raise SlackAutostartGateError(
            "Autostart approval gate mode "
            "must be 644"
        )

    if gate_stat.st_uid != expected_uid:
        raise SlackAutostartGateError(
            "Autostart approval gate owner "
            "is invalid"
        )

    if gate_stat.st_gid != expected_gid:
        raise SlackAutostartGateError(
            "Autostart approval gate group "
            "is invalid"
        )

    raw_bytes = gate_path.read_bytes()

    if len(raw_bytes) > MAXIMUM_GATE_BYTES:
        raise SlackAutostartGateError(
            "Autostart approval gate is too large"
        )

    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SlackAutostartGateError(
            "Autostart approval gate is not UTF-8"
        ) from exc

    if (
        "xoxb-" in raw_text
        or "xapp-" in raw_text
    ):
        raise SlackAutostartGateError(
            "Credential-shaped value detected "
            "in autostart approval gate"
        )

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise SlackAutostartGateError(
            "Autostart approval gate JSON "
            "is invalid"
        ) from exc

    if not isinstance(payload, dict):
        raise SlackAutostartGateError(
            "Autostart approval gate must "
            "contain a JSON object"
        )

    payload_fields = frozenset(
        payload.keys()
    )

    missing_fields = (
        REQUIRED_FIELDS - payload_fields
    )

    unexpected_fields = (
        payload_fields - REQUIRED_FIELDS
    )

    if missing_fields:
        raise SlackAutostartGateError(
            "Autostart approval gate is missing "
            "required fields"
        )

    if unexpected_fields:
        raise SlackAutostartGateError(
            "Autostart approval gate contains "
            "unexpected fields"
        )

    _require_exact_value(
        payload,
        "schema_version",
        EXPECTED_SCHEMA_VERSION,
    )

    _require_exact_value(
        payload,
        "approval_label",
        EXPECTED_APPROVAL_LABEL,
    )

    _require_exact_value(
        payload,
        "target_unit",
        EXPECTED_TARGET_UNIT,
    )

    _require_exact_value(
        payload,
        "production_status",
        "NO_GO",
    )

    _require_exact_value(
        payload,
        "safety_scope",
        EXPECTED_SAFETY_SCOPE,
    )

    _require_exact_value(
        payload,
        "slack_mode",
        "DRY_RUN",
    )

    _require_exact_value(
        payload,
        "production_database_allowed",
        False,
    )

    _require_exact_value(
        payload,
        "automatic_start_allowed",
        True,
    )

    target_commit = payload[
        "target_commit"
    ]

    if (
        not isinstance(target_commit, str)
        or not COMMIT_PATTERN.fullmatch(
            target_commit
        )
    ):
        raise SlackAutostartGateError(
            "target_commit format is invalid"
        )

    if target_commit != expected_commit:
        raise SlackAutostartGateError(
            "target_commit does not match "
            "the repository commit"
        )

    approved_by = payload[
        "approved_by"
    ]

    if (
        not isinstance(approved_by, str)
        or not approved_by.strip()
    ):
        raise SlackAutostartGateError(
            "approved_by is missing"
        )

    approved_at = _parse_datetime(
        payload["approved_at"],
        "approved_at",
    )

    expires_at = _parse_datetime(
        payload["expires_at"],
        "expires_at",
    )

    now_value = (
        now
        if now is not None
        else datetime.now(timezone.utc)
    )

    if now_value.tzinfo is None:
        raise SlackAutostartGateError(
            "Current time must include timezone"
        )

    now_value = now_value.astimezone(
        timezone.utc
    )

    if approved_at > (
        now_value + MAXIMUM_CLOCK_SKEW
    ):
        raise SlackAutostartGateError(
            "Autostart approval is not yet valid"
        )

    if expires_at <= approved_at:
        raise SlackAutostartGateError(
            "Autostart approval expiry "
            "must follow approval time"
        )

    if expires_at <= now_value:
        raise SlackAutostartGateError(
            "Autostart approval has expired"
        )

    if (
        expires_at - approved_at
        > maximum_validity
    ):
        raise SlackAutostartGateError(
            "Autostart approval validity "
            "window is too long"
        )

    return SlackAutostartApproval(
        target_commit=target_commit,
        approved_by=approved_by.strip(),
        approved_at=approved_at,
        expires_at=expires_at,
        target_unit=payload["target_unit"],
        safety_scope=payload["safety_scope"],
        slack_mode=payload["slack_mode"],
        production_database_allowed=False,
        automatic_start_allowed=True,
    )
