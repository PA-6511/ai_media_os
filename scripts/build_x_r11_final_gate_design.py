from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


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
from scripts.build_x_r9_preflight_approval_pack import (
    REQUIRED_APPROVAL_LABEL,
    atomic_write_json,
    canonical_digest,
    json_storage_snapshot,
    sqlite_read_only_url,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    EXPECTED_LOCK_STATE,
    EXPECTED_LOCK_TYPE,
    EXPECTED_PACK_STATUS,
    NEXT_PHASE,
    TOKEN_STATE,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    sha256_file,
)
from scripts.run_x_r8_isolated_x_fb_write import (
    load_json_object,
)


ROOT = REPOSITORY_ROOT

FINAL_APPROVAL_LABEL = (
    "APPROVED_FOR_X_R11_NORMAL_X_FB_"
    "ONE_SHOT_WRITE_ONLY"
)
FINAL_APPROVAL_STATE = (
    "NOT_APPROVED_FOR_X_R11_NORMAL_X_FB_"
    "ONE_SHOT_WRITE"
)
FINAL_GATE_STATE = (
    "DESIGN_READY_NOT_EXECUTABLE"
)

EXPECTED_TOKEN_STATUS = (
    "APPROVAL_TOKEN_ISSUED_NO_EXECUTION"
)

OUTPUT_FILENAME = (
    "x_r11_final_gate_design.json"
)
RESULT_FILENAME = (
    "x_r11_final_gate_result.json"
)


class XR11FinalGateDesignError(RuntimeError):
    """Raised when X-R11 final-gate design validation fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR11FinalGateDesignError(message)


def canonical_json_digest(
    value: dict[str, Any],
) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


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


def assert_diagnostic_path(
    path: Path,
    normal_x_fb_root: Path,
    field_name: str,
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
                path,
                forbidden_root,
            ),
            (
                f"{field_name} must not be inside "
                "normal X-FB storage"
            ),
        )


def validate_optional_bundle(
    *,
    approval_pack_path: Path | None,
    preflight_lock_path: Path | None,
    approval_token_path: Path | None,
    initialize_request_path: Path | None,
) -> None:
    values = (
        approval_pack_path,
        preflight_lock_path,
        approval_token_path,
        initialize_request_path,
    )

    supplied_count = sum(
        value is not None
        for value in values
    )

    require(
        supplied_count in (0, 4),
        (
            "approval pack, preflight lock, "
            "approval token and initialize "
            "request must be supplied together"
        ),
    )


def validate_pack(
    pack: dict[str, Any],
) -> str:
    require(
        pack.get("status")
        == EXPECTED_PACK_STATUS,
        "approval pack status is invalid",
    )
    require(
        pack.get("required_approval_label")
        == REQUIRED_APPROVAL_LABEL,
        (
            "approval pack approval label "
            "is invalid"
        ),
    )
    require(
        pack.get("approval_label_consumed")
        is False,
        (
            "approval pack label must remain "
            "unconsumed"
        ),
    )
    require(
        pack.get("execution_allowed")
        is False,
        (
            "approval pack execution_allowed "
            "must be false"
        ),
    )
    require(
        pack.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "approval pack normal X-FB "
            "write must be false"
        ),
    )
    require(
        pack.get("existing_current_record")
        is False,
        (
            "approval pack reports an "
            "existing current record"
        ),
    )

    stored_digest = pack.get(
        "approval_pack_digest_sha256"
    )

    require(
        isinstance(stored_digest, str)
        and len(stored_digest) == 64,
        "approval pack digest is invalid",
    )

    payload = {
        key: value
        for key, value in pack.items()
        if key
        != "approval_pack_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == stored_digest,
        (
            "approval pack tampering detected: "
            "digest mismatch"
        ),
    )

    return stored_digest


def validate_lock(
    lock: dict[str, Any],
    *,
    pack_digest: str,
    feedback_id: str,
    approval_request_id: str,
) -> None:
    require(
        lock.get("lock_type")
        == EXPECTED_LOCK_TYPE,
        "preflight lock type is invalid",
    )
    require(
        lock.get("lock_state")
        == EXPECTED_LOCK_STATE,
        "preflight lock state is invalid",
    )
    require(
        lock.get("feedback_id")
        == feedback_id,
        (
            "feedback_id mismatch between "
            "pack and lock"
        ),
    )
    require(
        lock.get("approval_request_id")
        == approval_request_id,
        (
            "approval_request_id mismatch "
            "between pack and lock"
        ),
    )
    require(
        lock.get(
            "approval_pack_digest_sha256"
        )
        == pack_digest,
        (
            "preflight lock digest does not "
            "match approval pack"
        ),
    )
    require(
        lock.get("approval_label_consumed")
        is False,
        (
            "preflight lock approval label "
            "must remain unconsumed"
        ),
    )
    require(
        lock.get("execution_allowed")
        is False,
        (
            "preflight lock execution_allowed "
            "must be false"
        ),
    )
    require(
        lock.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "preflight lock normal X-FB "
            "write must be false"
        ),
    )


def validate_token(
    token: dict[str, Any],
    *,
    pack_path: Path,
    lock_path: Path,
    pack_digest: str,
    feedback_id: str,
    approval_request_id: str,
) -> str:
    require(
        token.get("status")
        == EXPECTED_TOKEN_STATUS,
        "approval token status is invalid",
    )
    require(
        token.get("token_state")
        == TOKEN_STATE,
        (
            "approval token state must be "
            "ISSUED_NOT_CONSUMED"
        ),
    )
    require(
        token.get("feedback_id")
        == feedback_id,
        (
            "feedback_id mismatch between "
            "pack and token"
        ),
    )
    require(
        token.get("approval_request_id")
        == approval_request_id,
        (
            "approval_request_id mismatch "
            "between pack and token"
        ),
    )
    require(
        token.get(
            "approval_pack_digest_sha256"
        )
        == pack_digest,
        (
            "approval token pack digest "
            "does not match"
        ),
    )
    require(
        token.get("approval_label")
        == REQUIRED_APPROVAL_LABEL,
        "approval token label is invalid",
    )
    require(
        token.get("approval_label_consumed")
        is True,
        (
            "approval token must record "
            "consumed approval label"
        ),
    )
    require(
        token.get("preflight_lock_consumed")
        is False,
        (
            "preflight lock must remain "
            "unconsumed"
        ),
    )
    require(
        token.get("execution_token_consumed")
        is False,
        (
            "approval token must remain "
            "unconsumed"
        ),
    )
    require(
        token.get("execution_allowed")
        is False,
        (
            "approval token execution_allowed "
            "must remain false"
        ),
    )
    require(
        token.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "approval token normal X-FB "
            "write must remain false"
        ),
    )
    require(
        token.get("authorized_next_phase")
        == NEXT_PHASE,
        (
            "approval token is not authorized "
            "for X-R11"
        ),
    )
    require(
        token.get("approval_pack_file_sha256")
        == sha256_file(pack_path),
        (
            "approval pack file hash does not "
            "match token"
        ),
    )
    require(
        token.get("one_shot_lock_file_sha256")
        == sha256_file(lock_path),
        (
            "preflight lock file hash does not "
            "match token"
        ),
    )

    token_digest = token.get(
        "execution_token_digest_sha256"
    )

    require(
        isinstance(token_digest, str)
        and len(token_digest) == 64,
        "approval token digest is invalid",
    )

    payload = {
        key: value
        for key, value in token.items()
        if key
        != "execution_token_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == token_digest,
        (
            "approval token tampering detected: "
            "digest mismatch"
        ),
    )

    return token_digest


def build_no_candidate_result(
    *,
    source_database_path: Path,
    database_scope: str,
    output_root: Path,
    database_sha256: str,
) -> dict[str, Any]:
    result = {
        "phase": "X-R11-FINAL-GATE-DESIGN",
        "status": (
            "PASS_READ_ONLY_NO_ELIGIBLE_"
            "CANDIDATE_NO_FINAL_GATE"
        ),
        "database_scope": database_scope,
        "source_database_path": str(
            source_database_path
        ),
        "candidate_count": 0,
        "final_gate_design_created": False,
        "final_approval_state": (
            FINAL_APPROVAL_STATE
        ),
        "final_approval_label_consumed": False,
        "execution_token_consumed": False,
        "preflight_lock_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "production_status": "NO_GO",
        "safety_state": "DESIGN_ONLY_NO_EXECUTION",
        "source_database_sha256_before": (
            database_sha256
        ),
        "source_database_sha256_after": (
            database_sha256
        ),
        "source_database_unchanged": True,
    }

    atomic_write_json(
        output_root / RESULT_FILENAME,
        result,
    )

    return result


def run_x_r11_final_gate_design(
    *,
    source_database_path: Path,
    wordpress_base_url: str,
    output_root: Path,
    normal_x_fb_root: Path = ROOT,
    approval_request_id: str | None = None,
    approval_pack_path: Path | None = None,
    preflight_lock_path: Path | None = None,
    approval_token_path: Path | None = None,
    initialize_request_path: Path | None = None,
    database_scope: str = "READ_ONLY_DATABASE",
) -> dict[str, Any]:
    source_database_path = (
        source_database_path.resolve()
    )
    output_root = output_root.resolve()
    normal_x_fb_root = (
        normal_x_fb_root.resolve()
    )

    approval_pack_path = (
        approval_pack_path.resolve()
        if approval_pack_path is not None
        else None
    )
    preflight_lock_path = (
        preflight_lock_path.resolve()
        if preflight_lock_path is not None
        else None
    )
    approval_token_path = (
        approval_token_path.resolve()
        if approval_token_path is not None
        else None
    )
    initialize_request_path = (
        initialize_request_path.resolve()
        if initialize_request_path is not None
        else None
    )

    validate_optional_bundle(
        approval_pack_path=(
            approval_pack_path
        ),
        preflight_lock_path=(
            preflight_lock_path
        ),
        approval_token_path=(
            approval_token_path
        ),
        initialize_request_path=(
            initialize_request_path
        ),
    )

    require(
        source_database_path.is_file(),
        (
            "source database is missing: "
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

    assert_diagnostic_path(
        output_root,
        normal_x_fb_root,
        "output_root",
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

            candidate_ids = (
                read_service
                .find_latest_candidate_ids(
                    limit=10
                )
            )

            selected_id = approval_request_id

            if selected_id is None:
                if not candidate_ids:
                    database_sha_after = (
                        sha256_file(
                            source_database_path
                        )
                    )

                    require(
                        database_sha_before
                        == database_sha_after,
                        (
                            "source database "
                            "changed"
                        ),
                    )

                    return build_no_candidate_result(
                        source_database_path=(
                            source_database_path
                        ),
                        database_scope=(
                            database_scope
                        ),
                        output_root=output_root,
                        database_sha256=(
                            database_sha_after
                        ),
                    )

                selected_id = candidate_ids[0]

            require(
                selected_id in candidate_ids,
                (
                    "approval request is not "
                    "currently eligible"
                ),
            )

            require(
                approval_pack_path is not None
                and preflight_lock_path
                is not None
                and approval_token_path
                is not None
                and initialize_request_path
                is not None,
                (
                    "eligible candidate requires "
                    "the full approval artifact "
                    "bundle"
                ),
            )

            read_result = (
                read_service.read_and_adapt(
                    selected_id
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

    finally:
        engine.dispose()

    draft_input = (
        read_result
        .adapter_result
        .x_draft_input
    )

    registration_service = (
        XDraftFeedbackRegistrationService()
    )

    # Generate the deterministic feedback ID before invoking
    # X-FB INITIALIZE validation. This allows the final gate
    # to reject an existing normal record with its own
    # fail-closed error instead of leaking the lower-level
    # manager exception.
    draft_preview = (
        registration_service
        .generation_service
        .generate(draft_input)
    )

    preview_feedback_id = (
        draft_preview.feedback_id
    )

    preview_current_path = (
        normal_x_fb_root
        / "exchange/input/x_post_feedback"
        / preview_feedback_id
        / "current.json"
    )
    preview_operation_result_path = (
        normal_x_fb_root
        / "exchange/logs"
        / (
            f"x_fb_1_{preview_feedback_id}_"
            "v001_result.json"
        )
    )

    require(
        not preview_current_path.exists(),
        (
            "normal X-FB current.json "
            "already exists"
        ),
    )
    require(
        not preview_operation_result_path.exists(),
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
        # Close the check/use race with the same final-gate
        # error classification if a record appears after the
        # explicit path check.
        if (
            "INITIALIZE is forbidden because "
            "current record exists"
        ) in str(exc):
            raise XR11FinalGateDesignError(
                "normal X-FB current.json "
                "already exists"
            ) from exc

        raise XR11FinalGateDesignError(
            "X-FB final-gate dry-run failed: "
            f"{exc}"
        ) from exc

    require(
        registration.status
        == "PASS_DRY_RUN_NO_WRITE",
        (
            "X-FB registration preflight "
            "must remain dry-run"
        ),
    )

    pack = load_json_object(
        approval_pack_path
    )
    lock = load_json_object(
        preflight_lock_path
    )
    token = load_json_object(
        approval_token_path
    )
    initialize_request = load_json_object(
        initialize_request_path
    )

    pack_digest = validate_pack(pack)

    feedback_id = registration.feedback_id
    approval_request_id_actual = (
        read_result
        .read_model
        .approval_request_id
    )

    require(
        pack.get("feedback_id")
        == feedback_id,
        (
            "regenerated feedback_id does not "
            "match approval pack"
        ),
    )
    require(
        pack.get("approval_request_id")
        == approval_request_id_actual,
        (
            "approval_request_id does not "
            "match approval pack"
        ),
    )
    require(
        pack.get("generated_text")
        == registration.generated_text,
        (
            "regenerated X draft differs "
            "from approved text"
        ),
    )
    require(
        pack.get("wordpress_post_id")
        == (
            read_result
            .adapter_result
            .x_draft_input
            .wordpress_draft_id
        ),
        (
            "WordPress post ID changed after "
            "approval"
        ),
    )
    require(
        pack.get("article_url")
        == (
            read_result
            .adapter_result
            .x_draft_input
            .article_url
        ),
        (
            "article URL changed after "
            "approval"
        ),
    )

    pack_database_path = Path(
        str(
            pack.get(
                "source_database_path",
                "",
            )
        )
    ).resolve()

    require(
        pack_database_path
        == source_database_path,
        (
            "approval pack source database "
            "does not match supplied database"
        ),
    )

    validate_lock(
        lock,
        pack_digest=pack_digest,
        feedback_id=feedback_id,
        approval_request_id=(
            approval_request_id_actual
        ),
    )

    token_digest = validate_token(
        token,
        pack_path=approval_pack_path,
        lock_path=preflight_lock_path,
        pack_digest=pack_digest,
        feedback_id=feedback_id,
        approval_request_id=(
            approval_request_id_actual
        ),
    )

    request_digest = canonical_json_digest(
        initialize_request
    )
    regenerated_request_digest = (
        canonical_json_digest(
            registration.initialize_request
        )
    )

    require(
        request_digest
        == regenerated_request_digest,
        (
            "initialize request differs from "
            "regenerated approved request"
        ),
    )

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
    normal_archive_root = (
        normal_x_fb_root
        / "exchange/archive/x_post_feedback"
        / feedback_id
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

    database_sha_after = sha256_file(
        source_database_path
    )

    require(
        database_sha_before
        == database_sha_after,
        "source database changed",
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
            "during final-gate design"
        ),
    )

    design_payload = {
        "phase": "X-R11-FINAL-GATE-DESIGN",
        "status": (
            "FINAL_GATE_DESIGN_READY_"
            "NO_EXECUTION"
        ),
        "gate_state": FINAL_GATE_STATE,
        "database_scope": database_scope,
        "source_database_path": str(
            source_database_path
        ),
        "approval_request_id": (
            approval_request_id_actual
        ),
        "feedback_id": feedback_id,
        "approval_pack_path": str(
            approval_pack_path
        ),
        "preflight_lock_path": str(
            preflight_lock_path
        ),
        "approval_token_path": str(
            approval_token_path
        ),
        "initialize_request_path": str(
            initialize_request_path
        ),
        "approval_pack_digest_sha256": (
            pack_digest
        ),
        "approval_token_digest_sha256": (
            token_digest
        ),
        "initialize_request_digest_sha256": (
            request_digest
        ),
        "regenerated_request_digest_sha256": (
            regenerated_request_digest
        ),
        "regenerated_draft_matches_approval": True,
        "candidate_revalidated": True,
        "wordpress_status_revalidated": "DRAFT",
        "review_status_revalidated": "APPROVED",
        "workflow_status_revalidated": "READY",
        "target_paths": {
            "current_record_path": str(
                normal_current_path
            ),
            "operation_result_path": str(
                normal_operation_result_path
            ),
            "archive_root": str(
                normal_archive_root
            ),
            "paths_fixed": True,
            "path_substitution_allowed": False,
        },
        "required_final_approval_label": (
            FINAL_APPROVAL_LABEL
        ),
        "final_approval_state": (
            FINAL_APPROVAL_STATE
        ),
        "final_approval_label_consumed": False,
        "execution_token_consumed": False,
        "preflight_lock_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "execution_contract": {
            "maximum_record_count": 1,
            "operation": "INITIALIZE",
            "expected_record_version": 1,
            "expected_record_stage": (
                "DRAFT_GENERATED"
            ),
            "expected_review_status": (
                "UNREVIEWED"
            ),
            "dry_run_required_immediately_before_write": (
                True
            ),
            "candidate_revalidation_required_immediately_before_write": (
                True
            ),
            "database_sha256_revalidation_required": (
                True
            ),
            "approval_pack_digest_revalidation_required": (
                True
            ),
            "approval_token_digest_revalidation_required": (
                True
            ),
            "initialize_request_digest_revalidation_required": (
                True
            ),
            "token_and_lock_consumption_required": (
                True
            ),
            "second_execution_forbidden": True,
            "x_api_call_allowed": False,
            "x_post_allowed": False,
        },
        "failure_policy": {
            "fail_closed": True,
            "automatic_retry_allowed": False,
            "batch_continuation_allowed": False,
            "on_prewrite_validation_failure": (
                "STOP_NO_WRITE"
            ),
            "on_current_written_result_missing": (
                "STOP_AND_REQUIRE_HUMAN_RECOVERY"
            ),
            "on_result_written_token_unconsumed": (
                "STOP_AND_REQUIRE_HUMAN_RECOVERY"
            ),
            "on_token_consumed_lock_unconsumed": (
                "STOP_AND_REQUIRE_HUMAN_RECOVERY"
            ),
            "on_digest_mismatch": (
                "STOP_TAMPERING_SUSPECTED"
            ),
            "rollback_after_normal_current_write": (
                "NO_AUTOMATIC_DELETE"
            ),
            "manual_evidence_capture_required": True,
        },
        "recovery_classification": {
            "before_current_write": (
                "SAFE_ABORT"
            ),
            "after_current_before_result": (
                "PARTIAL_WRITE_HUMAN_REVIEW"
            ),
            "after_result_before_consumption": (
                "RECORDED_BUT_UNCONSUMED_HUMAN_REVIEW"
            ),
            "after_token_before_lock": (
                "INCONSISTENT_CONSUMPTION_HUMAN_REVIEW"
            ),
            "after_complete_consumption": (
                "COMMITTED"
            ),
        },
        "safety": {
            "database_read": True,
            "database_write": False,
            "workflow_write": False,
            "wordpress_write": False,
            "x_api_call": False,
            "x_post": False,
            "external_api_call": False,
            "normal_x_fb_storage_modified": False,
            "production_status": "NO_GO",
            "safety_state": (
                "DESIGN_ONLY_NO_EXECUTION"
            ),
        },
    }

    design_digest = canonical_digest(
        design_payload
    )

    design = {
        **design_payload,
        "final_gate_design_digest_sha256": (
            design_digest
        ),
    }

    design_path = (
        output_root / OUTPUT_FILENAME
    )
    result_path = (
        output_root / RESULT_FILENAME
    )

    atomic_write_json(
        design_path,
        design,
    )

    result = {
        "phase": "X-R11-FINAL-GATE-DESIGN",
        "status": (
            "PASS_FINAL_GATE_DESIGN_"
            "READY_NO_EXECUTION"
        ),
        "gate_state": FINAL_GATE_STATE,
        "database_scope": database_scope,
        "candidate_count": len(
            candidate_ids
        ),
        "approval_request_id": (
            approval_request_id_actual
        ),
        "feedback_id": feedback_id,
        "final_gate_design_path": str(
            design_path
        ),
        "final_gate_design_digest_sha256": (
            design_digest
        ),
        "required_final_approval_label": (
            FINAL_APPROVAL_LABEL
        ),
        "final_approval_state": (
            FINAL_APPROVAL_STATE
        ),
        "final_approval_label_consumed": False,
        "execution_token_consumed": False,
        "preflight_lock_consumed": False,
        "execution_allowed": False,
        "normal_x_fb_write_allowed": False,
        "candidate_revalidated": True,
        "approval_pack_verified": True,
        "preflight_lock_verified": True,
        "approval_token_verified": True,
        "initialize_request_verified": True,
        "target_paths_fixed": True,
        "current_record_written": False,
        "operation_result_written": False,
        "normal_x_fb_storage_modified": False,
        "source_database_sha256_before": (
            database_sha_before
        ),
        "source_database_sha256_after": (
            database_sha_after
        ),
        "source_database_unchanged": True,
        "database_read": True,
        "database_write": False,
        "workflow_write": False,
        "wordpress_write": False,
        "x_api_call": False,
        "x_post": False,
        "external_api_call": False,
        "production_status": "NO_GO",
        "safety_state": (
            "DESIGN_ONLY_NO_EXECUTION"
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
    parser.add_argument(
        "--approval-request-id",
    )
    parser.add_argument(
        "--approval-pack",
        type=Path,
    )
    parser.add_argument(
        "--preflight-lock",
        type=Path,
    )
    parser.add_argument(
        "--approval-token",
        type=Path,
    )
    parser.add_argument(
        "--initialize-request",
        type=Path,
    )
    parser.add_argument(
        "--database-scope",
        default="READ_ONLY_DATABASE",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = (
            run_x_r11_final_gate_design(
                source_database_path=(
                    args.source_db
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
                approval_request_id=(
                    args.approval_request_id
                ),
                approval_pack_path=(
                    args.approval_pack
                ),
                preflight_lock_path=(
                    args.preflight_lock
                ),
                approval_token_path=(
                    args.approval_token
                ),
                initialize_request_path=(
                    args.initialize_request
                ),
                database_scope=(
                    args.database_scope
                ),
            )
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": (
                        "X-R11-FINAL-GATE-DESIGN"
                    ),
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "execution_allowed": False,
                    "normal_x_fb_write_allowed": False,
                    "database_write": False,
                    "workflow_write": False,
                    "wordpress_write": False,
                    "x_api_call": False,
                    "x_post": False,
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
