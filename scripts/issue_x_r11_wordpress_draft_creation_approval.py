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


from scripts.build_x_r11_final_gate_design import atomic_write_json
from scripts.build_x_r9_preflight_approval_pack import canonical_digest


PHASE = (
    "X-R11-PRODUCTION-CANDIDATE-1-"
    "WORDPRESS-DRAFT-CREATION-EXPLICIT-APPROVAL"
)

EXPECTED_DATABASE_SHA = (
    "ff1b6db6212bded101c144f2e9b0a741"
    "0f7cf3cafe96a5e36103f6a1d24ecae7"
)

EXPECTED_FINAL_GATE_DIGEST = (
    "f348d6f37980fdd5ccd5e9c9f5bc84c3"
    "7afc80509b369cd293fb5614f7edfd86"
)

EXPECTED_CREATION_REQUEST_ID = (
    "xr11-wp-draft-create-"
    "baf4e4451e14b3b4b3984bd2"
)

APPROVAL_LABEL = (
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


class CreationApprovalError(RuntimeError):
    pass


def require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise CreationApprovalError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(
        path.is_file(),
        f"JSON file is missing: {path}",
    )

    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    require(
        isinstance(value, dict),
        f"JSON root must be an object: {path}",
    )

    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def validate_approval_label(
    value: str,
) -> None:
    require(
        value == APPROVAL_LABEL,
        (
            "approval label must exactly equal "
            f"{APPROVAL_LABEL}"
        ),
    )


def verify_final_gate(
    value: dict[str, Any],
    *,
    expected_digest: str = EXPECTED_FINAL_GATE_DIGEST,
) -> None:
    recorded_digest = value.get(
        "wordpress_draft_final_gate_digest_sha256"
    )

    require(
        recorded_digest == expected_digest,
        "Final Gate digest mismatch",
    )

    payload = {
        key: item
        for key, item in value.items()
        if key
        != "wordpress_draft_final_gate_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == expected_digest,
        "Final Gate canonical digest verification failed",
    )

    require(
        value.get("status")
        == (
            "PASS_WORDPRESS_DRAFT_FINAL_GATE_"
            "READY_AWAITING_EXPLICIT_"
            "CREATION_APPROVAL"
        ),
        "Final Gate status mismatch",
    )

    require(
        value.get("final_gate_state")
        == (
            "READY_AWAITING_EXPLICIT_"
            "WORDPRESS_DRAFT_CREATION_APPROVAL"
        ),
        "Final Gate state mismatch",
    )

    require(
        value.get("creation_request_id")
        == EXPECTED_CREATION_REQUEST_ID,
        "creation request ID mismatch",
    )

    require(
        value.get("next_approval_label")
        == APPROVAL_LABEL,
        "next approval label mismatch",
    )

    require(
        value.get("next_approval_scope")
        == "WORDPRESS_DRAFT_CREATION_ONLY",
        "next approval scope mismatch",
    )

    require(
        value.get("next_approval_issued")
        is False,
        "creation approval was already issued",
    )

    require(
        value.get("next_approval_consumed")
        is False,
        "creation approval was already consumed",
    )

    require(
        value.get("draft_creation_allowed")
        is False,
        "draft creation is unexpectedly allowed",
    )

    require(
        value.get("wordpress_api_call")
        is False,
        "WordPress API was unexpectedly called",
    )

    require(
        value.get("wordpress_write")
        is False,
        "WordPress write unexpectedly occurred",
    )

    request = value.get(
        "wordpress_draft_request"
    )

    require(
        isinstance(request, dict),
        "WordPress draft request is missing",
    )

    require(
        request.get("title") == EXPECTED_TITLE,
        "draft title mismatch",
    )

    require(
        request.get("slug") == EXPECTED_SLUG,
        "draft slug mismatch",
    )

    require(
        request.get("status") == "draft",
        "draft status must equal draft",
    )

    require(
        request.get("category_ids") == [43],
        "draft category IDs must equal [43]",
    )

    require(
        request.get("maximum_create_count") == 1,
        "maximum creation count must equal one",
    )

    require(
        request.get("expected_api_method")
        == "POST_ONCE",
        "expected WordPress API method mismatch",
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
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError as exc:
        raise CreationApprovalError(
            f"approval artifact already exists: {path}"
        ) from exc

    try:
        os.write(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def issue_approval(
    *,
    production_database_path: Path,
    final_gate_pack_path: Path,
    approval_label: str,
    certificate_path: Path,
    issuance_lock_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    production_database_path = (
        production_database_path.resolve()
    )

    final_gate_pack_path = (
        final_gate_pack_path.resolve()
    )

    certificate_path = certificate_path.resolve()
    issuance_lock_path = issuance_lock_path.resolve()
    receipt_path = receipt_path.resolve()

    validate_approval_label(
        approval_label
    )

    require(
        sha256_file(production_database_path)
        == EXPECTED_DATABASE_SHA,
        "production database changed",
    )

    require(
        not certificate_path.exists(),
        "creation approval certificate already exists",
    )

    require(
        not issuance_lock_path.exists(),
        "creation approval issuance lock already exists",
    )

    final_gate = load_json(
        final_gate_pack_path
    )

    verify_final_gate(
        final_gate
    )

    rendered_html_path = Path(
        final_gate["rendered_html_path"]
    ).resolve()

    payload_preview_path = Path(
        final_gate["payload_preview_path"]
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
        == final_gate["rendered_html_sha256"],
        "rendered HTML changed after Final Gate",
    )

    payload_preview = load_json(
        payload_preview_path
    )

    payload_digest = payload_preview.get(
        "wordpress_draft_payload_preview_digest_sha256"
    )

    require(
        isinstance(payload_digest, str)
        and re.fullmatch(
            r"[0-9a-f]{64}",
            payload_digest,
        )
        is not None,
        "payload preview digest is invalid",
    )

    payload_without_digest = {
        key: item
        for key, item in payload_preview.items()
        if key
        != "wordpress_draft_payload_preview_digest_sha256"
    }

    require(
        canonical_digest(payload_without_digest)
        == payload_digest,
        "payload preview digest verification failed",
    )

    require(
        payload_digest
        == final_gate[
            "payload_preview_digest_sha256"
        ],
        "payload preview differs from Final Gate",
    )

    issued_at = datetime.now(
        timezone.utc
    ).isoformat()

    certificate_payload = {
        "phase": PHASE,
        "status": (
            "WORDPRESS_DRAFT_CREATION_"
            "APPROVAL_ISSUED_NOT_CONSUMED"
        ),
        "issued_at": issued_at,
        "approval_label": approval_label,
        "approval_scope": (
            "WORDPRESS_DRAFT_CREATION_ONLY"
        ),
        "creation_request_id": (
            EXPECTED_CREATION_REQUEST_ID
        ),
        "source_final_gate_pack_path": str(
            final_gate_pack_path
        ),
        "source_final_gate_digest_sha256": (
            EXPECTED_FINAL_GATE_DIGEST
        ),
        "rendered_html_path": str(
            rendered_html_path
        ),
        "rendered_html_sha256": final_gate[
            "rendered_html_sha256"
        ],
        "payload_preview_path": str(
            payload_preview_path
        ),
        "payload_preview_digest_sha256": (
            payload_digest
        ),
        "wordpress_request_constraints": {
            "title": EXPECTED_TITLE,
            "slug": EXPECTED_SLUG,
            "status": "draft",
            "category_ids": [43],
            "maximum_create_count": 1,
            "api_method": "POST_ONCE",
            "duplicate_preflight_required": True,
            "failure_stops_all": True,
        },
        "runner_execution_allowed": True,
        "approval_consumed": False,
        "draft_creation_executed": False,
        "publication_allowed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "database_write": False,
        "workflow_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": (
            "CREATION_APPROVAL_ISSUED_"
            "RUNNER_NOT_EXECUTED"
        ),
    }

    certificate = {
        **certificate_payload,
        "wordpress_draft_creation_approval_"
        "certificate_digest_sha256": (
            canonical_digest(
                certificate_payload
            )
        ),
    }

    atomic_create_json(
        certificate_path,
        certificate,
    )

    lock_payload = {
        "lock_type": (
            "X_R11_WORDPRESS_DRAFT_CREATION_"
            "APPROVAL_ISSUANCE"
        ),
        "created_at": issued_at,
        "creation_request_id": (
            EXPECTED_CREATION_REQUEST_ID
        ),
        "source_final_gate_digest_sha256": (
            EXPECTED_FINAL_GATE_DIGEST
        ),
        "approval_label": approval_label,
        "approval_certificate_path": str(
            certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_draft_creation_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "approval_consumed": False,
    }

    atomic_create_json(
        issuance_lock_path,
        lock_payload,
    )

    receipt_payload = {
        "phase": PHASE,
        "status": (
            "PASS_WORDPRESS_DRAFT_CREATION_"
            "APPROVAL_ISSUED_NOT_CONSUMED"
        ),
        "issued_at": issued_at,
        "creation_request_id": (
            EXPECTED_CREATION_REQUEST_ID
        ),
        "approval_label": approval_label,
        "approval_certificate_path": str(
            certificate_path
        ),
        "approval_certificate_digest_sha256": (
            certificate[
                "wordpress_draft_creation_"
                "approval_certificate_digest_sha256"
            ]
        ),
        "issuance_lock_path": str(
            issuance_lock_path
        ),
        "approval_consumed": False,
        "runner_execution_allowed": True,
        "draft_creation_executed": False,
        "wordpress_api_call": False,
        "wordpress_write": False,
        "production_status": "NO_GO",
    }

    receipt = {
        **receipt_payload,
        "wordpress_draft_creation_approval_"
        "issuance_receipt_digest_sha256": (
            canonical_digest(
                receipt_payload
            )
        ),
    }

    atomic_write_json(
        receipt_path,
        receipt,
    )

    return receipt


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
        "--approval-label",
        required=True,
    )

    parser.add_argument(
        "--certificate",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--issuance-lock",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--receipt",
        required=True,
        type=Path,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        receipt = issue_approval(
            production_database_path=(
                args.production_db
            ),
            final_gate_pack_path=(
                args.final_gate_pack
            ),
            approval_label=args.approval_label,
            certificate_path=args.certificate,
            issuance_lock_path=(
                args.issuance_lock
            ),
            receipt_path=args.receipt,
        )

    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": (
                        "FAIL_WORDPRESS_DRAFT_"
                        "CREATION_APPROVAL_ISSUANCE"
                    ),
                    "error": str(exc),
                    "approval_consumed": False,
                    "draft_creation_executed": False,
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
                "phase": receipt["phase"],
                "status": receipt["status"],
                "creation_request_id": (
                    receipt["creation_request_id"]
                ),
                "approval_label": (
                    receipt["approval_label"]
                ),
                "approval_consumed": False,
                "runner_execution_allowed": True,
                "draft_creation_executed": False,
                "wordpress_api_call": False,
                "wordpress_write": False,
                "production_status": "NO_GO",
                "approval_certificate_path": (
                    receipt[
                        "approval_certificate_path"
                    ]
                ),
                "approval_certificate_digest_sha256": (
                    receipt[
                        "approval_certificate_"
                        "digest_sha256"
                    ]
                ),
                "issuance_lock_path": (
                    receipt["issuance_lock_path"]
                ),
                "receipt_path": str(
                    args.receipt.resolve()
                ),
                "receipt_digest_sha256": (
                    receipt[
                        "wordpress_draft_creation_"
                        "approval_issuance_receipt_"
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
