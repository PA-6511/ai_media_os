from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R12-SLACK-DRAFT-REVIEW-"
    "ONE-SHOT-DELIVERY-EXECUTION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_PREP_DIGEST = (
    "bc6ec4fa94a3cf78767119f63f06ba34"
    "fe15b6090d40cd3932100d67abc63695"
)

EXPECTED_CERTIFICATE_DIGEST = (
    "e436f12dbc8005628083c0b8ebc7347f"
    "388034bf40b029a92a67717ab924588c"
)

EXPECTED_GATE_DIGEST = (
    "28207c7b2d9777f803a9eecd52441d25"
    "f7a7c7b46440146aa56facd2b7e6dc70"
)

EXPECTED_APPROVAL_REQUEST_ID = (
    "xr12-slack-delivery-"
    "bc6ec4fa94a3cf78767119f6"
)

EXPECTED_REVIEW_REQUEST_ID = (
    "xr12-slack-review-"
    "fe82e93e5d2f92e94d6827e6"
)

EXPECTED_X_ACCOUNT_HANDLE = "@mz_GK7_DM2"

EXPECTED_TEXT_SHA = (
    "125481ce9a0a1ad8972c2f855e9d2bb5"
    "5f4e3215152ba6ba0fa626e489a81d67"
)

EXPECTED_AFFILIATE_URL = (
    "https://a.r10.to/hPKo3p"
)

CREDENTIAL_ENV_KEY = (
    "SLACK_X_DRAFT_REVIEW_WEBHOOK_URL"
)

EXECUTION_CONFIRMATION = (
    "EXECUTE_ONE_SLACK_X_DRAFT_"
    "REVIEW_DELIVERY_NOW"
)

WEBHOOK_PATTERN = re.compile(
    r"https://hooks\.slack\.com/services/"
    r"[A-Za-z0-9]+/"
    r"[A-Za-z0-9]+/"
    r"[A-Za-z0-9_-]+"
)


class SlackDeliveryExecutionError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise SlackDeliveryExecutionError(
            message
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise SlackDeliveryExecutionError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str,
    label: str,
) -> None:
    require(
        value.get(digest_field)
        == expected_digest,
        f"{label} recorded digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        f"{label} canonical digest mismatch",
    )


def atomic_create_json(
    path: Path,
    value: dict[str, Any],
) -> None:
    path = path.resolve()

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = (
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise SlackDeliveryExecutionError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def redact_sensitive_text(
    value: object,
    secret: str = "",
) -> str:
    text = str(value)

    if secret:
        text = text.replace(
            secret,
            "[REDACTED]",
        )

    text = WEBHOOK_PATTERN.sub(
        "[REDACTED_SLACK_WEBHOOK]",
        text,
    )

    text = text.replace(
        "xoxb-",
        "[REDACTED_TOKEN_PREFIX]",
    )

    text = text.replace(
        "xapp-",
        "[REDACTED_TOKEN_PREFIX]",
    )

    return text[:1000]


def read_webhook_secret(
    credential_env_path: Path,
) -> str:
    credential_env_path = (
        credential_env_path.resolve()
    )

    require(
        credential_env_path.is_file(),
        "credential.env is missing",
    )

    require(
        not credential_env_path.is_symlink(),
        "credential.env must not be a symlink",
    )

    mode = stat.S_IMODE(
        credential_env_path.stat().st_mode
    )

    require(
        mode & 0o077 == 0,
        "credential.env permissions are too broad",
    )

    values: list[str] = []

    for raw_line in credential_env_path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].lstrip()

        if "=" not in line:
            continue

        name, raw_value = line.split("=", 1)

        if name.strip() != CREDENTIAL_ENV_KEY:
            continue

        value = raw_value.strip()

        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ("'", '"')
        ):
            value = value[1:-1]

        values.append(value)

    require(
        len(values) == 1,
        (
            "Slack webhook credential must "
            "exist exactly once"
        ),
    )

    webhook = values[0]

    require(
        WEBHOOK_PATTERN.fullmatch(webhook)
        is not None,
        "Slack webhook credential format invalid",
    )

    return webhook


def response_is_success(
    status_code: int,
    response_body: str,
) -> bool:
    return (
        status_code == 200
        and response_body.strip() == "ok"
    )


def post_slack_payload(
    webhook: str,
    payload: dict[str, Any],
    *,
    timeout_seconds: int = 20,
) -> tuple[int, str]:
    request_body = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")

    request = Request(
        webhook,
        data=request_body,
        method="POST",
        headers={
            "Content-Type": (
                "application/json; charset=utf-8"
            ),
            "User-Agent": (
                "ai-media-os-x-r12-slack/1.0"
            ),
        },
    )

    try:
        with urlopen(
            request,
            timeout=timeout_seconds,
        ) as response:
            return (
                int(response.status),
                response.read(4096).decode(
                    "utf-8",
                    errors="replace",
                ),
            )

    except HTTPError as exc:
        return (
            int(exc.code),
            exc.read(4096).decode(
                "utf-8",
                errors="replace",
            ),
        )

    except URLError as exc:
        raise SlackDeliveryExecutionError(
            "Slack network error: "
            + redact_sensitive_text(
                exc.reason,
                webhook,
            )
        ) from exc


def validate_source_artifacts(
    *,
    prep: dict[str, Any],
    review_request: dict[str, Any],
    slack_preview: dict[str, Any],
    certificate: dict[str, Any],
    gate: dict[str, Any],
    issuance_lock: dict[str, Any],
) -> tuple[str, str]:
    verify_digest(
        prep,
        digest_field=(
            "x_r12_slack_draft_review_delivery_"
            "prep_digest_sha256"
        ),
        expected_digest=EXPECTED_PREP_DIGEST,
        label="Slack delivery prep",
    )

    require(
        prep.get("status")
        == (
            "PASS_X_R12_SLACK_DRAFT_REVIEW_"
            "DELIVERY_PREP_READY"
        ),
        "Prep status mismatch",
    )

    require(
        prep.get("delivery_state")
        == "LOCAL_PREVIEW_READY_SLACK_NOT_SENT",
        "Prep delivery state mismatch",
    )

    review_reference = prep.get(
        "review_request"
    )

    preview_reference = prep.get(
        "slack_message_preview"
    )

    require(
        isinstance(review_reference, dict),
        "review request reference missing",
    )

    require(
        isinstance(preview_reference, dict),
        "Slack preview reference missing",
    )

    request_digest = review_reference.get(
        "digest_sha256"
    )

    preview_digest = preview_reference.get(
        "digest_sha256"
    )

    require(
        isinstance(request_digest, str)
        and len(request_digest) == 64,
        "review request digest invalid",
    )

    require(
        isinstance(preview_digest, str)
        and len(preview_digest) == 64,
        "Slack preview digest invalid",
    )

    require(
        canonical_digest(review_request)
        == request_digest,
        "review request digest mismatch",
    )

    require(
        review_request.get(
            "review_request_id"
        )
        == EXPECTED_REVIEW_REQUEST_ID,
        "review request ID mismatch",
    )

    require(
        review_request.get("status")
        == "PENDING_SLACK_DELIVERY",
        "review request status mismatch",
    )

    require(
        review_request.get("review_state")
        == "NOT_REVIEWED",
        "review request already reviewed",
    )

    require(
        review_request.get(
            "x_account_handle"
        )
        == EXPECTED_X_ACCOUNT_HANDLE,
        "X account binding mismatch",
    )

    require(
        review_request.get(
            "draft_text_sha256"
        )
        == EXPECTED_TEXT_SHA,
        "draft text SHA mismatch",
    )

    require(
        review_request.get("affiliate_url")
        == EXPECTED_AFFILIATE_URL,
        "affiliate URL binding mismatch",
    )

    require(
        review_request.get(
            "slack_message_sent"
        )
        is False,
        "review request already records send",
    )

    require(
        canonical_digest(slack_preview)
        == preview_digest,
        "Slack preview digest mismatch",
    )

    preview_text = json.dumps(
        slack_preview,
        ensure_ascii=False,
    )

    for required_text in (
        EXPECTED_REVIEW_REQUEST_ID,
        EXPECTED_AFFILIATE_URL,
        "【PR・新刊】",
        "APPROVE",
        "REVISE",
        "REJECT",
    ):
        require(
            required_text in preview_text,
            (
                "required Slack preview value "
                f"missing: {required_text}"
            ),
        )

    for forbidden in (
        "hooks.slack.com/services/",
        "xoxb-",
        "xapp-",
    ):
        require(
            forbidden not in preview_text,
            "secret material leaked into preview",
        )

    verify_digest(
        certificate,
        digest_field=(
            "x_r12_slack_delivery_approval_"
            "certificate_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_CERTIFICATE_DIGEST
        ),
        label="Slack approval certificate",
    )

    require(
        certificate.get("status")
        == (
            "SLACK_DRAFT_REVIEW_ONE_SHOT_"
            "DELIVERY_APPROVAL_ISSUED_"
            "NOT_CONSUMED"
        ),
        "certificate status mismatch",
    )

    require(
        certificate.get(
            "approval_request_id"
        )
        == EXPECTED_APPROVAL_REQUEST_ID,
        "certificate approval request mismatch",
    )

    require(
        certificate.get(
            "one_slack_delivery_authorized"
        )
        is True,
        "Slack delivery is not authorized",
    )

    require(
        certificate.get("approval_consumed")
        is False,
        "certificate was already consumed",
    )

    require(
        certificate.get("slack_message_sent")
        is False,
        "certificate already records send",
    )

    require(
        certificate.get(
            "automatic_retry_allowed"
        )
        is False,
        "certificate permits automatic retry",
    )

    verify_digest(
        gate,
        digest_field=(
            "x_r12_slack_delivery_approval_"
            "gate_digest_sha256"
        ),
        expected_digest=EXPECTED_GATE_DIGEST,
        label="Slack approval gate",
    )

    require(
        gate.get("status")
        == (
            "PASS_X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_APPROVAL_"
            "GATE_READY"
        ),
        "approval gate status mismatch",
    )

    require(
        gate.get("gate_state")
        == (
            "ONE_SLACK_DELIVERY_APPROVED_"
            "NOT_EXECUTED"
        ),
        "approval gate state mismatch",
    )

    require(
        gate.get("approval_consumed")
        is False,
        "approval gate was already consumed",
    )

    require(
        gate.get("slack_message_sent")
        is False,
        "approval gate already records send",
    )

    require(
        gate.get(
            "automatic_retry_allowed"
        )
        is False,
        "approval gate permits automatic retry",
    )

    require(
        issuance_lock.get("lock_type")
        == (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_APPROVAL_"
            "ISSUANCE"
        ),
        "issuance lock type mismatch",
    )

    require(
        issuance_lock.get(
            "approval_certificate_digest_sha256"
        )
        == EXPECTED_CERTIFICATE_DIGEST,
        "issuance certificate digest mismatch",
    )

    require(
        issuance_lock.get(
            "approval_gate_digest_sha256"
        )
        == EXPECTED_GATE_DIGEST,
        "issuance gate digest mismatch",
    )

    require(
        issuance_lock.get("approval_issued")
        is True,
        "approval was not issued",
    )

    require(
        issuance_lock.get("approval_consumed")
        is False,
        "issuance approval was consumed",
    )

    require(
        issuance_lock.get(
            "reissuance_allowed"
        )
        is False,
        "issuance permits reissuance",
    )

    return request_digest, preview_digest


def build_failure_result(
    *,
    delivery_state: str,
    claim_path: Path,
    claim_digest: str,
    error: str,
    status_code: int | None = None,
    response_body: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "phase": PHASE,
        "status": (
            "FAIL_X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_EXECUTION"
        ),
        "delivery_state": delivery_state,
        "failed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "execution_claim_path": str(
            claim_path
        ),
        "execution_claim_digest_sha256": (
            claim_digest
        ),
        "error": error,
        "response_status_code": status_code,
        "response_body": response_body,
        "slack_delivery_attempted": True,
        "slack_message_sent": (
            False
            if status_code is not None
            else None
        ),
        "approval_consumed": False,
        "reexecution_allowed": False,
        "automatic_retry_allowed": False,
        "manual_reconciliation_required": True,
        "credential_read": True,
        "credential_value_recorded": False,
        "database_write": False,
        "x_api_call": False,
        "slack_api_call": True,
        "production_status": "NO_GO",
    }

    return {
        **payload,
        "x_r12_slack_delivery_execution_"
        "result_digest_sha256": (
            canonical_digest(payload)
        ),
    }


def execute_delivery(
    *,
    production_database_path: Path,
    prep_pack_path: Path,
    review_request_path: Path,
    slack_preview_path: Path,
    certificate_path: Path,
    gate_pack_path: Path,
    issuance_lock_path: Path,
    credential_env_path: Path,
    confirmation: str,
    execution_claim_path: Path,
    result_pack_path: Path,
    consumption_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    prep_pack_path = prep_pack_path.resolve()
    review_request_path = (
        review_request_path.resolve()
    )
    slack_preview_path = (
        slack_preview_path.resolve()
    )
    certificate_path = certificate_path.resolve()
    gate_pack_path = gate_pack_path.resolve()
    issuance_lock_path = (
        issuance_lock_path.resolve()
    )
    credential_env_path = (
        credential_env_path.resolve()
    )
    execution_claim_path = (
        execution_claim_path.resolve()
    )
    result_pack_path = (
        result_pack_path.resolve()
    )
    consumption_lock_path = (
        consumption_lock_path.resolve()
    )

    require(
        confirmation == EXECUTION_CONFIRMATION,
        "execution confirmation mismatch",
    )

    require(
        sha256_file(production_database_path)
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    prep = load_json(prep_pack_path)
    review_request = load_json(
        review_request_path
    )
    slack_preview = load_json(
        slack_preview_path
    )
    certificate = load_json(certificate_path)
    gate = load_json(gate_pack_path)
    issuance_lock = load_json(
        issuance_lock_path
    )

    (
        request_digest,
        preview_digest,
    ) = validate_source_artifacts(
        prep=prep,
        review_request=review_request,
        slack_preview=slack_preview,
        certificate=certificate,
        gate=gate,
        issuance_lock=issuance_lock,
    )

    for path, label in (
        (
            execution_claim_path,
            "execution claim",
        ),
        (
            result_pack_path,
            "delivery result",
        ),
        (
            consumption_lock_path,
            "approval consumption lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    webhook = read_webhook_secret(
        credential_env_path
    )

    claimed_at = datetime.now(
        timezone.utc
    ).isoformat()

    claim_payload = {
        "lock_type": (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_EXECUTION_CLAIM"
        ),
        "claimed_at": claimed_at,
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "source_prep_digest_sha256": (
            EXPECTED_PREP_DIGEST
        ),
        "approval_certificate_digest_sha256": (
            EXPECTED_CERTIFICATE_DIGEST
        ),
        "approval_gate_digest_sha256": (
            EXPECTED_GATE_DIGEST
        ),
        "review_request_digest_sha256": (
            request_digest
        ),
        "slack_preview_digest_sha256": (
            preview_digest
        ),
        "execution_claimed": True,
        "reexecution_allowed": False,
        "automatic_retry_allowed": False,
        "slack_message_sent_at_claim_time": False,
        "credential_value_recorded": False,
    }

    claim = {
        **claim_payload,
        "x_r12_slack_delivery_execution_"
        "claim_digest_sha256": (
            canonical_digest(claim_payload)
        ),
    }

    atomic_create_json(
        execution_claim_path,
        claim,
    )

    claim_digest = claim[
        "x_r12_slack_delivery_execution_"
        "claim_digest_sha256"
    ]

    try:
        status_code, response_body = (
            post_slack_payload(
                webhook,
                slack_preview,
            )
        )
    except Exception as exc:
        error = redact_sensitive_text(
            exc,
            webhook,
        )

        failure = build_failure_result(
            delivery_state=(
                "NETWORK_RESULT_UNVERIFIED_"
                "MANUAL_RECONCILIATION_REQUIRED"
            ),
            claim_path=execution_claim_path,
            claim_digest=claim_digest,
            error=error,
        )

        atomic_create_json(
            result_pack_path,
            failure,
        )

        raise SlackDeliveryExecutionError(
            error
        ) from exc

    safe_body = redact_sensitive_text(
        response_body,
        webhook,
    ).strip()

    if not response_is_success(
        status_code,
        response_body,
    ):
        failure = build_failure_result(
            delivery_state=(
                "SLACK_REJECTED_OR_UNEXPECTED_"
                "RESPONSE_NO_AUTOMATIC_RETRY"
            ),
            claim_path=execution_claim_path,
            claim_digest=claim_digest,
            error=(
                "Slack did not return HTTP 200 / ok"
            ),
            status_code=status_code,
            response_body=safe_body,
        )

        atomic_create_json(
            result_pack_path,
            failure,
        )

        raise SlackDeliveryExecutionError(
            (
                "Slack delivery did not return "
                f"HTTP 200 / ok: {status_code} "
                f"{safe_body}"
            )
        )

    delivered_at = datetime.now(
        timezone.utc
    ).isoformat()

    result_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_EXECUTED"
        ),
        "delivery_state": (
            "SLACK_MESSAGE_SENT_"
            "APPROVAL_CONSUMED"
        ),
        "delivered_at": delivered_at,
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "source_prep_digest_sha256": (
            EXPECTED_PREP_DIGEST
        ),
        "approval_certificate_digest_sha256": (
            EXPECTED_CERTIFICATE_DIGEST
        ),
        "approval_gate_digest_sha256": (
            EXPECTED_GATE_DIGEST
        ),
        "review_request_digest_sha256": (
            request_digest
        ),
        "slack_preview_digest_sha256": (
            preview_digest
        ),
        "execution_claim_path": str(
            execution_claim_path
        ),
        "execution_claim_digest_sha256": (
            claim_digest
        ),
        "response_status_code": status_code,
        "response_body": safe_body,
        "response_body_sha256": (
            sha256_text(response_body)
        ),
        "delivery_confirmation": (
            "HTTP_200_AND_BODY_OK"
        ),
        "slack_delivery_attempted": True,
        "slack_message_sent": True,
        "approval_consumed": True,
        "reexecution_allowed": False,
        "automatic_retry_allowed": False,
        "human_review_state": "NOT_REVIEWED",
        "credential_read": True,
        "credential_present": True,
        "credential_format_valid": True,
        "credential_value_recorded": False,
        "credential_hash_recorded": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_post_executed": False,
        "x_api_call": False,
        "slack_api_call": True,
        "slack_api_call_count": 1,
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_SLACK_DELIVERY_COMPLETE_"
            "NO_RETRY_NO_X_POST"
        ),
        "authorized_next_phase": (
            "X-R12-SLACK-DRAFT-REVIEW-"
            "MANUAL-VISIBILITY-CONFIRMATION"
        ),
    }

    result = {
        **result_payload,
        "x_r12_slack_delivery_execution_"
        "result_digest_sha256": (
            canonical_digest(result_payload)
        ),
    }

    result_digest = result[
        "x_r12_slack_delivery_execution_"
        "result_digest_sha256"
    ]

    consumption_lock = {
        "lock_type": (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_APPROVAL_"
            "CONSUMPTION"
        ),
        "consumed_at": delivered_at,
        "approval_request_id": (
            EXPECTED_APPROVAL_REQUEST_ID
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "approval_certificate_digest_sha256": (
            EXPECTED_CERTIFICATE_DIGEST
        ),
        "approval_gate_digest_sha256": (
            EXPECTED_GATE_DIGEST
        ),
        "execution_claim_digest_sha256": (
            claim_digest
        ),
        "delivery_result_path": str(
            result_pack_path
        ),
        "delivery_result_digest_sha256": (
            result_digest
        ),
        "approval_consumed": True,
        "slack_message_sent": True,
        "reexecution_allowed": False,
        "automatic_retry_allowed": False,
        "additional_slack_delivery_allowed": False,
        "x_post_allowed": False,
    }

    atomic_create_json(
        result_pack_path,
        result,
    )

    atomic_create_json(
        consumption_lock_path,
        consumption_lock,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--prep-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--review-request",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--slack-preview",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--certificate",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--gate-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--issuance-lock",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--credential-env",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--confirmation",
        required=True,
    )
    parser.add_argument(
        "--execution-claim",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--result-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--consumption-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = execute_delivery(
            production_database_path=(
                args.production_db
            ),
            prep_pack_path=args.prep_pack,
            review_request_path=(
                args.review_request
            ),
            slack_preview_path=(
                args.slack_preview
            ),
            certificate_path=args.certificate,
            gate_pack_path=args.gate_pack,
            issuance_lock_path=(
                args.issuance_lock
            ),
            credential_env_path=(
                args.credential_env
            ),
            confirmation=args.confirmation,
            execution_claim_path=(
                args.execution_claim
            ),
            result_pack_path=args.result_pack,
            consumption_lock_path=(
                args.consumption_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_R12_SLACK_DRAFT_"
                        "REVIEW_ONE_SHOT_DELIVERY_"
                        "EXECUTION"
                    ),
                    "error": redact_sensitive_text(
                        exc
                    ),
                    "automatic_rerun_allowed": False,
                    "slack_message_sent": (
                        "UNVERIFIED_OR_FALSE"
                    ),
                    "database_write": False,
                    "x_api_call": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )

        return 1

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "delivery_state": (
                    result["delivery_state"]
                ),
                "approval_request_id": (
                    result["approval_request_id"]
                ),
                "review_request_id": (
                    result["review_request_id"]
                ),
                "response_status_code": (
                    result["response_status_code"]
                ),
                "response_body": (
                    result["response_body"]
                ),
                "delivery_confirmation": (
                    result["delivery_confirmation"]
                ),
                "slack_message_sent": True,
                "approval_consumed": True,
                "human_review_state": (
                    result["human_review_state"]
                ),
                "credential_value_recorded": False,
                "automatic_retry_allowed": False,
                "reexecution_allowed": False,
                "x_post_executed": False,
                "database_write": False,
                "x_api_call": False,
                "slack_api_call": True,
                "production_status": "NO_GO",
                "result_pack_path": str(
                    args.result_pack.resolve()
                ),
                "result_digest_sha256": (
                    result[
                        "x_r12_slack_delivery_"
                        "execution_result_digest_sha256"
                    ]
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
