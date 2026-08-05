from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.services.workflow_approved_x_draft_read_service import (
    WorkflowApprovedXDraftReadService,
    normalize_wordpress_base_url,
)
from app.services.x_draft_feedback_registration_service import (
    XDraftFeedbackRegistrationError,
    XDraftFeedbackRegistrationService,
)
from scripts.build_x_r11_final_gate_design import (
    atomic_write_json,
    canonical_json_digest,
)
from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
    json_storage_snapshot,
    sqlite_read_only_url,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    sha256_file,
)


ROOT = REPOSITORY_ROOT

PRODUCTION_DATABASE_PATH = (
    ROOT / "data/database/ebook_affiliate.db"
).resolve()

PHASE = "X-R11-PRODUCTION-ELIGIBILITY-GATE"

ELIGIBILITY_STATE = (
    "PRODUCTION_CANDIDATE_ELIGIBLE_"
    "FOR_APPROVAL_PACK_ONLY"
)

NO_CANDIDATE_STATE = (
    "NO_ELIGIBLE_PRODUCTION_CANDIDATE"
)

MULTIPLE_CANDIDATE_STATE = (
    "BLOCKED_MULTIPLE_ELIGIBLE_"
    "PRODUCTION_CANDIDATES"
)

REQUIRED_NEXT_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_PRODUCTION_"
    "CANDIDATE_PREFLIGHT_PACK_ONLY"
)

AUTHORIZED_NEXT_PHASE = (
    "X-R11-PRODUCTION-X-R9-"
    "PREFLIGHT-PACK"
)


class XR11ProductionEligibilityError(RuntimeError):
    """Raised when production eligibility validation fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR11ProductionEligibilityError(message)


def is_within(
    path: Path,
    parent: Path,
) -> bool:
    try:
        path.resolve().relative_to(
            parent.resolve()
        )
    except ValueError:
        return False

    return True


def assert_diagnostic_output(
    output_root: Path,
    normal_x_fb_root: Path,
) -> None:
    forbidden_roots = (
        normal_x_fb_root
        / "exchange/input/x_post_feedback",
        normal_x_fb_root
        / "exchange/archive/x_post_feedback",
        normal_x_fb_root
        / "exchange/logs",
    )

    for forbidden_root in forbidden_roots:
        require(
            not is_within(
                output_root,
                forbidden_root,
            ),
            (
                "output_root must not be inside "
                "normal X-FB storage"
            ),
        )


def base_result(
    *,
    status: str,
    eligibility_state: str,
    source_database_path: Path,
    source_database_sha256: str,
    candidate_ids: list[str],
) -> dict[str, Any]:
    return {
        "phase": PHASE,
        "status": status,
        "eligibility_state": eligibility_state,
        "database_scope": "PRODUCTION_READ_ONLY",
        "source_database_path": str(
            source_database_path
        ),
        "source_database_sha256_before": (
            source_database_sha256
        ),
        "source_database_sha256_after": (
            source_database_sha256
        ),
        "source_database_unchanged": True,
        "eligible_candidate_count": len(
            candidate_ids
        ),
        "eligible_candidate_ids": candidate_ids,
        "eligibility_pack_created": False,
        "approval_pack_created": False,
        "approval_token_created": False,
        "final_approval_certificate_created": False,
        "approval_label_consumed": False,
        "certificate_consumed": False,
        "execution_token_consumed": False,
        "preflight_lock_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "current_record_written": False,
        "operation_result_written": False,
        "normal_x_fb_storage_modified": False,
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_READ_ONLY_"
            "ELIGIBILITY_CHECK"
        ),
    }


def run_x_r11_production_eligibility_gate(
    *,
    source_database_path: Path,
    expected_production_database_path: Path,
    wordpress_base_url: str,
    output_root: Path,
    normal_x_fb_root: Path = ROOT,
) -> dict[str, Any]:
    source_database_path = (
        source_database_path.resolve()
    )
    expected_production_database_path = (
        expected_production_database_path.resolve()
    )
    output_root = output_root.resolve()
    normal_x_fb_root = (
        normal_x_fb_root.resolve()
    )

    require(
        source_database_path
        == expected_production_database_path,
        (
            "source database must exactly match "
            "the fixed production database path"
        ),
    )
    require(
        source_database_path.is_file(),
        (
            "production database is missing: "
            f"{source_database_path}"
        ),
    )

    if output_root.exists():
        require(
            not any(output_root.iterdir()),
            (
                "output_root must be empty: "
                f"{output_root}"
            ),
        )

    assert_diagnostic_output(
        output_root,
        normal_x_fb_root,
    )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_base_url = (
        normalize_wordpress_base_url(
            wordpress_base_url
        )
    )

    expected_host = urlparse(
        normalized_base_url
    ).netloc.lower()

    require(
        bool(expected_host),
        (
            "WordPress base URL must contain "
            "a valid host"
        ),
    )

    database_sha_before = sha256_file(
        source_database_path
    )

    normal_snapshot_before = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    engine = create_engine(
        sqlite_read_only_url(
            source_database_path
        ),
        connect_args={
            "check_same_thread": False,
        },
    )

    try:
        with Session(
            engine,
            autoflush=False,
            expire_on_commit=False,
        ) as session:
            read_service = (
                WorkflowApprovedXDraftReadService(
                    session,
                    wordpress_base_url=(
                        normalized_base_url
                    ),
                )
            )

            candidate_ids = list(
                read_service.find_latest_candidate_ids(
                    limit=10
                )
            )

            require(
                not session.new,
                (
                    "read-only session has "
                    "new objects"
                ),
            )
            require(
                not session.dirty,
                (
                    "read-only session has "
                    "dirty objects"
                ),
            )
            require(
                not session.deleted,
                (
                    "read-only session has "
                    "deleted objects"
                ),
            )

            if not candidate_ids:
                database_sha_after = sha256_file(
                    source_database_path
                )

                require(
                    database_sha_before
                    == database_sha_after,
                    (
                        "production database "
                        "changed during read-only "
                        "eligibility check"
                    ),
                )

                normal_snapshot_after = (
                    json_storage_snapshot(
                        normal_x_fb_root
                    )
                )

                require(
                    normal_snapshot_before
                    == normal_snapshot_after,
                    (
                        "normal X-FB storage "
                        "changed during eligibility "
                        "check"
                    ),
                )

                result = base_result(
                    status=(
                        "PASS_PRODUCTION_READ_ONLY_"
                        "NO_ELIGIBLE_CANDIDATE"
                    ),
                    eligibility_state=(
                        NO_CANDIDATE_STATE
                    ),
                    source_database_path=(
                        source_database_path
                    ),
                    source_database_sha256=(
                        database_sha_after
                    ),
                    candidate_ids=[],
                )

                atomic_write_json(
                    output_root
                    / (
                        "x_r11_production_"
                        "eligibility_result.json"
                    ),
                    result,
                )

                return result

            if len(candidate_ids) != 1:
                database_sha_after = sha256_file(
                    source_database_path
                )

                require(
                    database_sha_before
                    == database_sha_after,
                    (
                        "production database "
                        "changed during read-only "
                        "eligibility check"
                    ),
                )

                result = base_result(
                    status=(
                        "BLOCKED_MULTIPLE_ELIGIBLE_"
                        "PRODUCTION_CANDIDATES"
                    ),
                    eligibility_state=(
                        MULTIPLE_CANDIDATE_STATE
                    ),
                    source_database_path=(
                        source_database_path
                    ),
                    source_database_sha256=(
                        database_sha_after
                    ),
                    candidate_ids=candidate_ids,
                )

                result.update(
                    {
                        "fail_closed": True,
                        "human_selection_allowed": (
                            False
                        ),
                        "automatic_selection_allowed": (
                            False
                        ),
                        "authorized_next_phase": None,
                    }
                )

                atomic_write_json(
                    output_root
                    / (
                        "x_r11_production_"
                        "eligibility_result.json"
                    ),
                    result,
                )

                return result

            approval_request_id = (
                candidate_ids[0]
            )

            read_result = (
                read_service.read_and_adapt(
                    approval_request_id
                )
            )

            require(
                not session.new,
                (
                    "read-only session has "
                    "new objects after candidate "
                    "adaptation"
                ),
            )
            require(
                not session.dirty,
                (
                    "read-only session has "
                    "dirty objects after candidate "
                    "adaptation"
                ),
            )
            require(
                not session.deleted,
                (
                    "read-only session has "
                    "deleted objects after candidate "
                    "adaptation"
                ),
            )

    finally:
        engine.dispose()

    draft_input = (
        read_result
        .adapter_result
        .x_draft_input
    )

    require(
        draft_input.wordpress_status
        == "DRAFT",
        (
            "production WordPress status "
            "must be DRAFT"
        ),
    )
    require(
        isinstance(
            draft_input.wordpress_draft_id,
            int,
        )
        and draft_input.wordpress_draft_id > 0,
        (
            "production WordPress draft ID "
            "must be positive"
        ),
    )

    article_host = urlparse(
        draft_input.article_url
    ).netloc.lower()

    require(
        article_host == expected_host,
        (
            "production article URL host "
            "does not match WordPress base URL"
        ),
    )

    registration_service = (
        XDraftFeedbackRegistrationService()
    )

    preview = (
        registration_service
        .generation_service
        .generate(draft_input)
    )

    feedback_id = preview.feedback_id

    normal_current_path = (
        normal_x_fb_root
        / "exchange/input/x_post_feedback"
        / feedback_id
        / "current.json"
    )
    normal_operation_result_path = (
        normal_x_fb_root
        / "exchange/logs"
        / (
            f"x_fb_1_{feedback_id}_"
            "v001_result.json"
        )
    )

    require(
        not normal_current_path.exists(),
        (
            "normal X-FB current.json "
            "already exists"
        ),
    )
    require(
        not normal_operation_result_path.exists(),
        (
            "normal X-FB operation result "
            "already exists"
        ),
    )

    try:
        registration = (
            registration_service
            .dry_run_register(
                draft_input,
                storage_root=normal_x_fb_root,
            )
        )
    except XDraftFeedbackRegistrationError as exc:
        raise XR11ProductionEligibilityError(
            (
                "production X-FB dry-run "
                f"eligibility check failed: {exc}"
            )
        ) from exc

    require(
        registration.status
        == "PASS_DRY_RUN_NO_WRITE",
        (
            "production X-FB eligibility "
            "check must remain dry-run"
        ),
    )
    require(
        registration.feedback_id
        == feedback_id,
        (
            "feedback ID changed between "
            "preview and dry-run"
        ),
    )
    require(
        not normal_current_path.exists(),
        (
            "dry-run created normal "
            "current.json"
        ),
    )
    require(
        not normal_operation_result_path.exists(),
        (
            "dry-run created normal "
            "operation result"
        ),
    )

    request_digest = canonical_json_digest(
        registration.initialize_request
    )

    candidate_snapshot = {
        "approval_request_id": (
            approval_request_id
        ),
        "ebook_item_id": (
            draft_input.ebook_item_id
        ),
        "title": draft_input.title,
        "volume_label": (
            draft_input.volume_label
        ),
        "release_date": (
            draft_input.release_date
        ),
        "category": draft_input.category,
        "author_name": (
            draft_input.author_name
        ),
        "wordpress_draft_id": (
            draft_input.wordpress_draft_id
        ),
        "wordpress_status": (
            draft_input.wordpress_status
        ),
        "article_url": (
            draft_input.article_url
        ),
        "feedback_id": feedback_id,
        "generated_text": (
            registration.generated_text
        ),
        "initialize_request_digest_sha256": (
            request_digest
        ),
    }

    candidate_digest = canonical_digest(
        candidate_snapshot
    )

    database_sha_after = sha256_file(
        source_database_path
    )

    require(
        database_sha_before
        == database_sha_after,
        (
            "production database changed "
            "during eligibility gate"
        ),
    )

    normal_snapshot_after = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    require(
        normal_snapshot_before
        == normal_snapshot_after,
        (
            "normal X-FB storage changed "
            "during eligibility gate"
        ),
    )

    request_path = (
        output_root
        / (
            "x_r11_production_candidate_"
            "initialize_request.json"
        )
    )
    pack_path = (
        output_root
        / (
            "x_r11_production_"
            "eligibility_pack.json"
        )
    )
    result_path = (
        output_root
        / (
            "x_r11_production_"
            "eligibility_result.json"
        )
    )

    atomic_write_json(
        request_path,
        registration.initialize_request,
    )

    pack_payload = {
        "phase": PHASE,
        "status": (
            "PRODUCTION_ELIGIBILITY_"
            "PACK_READY_NO_EXECUTION"
        ),
        "eligibility_state": (
            ELIGIBILITY_STATE
        ),
        "database_scope": (
            "PRODUCTION_READ_ONLY"
        ),
        "source_database_path": str(
            source_database_path
        ),
        "source_database_sha256": (
            database_sha_after
        ),
        "eligible_candidate_count": 1,
        "approval_request_id": (
            approval_request_id
        ),
        "feedback_id": feedback_id,
        "candidate_snapshot": (
            candidate_snapshot
        ),
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "initialize_request_path": str(
            request_path
        ),
        "initialize_request_digest_sha256": (
            request_digest
        ),
        "fixed_target_paths": {
            "current_record_path": str(
                normal_current_path
            ),
            "operation_result_path": str(
                normal_operation_result_path
            ),
            "paths_fixed": True,
            "path_substitution_allowed": False,
        },
        "required_next_approval_label": (
            REQUIRED_NEXT_APPROVAL_LABEL
        ),
        "approval_state": (
            "NOT_APPROVED_FOR_PRODUCTION_"
            "CANDIDATE_PREFLIGHT_PACK"
        ),
        "approval_label_consumed": False,
        "approval_pack_created": False,
        "approval_token_created": False,
        "final_approval_certificate_created": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "authorized_next_phase": (
            AUTHORIZED_NEXT_PHASE
        ),
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_ELIGIBILITY_"
            "PACK_ONLY_NO_EXECUTION"
        ),
    }

    pack_digest = canonical_digest(
        pack_payload
    )

    pack = {
        **pack_payload,
        "eligibility_pack_digest_sha256": (
            pack_digest
        ),
    }

    atomic_write_json(
        pack_path,
        pack,
    )

    result = {
        "phase": PHASE,
        "status": (
            "PASS_PRODUCTION_ELIGIBILITY_"
            "PACK_READY_NO_EXECUTION"
        ),
        "eligibility_state": (
            ELIGIBILITY_STATE
        ),
        "database_scope": (
            "PRODUCTION_READ_ONLY"
        ),
        "source_database_path": str(
            source_database_path
        ),
        "source_database_sha256_before": (
            database_sha_before
        ),
        "source_database_sha256_after": (
            database_sha_after
        ),
        "source_database_unchanged": True,
        "eligible_candidate_count": 1,
        "approval_request_id": (
            approval_request_id
        ),
        "feedback_id": feedback_id,
        "candidate_digest_sha256": (
            candidate_digest
        ),
        "eligibility_pack_path": str(
            pack_path
        ),
        "eligibility_pack_digest_sha256": (
            pack_digest
        ),
        "initialize_request_path": str(
            request_path
        ),
        "initialize_request_digest_sha256": (
            request_digest
        ),
        "candidate_revalidated": True,
        "wordpress_status_revalidated": (
            "DRAFT"
        ),
        "wordpress_host_revalidated": True,
        "x_fb_dry_run_status": (
            registration.status
        ),
        "fixed_target_paths_verified": True,
        "required_next_approval_label": (
            REQUIRED_NEXT_APPROVAL_LABEL
        ),
        "approval_state": (
            "NOT_APPROVED_FOR_PRODUCTION_"
            "CANDIDATE_PREFLIGHT_PACK"
        ),
        "approval_label_consumed": False,
        "approval_pack_created": False,
        "approval_token_created": False,
        "final_approval_certificate_created": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "current_record_written": False,
        "operation_result_written": False,
        "normal_x_fb_storage_modified": False,
        "authorized_next_phase": (
            AUTHORIZED_NEXT_PHASE
        ),
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_execution": False,
        "production_status": "NO_GO",
        "safety_state": (
            "PRODUCTION_ELIGIBILITY_"
            "PACK_ONLY_NO_EXECUTION"
        ),
    }

    atomic_write_json(
        result_path,
        result,
    )

    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-db",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--expected-production-db",
        type=Path,
        default=PRODUCTION_DATABASE_PATH,
    )
    parser.add_argument(
        "--wordpress-base-url",
        required=True,
    )
    parser.add_argument(
        "--output-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--normal-x-fb-root",
        type=Path,
        default=ROOT,
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = (
            run_x_r11_production_eligibility_gate(
                source_database_path=(
                    args.source_db
                ),
                expected_production_database_path=(
                    args.expected_production_db
                ),
                wordpress_base_url=(
                    args.wordpress_base_url
                ),
                output_root=(
                    args.output_root
                ),
                normal_x_fb_root=(
                    args.normal_x_fb_root
                ),
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": PHASE,
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "approval_label_consumed": False,
                    "approval_pack_created": False,
                    "approval_token_created": False,
                    "final_approval_certificate_created": False,
                    "execution_allowed": False,
                    "normal_x_fb_write_allowed": False,
                    "database_write": False,
                    "workflow_write": False,
                    "wordpress_write": False,
                    "x_api_call": False,
                    "x_post": False,
                    "production_execution": False,
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
            result,
            ensure_ascii=False,
            indent=2,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
