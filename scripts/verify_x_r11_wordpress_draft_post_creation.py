from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import atomic_write_json
from scripts.build_x_r9_preflight_approval_pack import canonical_digest
from scripts.run_x_r11_wordpress_draft_creation_once import (
    build_authorization_header,
    build_rest_base,
    find_duplicate_posts,
    first_env,
    load_json,
    parse_env_file,
    request_json,
    sha256_file,
    validate_category,
    validate_created_post,
    verify_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-POST-CREATION-VERIFICATION"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_FINAL_GATE_DIGEST = (
    "f348d6f37980fdd5ccd5e9c9f5bc84c3"
    "7afc80509b369cd293fb5614f7edfd86"
)

EXPECTED_CREATION_RECEIPT_DIGEST = (
    "c34dafd1f40b744fc8ea978d420a355d"
    "d212b01c2502df780a6980b80bc96141"
)

EXPECTED_APPROVAL_CERTIFICATE_DIGEST = (
    "794843a83eb52837ea01181754f3f3f66"
    "89f1eb4c8ca6225adc85884203962fa"
)

EXPECTED_CREATION_REQUEST_ID = (
    "xr11-wp-draft-create-"
    "baf4e4451e14b3b4b3984bd2"
)

EXPECTED_POST_ID = 195

EXPECTED_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_CATEGORY_ID = 43


class PostCreationVerificationError(
    RuntimeError
):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise PostCreationVerificationError(
            message
        )


def validate_duplicate_state(
    value: dict[str, Any],
) -> None:
    require(
        value.get("duplicate_found")
        is True,
        "created post was not found by duplicate search",
    )

    require(
        value.get("exact_slug_match_count")
        == 1,
        (
            "exact slug match count must "
            "equal one"
        ),
    )

    require(
        value.get("exact_title_match_count")
        == 1,
        (
            "exact title match count must "
            "equal one"
        ),
    )

    require(
        value.get("matched_post_ids")
        == [EXPECTED_POST_ID],
        (
            "duplicate search must resolve "
            f"only to post {EXPECTED_POST_ID}"
        ),
    )


def validate_execution_evidence(
    *,
    execution_claim: dict[str, Any],
    consumption_lock: dict[str, Any],
    payload_digest: str,
) -> None:
    require(
        execution_claim.get("lock_type")
        == (
            "X_R11_WORDPRESS_DRAFT_"
            "CREATION_EXECUTION_CLAIM"
        ),
        "execution claim type mismatch",
    )

    require(
        execution_claim.get(
            "creation_request_id"
        )
        == EXPECTED_CREATION_REQUEST_ID,
        "execution claim request ID mismatch",
    )

    require(
        execution_claim.get(
            "approval_certificate_digest_sha256"
        )
        == EXPECTED_APPROVAL_CERTIFICATE_DIGEST,
        "execution claim approval digest mismatch",
    )

    require(
        execution_claim.get(
            "payload_preview_digest_sha256"
        )
        == payload_digest,
        "execution claim payload digest mismatch",
    )

    require(
        execution_claim.get(
            "maximum_post_create_count"
        )
        == 1,
        "execution claim maximum count mismatch",
    )

    require(
        execution_claim.get(
            "execution_claimed"
        )
        is True,
        "execution was not claimed",
    )

    require(
        execution_claim.get(
            "reexecution_allowed"
        )
        is False,
        "execution claim permits reexecution",
    )

    require(
        consumption_lock.get("lock_type")
        == (
            "X_R11_WORDPRESS_DRAFT_"
            "CREATION_APPROVAL_CONSUMPTION"
        ),
        "consumption lock type mismatch",
    )

    require(
        consumption_lock.get(
            "creation_request_id"
        )
        == EXPECTED_CREATION_REQUEST_ID,
        "consumption lock request ID mismatch",
    )

    require(
        consumption_lock.get(
            "approval_certificate_digest_sha256"
        )
        == EXPECTED_APPROVAL_CERTIFICATE_DIGEST,
        "consumption lock approval digest mismatch",
    )

    require(
        consumption_lock.get(
            "wordpress_post_id"
        )
        == EXPECTED_POST_ID,
        "consumption lock post ID mismatch",
    )

    require(
        consumption_lock.get(
            "wordpress_post_status"
        )
        == "draft",
        "consumption lock post status mismatch",
    )

    require(
        consumption_lock.get(
            "approval_consumed"
        )
        is True,
        "approval was not consumed",
    )

    require(
        consumption_lock.get(
            "reexecution_allowed"
        )
        is False,
        "consumption lock permits reexecution",
    )


def verify_post_creation(
    *,
    production_database_path: Path,
    final_gate_pack_path: Path,
    creation_receipt_path: Path,
    execution_claim_path: Path,
    consumption_lock_path: Path,
    credential_env_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )
    final_gate_pack_path = (
        final_gate_pack_path.resolve()
    )
    creation_receipt_path = (
        creation_receipt_path.resolve()
    )
    execution_claim_path = (
        execution_claim_path.resolve()
    )
    consumption_lock_path = (
        consumption_lock_path.resolve()
    )
    credential_env_path = (
        credential_env_path.resolve()
    )
    output_path = output_path.resolve()

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    final_gate = load_json(
        final_gate_pack_path
    )

    verify_digest(
        final_gate,
        digest_field=(
            "wordpress_draft_final_gate_"
            "digest_sha256"
        ),
        expected_digest=(
            EXPECTED_FINAL_GATE_DIGEST
        ),
        label="Final Gate",
    )

    receipt = load_json(
        creation_receipt_path
    )

    verify_digest(
        receipt,
        digest_field=(
            "wordpress_draft_creation_"
            "one_shot_receipt_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_CREATION_RECEIPT_DIGEST
        ),
        label="creation receipt",
    )

    require(
        receipt.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_CREATED_"
            "ONE_SHOT"
        ),
        "creation receipt status mismatch",
    )

    require(
        receipt.get("creation_request_id")
        == EXPECTED_CREATION_REQUEST_ID,
        "creation receipt request ID mismatch",
    )

    require(
        receipt.get("actual_create_count")
        == 1,
        "actual create count must equal one",
    )

    require(
        receipt.get("approval_consumed")
        is True,
        "creation approval was not consumed",
    )

    require(
        receipt.get("reexecution_allowed")
        is False,
        "creation receipt permits reexecution",
    )

    require(
        receipt.get("wordpress_write")
        is True,
        "creation receipt does not record a write",
    )

    require(
        receipt.get("publication_allowed")
        is False,
        "publication is unexpectedly allowed",
    )

    receipt_post = receipt.get(
        "wordpress_post"
    )

    require(
        isinstance(receipt_post, dict),
        "creation receipt post evidence is missing",
    )

    require(
        receipt_post.get("post_id")
        == EXPECTED_POST_ID,
        "creation receipt post ID mismatch",
    )

    execution_claim = load_json(
        execution_claim_path
    )

    consumption_lock = load_json(
        consumption_lock_path
    )

    payload_preview_path = Path(
        final_gate["payload_preview_path"]
    ).resolve()

    payload_preview = load_json(
        payload_preview_path
    )

    payload_digest = verify_digest(
        payload_preview,
        digest_field=(
            "wordpress_draft_payload_"
            "preview_digest_sha256"
        ),
        expected_digest=(
            final_gate[
                "payload_preview_digest_sha256"
            ]
        ),
        label="payload preview",
    )

    request_payload = payload_preview.get(
        "wordpress_request"
    )

    require(
        isinstance(request_payload, dict),
        "WordPress request payload is missing",
    )

    expected_content = request_payload.get(
        "content"
    )

    require(
        isinstance(expected_content, str)
        and expected_content,
        "expected article content is missing",
    )

    validate_execution_evidence(
        execution_claim=execution_claim,
        consumption_lock=consumption_lock,
        payload_digest=payload_digest,
    )

    env_values = parse_env_file(
        credential_env_path
    )

    rest_base = build_rest_base(
        env_values
    )

    username = first_env(
        env_values,
        (
            "WORDPRESS_USERNAME",
            "WP_USERNAME",
            "WORDPRESS_USER",
            "WP_USER",
        ),
        "WordPress username",
    )

    application_password = first_env(
        env_values,
        (
            "WORDPRESS_APPLICATION_PASSWORD",
            "WP_APPLICATION_PASSWORD",
            "WORDPRESS_APP_PASSWORD",
            "WP_APP_PASSWORD",
        ),
        "WordPress application password",
    )

    authorization = (
        build_authorization_header(
            username,
            application_password,
        )
    )

    post_url = (
        rest_base.rstrip("/")
        + "/posts/"
        + str(EXPECTED_POST_ID)
        + "?context=edit"
        + "&_fields=id,title,slug,status,"
        + "categories,content,link,date,modified"
    )

    live_post = request_json(
        method="GET",
        url=post_url,
        authorization=authorization,
    )

    require(
        isinstance(live_post, dict),
        "live post response is invalid",
    )

    post_result = validate_created_post(
        live_post,
        expected_content=expected_content,
    )

    require(
        post_result["post_id"]
        == EXPECTED_POST_ID,
        "live WordPress post ID mismatch",
    )

    duplicate_state = find_duplicate_posts(
        rest_base=rest_base,
        authorization=authorization,
    )

    validate_duplicate_state(
        duplicate_state
    )

    category_state = validate_category(
        rest_base=rest_base,
        authorization=authorization,
    )

    verified_at = datetime.now(
        timezone.utc
    ).isoformat()

    verification_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_DRAFT_"
            "POST_CREATION_VERIFICATION"
        ),
        "verification_state": (
            "WORDPRESS_DRAFT_195_VERIFIED_"
            "REEXECUTION_BLOCKED_X_DRAFT_READY"
        ),
        "verified_at": verified_at,
        "creation_request_id": (
            EXPECTED_CREATION_REQUEST_ID
        ),
        "source_final_gate_pack_path": str(
            final_gate_pack_path
        ),
        "source_final_gate_digest_sha256": (
            EXPECTED_FINAL_GATE_DIGEST
        ),
        "source_creation_receipt_path": str(
            creation_receipt_path
        ),
        "source_creation_receipt_digest_sha256": (
            EXPECTED_CREATION_RECEIPT_DIGEST
        ),
        "execution_claim_path": str(
            execution_claim_path
        ),
        "consumption_lock_path": str(
            consumption_lock_path
        ),
        "wordpress_post": post_result,
        "wordpress_live_post_date": (
            live_post.get("date")
        ),
        "wordpress_live_post_modified": (
            live_post.get("modified")
        ),
        "duplicate_verification": (
            duplicate_state
        ),
        "category_verification": (
            category_state
        ),
        "content_sha256": final_gate[
            "rendered_html_sha256"
        ],
        "actual_create_count": 1,
        "approval_consumed": True,
        "reexecution_allowed": False,
        "duplicate_count_verified": 1,
        "wordpress_api_call": True,
        "wordpress_api_method": "GET_ONLY",
        "wordpress_write": False,
        "wordpress_post_status": "draft",
        "publication_allowed": False,
        "wordpress_media_upload_required_before_publish": (
            True
        ),
        "database_write": False,
        "workflow_write": False,
        "x_draft_generation_allowed": True,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "WORDPRESS_DRAFT_VERIFIED_"
            "NO_FURTHER_WORDPRESS_WRITE_ALLOWED"
        ),
        "authorized_next_phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "X-DRAFT-LOCAL-GENERATION"
        ),
    }

    verification = {
        **verification_payload,
        "wordpress_draft_post_creation_"
        "verification_digest_sha256": (
            canonical_digest(
                verification_payload
            )
        ),
    }

    atomic_write_json(
        output_path,
        verification,
    )

    return verification


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--final-gate-pack",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--creation-receipt",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--execution-claim",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--consumption-lock",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--credential-env",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = verify_post_creation(
            production_database_path=(
                args.production_db
            ),
            final_gate_pack_path=(
                args.final_gate_pack
            ),
            creation_receipt_path=(
                args.creation_receipt
            ),
            execution_claim_path=(
                args.execution_claim
            ),
            consumption_lock_path=(
                args.consumption_lock
            ),
            credential_env_path=(
                args.credential_env
            ),
            output_path=args.output,
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_DRAFT_"
                        "POST_CREATION_VERIFICATION"
                    ),
                    "error": str(exc),
                    "wordpress_api_call": True,
                    "wordpress_api_method": "GET_ONLY",
                    "wordpress_write": False,
                    "reexecution_allowed": False,
                    "production_status": "NO_GO",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    post = result["wordpress_post"]

    print(
        json.dumps(
            {
                "phase": result["phase"],
                "status": result["status"],
                "verification_state": (
                    result["verification_state"]
                ),
                "wordpress_post_id": (
                    post["post_id"]
                ),
                "wordpress_post_title": (
                    post["title"]
                ),
                "wordpress_post_slug": (
                    post["slug"]
                ),
                "wordpress_post_status": (
                    post["status"]
                ),
                "wordpress_category_ids": (
                    post["categories"]
                ),
                "duplicate_count_verified": 1,
                "approval_consumed": True,
                "reexecution_allowed": False,
                "wordpress_api_method": "GET_ONLY",
                "wordpress_write": False,
                "x_draft_generation_allowed": True,
                "production_status": "NO_GO",
                "verification_pack_path": str(
                    args.output.resolve()
                ),
                "verification_digest_sha256": (
                    result[
                        "wordpress_draft_"
                        "post_creation_verification_"
                        "digest_sha256"
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
