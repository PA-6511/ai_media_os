from __future__ import annotations

import argparse
import hashlib
import json
import os
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
    "DELIVERY-PREP"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_CORRECTIVE_EVIDENCE_DIGEST = (
    "478a6fb4f766b139da0d30f50884be72"
    "a39a339fe9be9bc7d335075c316007d2"
)

EXPECTED_METRICS_BASELINE_DIGEST = (
    "6266866ff6f392dee253685e080e6a51"
    "4861ae9e1f8c4be074777194dc8580c6"
)

EXPECTED_X_POST_ID = "2078417820015333645"

EXPECTED_X_POST_URL = (
    "https://x.com/mz_GK7_DM2/"
    "status/2078417820015333645"
)

EXPECTED_X_ACCOUNT_HANDLE = "@mz_GK7_DM2"

EXPECTED_REVISION = (
    "CORRECTIVE_DIRECT_AFFILIATE_V1"
)

EXPECTED_LINK_ROUTE = "DIRECT_AFFILIATE"
EXPECTED_STORE = "RAKUTEN_KOBO"

EXPECTED_AFFILIATE_URL = (
    "https://a.r10.to/hPKo3p"
)

EXPECTED_TEXT_SHA = (
    "125481ce9a0a1ad8972c2f855e9d2bb5"
    "5f4e3215152ba6ba0fa626e489a81d67"
)

POLICY_SCHEMA = (
    "X_R12_SLACK_DRAFT_REVIEW_"
    "DELIVERY_POLICY_V1"
)

APPROVAL_TOKENS = [
    "APPROVE",
    "REVISE",
    "REJECT",
]


class SlackDraftPrepError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise SlackDraftPrepError(message)


def sha256_file(path: Path) -> str:
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
        raise SlackDraftPrepError(
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
        raise SlackDraftPrepError(
            f"artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def validate_policy(
    policy: dict[str, Any],
) -> None:
    require(
        policy.get("schema_version")
        == POLICY_SCHEMA,
        "policy schema mismatch",
    )

    require(
        policy.get("phase") == PHASE,
        "policy phase mismatch",
    )

    require(
        policy.get("status")
        == "PREP_ONLY_NO_DELIVERY",
        "policy status mismatch",
    )

    delivery = policy.get("delivery")

    require(
        isinstance(delivery, dict),
        "delivery policy is missing",
    )

    require(
        delivery.get("transport")
        == "SLACK_INCOMING_WEBHOOK",
        "Slack transport mismatch",
    )

    require(
        delivery.get("credential_env_key")
        == "SLACK_X_DRAFT_REVIEW_WEBHOOK_URL",
        "Slack credential key mismatch",
    )

    require(
        delivery.get(
            "credential_read_allowed_in_prep"
        )
        is False,
        "credential read is allowed in prep",
    )

    require(
        delivery.get(
            "slack_api_call_allowed_in_prep"
        )
        is False,
        "Slack API call is allowed in prep",
    )

    require(
        delivery.get(
            "message_send_allowed_in_prep"
        )
        is False,
        "Slack message send is allowed in prep",
    )

    require(
        delivery.get(
            "interactive_buttons_enabled"
        )
        is False,
        "interactive buttons must remain disabled",
    )

    review = policy.get("review")

    require(
        isinstance(review, dict),
        "review policy is missing",
    )

    require(
        review.get("human_approval_required")
        is True,
        "human approval is not required",
    )

    require(
        review.get("approval_tokens")
        == APPROVAL_TOKENS,
        "approval tokens mismatch",
    )

    for field in (
        "approval_expires_after_text_change",
        "approval_expires_after_url_change",
        "approval_expires_after_account_change",
    ):
        require(
            review.get(field) is True,
            f"approval invalidation rule missing: {field}",
        )

    posting = policy.get("posting")

    require(
        isinstance(posting, dict),
        "posting policy is missing",
    )

    require(
        posting.get("x_posting_mode")
        == "MANUAL",
        "X posting mode mismatch",
    )

    require(
        posting.get("x_api_allowed")
        is False,
        "X API is allowed",
    )

    require(
        posting.get(
            "browser_automation_allowed"
        )
        is False,
        "browser automation is allowed",
    )

    require(
        posting.get(
            "automatic_posting_allowed"
        )
        is False,
        "automatic X posting is allowed",
    )

    require(
        policy.get("production_status")
        == "NO_GO",
        "policy production status mismatch",
    )


def validate_corrective_evidence(
    value: dict[str, Any],
) -> str:
    verify_digest(
        value,
        digest_field=(
            "x_manual_posting_corrective_"
            "evidence_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_CORRECTIVE_EVIDENCE_DIGEST
        ),
        label="corrective posting evidence",
    )

    require(
        value.get("status")
        == (
            "PASS_X_MANUAL_POSTING_CORRECTIVE_"
            "EVIDENCE_REGISTERED"
        ),
        "corrective evidence status mismatch",
    )

    require(
        value.get("revision")
        == EXPECTED_REVISION,
        "revision mismatch",
    )

    require(
        value.get("link_route")
        == EXPECTED_LINK_ROUTE,
        "link route mismatch",
    )

    require(
        value.get("store")
        == EXPECTED_STORE,
        "store mismatch",
    )

    post = value.get("x_post")

    require(
        isinstance(post, dict),
        "X post evidence is missing",
    )

    require(
        post.get("post_id")
        == EXPECTED_X_POST_ID,
        "X post ID mismatch",
    )

    require(
        post.get("post_url")
        == EXPECTED_X_POST_URL,
        "X post URL mismatch",
    )

    require(
        post.get("x_account_handle")
        == EXPECTED_X_ACCOUNT_HANDLE,
        "X account mismatch",
    )

    require(
        post.get("affiliate_url")
        == EXPECTED_AFFILIATE_URL,
        "affiliate URL mismatch",
    )

    transcription = value.get(
        "corrective_transcription"
    )

    require(
        isinstance(transcription, dict),
        "corrective transcription is missing",
    )

    text = transcription.get("text")

    require(
        isinstance(text, str),
        "corrective draft text is missing",
    )

    require(
        transcription.get("text_sha256")
        == EXPECTED_TEXT_SHA,
        "corrective text SHA mismatch",
    )

    require(
        hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest()
        == EXPECTED_TEXT_SHA,
        "corrective text content mismatch",
    )

    require(
        text.startswith("【PR・新刊】\n"),
        "visible PR disclosure is missing",
    )

    require(
        text.count(EXPECTED_AFFILIATE_URL)
        == 1,
        "affiliate URL count mismatch",
    )

    old_approval = value.get(
        "old_manual_posting_approval"
    )

    require(
        isinstance(old_approval, dict),
        "old approval disposition is missing",
    )

    require(
        old_approval.get("approval_consumed")
        is False,
        "old approval was consumed",
    )

    require(
        old_approval.get("superseded")
        is True,
        "old approval was not superseded",
    )

    require(
        old_approval.get("reuse_allowed")
        is False,
        "old approval remains reusable",
    )

    return text


def validate_metrics_baseline(
    value: dict[str, Any],
) -> None:
    verify_digest(
        value,
        digest_field=(
            "x_post_metrics_baseline_"
            "prep_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_METRICS_BASELINE_DIGEST
        ),
        label="metrics baseline",
    )

    require(
        value.get("status")
        == (
            "PASS_X_POST_METRICS_"
            "BASELINE_PREP_READY"
        ),
        "metrics baseline status mismatch",
    )

    require(
        value.get("baseline_state")
        == (
            "AWAITING_MANUAL_METRICS_"
            "CAPTURE_24H_AND_7D"
        ),
        "metrics baseline state mismatch",
    )

    require(
        value.get("additional_x_post_allowed")
        is False,
        "metrics baseline permits another X post",
    )

    require(
        value.get("database_write")
        is False,
        "metrics baseline wrote to database",
    )

    require(
        value.get("x_api_call")
        is False,
        "metrics baseline called X API",
    )

    require(
        value.get("production_status")
        == "NO_GO",
        "metrics baseline production status mismatch",
    )


def build_review_request(
    *,
    draft_text: str,
    required_checks: list[str],
) -> dict[str, Any]:
    seed = {
        "revision": EXPECTED_REVISION,
        "text_sha256": EXPECTED_TEXT_SHA,
        "x_account_handle": (
            EXPECTED_X_ACCOUNT_HANDLE
        ),
        "affiliate_url": (
            EXPECTED_AFFILIATE_URL
        ),
        "required_checks": required_checks,
    }

    request_digest = canonical_digest(seed)

    return {
        "schema_version": (
            "X_R12_SLACK_DRAFT_REVIEW_REQUEST_V1"
        ),
        "review_request_id": (
            f"xr12-slack-review-{request_digest[:24]}"
        ),
        "status": (
            "PENDING_SLACK_DELIVERY"
        ),
        "review_state": "NOT_REVIEWED",
        "source_type": (
            "REFERENCE_STANDARD_FROM_"
            "CORRECTIVE_DIRECT_AFFILIATE_V1"
        ),
        "x_account_handle": (
            EXPECTED_X_ACCOUNT_HANDLE
        ),
        "revision": EXPECTED_REVISION,
        "link_route": EXPECTED_LINK_ROUTE,
        "store": EXPECTED_STORE,
        "affiliate_url": EXPECTED_AFFILIATE_URL,
        "draft_text": draft_text,
        "draft_text_sha256": (
            EXPECTED_TEXT_SHA
        ),
        "required_checks": required_checks,
        "review_commands": {
            "approve": "APPROVE",
            "revise": "REVISE",
            "reject": "REJECT",
        },
        "approval_binding": {
            "bind_text_sha256": True,
            "bind_affiliate_url": True,
            "bind_x_account_handle": True,
            "invalidate_on_any_change": True,
        },
        "delivery": {
            "transport": (
                "SLACK_INCOMING_WEBHOOK"
            ),
            "state": "NOT_SENT_PREP_ONLY",
            "slack_channel_resolved": False,
            "slack_message_timestamp": None,
            "slack_thread_timestamp": None,
        },
        "human_approval_required": True,
        "slack_message_sent": False,
        "x_post_allowed": False,
        "x_api_call": False,
        "browser_automation": False,
        "database_write": False,
        "production_status": "NO_GO",
    }


def build_slack_payload(
    request: dict[str, Any],
) -> dict[str, Any]:
    text = request["draft_text"]

    require(
        len(text) <= 280,
        "X draft exceeds 280 characters",
    )

    require(
        "【PR・新刊】" in text,
        "Slack preview lacks PR disclosure",
    )

    require(
        request["affiliate_url"] in text,
        "Slack preview lacks affiliate URL",
    )

    checks = "\n".join(
        f"• `{item}`"
        for item in request["required_checks"]
    )

    plaintext = (
        "【X投稿レビュー待ち】\n"
        f"Request: {request['review_request_id']}\n"
        f"Account: {request['x_account_handle']}\n"
        f"Store: {request['store']}\n\n"
        f"{text}\n\n"
        "確認後、スレッドへ "
        "APPROVE / REVISE / REJECT "
        "のいずれかを返信してください。"
    )

    payload = {
        "text": plaintext,
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "X投稿レビュー待ち",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*Request ID*\n"
                            f"`{request['review_request_id']}`"
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*投稿アカウント*\n"
                            f"`{request['x_account_handle']}`"
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*リンク方式*\n"
                            f"`{request['link_route']}`"
                        ),
                    },
                    {
                        "type": "mrkdwn",
                        "text": (
                            "*ストア*\n"
                            f"`{request['store']}`"
                        ),
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*投稿予定本文*\n"
                        "```"
                        f"{text}"
                        "```"
                    ),
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*投稿前検査*\n"
                        f"{checks}"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            "スレッドへ "
                            "`APPROVE` / `REVISE` / "
                            "`REJECT` のいずれかを返信。"
                        ),
                    }
                ],
            },
        ],
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
    )

    forbidden_fragments = (
        "hooks.slack.com/services/",
        "xoxb-",
        "xapp-",
        "SLACK_WEBHOOK_URL=",
    )

    for fragment in forbidden_fragments:
        require(
            fragment not in serialized,
            "Slack credential leaked into preview",
        )

    return payload


def build_prep(
    *,
    production_database_path: Path,
    corrective_evidence_path: Path,
    metrics_baseline_path: Path,
    policy_path: Path,
    review_request_path: Path,
    slack_preview_path: Path,
    prep_pack_path: Path,
    generation_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    corrective_evidence_path = (
        corrective_evidence_path.resolve()
    )

    metrics_baseline_path = (
        metrics_baseline_path.resolve()
    )

    policy_path = policy_path.resolve()
    review_request_path = (
        review_request_path.resolve()
    )

    slack_preview_path = (
        slack_preview_path.resolve()
    )

    prep_pack_path = prep_pack_path.resolve()
    generation_lock_path = (
        generation_lock_path.resolve()
    )

    require(
        sha256_file(production_database_path)
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    policy = load_json(policy_path)
    validate_policy(policy)

    corrective_evidence = load_json(
        corrective_evidence_path
    )

    draft_text = validate_corrective_evidence(
        corrective_evidence
    )

    metrics_baseline = load_json(
        metrics_baseline_path
    )

    validate_metrics_baseline(
        metrics_baseline
    )

    required_checks = policy.get(
        "required_checks"
    )

    require(
        isinstance(required_checks, list),
        "required checks are missing",
    )

    require(
        all(
            isinstance(item, str)
            and item
            for item in required_checks
        ),
        "required checks are invalid",
    )

    for path, label in (
        (
            review_request_path,
            "review request",
        ),
        (
            slack_preview_path,
            "Slack message preview",
        ),
        (
            prep_pack_path,
            "Slack delivery prep pack",
        ),
        (
            generation_lock_path,
            "Slack delivery prep lock",
        ),
    ):
        require(
            not path.exists(),
            f"{label} already exists",
        )

    review_request = build_review_request(
        draft_text=draft_text,
        required_checks=required_checks,
    )

    slack_payload = build_slack_payload(
        review_request
    )

    prepared_at = datetime.now(
        timezone.utc
    ).isoformat()

    policy_digest = canonical_digest(policy)

    request_digest = canonical_digest(
        review_request
    )

    preview_digest = canonical_digest(
        slack_payload
    )

    prep_payload = {
        "phase": PHASE,
        "status": (
            "PASS_X_R12_SLACK_DRAFT_REVIEW_"
            "DELIVERY_PREP_READY"
        ),
        "delivery_state": (
            "LOCAL_PREVIEW_READY_"
            "SLACK_NOT_SENT"
        ),
        "prepared_at": prepared_at,
        "policy_path": str(policy_path),
        "policy_digest_sha256": policy_digest,
        "source_corrective_evidence_path": str(
            corrective_evidence_path
        ),
        "source_corrective_evidence_digest_sha256": (
            EXPECTED_CORRECTIVE_EVIDENCE_DIGEST
        ),
        "source_metrics_baseline_path": str(
            metrics_baseline_path
        ),
        "source_metrics_baseline_digest_sha256": (
            EXPECTED_METRICS_BASELINE_DIGEST
        ),
        "review_request": {
            "path": str(review_request_path),
            "review_request_id": (
                review_request[
                    "review_request_id"
                ]
            ),
            "digest_sha256": request_digest,
            "status": (
                review_request["status"]
            ),
        },
        "slack_message_preview": {
            "path": str(slack_preview_path),
            "digest_sha256": preview_digest,
            "transport": (
                "SLACK_INCOMING_WEBHOOK"
            ),
            "message_sent": False,
        },
        "credential": {
            "env_key": (
                "SLACK_X_DRAFT_REVIEW_WEBHOOK_URL"
            ),
            "source": (
                "/etc/ai-media-os/credential.env"
            ),
            "credential_read": False,
            "credential_value_recorded": False,
        },
        "review_mode": (
            "SLACK_THREAD_TEXT_COMMANDS"
        ),
        "human_approval_required": True,
        "interactive_buttons_enabled": False,
        "slack_delivery_allowed": False,
        "slack_message_sent": False,
        "x_post_allowed": False,
        "additional_x_post_allowed": False,
        "credential_read": False,
        "normal_x_fb_write": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "browser_automation": False,
        "x_api_call": False,
        "slack_api_call": False,
        "production_status": "NO_GO",
        "safety_state": (
            "LOCAL_PREVIEW_ONLY_"
            "NO_CREDENTIAL_READ_"
            "NO_SLACK_SEND_"
            "NO_X_POST"
        ),
        "authorized_next_phase": (
            "X-R12-SLACK-DRAFT-REVIEW-"
            "ONE-SHOT-DELIVERY-APPROVAL-GATE"
        ),
    }

    prep_pack = {
        **prep_payload,
        "x_r12_slack_draft_review_delivery_"
        "prep_digest_sha256": (
            canonical_digest(prep_payload)
        ),
    }

    prep_digest = prep_pack[
        "x_r12_slack_draft_review_delivery_"
        "prep_digest_sha256"
    ]

    generation_lock = {
        "lock_type": (
            "X_R12_SLACK_DRAFT_REVIEW_"
            "DELIVERY_PREP_GENERATION"
        ),
        "created_at": prepared_at,
        "source_corrective_evidence_digest_sha256": (
            EXPECTED_CORRECTIVE_EVIDENCE_DIGEST
        ),
        "source_metrics_baseline_digest_sha256": (
            EXPECTED_METRICS_BASELINE_DIGEST
        ),
        "review_request_id": (
            review_request["review_request_id"]
        ),
        "prep_pack_path": str(prep_pack_path),
        "prep_pack_digest_sha256": prep_digest,
        "generation_completed": True,
        "reexecution_allowed": False,
        "slack_message_sent": False,
        "x_post_allowed": False,
    }

    atomic_create_json(
        review_request_path,
        review_request,
    )

    atomic_create_json(
        slack_preview_path,
        slack_payload,
    )

    atomic_create_json(
        prep_pack_path,
        prep_pack,
    )

    atomic_create_json(
        generation_lock_path,
        generation_lock,
    )

    return prep_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--corrective-evidence",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--metrics-baseline",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--policy",
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
        "--prep-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--generation-lock",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = build_prep(
            production_database_path=(
                args.production_db
            ),
            corrective_evidence_path=(
                args.corrective_evidence
            ),
            metrics_baseline_path=(
                args.metrics_baseline
            ),
            policy_path=args.policy,
            review_request_path=(
                args.review_request
            ),
            slack_preview_path=(
                args.slack_preview
            ),
            prep_pack_path=args.prep_pack,
            generation_lock_path=(
                args.generation_lock
            ),
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_X_R12_SLACK_DRAFT_"
                        "REVIEW_DELIVERY_PREP"
                    ),
                    "error": str(exc),
                    "automatic_rerun_allowed": False,
                    "slack_message_sent": False,
                    "credential_read": False,
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
                "delivery_state": (
                    result["delivery_state"]
                ),
                "review_request_id": (
                    result[
                        "review_request"
                    ]["review_request_id"]
                ),
                "review_mode": (
                    result["review_mode"]
                ),
                "human_approval_required": True,
                "interactive_buttons_enabled": False,
                "slack_delivery_allowed": False,
                "slack_message_sent": False,
                "credential_read": False,
                "database_write": False,
                "x_api_call": False,
                "slack_api_call": False,
                "production_status": "NO_GO",
                "prep_pack_path": str(
                    args.prep_pack.resolve()
                ),
                "prep_digest_sha256": (
                    result[
                        "x_r12_slack_draft_review_"
                        "delivery_prep_digest_sha256"
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
