from __future__ import annotations

import os

import pytest

from scripts.build_x_r12_slack_draft_review_one_shot_delivery_approval_gate import (
    CREDENTIAL_ENV_KEY,
    SlackDeliveryApprovalError,
    read_webhook_without_exposure,
)


def write_env(
    path,
    content: str,
) -> None:
    path.write_text(
        content,
        encoding="utf-8",
    )

    os.chmod(path, 0o600)


def test_valid_webhook_passes(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        (
            f"{CREDENTIAL_ENV_KEY}="
            "https://hooks.slack.com/services/"
            "T00000000/B00000000/"
            "TEST_TOKEN_123\n"
        ),
    )

    assert (
        read_webhook_without_exposure(path)
        is None
    )


def test_export_and_quotes_pass(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        (
            f"export {CREDENTIAL_ENV_KEY}="
            "\"https://hooks.slack.com/services/"
            "T111/B222/TEST_TOKEN\"\n"
        ),
    )

    assert (
        read_webhook_without_exposure(path)
        is None
    )


def test_missing_key_fails(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        "OTHER_KEY=value\n",
    )

    with pytest.raises(
        SlackDeliveryApprovalError,
        match="exactly once",
    ):
        read_webhook_without_exposure(path)


def test_duplicate_key_fails(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        (
            f"{CREDENTIAL_ENV_KEY}="
            "https://hooks.slack.com/services/"
            "T1/B1/TOKEN1\n"
            f"{CREDENTIAL_ENV_KEY}="
            "https://hooks.slack.com/services/"
            "T2/B2/TOKEN2\n"
        ),
    )

    with pytest.raises(
        SlackDeliveryApprovalError,
        match="exactly once",
    ):
        read_webhook_without_exposure(path)


def test_invalid_url_fails(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        (
            f"{CREDENTIAL_ENV_KEY}="
            "https://example.com/webhook\n"
        ),
    )

    with pytest.raises(
        SlackDeliveryApprovalError,
        match="format is invalid",
    ):
        read_webhook_without_exposure(path)


def test_broad_permissions_fail(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        (
            f"{CREDENTIAL_ENV_KEY}="
            "https://hooks.slack.com/services/"
            "T1/B1/TOKEN\n"
        ),
    )

    os.chmod(path, 0o644)

    with pytest.raises(
        SlackDeliveryApprovalError,
        match="permissions are too broad",
    ):
        read_webhook_without_exposure(path)
