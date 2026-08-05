from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path

import pytest

from app.services.slack_autostart_gate import (
    SlackAutostartGateError,
    validate_slack_autostart_gate,
)


COMMIT = "a" * 40

NOW = datetime(
    2026,
    7,
    14,
    12,
    0,
    tzinfo=timezone.utc,
)


def valid_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        "approval_label": (
            "APPROVED_FOR_SLACK_"
            "READINESS_AUTOSTART_ONLY"
        ),
        "target_unit": (
            "ai-media-os-slack-approval-"
            "readiness.service"
        ),
        "target_commit": COMMIT,
        "approved_by": "human-operator",
        "approved_at": (
            NOW - timedelta(minutes=1)
        ).isoformat(),
        "expires_at": (
            NOW + timedelta(hours=1)
        ).isoformat(),
        "production_status": "NO_GO",
        "safety_scope": (
            "READINESS_DRY_RUN_AUTOSTART_ONLY"
        ),
        "slack_mode": "DRY_RUN",
        "production_database_allowed": False,
        "automatic_start_allowed": True,
    }


def write_gate(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    path.chmod(0o644)


def validate(path: Path):
    return validate_slack_autostart_gate(
        gate_path=path,
        expected_commit=COMMIT,
        now=NOW,
        expected_uid=os.getuid(),
        expected_gid=os.getgid(),
    )


def test_valid_gate_is_approved(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    write_gate(gate, valid_payload())

    approval = validate(gate)

    assert approval.target_commit == COMMIT
    assert approval.slack_mode == "DRY_RUN"
    assert (
        approval.production_database_allowed
        is False
    )
    assert (
        approval.automatic_start_allowed
        is True
    )


def test_missing_gate_is_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(tmp_path / "missing.json")


def test_symbolic_link_is_rejected(
    tmp_path: Path,
) -> None:
    real_gate = tmp_path / "real.json"
    linked_gate = tmp_path / "linked.json"

    write_gate(real_gate, valid_payload())
    linked_gate.symlink_to(real_gate)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(linked_gate)


def test_wrong_file_mode_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    write_gate(gate, valid_payload())
    gate.chmod(0o600)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


def test_wrong_owner_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    write_gate(gate, valid_payload())

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate_slack_autostart_gate(
            gate_path=gate,
            expected_commit=COMMIT,
            now=NOW,
            expected_uid=os.getuid() + 1,
            expected_gid=os.getgid(),
        )


def test_commit_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload["target_commit"] = "b" * 40

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


def test_expired_gate_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload["expires_at"] = (
        NOW - timedelta(seconds=1)
    ).isoformat()

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


def test_future_approval_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload["approved_at"] = (
        NOW + timedelta(minutes=6)
    ).isoformat()
    payload["expires_at"] = (
        NOW + timedelta(hours=1)
    ).isoformat()

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


def test_excessive_validity_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload["approved_at"] = NOW.isoformat()
    payload["expires_at"] = (
        NOW + timedelta(hours=25)
    ).isoformat()

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


def test_credential_shape_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload["approved_by"] = (
        "xoxb-this-value-must-not-appear"
    )

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


def test_unexpected_field_is_rejected(
    tmp_path: Path,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload["unexpected"] = True

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("schema_version", 2),
        ("approval_label", "WRONG"),
        ("target_unit", "wrong.service"),
        ("production_status", "GO"),
        ("safety_scope", "PRODUCTION"),
        ("slack_mode", "LIVE"),
        (
            "production_database_allowed",
            True,
        ),
        (
            "automatic_start_allowed",
            False,
        ),
    ),
)
def test_policy_mismatch_is_rejected(
    tmp_path: Path,
    field: str,
    value: object,
) -> None:
    gate = tmp_path / "gate.json"

    payload = valid_payload()
    payload[field] = value

    write_gate(gate, payload)

    with pytest.raises(
        SlackAutostartGateError
    ):
        validate(gate)
