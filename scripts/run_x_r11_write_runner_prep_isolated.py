from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))


from scripts.build_x_r9_preflight_approval_pack import (
    canonical_digest,
    json_storage_snapshot,
)
from scripts.issue_x_r10_one_shot_approval_token import (
    EXPECTED_LOCK_STATE,
    TOKEN_STATE,
)
from scripts.issue_x_r11_final_approval_certificate import (
    AUTHORIZED_NEXT_PHASE,
    CERTIFICATE_STATE,
    validate_approval_bundle,
    validate_final_gate_design,
    validate_final_gate_result,
)
from scripts.run_x_r11_prep_isolated_atomic_consume import (
    assert_isolated_run_root,
    atomic_write_bytes,
    atomic_write_json,
    copy_exact,
)
from scripts.run_x_r7_isolated_e2e_dry_run import (
    find_normal_x_fb_matches,
    prepare_isolated_x_fb_root,
    sha256_file,
)
from scripts.run_x_r8_isolated_x_fb_write import (
    load_json_object,
    run_feedback_manager,
    validate_execution_boundary,
)


ROOT = REPOSITORY_ROOT

CONSUMED_CERTIFICATE_STATE = (
    "CONSUMED_BY_X_R11_WRITE_RUNNER_PREP_ISOLATED"
)
CONSUMED_TOKEN_STATE = (
    "CONSUMED_BY_X_R11_WRITE_RUNNER_PREP_ISOLATED"
)
CONSUMED_LOCK_STATE = (
    "CONSUMED_BY_X_R11_WRITE_RUNNER_PREP_ISOLATED"
)

TRANSACTION_TYPE = (
    "X_R11_WRITE_RUNNER_PREP_ISOLATED_REHEARSAL"
)

ALLOWED_FAULTS = {
    None,
    "AFTER_X_FB_WRITE",
    "AFTER_CERTIFICATE_REPLACE",
    "AFTER_TOKEN_REPLACE",
    "AFTER_LOCK_REPLACE",
}


class XR11WriteRunnerPrepError(RuntimeError):
    """Raised when isolated final-write rehearsal fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise XR11WriteRunnerPrepError(message)


def inject_fault(
    fault_injection: str | None,
    checkpoint: str,
) -> None:
    if fault_injection == checkpoint:
        raise XR11WriteRunnerPrepError(
            f"FAULT_INJECTION:{checkpoint}"
        )


def validate_certificate(
    certificate: dict[str, Any],
    *,
    certificate_path: Path,
    final_gate_result_path: Path,
    final_gate_design_path: Path,
    design: dict[str, Any],
    design_digest: str,
    bundle: dict[str, Any],
) -> str:
    require(
        certificate.get("phase")
        == "X-R11-FINAL-APPROVAL-PROTOCOL",
        "final approval certificate phase is invalid",
    )

    # Reject certificate reuse by state before checking
    # secondary status fields. A consumed certificate changes
    # both status and state, but the one-shot state is the
    # primary execution boundary.
    require(
        certificate.get("certificate_state")
        == CERTIFICATE_STATE,
        (
            "final approval certificate state "
            "must be ISSUED_NOT_CONSUMED"
        ),
    )
    require(
        certificate.get("status")
        == (
            "FINAL_APPROVAL_CERTIFICATE_"
            "ISSUED_NO_EXECUTION"
        ),
        "final approval certificate status is invalid",
    )
    require(
        certificate.get("certificate_scope")
        == "ISOLATED_PROTOCOL_VALIDATION_ONLY",
        (
            "certificate scope must be "
            "ISOLATED_PROTOCOL_VALIDATION_ONLY"
        ),
    )
    require(
        certificate.get("database_scope")
        != "PRODUCTION_READ_ONLY",
        (
            "production-scoped certificate is "
            "forbidden in WRITE-RUNNER-PREP"
        ),
    )
    require(
        certificate.get("feedback_id")
        == design.get("feedback_id"),
        (
            "feedback_id mismatch between "
            "certificate and design"
        ),
    )
    require(
        certificate.get("approval_request_id")
        == design.get("approval_request_id"),
        (
            "approval_request_id mismatch between "
            "certificate and design"
        ),
    )
    require(
        certificate.get("execution_token_id")
        == bundle["execution_token_id"],
        (
            "execution token ID mismatch between "
            "certificate and approval bundle"
        ),
    )
    require(
        Path(
            str(certificate["final_gate_result_path"])
        ).resolve()
        == final_gate_result_path,
        (
            "certificate final-gate result path "
            "does not match supplied result"
        ),
    )
    require(
        Path(
            str(certificate["final_gate_design_path"])
        ).resolve()
        == final_gate_design_path,
        (
            "certificate final-gate design path "
            "does not match supplied design"
        ),
    )
    require(
        certificate.get(
            "final_gate_design_digest_sha256"
        )
        == design_digest,
        (
            "certificate final-gate design digest "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "approval_pack_digest_sha256"
        )
        == bundle["approval_pack_digest"],
        (
            "certificate approval-pack digest "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "approval_token_digest_sha256"
        )
        == bundle["approval_token_digest"],
        (
            "certificate approval-token digest "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "initialize_request_digest_sha256"
        )
        == bundle["initialize_request_digest"],
        (
            "certificate initialize-request digest "
            "does not match"
        ),
    )
    require(
        certificate.get(
            "final_approval_label_consumed"
        )
        is True,
        (
            "certificate must record consumed "
            "final approval label"
        ),
    )
    require(
        certificate.get("certificate_consumed")
        is False,
        "certificate must remain unconsumed",
    )
    require(
        certificate.get("execution_token_consumed")
        is False,
        "execution token must remain unconsumed",
    )
    require(
        certificate.get("preflight_lock_consumed")
        is False,
        "preflight lock must remain unconsumed",
    )
    require(
        certificate.get("execution_allowed")
        is False,
        (
            "certificate execution_allowed "
            "must remain false"
        ),
    )
    require(
        certificate.get(
            "normal_x_fb_write_allowed"
        )
        is False,
        (
            "certificate normal X-FB write "
            "must remain false"
        ),
    )
    require(
        certificate.get("authorized_next_phase")
        == AUTHORIZED_NEXT_PHASE,
        (
            "certificate is not authorized for "
            "WRITE-RUNNER-PREP"
        ),
    )
    require(
        certificate.get("production_execution")
        is False,
        (
            "certificate production_execution "
            "must be false"
        ),
    )
    require(
        certificate.get("production_status")
        == "NO_GO",
        (
            "certificate production_status "
            "must be NO_GO"
        ),
    )
    require(
        certificate.get("safety_state")
        == (
            "FINAL_APPROVAL_CERTIFICATE_"
            "ONLY_NO_EXECUTION"
        ),
        "certificate safety_state is invalid",
    )

    contract = certificate.get(
        "consumption_contract"
    )

    require(
        isinstance(contract, dict),
        "certificate consumption_contract is invalid",
    )

    for field_name in (
        "certificate_must_be_consumed_once",
        "execution_token_must_be_consumed_once",
        "preflight_lock_must_be_consumed_once",
        "all_consumption_must_share_transaction_id",
        "second_execution_forbidden",
    ):
        require(
            contract.get(field_name) is True,
            (
                "certificate consumption rule "
                f"must be true: {field_name}"
            ),
        )

    for field_name in (
        "automatic_retry_allowed",
        "normal_x_fb_write_in_this_phase",
        "x_api_call_allowed",
        "x_post_allowed",
    ):
        require(
            contract.get(field_name) is False,
            (
                "certificate consumption rule "
                f"must be false: {field_name}"
            ),
        )

    stored_digest = certificate.get(
        "final_approval_certificate_digest_sha256"
    )

    require(
        isinstance(stored_digest, str)
        and len(stored_digest) == 64,
        "final approval certificate digest is invalid",
    )

    payload = {
        key: value
        for key, value in certificate.items()
        if key
        != "final_approval_certificate_digest_sha256"
    }

    require(
        canonical_digest(payload)
        == stored_digest,
        (
            "final approval certificate tampering "
            "detected: digest mismatch"
        ),
    )

    require(
        certificate_path.is_file(),
        "final approval certificate is missing",
    )

    return stored_digest


def validate_token_and_lock(
    *,
    token: dict[str, Any],
    lock: dict[str, Any],
    certificate: dict[str, Any],
    design: dict[str, Any],
) -> None:
    require(
        token.get("token_state")
        == TOKEN_STATE,
        (
            "execution token state must be "
            "ISSUED_NOT_CONSUMED"
        ),
    )
    require(
        token.get("execution_token_consumed")
        is False,
        "execution token must remain unconsumed",
    )
    require(
        token.get("preflight_lock_consumed")
        is False,
        "execution token reports consumed lock",
    )
    require(
        token.get("execution_allowed")
        is False,
        (
            "execution token execution_allowed "
            "must remain false"
        ),
    )
    require(
        token.get("normal_x_fb_write_allowed")
        is False,
        (
            "execution token normal X-FB write "
            "must remain false"
        ),
    )
    require(
        token.get("token_id")
        == certificate.get("execution_token_id"),
        (
            "execution token ID does not match "
            "certificate"
        ),
    )
    require(
        token.get("feedback_id")
        == design.get("feedback_id"),
        (
            "execution token feedback_id "
            "does not match design"
        ),
    )

    require(
        lock.get("lock_state")
        == EXPECTED_LOCK_STATE,
        (
            "preflight lock state must be "
            "PREPARED_NOT_EXECUTABLE"
        ),
    )
    require(
        lock.get("consumed", False) is False,
        "preflight lock must remain unconsumed",
    )
    require(
        lock.get("execution_allowed")
        is False,
        (
            "preflight lock execution_allowed "
            "must remain false"
        ),
    )
    require(
        lock.get("normal_x_fb_write_allowed")
        is False,
        (
            "preflight lock normal X-FB write "
            "must remain false"
        ),
    )
    require(
        lock.get("feedback_id")
        == design.get("feedback_id"),
        (
            "preflight lock feedback_id "
            "does not match design"
        ),
    )


def with_consumed_digest(
    payload: dict[str, Any],
    digest_field: str,
) -> dict[str, Any]:
    return {
        **payload,
        digest_field: canonical_digest(payload),
    }


def build_consumed_certificate(
    certificate: dict[str, Any],
    *,
    transaction_id: str,
    consumed_at: str,
) -> dict[str, Any]:
    payload = dict(certificate)

    payload.pop(
        "final_approval_certificate_digest_sha256",
        None,
    )

    payload.update(
        {
            "status": (
                "FINAL_APPROVAL_CERTIFICATE_"
                "CONSUMED_ISOLATED_REHEARSAL"
            ),
            "certificate_state": (
                CONSUMED_CERTIFICATE_STATE
            ),
            "certificate_consumed": True,
            "execution_token_consumed": True,
            "preflight_lock_consumed": True,
            "execution_allowed": False,
            "normal_x_fb_write_allowed": False,
            "consumed_at": consumed_at,
            "consumed_by_phase": (
                "X-R11-WRITE-RUNNER-PREP"
            ),
            "consumption_scope": (
                "ISOLATED_X_FB_REHEARSAL_ONLY"
            ),
            "transaction_id": transaction_id,
            "production_execution": False,
            "production_status": "NO_GO",
            "safety_state": (
                "ISOLATED_WRITE_RUNNER_"
                "REHEARSAL_ONLY"
            ),
        }
    )

    return with_consumed_digest(
        payload,
        "consumed_certificate_digest_sha256",
    )


def build_consumed_token(
    token: dict[str, Any],
    *,
    transaction_id: str,
    consumed_at: str,
    certificate_id: str,
) -> dict[str, Any]:
    payload = dict(token)

    payload.pop(
        "execution_token_digest_sha256",
        None,
    )

    payload.update(
        {
            "token_state": CONSUMED_TOKEN_STATE,
            "certificate_consumed": True,
            "execution_token_consumed": True,
            "preflight_lock_consumed": True,
            "execution_allowed": False,
            "normal_x_fb_write_allowed": False,
            "consumed_at": consumed_at,
            "consumed_by_phase": (
                "X-R11-WRITE-RUNNER-PREP"
            ),
            "consumed_by_certificate_id": (
                certificate_id
            ),
            "consumption_scope": (
                "ISOLATED_X_FB_REHEARSAL_ONLY"
            ),
            "transaction_id": transaction_id,
            "production_status": "NO_GO",
            "safety_state": (
                "ISOLATED_WRITE_RUNNER_"
                "REHEARSAL_ONLY"
            ),
        }
    )

    return with_consumed_digest(
        payload,
        "consumed_token_digest_sha256",
    )


def build_consumed_lock(
    lock: dict[str, Any],
    *,
    transaction_id: str,
    consumed_at: str,
    certificate_id: str,
    token_id: str,
) -> dict[str, Any]:
    payload = dict(lock)

    payload.pop(
        "consumed_lock_digest_sha256",
        None,
    )

    payload.update(
        {
            "lock_state": CONSUMED_LOCK_STATE,
            "consumed": True,
            "approval_label_consumed": True,
            "certificate_consumed": True,
            "execution_token_consumed": True,
            "preflight_lock_consumed": True,
            "execution_allowed": False,
            "normal_x_fb_write_allowed": False,
            "consumed_at": consumed_at,
            "consumed_by_phase": (
                "X-R11-WRITE-RUNNER-PREP"
            ),
            "consumed_by_certificate_id": (
                certificate_id
            ),
            "consumed_by_token_id": token_id,
            "consumption_scope": (
                "ISOLATED_X_FB_REHEARSAL_ONLY"
            ),
            "transaction_id": transaction_id,
            "production_status": "NO_GO",
            "safety_state": (
                "ISOLATED_WRITE_RUNNER_"
                "REHEARSAL_ONLY"
            ),
        }
    )

    return with_consumed_digest(
        payload,
        "consumed_lock_digest_sha256",
    )


def run_x_r11_write_runner_prep(
    *,
    final_gate_result_path: Path,
    final_gate_design_path: Path,
    final_approval_certificate_path: Path,
    run_root: Path,
    evidence_path: Path,
    normal_x_fb_root: Path = ROOT,
    fault_injection: str | None = None,
) -> dict[str, Any]:
    require(
        fault_injection in ALLOWED_FAULTS,
        "unsupported fault injection value",
    )

    final_gate_result_path = (
        final_gate_result_path.resolve()
    )
    final_gate_design_path = (
        final_gate_design_path.resolve()
    )
    final_approval_certificate_path = (
        final_approval_certificate_path.resolve()
    )
    run_root = run_root.resolve()
    evidence_path = evidence_path.resolve()
    normal_x_fb_root = (
        normal_x_fb_root.resolve()
    )

    if run_root.exists():
        require(
            not any(run_root.iterdir()),
            f"run_root must be empty: {run_root}",
        )

    assert_isolated_run_root(
        run_root,
        normal_x_fb_root,
    )

    for path in (
        final_gate_result_path,
        final_gate_design_path,
        final_approval_certificate_path,
    ):
        require(
            path.is_file(),
            f"required artifact is missing: {path}",
        )

    result = load_json_object(
        final_gate_result_path
    )
    design = load_json_object(
        final_gate_design_path
    )

    design_digest = validate_final_gate_result(
        result,
        design_path=final_gate_design_path,
    )

    validate_final_gate_design(
        design,
        expected_digest=design_digest,
    )

    bundle = validate_approval_bundle(
        design
    )

    certificate = load_json_object(
        final_approval_certificate_path
    )

    certificate_digest = validate_certificate(
        certificate,
        certificate_path=(
            final_approval_certificate_path
        ),
        final_gate_result_path=(
            final_gate_result_path
        ),
        final_gate_design_path=(
            final_gate_design_path
        ),
        design=design,
        design_digest=design_digest,
        bundle=bundle,
    )

    source_database_path = Path(
        str(design["source_database_path"])
    ).resolve()

    require(
        source_database_path.is_file(),
        "source database is missing",
    )
    require(
        sha256_file(source_database_path)
        == certificate.get("source_database_sha256"),
        (
            "source database changed after "
            "final approval"
        ),
    )

    source_paths = {
        "final_gate_result": final_gate_result_path,
        "final_gate_design": final_gate_design_path,
        "final_approval_certificate": (
            final_approval_certificate_path
        ),
        "approval_pack": (
            bundle["approval_pack_path"]
        ),
        "preflight_lock": (
            bundle["preflight_lock_path"]
        ),
        "approval_token": (
            bundle["approval_token_path"]
        ),
        "initialize_request": (
            bundle["initialize_request_path"]
        ),
        "source_database": source_database_path,
    }

    source_hashes_before = {
        name: sha256_file(path)
        for name, path in source_paths.items()
    }

    lock = load_json_object(
        bundle["preflight_lock_path"]
    )
    token = load_json_object(
        bundle["approval_token_path"]
    )
    approval_pack = load_json_object(
        bundle["approval_pack_path"]
    )
    initialize_request = load_json_object(
        bundle["initialize_request_path"]
    )

    validate_token_and_lock(
        token=token,
        lock=lock,
        certificate=certificate,
        design=design,
    )

    feedback_id = str(
        design["feedback_id"]
    )
    approval_request_id = str(
        design["approval_request_id"]
    )

    require(
        approval_pack.get("feedback_id")
        == feedback_id,
        (
            "approval pack feedback_id "
            "does not match design"
        ),
    )
    require(
        initialize_request.get("feedback_id")
        == feedback_id,
        (
            "initialize request feedback_id "
            "does not match design"
        ),
    )

    normal_snapshot_before = (
        json_storage_snapshot(
            normal_x_fb_root
        )
    )

    normal_matches_before = (
        find_normal_x_fb_matches(
            repository_root=normal_x_fb_root,
            feedback_id=feedback_id,
        )
    )

    require(
        not normal_matches_before,
        (
            "normal X-FB already contains "
            f"target artifacts: {normal_matches_before}"
        ),
    )

    run_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    artifact_root = run_root / "artifacts"
    transaction_root = (
        run_root / "transaction"
    )
    backup_root = (
        transaction_root / "backup"
    )
    staged_root = (
        transaction_root / "staged"
    )
    isolated_x_fb_root = (
        run_root / "x_fb_root"
    )

    isolated_result_path = (
        artifact_root / "final_gate_result.json"
    )
    isolated_design_path = (
        artifact_root / "final_gate_design.json"
    )
    isolated_certificate_path = (
        artifact_root
        / "final_approval_certificate.json"
    )
    isolated_pack_path = (
        artifact_root / "approval_pack.json"
    )
    isolated_token_path = (
        artifact_root / "approval_token.json"
    )
    isolated_lock_path = (
        artifact_root / "preflight_lock.json"
    )
    isolated_request_path = (
        artifact_root / "initialize_request.json"
    )

    for source, destination in (
        (
            final_gate_result_path,
            isolated_result_path,
        ),
        (
            final_gate_design_path,
            isolated_design_path,
        ),
        (
            final_approval_certificate_path,
            isolated_certificate_path,
        ),
        (
            bundle["approval_pack_path"],
            isolated_pack_path,
        ),
        (
            bundle["approval_token_path"],
            isolated_token_path,
        ),
        (
            bundle["preflight_lock_path"],
            isolated_lock_path,
        ),
        (
            bundle["initialize_request_path"],
            isolated_request_path,
        ),
    ):
        copy_exact(
            source,
            destination,
        )

    prepare_isolated_x_fb_root(
        isolated_root=isolated_x_fb_root,
        repository_root=ROOT,
    )

    current_path = (
        isolated_x_fb_root
        / "exchange/input/x_post_feedback"
        / feedback_id
        / "current.json"
    )
    operation_result_path = (
        isolated_x_fb_root
        / "exchange/logs"
        / (
            f"x_fb_1_{feedback_id}_"
            "v001_result.json"
        )
    )
    archive_root = (
        isolated_x_fb_root
        / "exchange/archive/x_post_feedback"
        / feedback_id
    )

    require(
        not current_path.exists(),
        "isolated current.json already exists",
    )
    require(
        not operation_result_path.exists(),
        (
            "isolated operation result "
            "already exists"
        ),
    )

    (
        dry_run_rc,
        dry_run_result,
        _,
        dry_run_stderr,
    ) = run_feedback_manager(
        request_path=isolated_request_path,
        isolated_root=isolated_x_fb_root,
        dry_run=True,
    )

    require(
        dry_run_rc == 0,
        (
            "isolated manager dry-run failed: "
            f"{dry_run_stderr}"
        ),
    )
    require(
        dry_run_result.get("status")
        == "PASS_DRY_RUN_NO_WRITE",
        (
            "unexpected manager dry-run status"
        ),
    )
    require(
        not current_path.exists(),
        "manager dry-run created current.json",
    )
    require(
        not operation_result_path.exists(),
        (
            "manager dry-run created operation result"
        ),
    )

    transaction_id = (
        "xr11-write-prep-"
        + uuid.uuid4().hex
    )
    consumed_at = datetime.now(
        timezone.utc
    ).isoformat()

    consumed_certificate = (
        build_consumed_certificate(
            certificate,
            transaction_id=transaction_id,
            consumed_at=consumed_at,
        )
    )
    consumed_token = build_consumed_token(
        token,
        transaction_id=transaction_id,
        consumed_at=consumed_at,
        certificate_id=str(
            certificate["certificate_id"]
        ),
    )
    consumed_lock = build_consumed_lock(
        lock,
        transaction_id=transaction_id,
        consumed_at=consumed_at,
        certificate_id=str(
            certificate["certificate_id"]
        ),
        token_id=str(token["token_id"]),
    )

    backup_certificate_path = (
        backup_root
        / "final_approval_certificate.original.json"
    )
    backup_token_path = (
        backup_root / "approval_token.original.json"
    )
    backup_lock_path = (
        backup_root / "preflight_lock.original.json"
    )

    staged_certificate_path = (
        staged_root
        / "final_approval_certificate.consumed.json"
    )
    staged_token_path = (
        staged_root / "approval_token.consumed.json"
    )
    staged_lock_path = (
        staged_root / "preflight_lock.consumed.json"
    )

    backup_root.mkdir(
        parents=True,
        exist_ok=True,
    )
    staged_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    copy_exact(
        isolated_certificate_path,
        backup_certificate_path,
    )
    copy_exact(
        isolated_token_path,
        backup_token_path,
    )
    copy_exact(
        isolated_lock_path,
        backup_lock_path,
    )

    atomic_write_json(
        staged_certificate_path,
        consumed_certificate,
    )
    atomic_write_json(
        staged_token_path,
        consumed_token,
    )
    atomic_write_json(
        staged_lock_path,
        consumed_lock,
    )

    journal_path = (
        transaction_root / "journal.json"
    )
    rollback_path = (
        transaction_root / "rollback_result.json"
    )

    journal = {
        "phase": "X-R11-WRITE-RUNNER-PREP",
        "transaction_type": TRANSACTION_TYPE,
        "transaction_id": transaction_id,
        "state": "PREPARED",
        "feedback_id": feedback_id,
        "approval_request_id": (
            approval_request_id
        ),
        "certificate_id": (
            certificate["certificate_id"]
        ),
        "execution_token_id": token["token_id"],
        "certificate_scope": (
            certificate["certificate_scope"]
        ),
        "prepared_at": consumed_at,
        "fault_injection": fault_injection,
        "isolated_only": True,
        "normal_x_fb_write_allowed": False,
        "production_execution": False,
        "production_status": "NO_GO",
    }

    atomic_write_json(
        journal_path,
        journal,
    )

    transaction_started = True

    try:
        (
            write_rc,
            write_result,
            _,
            write_stderr,
        ) = run_feedback_manager(
            request_path=isolated_request_path,
            isolated_root=isolated_x_fb_root,
            dry_run=False,
        )

        require(
            write_rc == 0,
            (
                "isolated manager write failed: "
                f"{write_stderr}"
            ),
        )
        require(
            write_result.get("status")
            == "PASS_MANUAL_RECORD_OPERATION",
            (
                "unexpected isolated manager "
                "write status"
            ),
        )
        require(
            current_path.is_file(),
            (
                "isolated current.json "
                "was not created"
            ),
        )
        require(
            operation_result_path.is_file(),
            (
                "isolated operation result "
                "was not created"
            ),
        )

        current = load_json_object(
            current_path
        )
        operation_result = load_json_object(
            operation_result_path
        )

        require(
            current.get("feedback_id")
            == feedback_id,
            "isolated current feedback_id mismatch",
        )
        require(
            current.get("record_version") == 1,
            (
                "isolated record_version "
                "must be 1"
            ),
        )
        require(
            current.get("record_stage")
            == "DRAFT_GENERATED",
            (
                "isolated record_stage "
                "must be DRAFT_GENERATED"
            ),
        )
        require(
            current.get("review_status")
            == "UNREVIEWED",
            (
                "isolated review_status "
                "must be UNREVIEWED"
            ),
        )
        require(
            current.get(
                "text_snapshots",
                {},
            ).get("generated_text")
            == approval_pack.get("generated_text"),
            (
                "isolated generated text does "
                "not match approval pack"
            ),
        )
        require(
            operation_result.get("status")
            == "PASS_MANUAL_RECORD_OPERATION",
            (
                "stored operation-result status "
                "is invalid"
            ),
        )

        execution_boundary = current.get(
            "execution_boundary"
        )

        require(
            isinstance(execution_boundary, dict),
            "execution_boundary must be an object",
        )

        validate_execution_boundary(
            execution_boundary
        )

        inject_fault(
            fault_injection,
            "AFTER_X_FB_WRITE",
        )

        os.replace(
            staged_certificate_path,
            isolated_certificate_path,
        )

        inject_fault(
            fault_injection,
            "AFTER_CERTIFICATE_REPLACE",
        )

        os.replace(
            staged_token_path,
            isolated_token_path,
        )

        inject_fault(
            fault_injection,
            "AFTER_TOKEN_REPLACE",
        )

        os.replace(
            staged_lock_path,
            isolated_lock_path,
        )

        inject_fault(
            fault_injection,
            "AFTER_LOCK_REPLACE",
        )

        committed_at = datetime.now(
            timezone.utc
        ).isoformat()

        journal.update(
            {
                "state": "COMMITTED",
                "committed_at": committed_at,
                "isolated_current_record_written": (
                    True
                ),
                "isolated_operation_result_written": (
                    True
                ),
                "certificate_consumed": True,
                "execution_token_consumed": True,
                "preflight_lock_consumed": True,
            }
        )

        atomic_write_json(
            journal_path,
            journal,
        )

        consumed_certificate_actual = (
            load_json_object(
                isolated_certificate_path
            )
        )
        consumed_token_actual = (
            load_json_object(
                isolated_token_path
            )
        )
        consumed_lock_actual = (
            load_json_object(
                isolated_lock_path
            )
        )

        require(
            consumed_certificate_actual.get(
                "certificate_state"
            )
            == CONSUMED_CERTIFICATE_STATE,
            "consumed certificate state mismatch",
        )
        require(
            consumed_certificate_actual.get(
                "certificate_consumed"
            )
            is True,
            (
                "certificate was not "
                "marked consumed"
            ),
        )
        require(
            consumed_token_actual.get(
                "token_state"
            )
            == CONSUMED_TOKEN_STATE,
            "consumed token state mismatch",
        )
        require(
            consumed_token_actual.get(
                "execution_token_consumed"
            )
            is True,
            "execution token was not consumed",
        )
        require(
            consumed_lock_actual.get(
                "lock_state"
            )
            == CONSUMED_LOCK_STATE,
            "consumed lock state mismatch",
        )
        require(
            consumed_lock_actual.get("consumed")
            is True,
            "preflight lock was not consumed",
        )

        transaction_ids = {
            consumed_certificate_actual.get(
                "transaction_id"
            ),
            consumed_token_actual.get(
                "transaction_id"
            ),
            consumed_lock_actual.get(
                "transaction_id"
            ),
        }

        require(
            transaction_ids
            == {transaction_id},
            (
                "consumed artifacts do not share "
                "one transaction ID"
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
                "was modified"
            ),
        )

        normal_matches_after = (
            find_normal_x_fb_matches(
                repository_root=normal_x_fb_root,
                feedback_id=feedback_id,
            )
        )

        require(
            not normal_matches_after,
            (
                "normal X-FB contains rehearsal "
                f"artifacts: {normal_matches_after}"
            ),
        )

        source_hashes_after = {
            name: sha256_file(path)
            for name, path in source_paths.items()
        }

        require(
            source_hashes_before
            == source_hashes_after,
            (
                "source approval artifacts "
                "were modified"
            ),
        )

        result_payload = {
            "phase": "X-R11-WRITE-RUNNER-PREP",
            "status": (
                "PASS_ISOLATED_FINAL_WRITE_"
                "RUNNER_REHEARSAL"
            ),
            "transaction_id": transaction_id,
            "transaction_state": "COMMITTED",
            "run_root": str(run_root),
            "isolated_x_fb_root": str(
                isolated_x_fb_root
            ),
            "feedback_id": feedback_id,
            "approval_request_id": (
                approval_request_id
            ),
            "certificate_id": (
                certificate["certificate_id"]
            ),
            "execution_token_id": token["token_id"],
            "certificate_scope": (
                certificate["certificate_scope"]
            ),
            "final_gate_design_digest_sha256": (
                design_digest
            ),
            "final_approval_certificate_digest_sha256": (
                certificate_digest
            ),
            "manager_dry_run_status": (
                dry_run_result["status"]
            ),
            "manager_write_status": (
                write_result["status"]
            ),
            "isolated_current_record_path": str(
                current_path
            ),
            "isolated_operation_result_path": str(
                operation_result_path
            ),
            "consumed_certificate_path": str(
                isolated_certificate_path
            ),
            "consumed_token_path": str(
                isolated_token_path
            ),
            "consumed_lock_path": str(
                isolated_lock_path
            ),
            "transaction_journal_path": str(
                journal_path
            ),
            "isolated_current_record_written": True,
            "isolated_operation_result_written": True,
            "certificate_consumed": True,
            "execution_token_consumed": True,
            "preflight_lock_consumed": True,
            "shared_transaction_id_verified": True,
            "archive_created": (
                archive_root.exists()
                and any(
                    archive_root.glob("*.json")
                )
            ),
            "rollback_required": False,
            "source_artifacts_unchanged": True,
            "source_database_unchanged": True,
            "normal_x_fb_storage_modified": False,
            "normal_x_fb_write_allowed": False,
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
                "ISOLATED_WRITE_RUNNER_"
                "REHEARSAL_ONLY"
            ),
        }

        evidence_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        atomic_write_json(
            evidence_path,
            result_payload,
        )

        return result_payload

    except Exception as exc:
        rollback_errors: list[str] = []

        if transaction_started:
            for target, backup, label in (
                (
                    isolated_certificate_path,
                    backup_certificate_path,
                    "certificate",
                ),
                (
                    isolated_token_path,
                    backup_token_path,
                    "token",
                ),
                (
                    isolated_lock_path,
                    backup_lock_path,
                    "lock",
                ),
            ):
                try:
                    atomic_write_bytes(
                        target,
                        backup.read_bytes(),
                    )
                except Exception as restore_exc:
                    rollback_errors.append(
                        f"{label}_restore:{restore_exc}"
                    )

            for target, label in (
                (
                    current_path,
                    "current_cleanup",
                ),
                (
                    operation_result_path,
                    "result_cleanup",
                ),
            ):
                try:
                    target.unlink(missing_ok=True)
                except Exception as cleanup_exc:
                    rollback_errors.append(
                        f"{label}:{cleanup_exc}"
                    )

            try:
                if archive_root.exists():
                    shutil.rmtree(archive_root)
            except Exception as cleanup_exc:
                rollback_errors.append(
                    f"archive_cleanup:{cleanup_exc}"
                )

            staged_certificate_path.unlink(
                missing_ok=True
            )
            staged_token_path.unlink(
                missing_ok=True
            )
            staged_lock_path.unlink(
                missing_ok=True
            )

            restored_certificate = (
                load_json_object(
                    isolated_certificate_path
                )
            )
            restored_token = load_json_object(
                isolated_token_path
            )
            restored_lock = load_json_object(
                isolated_lock_path
            )

            rollback_result = {
                "phase": (
                    "X-R11-WRITE-RUNNER-PREP"
                ),
                "status": (
                    "ROLLBACK_COMPLETED"
                    if not rollback_errors
                    else "ROLLBACK_INCOMPLETE"
                ),
                "transaction_id": transaction_id,
                "transaction_state": (
                    "ROLLED_BACK"
                ),
                "error": str(exc),
                "rollback_errors": (
                    rollback_errors
                ),
                "isolated_current_record_exists": (
                    current_path.exists()
                ),
                "isolated_operation_result_exists": (
                    operation_result_path.exists()
                ),
                "certificate_restored": (
                    restored_certificate.get(
                        "certificate_state"
                    )
                    == CERTIFICATE_STATE
                ),
                "execution_token_restored": (
                    restored_token.get(
                        "token_state"
                    )
                    == TOKEN_STATE
                ),
                "preflight_lock_restored": (
                    restored_lock.get(
                        "lock_state"
                    )
                    == EXPECTED_LOCK_STATE
                ),
                "normal_x_fb_write_allowed": False,
                "production_execution": False,
                "production_status": "NO_GO",
            }

            atomic_write_json(
                rollback_path,
                rollback_result,
            )

            journal.update(
                {
                    "state": "ROLLED_BACK",
                    "rolled_back_at": (
                        datetime.now(
                            timezone.utc
                        ).isoformat()
                    ),
                    "error": str(exc),
                    "rollback_errors": (
                        rollback_errors
                    ),
                }
            )

            atomic_write_json(
                journal_path,
                journal,
            )

        if rollback_errors:
            raise XR11WriteRunnerPrepError(
                f"{exc}; rollback errors="
                f"{rollback_errors}"
            ) from exc

        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--final-gate-result",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--final-gate-design",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--final-approval-certificate",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--run-root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--evidence-path",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--normal-x-fb-root",
        type=Path,
        default=ROOT,
    )
    parser.add_argument(
        "--fault-injection",
        choices=sorted(
            value
            for value in ALLOWED_FAULTS
            if value is not None
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        result = run_x_r11_write_runner_prep(
            final_gate_result_path=(
                args.final_gate_result
            ),
            final_gate_design_path=(
                args.final_gate_design
            ),
            final_approval_certificate_path=(
                args.final_approval_certificate
            ),
            run_root=args.run_root,
            evidence_path=args.evidence_path,
            normal_x_fb_root=(
                args.normal_x_fb_root
            ),
            fault_injection=(
                args.fault_injection
            ),
        )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "phase": (
                        "X-R11-WRITE-RUNNER-PREP"
                    ),
                    "status": "FAIL_VALIDATION",
                    "error": str(exc),
                    "certificate_consumed": False,
                    "execution_token_consumed": False,
                    "preflight_lock_consumed": False,
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
