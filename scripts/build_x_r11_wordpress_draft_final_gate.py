from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
)


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-FINAL-GATE"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_REVIEW_DIGEST = (
    "7019d0dc4428b6a13c6ae94fb519ad07"
    "32dc893072b332e08e951c01b97e7a51"
)

EXPECTED_DRY_RUN_DIGEST = (
    "f17a372e636541d21b4d0b522cdd49863"
    "054e3f6c43442363521b4f7ce8f52db"
)

EXPECTED_RENDERED_HTML_SHA = (
    "ae18a9116741fea0ea51bc105ed89a6c5"
    "14bf512bc02d1d0c69f6998695aef5b"
)

EXPECTED_REVIEW_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "DRAFT_FINAL_GATE_ONLY"
)

NEXT_CREATION_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_WORDPRESS_"
    "DRAFT_CREATION_ONLY"
)

EXPECTED_TITLE = (
    "のあ先輩はともだち。 "
    "第11巻｜配信開始"
)

EXPECTED_SLUG = (
    "noa-senpai-wa-tomodachi-"
    "11-6ffa7a8d"
)

EXPECTED_CATEGORY_ID = 43
EXPECTED_CHECK_COUNT = 8

CURRENT_PRODUCT_HASH = (
    "bce9f1878b0032dc4745ecf22fd179a6"
)

BLOCKED_OLD_PRODUCT_HASH = (
    "f402536ea6473a172c957407fae06192"
)


class FinalGateError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise FinalGateError(message)


def load_json(
    path: Path,
) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    try:
        value = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except json.JSONDecodeError as exc:
        raise FinalGateError(
            f"invalid JSON: {path}: {exc}"
        ) from exc

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def verify_digest(
    value: dict[str, Any],
    *,
    digest_field: str,
    expected_digest: str | None,
    label: str,
) -> str:
    recorded = value.get(digest_field)

    require(
        isinstance(recorded, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            recorded,
        )
        is not None,
        f"{label} digest is invalid",
    )

    if expected_digest is not None:
        require(
            recorded == expected_digest,
            f"{label} digest mismatch",
        )

    payload = {
        key: item
        for key, item in value.items()
        if key != digest_field
    }

    require(
        canonical_digest(payload)
        == recorded,
        f"{label} digest verification failed",
    )

    return recorded


def validate_approval_label(
    approval_label: str,
) -> None:
    require(
        approval_label
        == EXPECTED_REVIEW_APPROVAL_LABEL,
        (
            "approval label must exactly equal "
            f"{EXPECTED_REVIEW_APPROVAL_LABEL}"
        ),
    )


def validate_pending_checklist(
    checklist: Any,
) -> None:
    require(
        isinstance(checklist, list),
        "human review checklist is missing",
    )

    require(
        len(checklist)
        == EXPECTED_CHECK_COUNT,
        (
            "human review checklist must "
            f"contain {EXPECTED_CHECK_COUNT} checks"
        ),
    )

    check_ids: list[str] = []

    for item in checklist:
        require(
            isinstance(item, dict),
            "human review checklist item is invalid",
        )

        check_id = item.get("check_id")

        require(
            isinstance(check_id, str)
            and check_id,
            "human review check ID is missing",
        )

        require(
            item.get("human_decision")
            == "PENDING",
            (
                "human review checklist is not "
                "in its original pending state"
            ),
        )

        check_ids.append(check_id)

    require(
        len(set(check_ids))
        == EXPECTED_CHECK_COUNT,
        "human review check IDs are not unique",
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
            (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
            ),
            0o600,
        )
    except FileExistsError as exc:
        raise FinalGateError(
            (
                "human review approval was "
                "already consumed: "
                f"{path}"
            )
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def build_final_gate(
    *,
    production_database_path: Path,
    review_pack_path: Path,
    approval_label: str,
    approval_certificate_path: Path,
    final_gate_pack_path: Path,
    consumption_lock_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    review_pack_path = (
        review_pack_path.resolve()
    )

    approval_certificate_path = (
        approval_certificate_path.resolve()
    )

    final_gate_pack_path = (
        final_gate_pack_path.resolve()
    )

    consumption_lock_path = (
        consumption_lock_path.resolve()
    )

    validate_approval_label(
        approval_label
    )

    require(
        production_database_path.is_file(),
        "production database is missing",
    )

    require(
        sha256_file(
            production_database_path
        )
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    require(
        not consumption_lock_path.exists(),
        (
            "human review approval has "
            "already been consumed"
        ),
    )

    review = load_json(
        review_pack_path
    )

    verify_digest(
        review,
        digest_field=(
            "wordpress_draft_render_human_"
            "review_request_digest_sha256"
        ),
        expected_digest=(
            EXPECTED_REVIEW_DIGEST
        ),
        label="human review request pack",
    )

    require(
        review.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_RENDER_"
            "HUMAN_REVIEW_REQUEST_READY"
        ),
        "human review request did not pass",
    )

    require(
        review.get("human_review_state")
        == (
            "AWAITING_EXPLICIT_HUMAN_DECISION"
        ),
        "human review state mismatch",
    )

    require(
        review.get(
            "approval_label_if_approved"
        )
        == EXPECTED_REVIEW_APPROVAL_LABEL,
        "review approval label mismatch",
    )

    require(
        review.get("human_decision")
        == "PENDING",
        "human decision is not pending",
    )

    require(
        review.get(
            "human_review_completed"
        )
        is False,
        "human review is already complete",
    )

    require(
        review.get("approval_issued")
        is False,
        "approval was already issued",
    )

    require(
        review.get("final_gate_allowed")
        is False,
        "Final Gate is already allowed",
    )

    require(
        review.get(
            "draft_creation_allowed"
        )
        is False,
        (
            "draft creation must remain "
            "blocked"
        ),
    )

    require(
        review.get("wordpress_write")
        is False,
        "WordPress write unexpectedly occurred",
    )

    machine_precheck = review.get(
        "machine_precheck"
    )

    require(
        isinstance(machine_precheck, dict),
        "machine precheck is missing",
    )

    require(
        machine_precheck.get("passed")
        is True,
        "machine precheck did not pass",
    )

    checks = machine_precheck.get(
        "checks"
    )

    require(
        isinstance(checks, dict)
        and checks,
        "machine precheck checks are missing",
    )

    failed_checks = [
        name
        for name, passed
        in checks.items()
        if passed is not True
    ]

    require(
        not failed_checks,
        (
            "machine precheck contains "
            "failed checks: "
            + ", ".join(failed_checks)
        ),
    )

    checklist = review.get(
        "human_review_checklist"
    )

    validate_pending_checklist(
        checklist
    )

    review_target = review.get(
        "review_target"
    )

    require(
        isinstance(review_target, dict),
        "review target is missing",
    )

    require(
        review_target.get("title")
        == EXPECTED_TITLE,
        "review title mismatch",
    )

    require(
        review_target.get("slug")
        == EXPECTED_SLUG,
        "review slug mismatch",
    )

    require(
        review_target.get("status")
        == "draft",
        "review post status must be draft",
    )

    require(
        review_target.get("category_ids")
        == [EXPECTED_CATEGORY_ID],
        "review category mismatch",
    )

    require(
        review_target.get(
            "maximum_post_create_count"
        )
        == 1,
        "maximum post creation count must be one",
    )

    require(
        review.get(
            "source_dry_run_digest_sha256"
        )
        == EXPECTED_DRY_RUN_DIGEST,
        "source Dry Run digest mismatch",
    )

    rendered_html_path = Path(
        review["rendered_html_path"]
    ).resolve()

    payload_preview_path = Path(
        review["payload_preview_path"]
    ).resolve()

    require(
        rendered_html_path.is_file(),
        "rendered HTML is missing",
    )

    require(
        payload_preview_path.is_file(),
        "payload preview is missing",
    )

    require(
        sha256_file(rendered_html_path)
        == EXPECTED_RENDERED_HTML_SHA,
        "rendered HTML SHA mismatch",
    )

    require(
        review.get("rendered_html_sha256")
        == EXPECTED_RENDERED_HTML_SHA,
        "rendered HTML evidence mismatch",
    )

    rendered_html = rendered_html_path.read_text(
        encoding="utf-8"
    )

    require(
        CURRENT_PRODUCT_HASH
        in rendered_html,
        "current affiliate product hash is missing",
    )

    require(
        BLOCKED_OLD_PRODUCT_HASH
        not in rendered_html,
        (
            "superseded affiliate product "
            "hash is present"
        ),
    )

    payload_preview = load_json(
        payload_preview_path
    )

    payload_digest = verify_digest(
        payload_preview,
        digest_field=(
            "wordpress_draft_payload_"
            "preview_digest_sha256"
        ),
        expected_digest=None,
        label="payload preview",
    )

    require(
        payload_digest
        == review.get(
            "payload_preview_digest_sha256"
        ),
        "payload preview evidence mismatch",
    )

    require(
        payload_preview.get("preview_only")
        is True,
        "payload is not preview-only",
    )

    require(
        payload_preview.get(
            "execution_allowed"
        )
        is False,
        "payload execution is unexpectedly allowed",
    )

    require(
        payload_preview.get(
            "wordpress_api_method"
        )
        == "NOT_CALLED",
        "WordPress API method mismatch",
    )

    wordpress_request = payload_preview.get(
        "wordpress_request"
    )

    require(
        isinstance(wordpress_request, dict),
        "WordPress request preview is missing",
    )

    require(
        wordpress_request.get("title")
        == EXPECTED_TITLE,
        "WordPress request title mismatch",
    )

    require(
        wordpress_request.get("slug")
        == EXPECTED_SLUG,
        "WordPress request slug mismatch",
    )

    require(
        wordpress_request.get("status")
        == "draft",
        "WordPress request status must be draft",
    )

    require(
        wordpress_request.get("categories")
        == [EXPECTED_CATEGORY_ID],
        "WordPress request categories mismatch",
    )

    require(
        wordpress_request.get("content")
        == rendered_html,
        "WordPress request content mismatch",
    )

    approved_checklist = [
        {
            **item,
            "human_decision": "APPROVED",
        }
        for item in checklist
    ]

    approved_at = datetime.now(
        timezone.utc
    ).isoformat()

    request_material = (
        EXPECTED_REVIEW_DIGEST
        + ":"
        + payload_digest
        + ":"
        + EXPECTED_TITLE
        + ":"
        + EXPECTED_SLUG
    )

    creation_request_id = (
        "xr11-wp-draft-create-"
        + hashlib.sha256(
            request_material.encode("utf-8")
        ).hexdigest()[:24]
    )

    certificate_payload = {
        "phase": (
            "X-R11-PRODUCTION-CANDIDATE-1-"
            "WORDPRESS-DRAFT-HUMAN-REVIEW-"
            "EXPLICIT-APPROVAL"
        ),
        "status": (
            "WORDPRESS_DRAFT_FINAL_GATE_"
            "APPROVAL_ISSUED_AND_CONSUMED"
        ),
        "issued_at": approved_at,
        "approval_label": approval_label,
        "approval_scope": (
            "WORDPRESS_DRAFT_FINAL_GATE_ONLY"
        ),
        "source_review_pack_path": str(
            review_pack_path
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "human_decision": "APPROVED",
        "human_review_completed": True,
        "human_review_checklist": (
            approved_checklist
        ),
        "approval_consumed": True,
        "consumed_by_phase": PHASE,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "production_status": "NO_GO",
    }

    certificate = {
        **certificate_payload,
        "wordpress_draft_final_gate_"
        "approval_certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    final_gate_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_DRAFT_FINAL_GATE_"
            "READY_AWAITING_EXPLICIT_"
            "CREATION_APPROVAL"
        ),
        "final_gate_state": (
            "READY_AWAITING_EXPLICIT_"
            "WORDPRESS_DRAFT_CREATION_APPROVAL"
        ),
        "generated_at": approved_at,
        "creation_request_id": (
            creation_request_id
        ),
        "source_review_pack_path": str(
            review_pack_path
        ),
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "human_review": {
            "decision": "APPROVED",
            "completed": True,
            "approval_label": approval_label,
            "approval_consumed": True,
            "approved_check_count": (
                EXPECTED_CHECK_COUNT
            ),
        },
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_draft_final_gate_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "rendered_html_path": str(
            rendered_html_path
        ),
        "rendered_html_sha256": (
            EXPECTED_RENDERED_HTML_SHA
        ),
        "payload_preview_path": str(
            payload_preview_path
        ),
        "payload_preview_digest_sha256": (
            payload_digest
        ),
        "wordpress_draft_request": {
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "category_ids": [
                EXPECTED_CATEGORY_ID
            ],
            "maximum_create_count": 1,
            "expected_api_method": "POST_ONCE",
        },
        "execution_constraints": {
            "duplicate_preflight_required": True,
            "slug_uniqueness_required": True,
            "post_status_must_equal": "draft",
            "category_ids_must_equal": [
                EXPECTED_CATEGORY_ID
            ],
            "maximum_create_count": 1,
            "failure_stops_all": True,
            "reexecution_lock_required": True,
            "wordpress_media_upload_before_publish": (
                True
            ),
            "publication_allowed": False,
        },
        "next_approval_label": (
            NEXT_CREATION_APPROVAL_LABEL
        ),
        "next_approval_scope": (
            "WORDPRESS_DRAFT_CREATION_ONLY"
        ),
        "next_approval_issued": False,
        "next_approval_consumed": False,
        "draft_creation_allowed": False,
        "draft_runner_execution_allowed": False,
        "database_write": False,
        "workflow_write": False,
        "wordpress_api_call": False,
        "wordpress_api_method": "NOT_CALLED",
        "wordpress_write": False,
        "wordpress_media_write": False,
        "wordpress_post_creation": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "FINAL_GATE_READY_"
            "ALL_EXTERNAL_WRITES_BLOCKED"
        ),
    }

    final_gate = {
        **final_gate_payload,
        "wordpress_draft_final_gate_"
        "digest_sha256": (
            canonical_digest(
                final_gate_payload
            )
        ),
    }

    atomic_write_json(
        approval_certificate_path,
        certificate,
    )

    atomic_write_json(
        final_gate_pack_path,
        final_gate,
    )

    lock_payload = {
        "lock_type": (
            "X_R11_WORDPRESS_DRAFT_"
            "FINAL_GATE_REVIEW_APPROVAL_"
            "CONSUMPTION"
        ),
        "created_at": approved_at,
        "source_review_digest_sha256": (
            EXPECTED_REVIEW_DIGEST
        ),
        "approval_label": approval_label,
        "approval_certificate_path": str(
            approval_certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_draft_final_gate_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "final_gate_pack_path": str(
            final_gate_pack_path
        ),
        "final_gate_digest_sha256": (
            final_gate[
                "wordpress_draft_final_gate_"
                "digest_sha256"
            ]
        ),
        "approval_consumed": True,
    }

    atomic_create_json(
        consumption_lock_path,
        lock_payload,
    )

    return final_gate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--production-db",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--review-pack",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--approval-label",
        required=True,
    )

    parser.add_argument(
        "--approval-certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--final-gate-pack",
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
        result = build_final_gate(
            production_database_path=(
                args.production_db
            ),
            review_pack_path=(
                args.review_pack
            ),
            approval_label=(
                args.approval_label
            ),
            approval_certificate_path=(
                args.approval_certificate
            ),
            final_gate_pack_path=(
                args.final_gate_pack
            ),
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
                        "FAIL_WORDPRESS_DRAFT_"
                        "FINAL_GATE"
                    ),
                    "error": str(exc),
                    "draft_creation_allowed": False,
                    "wordpress_api_call": False,
                    "wordpress_write": False,
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
                "final_gate_state": (
                    result["final_gate_state"]
                ),
                "creation_request_id": (
                    result["creation_request_id"]
                ),
                "human_review_decision": (
                    "APPROVED"
                ),
                "human_review_completed": True,
                "review_approval_consumed": True,
                "next_approval_label": (
                    result[
                        "next_approval_label"
                    ]
                ),
                "next_approval_issued": False,
                "draft_creation_allowed": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "final_gate_pack_path": str(
                    args.final_gate_pack.resolve()
                ),
                "final_gate_digest_sha256": (
                    result[
                        "wordpress_draft_"
                        "final_gate_digest_sha256"
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
