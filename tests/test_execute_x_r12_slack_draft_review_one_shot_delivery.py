from __future__ import annotations

import os

import pytest

from scripts.execute_x_r12_slack_draft_review_one_shot_delivery import (
    CREDENTIAL_ENV_KEY,
    SlackDeliveryExecutionError,
    read_webhook_secret,
    redact_sensitive_text,
    response_is_success,
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


def test_http_200_ok_is_success() -> None:
    assert response_is_success(
        200,
        "ok",
    ) is True


def test_http_200_ok_newline_is_success() -> None:
    assert response_is_success(
        200,
        "ok\n",
    ) is True


def test_http_200_wrong_body_fails() -> None:
    assert response_is_success(
        200,
        "unexpected",
    ) is False


def test_non_200_fails() -> None:
    assert response_is_success(
        400,
        "invalid_payload",
    ) is False


def test_valid_webhook_passes(
    tmp_path,
) -> None:
    path = tmp_path / "credential.env"

    write_env(
        path,
        (
            f"{CREDENTIAL_ENV_KEY}="
            "'https://hooks.slack.com/services/"
            "T000/B000/TEST_TOKEN_123'\n"
        ),
    )

    value = read_webhook_secret(path)

    assert value.startswith(
        "https://hooks.slack.com/services/"
    )


def test_duplicate_webhook_fails(
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
        SlackDeliveryExecutionError,
        match="exactly once",
    ):
        read_webhook_secret(path)


def test_broad_permission_fails(
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
        SlackDeliveryExecutionError,
        match="permissions are too broad",
    ):
        read_webhook_secret(path)


def test_secret_redaction() -> None:
    secret = (
        "https://hooks.slack.com/services/"
        "T1/B1/SECRET"
    )

    value = redact_sensitive_text(
        f"failed at {secret}",
        secret,
    )

    assert secret not in value

    assert (
        "hooks.slack.com/services/"
        not in value
    )
