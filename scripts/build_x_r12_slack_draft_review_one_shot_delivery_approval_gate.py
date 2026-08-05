from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R12-SLACK-DRAFT-REVIEW-"
    "ONE-SHOT-DELIVERY-APPROVAL-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_PREP_DIGEST = (
    "bc6ec4fa94a3cf78767119f63f06ba34"
    "fe15b6090d40cd3932100d67abc63695"
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

EXPECTED_CONFIRMATION = (
    "APPROVED_FOR_ONE_SLACK_"
    "X_DRAFT_REVIEW_DELIVERY_ONLY"
)

WEBHOOK_PATTERN = re.compile(
    r"https://hooks\.slack\.com/services/"
    r"[A-Za-z0-9]+/"
    r"[A-Za-z0-9]+/"
    r"[A-Za-z0-9_-]+"
)


class SlackDeliveryApprovalError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise SlackDeliveryApprovalError(
            message
        )


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


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
        raise SlackDeliveryApprovalError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be object: {path}",
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
        raise SlackDeliveryApprovalError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def read_webhook_without_exposure(
    credential_env_path: Path,
) -> None:
    credential_env_path = (
        credential_env_path.resolve()
    )

    require(
        credential_env_path.is_file(),
        "credential.env is missing",
    )

    file_mode = stat.S_IMODE(
        credential_env_path.stat().st_mode
    )

    require(
        file_mode & 0o077 == 0,
        "credential.env permissions are too broad",
    )

    matches: list[str] = []

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

        matches.append(value)

    require(
        len(matches) == 1,
        (
            "Slack webhook credential must exist "
            "exactly once"
        ),
    )

    webhook = matches[0]

    require(
        bool(webhook),
        "Slack webhook credential is empty",
    )

    require(
        WEBHOOK_PATTERN.fullmatch(webhook)
        is not None,
        "Slack webhook credential format is invalid",
    )

    # 秘密値・長さ・ハッシュは返さない。
    return None


def validate_prep_pack(
    value: dict[str, Any],
) -> tuple[str, str]:
    verify_digest(
        value,
        digest_field=(
            "x_r12_slack_draft_review_delivery_"
            "prep_digest_sha256"
        ),
        expected_digest=EXPECTED_PREP_DIGEST,
        label="Slack delivery prep pack",
    )

    require(
        value.get("status")
        == (
            "PASS_X_R12_SLACK_DRAFT_REVIEW_"
            "DELIVERY_PREP_READY"
        ),
        "Slack prep status mismatch",
    )

    require(
        value.get("delivery_state")
        == "LOCAL_PREVIEW_READY_SLACK_NOT_SENT",
        "Slack prep delivery state mismatch",
    )

    review = value.get("review_request")

    require(
        isinstance(review, dict),
        "review request reference missing",
    )

    require(
        review.get("review_request_id")
        == EXPECTED_REVIEW_REQUEST_ID,
        "review request ID mismatch",
    )

    request_digest = review.get(
        "digest_sha256"
    )

    require(
        isinstance(request_digest, str)
        and len(request_digest) == 64,
        "review request digest invalid",
    )

    preview = value.get(
        "slack_message_preview"
    )

    require(
        isinstance(preview, dict),
        "Slack preview reference missing",
    )

    preview_digest = preview.get(
        "digest_sha256"
    )

    require(
        isinstance(preview_digest, str)
        and len(preview_digest) == 64,
        "Slack preview digest invalid",
    )

    require(
        preview.get("message_sent")
        is False,
        "Slack preview already records send",
    )

    credential = value.get("credential")

    require(
        isinstance(credential, dict),
        "credential policy missing",
    )

    require(
        credential.get("env_key")
        == CREDENTIAL_ENV_KEY,
        "credential environment key mismatch",
    )

    require(
        credential.get("credential_read")
        is False,
        "Prep already records credential read",
    )

    require(
        credential.get(
            "credential_value_recorded"
        )
        is False,
        "Prep records credential value",
    )

    for field in (
        "slack_delivery_allowed",
        "slack_message_sent",
        "credential_read",
        "database_write",
        "workflow_write",
        "browser_automation",
        "x_api_call",
        "slack_api_call",
    ):
        require(
            value.get(field) is False,
            f"unsafe prep field: {field}",
        )

    require(
        value.get("production_status")
        == "NO_GO",
        "Prep production status mismatch",
    )

    return request_digest, preview_digest


def validate_review_request(
    value: dict[str, Any],
    *,
    expected_digest: str,
) -> None:
    require(
        canonical_digest(value)
        == expected_digest,
        "review request canonical digest mismatch",
    )

    require(
        value.get("review_request_id")
        == EXPECTED_REVIEW_REQUEST_ID,
        "review request ID mismatch",
    )

    require(
        value.get("status")
        == "PENDING_SLACK_DELIVERY",
        "review request status mismatch",
    )

    require(
        value.get("review_state")
        == "NOT_REVIEWED",
        "review request was already reviewed",
    )

    require(
        value.get("x_account_handle")
        == EXPECTED_X_ACCOUNT_HANDLE,
        "X account binding mismatch",
    )

    require(
        value.get("draft_text_sha256")
        == EXPECTED_TEXT_SHA,
        "draft text SHA mismatch",
    )

    require(
        value.get("affiliate_url")
        == EXPECTED_AFFILIATE_URL,
        "affiliate URL binding mismatch",
    )

    delivery = value.get("delivery")

    require(
        isinstance(delivery, dict),
        "review delivery section missing",
    )

    require(
        delivery.get("state")
        == "NOT_SENT_PREP_ONLY",
        "review request already sent",
    )

    require(
        value.get("slack_message_sent")
        is False,
        "review request records Slack send",
    )

    require(
        value.get("x_post_allowed")
        is False,
        "review request permits X post",
    )


def validate_slack_preview(
    value: dict[str, Any],
    *,
    expected_digest: str,
) -> None:
    require(
        canonical_digest(value)
        == expected_digest,
        "Slack preview canonical digest mismatch",
    )

    serialized = json.dumps(
        value,
        ensure_ascii=False,
    )

    require(
        EXPECTED_REVIEW_REQUEST_ID
        in serialized,
        "Slack preview request ID missing",
    )

    require(
        EXPECTED_AFFILIATE_URL
        in serialized,
        "Slack preview affiliate URL missing",
    )

    require(
        "【PR・新刊】" in serialized,
        "Slack preview PR disclosure missing",
    )

    for token in (
        "APPROVE",
        "REVISE",
        "REJECT",
    ):
        require(
            token in serialized,
            f"Slack review token missing: {token}",
        )

    for secret_fragment in (
        "hooks.slack.com/services/",
        "xoxb-",
        "xapp-",
    ):
        require(
            secret_fragment not in serialized,
            "credential material leaked into preview",
        )


def validate_generation_lock(
    value: dict[str, Any],
) -> None:
    require(
        value.get("lock_type")
        == (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "DELIVERY_PREP_GENERATION"
        ),
        "generation lock type mismatch",
    )

    require(
        value.get("prep_pack_digest_sha256")
        == EXPECTED_PREP_DIGEST,
        "generation lock prep digest mismatch",
    )

    require(
        value.get("review_request_id")
        == EXPECTED_REVIEW_REQUEST_ID,
        "generation lock request ID mismatch",
    )

    require(
        value.get("generation_completed")
        is True,
        "Prep generation incomplete",
    )

    require(
        value.get("reexecution_allowed")
        is False,
        "Prep generation rerun remains allowed",
    )

    require(
        value.get("slack_message_sent")
        is False,
        "generation lock records Slack send",
    )

    require(
        value.get("x_post_allowed")
        is False,
        "generation lock permits X post",
    )


def build_gate(
    *,
    production_database_path: Path,
    prep_pack_path: Path,
    review_request_path: Path,
    slack_preview_path: Path,
    generation_lock_path: Path,
    credential_env_path: Path,
    confirmation: str,
    certificate_path: Path,
    gate_pack_path: Path,
    issuance_lock_path: Path,
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
    generation_lock_path = (
        generation_lock_path.resolve()
    )
    credential_env_path = (
        credential_env_path.resolve()
    )
    certificate_path = (
        certificate_path.resolve()
    )
    gate_pack_path = gate_pack_path.resolve()
    issuance_lock_path = (
        issuance_lock_path.resolve()
    )

    require(
        sha256_file(production_database_path)
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    require(
        confirmation == EXPECTED_CONFIRMATION,
        "explicit approval confirmation mismatch",
    )

    prep = load_json(prep_pack_path)

    (
        request_digest,
        preview_digest,
    ) = validate_prep_pack(prep)

    request = load_json(review_request_path)

    validate_review_request(
        request,
        expected_digest=request_digest,
    )

    preview = load_json(slack_preview_path)

    validate_slack_preview(
        preview,
        expected_digest=preview_digest,
    )

    generation_lock = load_json(
        generation_lock_path
    )

    validate_generation_lock(
        generation_lock
    )

    read_webhook_without_exposure(
        credential_env_path
    )

    for path, label in (
        (
            certificate_path,
            "Slack delivery approval certificate",
        ),
        (
            gate_pack_path,
            "Slack delivery approval gate pack",
        ),
        (
            issuance_lock_path,
            "Slack approval issuance lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    issued_at = datetime.now(
        timezone.utc
    ).isoformat()

    approval_request_id = (
        "xr12-slack-delivery-"
        f"{EXPECTED_PREP_DIGEST[:24]}"
    )

    certificate_payload = {
        "phase": PHASE,
        "status": (
            "SLACK_DRAFT_REVIEW_ONE_SHOT_"
            "DELIVERY_APPROVAL_ISSUED_"
            "NOT_CONSUMED"
        ),
        "issued_at": issued_at,
        "approval_request_id": (
            approval_request_id
        ),
        "approval_label": (
            EXPECTED_CONFIRMATION
        ),
        "source_prep_pack_path": str(
            prep_pack_path
        ),
        "source_prep_digest_sha256": (
            EXPECTED_PREP_DIGEST
        ),
        "review_request_path": str(
            review_request_path
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "review_request_digest_sha256": (
            request_digest
        ),
        "slack_preview_path": str(
            slack_preview_path
        ),
        "slack_preview_digest_sha256": (
            preview_digest
        ),
        "credential": {
            "source": str(
                credential_env_path
            ),
            "env_key": CREDENTIAL_ENV_KEY,
            "credential_present": True,
            "credential_format_valid": True,
            "credential_value_recorded": False,
            "credential_hash_recorded": False,
            "credential_length_recorded": False,
        },
        "binding": {
            "x_account_handle": (
                EXPECTED_X_ACCOUNT_HANDLE
            ),
            "draft_text_sha256": (
                EXPECTED_TEXT_SHA
            ),
            "affiliate_url": (
                EXPECTED_AFFILIATE_URL
            ),
            "invalidate_on_any_change": True,
        },
        "one_slack_delivery_authorized": True,
        "approval_consumed": False,
        "reissuance_allowed": False,
        "automatic_retry_allowed": False,
        "slack_message_sent": False,
        "x_post_allowed": False,
        "x_api_call": False,
        "slack_api_call": False,
        "database_write": False,
        "production_status": "NO_GO",
    }

    certificate = {
        **certificate_payload,
        "x_r12_slack_delivery_approval_"
        "certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    certificate_digest = certificate[
        "x_r12_slack_delivery_approval_"
        "certificate_digest_sha256"
    ]

    gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_APPROVAL_"
            "GATE_READY"
        ),
        "gate_state": (
            "ONE_SLACK_DELIVERY_APPROVED_"
            "NOT_EXECUTED"
        ),
        "issued_at": issued_at,
        "approval_request_id": (
            approval_request_id
        ),
        "approval_label": (
            EXPECTED_CONFIRMATION
        ),
        "source_prep_digest_sha256": (
            EXPECTED_PREP_DIGEST
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "review_request_digest_sha256": (
            request_digest
        ),
        "slack_preview_digest_sha256": (
            preview_digest
        ),
        "approval_certificate_path": str(
            certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate_digest
        ),
        "credential_present": True,
        "credential_format_valid": True,
        "credential_value_recorded": False,
        "one_slack_delivery_authorized": True,
        "approval_consumed": False,
        "slack_message_sent": False,
        "automatic_retry_allowed": False,
        "x_post_allowed": False,
        "browser_automation": False,
        "x_api_call": False,
        "slack_api_call": False,
        "database_write": False,
        "workflow_write": False,
        "production_status": "NO_GO",
        "safety_state": (
            "ONE_SHOT_SLACK_DELIVERY_"
            "APPROVED_NOT_EXECUTED_"
            "NO_X_POST"
        ),
        "authorized_next_phase": (
            "X-R12-SLACK-DRAFT-REVIEW-"
            "ONE-SHOT-DELIVERY-EXECUTION"
        ),
    }

    gate = {
        **gate_payload,
        "x_r12_slack_delivery_approval_"
        "gate_digest_sha256": (
            canonical_digest(gate_payload)
        ),
    }

    gate_digest = gate[
        "x_r12_slack_delivery_approval_"
        "gate_digest_sha256"
    ]

    issuance_lock = {
        "lock_type": (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "ONE_SHOT_DELIVERY_APPROVAL_"
            "ISSUANCE"
        ),
        "created_at": issued_at,
        "approval_request_id": (
            approval_request_id
        ),
        "review_request_id": (
            EXPECTED_REVIEW_REQUEST_ID
        ),
        "source_prep_digest_sha256": (
            EXPECTED_PREP_DIGEST
        ),
        "approval_certificate_digest_sha256": (
            certificate_digest
        ),
        "approval_gate_digest_sha256": (
            gate_digest
        ),
        "approval_issued": True,
        "approval_consumed": False,
        "reissuance_allowed": False,
        "slack_message_sent": False,
    }

    atomic_create_json(
        certificate_path,
        certificate,
    )

    atomic_create_json(
        gate_pack_path,
        gate,
    )

    atomic_create_json(
        issuance_lock_path,
        issuance_lock,
    )

    return gate


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
        "--generation-lock",
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

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_gate(
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
            generation_lock_path=(
                args.generation_lock
            ),
            credential_env_path=(
                args.credential_env
            ),
            confirmation=args.confirmation,
            certificate_path=args.certificate,
            gate_pack_path=args.gate_pack,
            issuance_lock_path=(
                args.issuance_lock
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
                        "APPROVAL_GATE"
                    ),
                    "error": str(exc),
                    "certificate_issued": False,
                    "approval_consumed": False,
                    "slack_message_sent": False,
                    "credential_value_recorded": False,
                    "database_write": False,
                    "x_api_call": False,
                    "slack_api_call": False,
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
                "gate_state": (
                    result["gate_state"]
                ),
                "approval_request_id": (
                    result["approval_request_id"]
                ),
                "review_request_id": (
                    result["review_request_id"]
                ),
                "credential_present": True,
                "credential_format_valid": True,
                "credential_value_recorded": False,
                "one_slack_delivery_authorized": True,
                "approval_consumed": False,
                "slack_message_sent": False,
                "automatic_retry_allowed": False,
                "x_post_allowed": False,
                "database_write": False,
                "x_api_call": False,
                "slack_api_call": False,
                "production_status": "NO_GO",
                "gate_pack_path": str(
                    args.gate_pack.resolve()
                ),
                "gate_digest_sha256": (
                    result[
                        "x_r12_slack_delivery_"
                        "approval_gate_digest_sha256"
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
